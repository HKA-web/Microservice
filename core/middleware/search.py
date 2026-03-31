import logging

from django.core.exceptions import ImproperlyConfigured

try:
    from django.utils.deprecation import MiddlewareMixin

    cls = MiddlewareMixin
except ImportError:
    cls = object

from core.utils.search import search_context_manager

logger = logging.getLogger(__name__)

SEARCH_MIDDLEWARE_FLAG = 'core.search.search_context_middleware_active'


class SearchContextMiddleware(cls):
    def process_request(self, request):
        if request.META.get(SEARCH_MIDDLEWARE_FLAG, False):
            raise ImproperlyConfigured('SearchContextMiddleware can only be included in MIDDLEWARE_CLASSES once.')
        request.META[SEARCH_MIDDLEWARE_FLAG] = True
        search_context_manager.start()

    def _close_search_context(self, request):
        if request.META.get(SEARCH_MIDDLEWARE_FLAG, False):
            del request.META[SEARCH_MIDDLEWARE_FLAG]
            search_context_manager.end()

    def process_response(self, request, response):
        self._close_search_context(request)
        return response

    def process_exception(self, request, exception):
        search_context_manager.invalidate()
        self._close_search_context(request)
