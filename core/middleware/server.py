import logging
import platform
import re as regex

from django.conf import settings

logger = logging.getLogger(__name__)


def headers():
    return dict(
        Server=f'Python @ {regex.sub(r'[^\d.]', '', platform.python_version())},{f' {settings.PROJECT['SERVER']} @ {settings.PROJECT[settings.PROJECT['SERVER'].upper()]}, ' if 'SERVER' in settings.PROJECT else ''} Django @ {settings.PROJECT['DJANGO']}',
        Framework='ERPro Framework @ Tukang Pecut Juru Ketik',
        Support='http://www.syifarahmat.github.io/, https://wa.me/6282266331136/',
    )


class ServerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for key, header in headers().items():
            response.headers[key] = header
        return response
