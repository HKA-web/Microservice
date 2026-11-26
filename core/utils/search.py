import json
import logging
import sys
from itertools import chain, islice
from threading import local
from functools import wraps
from weakref import WeakValueDictionary

from django.core.signals import request_finished
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import models, connections, router
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.db.models.functions import Cast
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, pre_delete
from django.utils.encoding import force_str
from django.utils.html import strip_tags
from django.core.serializers.json import DjangoJSONEncoder
from importlib import import_module
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


class SearchAdapterError(Exception):
    pass


class SearchAdapter(object):
    fields = ()
    exclude = ()
    store = ()

    def __init__(self, model):
        self.model = model

    def _resolve_field(self, obj, name):
        name_parts = name.split('__', 1)
        prefix = name_parts[0]
        if obj is None:
            return ''
        try:
            value = getattr(obj, prefix)
        except ObjectDoesNotExist:
            return ''
        except AttributeError:
            try:
                value = getattr(self, prefix)
            except AttributeError:
                raise SearchAdapterError(
                    'Could not find a property called {name!r}'
                    ' on either {obj!r} or {search_adapter!r}'.format(
                        name=prefix,
                        obj=obj,
                        search_adapter=self,
                    )
                )
            else:
                if not isinstance(value, (QuerySet, models.Manager)):
                    if callable(value):
                        value = value(obj)
        else:
            if not isinstance(value, (QuerySet, models.Manager)):
                if callable(value):
                    value = value()
        if len(name_parts) == 2:
            if isinstance(value, (QuerySet, models.Manager)):
                return ' '.join(force_str(self._resolve_field(obj, name_parts[1])) for obj in value.all())
            return self._resolve_field(value, name_parts[1])
        if isinstance(value, (QuerySet, models.Manager)):
            value = ' '.join(force_str(related) for related in value.all())
        return value

    def prepare_content(self, content):
        content = strip_tags(content)
        return content

    def get_title(self, obj):
        return force_str(obj)[:1000]

    def get_description(self, obj):
        return ''

    def get_content(self, obj):
        field_names = self.fields or (
            field.name for field in self.model._meta.fields if
            isinstance(field, (models.CharField, models.TextField))
        )
        field_names = (field_name for field_name in field_names if field_name not in self.exclude)
        return self.prepare_content(' '.join(
            force_str(self._resolve_field(obj, field_name))
            for field_name in field_names
        ))

    def get_url(self, obj):
        from django.urls import NoReverseMatch
        if hasattr(obj, 'get_absolute_url'):
            try:
                return obj.get_absolute_url()
            except NoReverseMatch as e:
                return ''
        return ''

    def get_meta(self, obj):
        return dict(
            (field_name, self._resolve_field(obj, field_name))
            for field_name in self.store
        )

    def serialize_meta(self, obj):
        meta_obj = self.get_meta(obj)
        return json.dumps(meta_obj, cls=DjangoJSONEncoder)

    def deserialize_meta(self, meta_encoded):
        return json.loads(meta_encoded)

    def get_live_queryset(self):
        return None


class SearchEngineError(Exception):
    pass


class RegistrationError(SearchEngineError):
    pass


class SearchContextError(Exception):
    pass


class SearchContextManager(local):
    def __init__(self):
        self._stack = []
        request_finished.connect(self._request_finished_receiver)

    def is_active(self):
        return bool(self._stack)

    def _assert_active(self):
        if not self.is_active():
            raise SearchContextError('The search context is not active.')

    def start(self):
        self._stack.append((set(), False))

    def add_to_context(self, engine, obj):
        self._assert_active()
        objects, _ = self._stack[-1]
        objects.add((engine, obj))

    def invalidate(self):
        self._assert_active()
        objects, _ = self._stack[-1]
        self._stack[-1] = (objects, True)

    def is_invalid(self):
        self._assert_active()
        _, is_invalid = self._stack[-1]
        return is_invalid


    def update_index(self):
        return SearchContext(self)

    def skip_index_update(self):
        return SkipSearchContext(self)

    def _request_finished_receiver(self, **kwargs):
        while self.is_active():
            self.end()


class SearchContext(object):
    def __init__(self, context_manager):
        self._context_manager = context_manager

    def __enter__(self):
        self._context_manager.start()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is not None:
                self._context_manager.invalidate()
        finally:
            self._context_manager.end()

    def __call__(self, func):
        @wraps(func)
        def do_search_context(*args, **kwargs):
            self.__enter__()
            exception = False
            try:
                return func(*args, **kwargs)
            except Exception:
                exception = True
                if not self.__exit__(*sys.exc_info()):
                    raise
            finally:
                if not exception:
                    self.__exit__(None, None, None)

        return do_search_context


class SkipSearchContext(SearchContext):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self._context_manager.invalidate()
        finally:
            self._context_manager.end()


search_context_manager = SearchContextManager()


