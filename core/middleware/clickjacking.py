import logging

from django.middleware.clickjacking import XFrameOptionsMiddleware

logger = logging.getLogger(__name__)


class IFrameOptionsMiddleware(XFrameOptionsMiddleware):
    def process_response(self, request, response):
        if response.get('X-Frame-Options') is not None:
            return response
        if getattr(response, 'xframe_options_exempt', False):
            return response
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response
