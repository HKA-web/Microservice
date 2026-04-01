import logging
from importlib import import_module

from django.conf import settings

logger = logging.getLogger(__name__)


def websocket_urlpatterns():
    urlpatterns = []
    for application in settings.INSTALLED_MODULE:
        try:
            routings = import_module('%s.routings' % (application,))
            if hasattr(routings, 'websocket_urlpatterns') and isinstance(routings.websocket_urlpatterns, list) and len(routings.websocket_urlpatterns) > 0:
                urlpatterns += getattr(routings, 'websocket_urlpatterns')
                logger.debug('Auto routings %s append', routings.__name__)
            else:
                logger.debug('Auto routings %s not contains websocket_urlpatterns or websocket_urlpatterns not list or websocket_urlpatterns empty', routings.__name__)
        except Exception as e:
            logger.info(e)
    return urlpatterns
