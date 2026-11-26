import json
import logging

from django.http import QueryDict
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.permissions import (
    DjangoModelPermissions,
    BasePermission,
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    SAFE_METHODS as SafeMethods
)

logger = logging.getLogger(__name__)


class ModelPermissions(DjangoModelPermissions):
    def __init__(self):
        self.perms_map['GET'] = ['%(app_label)s.view_%(model_name)s', ]


class ModelPermissionsExtra(ModelPermissions):
    # Example
    # 'GET': ('any', ['lookup_model', ]),
    # 'GET': ['lookup_model', 'approve_model', ],
    # 'POST': ['delete_model', ],
    def __init__(self):
        super().__init__()

    def get_extra_permissions(self, method, view, models):
        if not hasattr(view, 'extra_permissions'):
            logger.error('Attribute extra_permissions is required')
            return False, []
        if 'GET' not in view.extra_permissions:
            view.extra_permissions.update(GET=('any', [f'lookup_{models._meta.model_name}', ]))
        extra_permissions = view.extra_permissions.get(method, [])
        if isinstance(extra_permissions, tuple):
            anys, extra_permissions = view.extra_permissions.get(method, [])
            return anys.lower() in ['any', ], [f'{models._meta.app_label}.{permission}' for permission in extra_permissions]
        return False, [f'{models._meta.app_label}.{permission}' for permission in extra_permissions]

    def has_permission(self, request, view):
        if getattr(view, '_ignore_model_permissions', False):
            return True

        if not request.user or (not request.user.is_authenticated and self.authenticated_users_only):
            return False

        queryset = self._queryset(view)
        permissions = self.get_required_permissions(request.method, queryset.model)
        anys, extra_permissions = self.get_extra_permissions(request.method, view, queryset.model)
        permissions.extend(extra_permissions)
        if anys:
            required = request.user.has_anyperms(permissions)
            if not required:
                logger.warning(f'{request.method}: {request.path} required any permissions {permissions}')
            else:
                logger.debug(f'{request.method}: {request.path} granted any permissions {permissions}')
            return required
        else:
            required = request.user.has_perms(permissions)
            if not required:
                logger.warning(f'{request.method}: {request.path} required permissions {permissions}')
            else:
                logger.debug(f'{request.method}: {request.path} granted permissions {permissions}')
            return required


class IsAdminOrNotReadOnly(IsAuthenticated, ModelPermissions, ):
    def has_permission(self, request, view):
        if bool(request.user.is_authenticated and not request.user.is_superuser and request.user.read_only and request.method not in SafeMethods):
            raise exceptions.MethodNotAllowed(request.method, _('Method %(method)s not allowed for readonly user.') % dict(method=request.method))
        if bool(request.user.is_authenticated and not request.user.is_superuser and request.method not in SafeMethods):
            queryset = self._queryset(view)
            model = queryset.model
            data = request.data.dict() if isinstance(request.data, QueryDict) else request.data
            if 'kwargs' in request.parser_context and model._meta.pk.name in request.parser_context['kwargs']:
                data.update(dict(pk=[request.parser_context['kwargs'][model._meta.pk.name]]))
            elif 'kwargs' in request.parser_context and 'pk' in request.parser_context['kwargs']:
                data.update(dict(pk=[request.parser_context['kwargs']['pk']]))
            elif model._meta.pk.name in data:
                data.update(dict(pk=[data[model._meta.pk.name]]))
            elif 'key' in data:
                try:
                    key = data['key']
                    if isinstance(data['key'], str):
                        key = json.loads(data['key'])
                    if isinstance(key, list) and len(key) > 0 and isinstance(key[0], dict):
                        key = [key[model._meta.pk.name] for key in key]
                    data.update(dict(pk=key if isinstance(key, list) else [key]))
                except:
                    data.update(dict(pk=[data['key']]))
            if 'pk' in data and hasattr(model, 'read_only'):
                for current in model.objects.filter(pk__in=[pk for pk in data['pk']]):
                    if not bool(current.read_only):
                        continue
                    else:
                        raise exceptions.MethodNotAllowed(request.method, _('Method %(method)s not allowed for readonly data.') % dict(method=request.method))
        return True


'''
class ViewSet(viewsets.ModelViewSet):
    queryset = Model.objects.all()
    serializer_class = ModelSerializer
    permission_classes = (NotCreateAndIsAdminUser, CreateAndIsAuthenticated, NotSafeMethodAndAllowAny)
    def create(self, request):
        pass
    def list(self, request):
        pass
'''


class NotCreateAndIsAdminUser(IsAdminUser):
    def has_permission(self, request, view):
        return (view.action in [
            'update',
            'partial_update',
            'destroy',
            'list'
        ] and super(NotCreateAndIsAdminUser, self).has_permission(request, view))


class CreateAndIsAuthenticated(IsAuthenticated):
    def has_permission(self, request, view):
        return (view.action in [
            'create'
        ] and super(CreateAndIsAuthenticated, self).has_permission(request, view))


class NotSafeMethodAndAllowAny(AllowAny):
    def has_permission(self, request, view):
        return (view.action not in [
            'update',
            'partial_update',
            'destroy',
            'list',
            'create'
        ] and super(NotSafeMethodAndAllowAny, self).has_permission(request, view))


class IsAdminOrIsSelf(BasePermission):
    def has_object_permission(self, request, view, object):
        return request.user.is_superuser or object == request.user


class IsAdminOrEditable(BasePermission):
    def has_object_permission(self, request, view, object):
        return request.user.is_superuser or not object.read_only
