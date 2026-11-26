import json
import logging
import uuid

from django.conf import settings as djangosettings
from django.utils.translation import gettext_lazy as _
from prodict import Prodict
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.apis.permissions import IsAdminOrNotReadOnly, ModelPermissionsExtra
from core.apis.serializers import DatasourceSerializer
from core.apis.viewsets import DevExtremeModelViewSet
from core.models import Datasource
from core.utils import parse, create

logger = logging.getLogger(__name__)


class DatasourceViewSet(DevExtremeModelViewSet, ):
    permission_classes = [IsAdminOrNotReadOnly, ModelPermissionsExtra, ]
    extra_permissions = {}
    serializer_class = DatasourceSerializer
    queryset = Datasource.objects.all()

    def get_queryset(self):
        if hasattr(Datasource, 'all_objects') and self.request.META.get('HTTP_SOFTDELETED', 'false').lower() in ('true', 'yes', 'on',):
            return Datasource.all_objects.all()
        return self.queryset

    @action(
        detail=False,
        url_path='exists',
        url_name='exists',
        methods=['post'],
        permission_classes=[IsAuthenticated, ],
    )
    def exists(self, request, ):
        if ('datasource_id' in request.data):
            return Response(
                Datasource.objects
                .filter(**request.query_params.dict())
                .exclude(pk=request.data['datasource_id'])
                .exists(),
                status=status.HTTP_200_OK, )
        else:
            return Response(
                Datasource.objects
                .filter(**request.query_params.dict())
                .exists(),
                status=status.HTTP_200_OK, )

    @action(
        detail=False,
        url_path='delete',
        url_name='delete',
        methods=['post'],
        permission_classes=[IsAdminOrNotReadOnly, ModelPermissionsExtra, ],
        extra_permissions={
            'POST': ('any', ['delete_datasource', ]),
        },
    )
    def delete(self, request, *args, **kwargs):
        data = request.data.dict()
        values = json.loads(data['key'])
        if isinstance(values, list, ):
            datasources = Datasource.objects.filter(pk__in=[datasource['datasource_id'] for datasource in values])
            for datasource in datasources:
                datasource.delete()
            return Response(dict(
                message=_('Datasource data %(count)s have been successfully deleted') % dict(count=datasources.count()),
            ), status=status.HTTP_200_OK, )
        else:
            datasource = Datasource.objects.get(pk=values['datasource_id'])
            datasource.delete()
        return Response(dict(
            message=_('Datasource %(datasource_name)s have been successfully deleted') % dict(datasource_name=datasource.datasource_name),
        ), status=status.HTTP_200_OK, )

    @action(
        detail=False,
        url_path='undelete',
        url_name='undelete',
        methods=['post'],
        permission_classes=[IsAdminOrNotReadOnly, ModelPermissionsExtra, ],
        extra_permissions={
            'POST': ('any', ['undelete_datasource', ]),
        },
    )
    def undelete(self, request, *args, **kwargs):
        data = request.data.dict()
        values = json.loads(data['key'])
        if isinstance(values, list, ):
            datasources = Datasource.all_objects.filter(pk__in=[datasource['datasource_id'] for datasource in values])
            for datasource in datasources:
                datasource.is_removed = False
                datasource.save(update_fields=['is_removed', ])
            return Response(dict(
                message=_('Datasource data %(count)s have been successfully undeleted') % dict(count=datasources.count()),
            ), status=status.HTTP_200_OK, )
        else:
            datasource = Datasource.all_objects.get(pk=values['datasource_id'])
            datasource.is_removed = False
            datasource.save(update_fields=['is_removed', ])
        return Response(dict(
            message=_('Datasource %(datasource_name)s have been successfully undeleted') % dict(datasource_name=datasource.datasource_name),
        ), status=status.HTTP_200_OK, )

    @action(
        detail=False,
        url_path='test',
        url_name='test',
        methods=['post'],
        permission_classes=[IsAdminOrNotReadOnly, ModelPermissionsExtra, ],
    )
    def test(self, request, *args, **kwargs):
        data = request.data.dict()
        data['properties'] = json.loads(data['properties']) if 'properties' in data else {}
        data = Prodict.from_dict(data)
        if 'datasource_id' not in data:
            data.datasource_id = str(uuid.uuid4())
        value = dict(
            NAME=data.database,
            **data.properties,
        )
        if 'database' in data:
            value['NAME'] = data.database
        if 'engine' in data:
            value['ENGINE'] = data.engine
        if 'user' in data:
            value['USER'] = data.user
        if 'password' in data:
            value['PASSWORD'] = data.password
        if 'host' in data:
            value['HOST'] = data.host
        if 'port' in data:
            value['PORT'] = data.port
        if 'url' in data:
            value = dict(
                **parse(url=data.url),
                **data.properties,
            )
        djangosettings.DATABASES[data.datasource_id] = value
        connection = create(data.datasource_id)
        connection.cursor()
        connection.close()
        del djangosettings.DATABASES[data.datasource_id]
        return Response(dict(
            datasource=data,
            message=_('Datasource %(datasource_name)s have been successfully connected') % data,
        ), status=status.HTTP_200_OK, )