class SearchEngine(object):
    _created_engines = WeakValueDictionary()

    @classmethod
    def get_created_engines(cls):
        return list(cls._created_engines.items())

    def __init__(self, engine_slug, search_context_manager=search_context_manager):
        if engine_slug in SearchEngine._created_engines:
            raise SearchEngineError(
                'A search engine has already been created with the slug {engine_slug!r}'.format(
                    engine_slug=engine_slug,
                )
            )
        self._registered_models = {}
        self._engine_slug = engine_slug
        self._search_context_manager = search_context_manager
        self.__class__._created_engines[engine_slug] = self

    def is_registered(self, model):
        return model in self._registered_models

    def register(self, model, adapter_cls=SearchAdapter, **field_overrides):
        if isinstance(model, QuerySet):
            live_queryset = model
            model = model.model
            field_overrides['get_live_queryset'] = lambda self_: live_queryset.all()
        if self.is_registered(model):
            raise RegistrationError(
                '{model!r} is already registered with this search engine'.format(
                    model=model,
                ))
        if field_overrides:
            adapter_cls = type(
                str('Custom') + adapter_cls.__name__, (adapter_cls,), field_overrides
            )
        adapter_obj = adapter_cls(model)
        self._registered_models[model] = adapter_obj
        post_save.connect(self._post_save_receiver, model)
        pre_delete.connect(self._pre_delete_receiver, model)
        if model._meta.proxy_for_model is not None and not self.is_registered(model._meta.proxy_for_model):
            self.register(model._meta.proxy_for_model, adapter_cls, **field_overrides)

    def unregister(self, model):
        if isinstance(model, QuerySet):
            model = model.model
        if not self.is_registered(model):
            raise RegistrationError('{model!r} is not registered with this search engine'.format(
                model=model,
            ))
        del self._registered_models[model]
        post_save.disconnect(self._post_save_receiver, model)
        pre_delete.disconnect(self._pre_delete_receiver, model)

    def get_registered_models(self):
        return list(self._registered_models.keys())

    def get_adapter(self, model):
        if self.is_registered(model):
            return self._registered_models[model]
        raise RegistrationError('{model!r} is not registered with this search engine'.format(
            model=model,
        ))


    def cleanup_model_index(self, model):
        search_entries = self._get_deleted_entries_for_model(model)
        search_entries.delete()


    def _post_save_receiver(self, instance, **kwargs):
        if self._search_context_manager.is_active():
            self._search_context_manager.add_to_context(self, instance)
        else:
            self.update_obj_index(instance)

    def _pre_delete_receiver(self, instance, **kwargs):
        _, search_entries = self._get_entries_for_obj(instance)
        search_entries.delete()


    def _get_included_models(self, models):
        for model in models or self.get_registered_models():
            if isinstance(model, QuerySet):
                yield model
            else:
                adaptor = self.get_adapter(model)
                queryset = adaptor.get_live_queryset()
                if queryset is None:
                    yield model
                else:
                    yield queryset.all()

    def filter(self, queryset, search_text, ranking=True, backend_name=None):
        if isinstance(queryset, type) and issubclass(queryset, models.Model):
            queryset = queryset._default_manager.all()
        search_text = search_text.strip()
        if not search_text:
            return queryset
        backend = get_backend(backend_name=backend_name)
        queryset = backend.do_filter(self._engine_slug, queryset, search_text)
        if ranking:
            queryset = backend.do_filter_ranking(self._engine_slug, queryset, search_text)
        return queryset


default_search_engine = SearchEngine('default')
_backends_cache = {}


def get_backend(backend_name=None):
    global _backends_cache
    if not backend_name:
        backend_name = getattr(djangosettings, 'SEARCH_BACKEND', 'core.backends.AdaptiveSearchBackend')
    if backend_name in _backends_cache:
        return _backends_cache[backend_name]
    backend_module_name, backend_cls_name = backend_name.rsplit('.', 1)
    backend_module = import_module(backend_module_name)
    try:
        backend_cls = getattr(backend_module, backend_cls_name)
    except AttributeError:
        raise ImproperlyConfigured(
            'Could not find a class named {backend_module_name!r} in {backend_cls_name!r}'.format(
                backend_module_name=backend_module_name,
                backend_cls_name=backend_cls_name,
            ))
    backend = backend_cls()
    _backends_cache[backend_name] = backend
    return backend


filter = default_search_engine.filter

register = default_search_engine.register
unregister = default_search_engine.unregister
is_registered = default_search_engine.is_registered
get_registered_models = default_search_engine.get_registered_models
get_adapter = default_search_engine.get_adapter

update_index = search_context_manager.update_index
skip_index_update = search_context_manager.skip_index_update

if any(item in [
    'migrate',
    'makemigrations',
    'showmigrations',
    'makemessages',
    'compilemessages',
    'makelocale',
    'compilelocale',
] for item in sys.argv):
    def empty(*args, **kwargs):
        pass
    register = empty
pass
