import logging

from django.http import QueryDict
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class PostTunnelingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        meta = dict((key.lower(), value) for key, value in request.META.items())
        if 'http_methodoverride' in meta:
            method = meta['http_methodoverride']
            if method.lower() == 'put':
                request.method = 'PUT'
                request.META['REQUEST_METHOD'] = 'PUT'
                request.PUT = QueryDict(request.body)
            if method.lower() == 'delete':
                request.method = 'DELETE'
                request.META['REQUEST_METHOD'] = 'DELETE'
                request.DELETE = QueryDict(request.body)
        return None
