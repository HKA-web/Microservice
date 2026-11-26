import logging

import django
from django.contrib.sites.models import Site
from django.core import signals
from django.template.defaultfilters import slugify
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


def get_cache_backend():
    if django.VERSION[0] >= 3:
        from django.core.cache import caches
        cache = caches.create_connection(getattr(djangosettings, 'TEMPLATES_CACHE_BACKEND', 'default'))
    else:
        from django.core.cache import _create_cache
        cache = _create_cache(getattr(djangosettings, 'TEMPLATES_CACHE_BACKEND', 'default'))
    signals.request_finished.connect(cache.close)
    return cache


cache = get_cache_backend()


def get_cache_key(name):
    current_site = Site.objects.get_current()
    return 'templates::%s::%s' % (slugify(name), current_site.pk)


def get_cache_notfound_key(name):
    return get_cache_key(name) + '::notfound'


def remove_notfound_key(instance):
    cache.delete(get_cache_notfound_key(instance.template_name))


def set_and_return(cache_key, content, display_name):
    if cache:
        cache.set(cache_key, content)
    return (content, display_name)


def add_template_to_cache(instance, **kwargs):
    remove_cached_template(instance)
    remove_notfound_key(instance)
    cache.set(get_cache_key(instance.template_name), instance.content)


def remove_cached_template(instance, **kwargs):
    cache.delete(get_cache_key(instance.template_name))
