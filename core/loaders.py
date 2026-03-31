import logging

from django.contrib.sites.models import Site
from django.conf import settings as djangosettings
from django.db import router
from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader

from core.utils.cache import (
    cache,
    get_cache_key,
    set_and_return,
    get_cache_notfound_key,
)

logger = logging.getLogger(__name__)


class DatabaseLoader(BaseLoader):
    is_usable = True
    def __init__(self, engine, dirs=None):
        super().__init__(engine)

    def get_template_sources(self, template_name, template_dirs=None):
        yield Origin(
            name=template_name,
            template_name=template_name,
            loader=self,
        )

    def get_contents(self, origin):
        content, _ = self._load_template_source(origin.template_name)
        return content

    def _load_template_source(self, template_name, template_dirs=None):
        site = Site.objects.get_current()
        cache_key = get_cache_key(template_name)
        if not djangosettings.DEBUG and cache:
            try:
                backend_template = cache.get(cache_key)
                if backend_template:
                    logger.debug('Load template %s from cache', template_name)
                    return backend_template, template_name
            except Exception as e:
                pass
        cache_notfound_key = get_cache_notfound_key(template_name)
        if not djangosettings.DEBUG and cache:
            try:
                notfound = cache.get(cache_notfound_key)
                if notfound:
                    raise TemplateDoesNotExist(template_name)
            except Exception as e:
                raise TemplateDoesNotExist(template_name)

        if not djangosettings.DEBUG and cache:
            cache.set(cache_notfound_key, '1')
        raise TemplateDoesNotExist(template_name)