import logging

from django.utils import translation, timezone
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin

from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


class LocaleMiddleware(MiddlewareMixin):
    def get_locale_from_user(self, request):
        if request.user.is_authenticated:
            return request.user.locale
        return translation.get_language_from_request(request)

    def process_request(self, request):
        translation.activate(self.get_locale_from_user(request))
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            timezone.activate(djangosettings.TIME_ZONE if not request.user.timezone else request.user.timezone)
