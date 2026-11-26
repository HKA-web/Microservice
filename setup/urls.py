import logging
import sys
from importlib import import_module

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import path, include, re_path, register_converter, URLResolver
from django.views.decorators.cache import cache_page
from django.views.i18n import JavaScriptCatalog, JSONCatalog
from django.views.static import serve

import library.jsreverse.views as reverse
from core import views
from core.models.base import Base64PkConverter
from core.utils import ShortUUID

logger = logging.getLogger(__name__)
register_converter(Base64PkConverter, Base64PkConverter.name)
key = ShortUUID().random(length=10)


def urlpatterns():
    patterns = [
        path('core/', include('core.urls')),
        path('', views.IndexView.as_view(), name='index'),
    ]
    if settings.CACHEOPS_ENABLED and False:
        patterns += [
            path('i18n.js', cache_page(86400, key_prefix='i18n.js?_dc=%s' % key)(JavaScriptCatalog.as_view()), name='i18n-js'),
            path('i18n.json', cache_page(86400, key_prefix='i18n.json?_dc=%s' % key)(JSONCatalog.as_view()), name='i18n-json'),
            path('reverse.js', cache_page(86400, key_prefix='reverse.js?_dc=%s' % key)(reverse.urls_js), name='reverse-js'),
            path('reverse.json', cache_page(86400, key_prefix='reverse.json?_dc=%s' % key)(reverse.urls_json), name='reverse-json'),
        ]
    else:
        patterns += [
            path('i18n.js', JavaScriptCatalog.as_view(), name='i18n-js'),
            path('i18n.json', JSONCatalog.as_view(), name='i18n-json'),
            path('reverse.js', reverse.urls_js, name='reverse-js'),
            path('reverse.json', reverse.urls_json, name='reverse-json'),
        ]
    if settings.DEBUG:
        patterns += [
            re_path(r'^media/(?P<path>.*)$', serve, dict(document_root=settings.MEDIA_ROOT, show_indexes=True, )),
        ]
        if 'rosetta' in settings.INSTALLED_APPS:
            patterns += [
                re_path(r'^locale/', include('rosetta.urls'), name='rosetta')
            ]
    else:
        patterns += [
            re_path(r'^media/(?P<path>.*)$', serve, dict(document_root=settings.MEDIA_ROOT, )),
        ]
    logger.debug('Modules %s', settings.INSTALLED_MODULE)
    for application in [application for application in settings.INSTALLED_MODULE if application not in [pattern.namespace for pattern in patterns if isinstance(pattern, URLResolver)]]:
        try:
            urls = import_module('%s.urls' % (application,))
            logger.debug('Application %s', application)
            if hasattr(urls, 'urlpatterns'):
                patterns.append(path('%s/' % (urls.app_name or application,), include('%s.urls' % (urls.app_name or application,)), name=urls.app_name or application))
                logger.debug('Auto urls %s.urls append', application)
            else:
                logger.debug('Auto urls %s.urls not contains urlpatterns', application)
        except Exception as e:
            logger.info(e)
    return patterns


urlpatterns = urlpatterns()
module = sys.modules[__name__]
setattr(module, 'handler400', views.BadRequest)
setattr(module, 'handler403', views.PermissionDenied)
setattr(module, 'handler404', views.PageNotFound)
setattr(module, 'handler500', views.ServerError)
if sys.stdin and sys.stdin.isatty():
    pass
else:
    pass