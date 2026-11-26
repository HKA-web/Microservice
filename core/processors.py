import logging
import os

from django.middleware.csrf import get_token
from django.urls import resolve
from django.utils import translation
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


def template(request):
    return {
        'settings': djangosettings.__dict__,
        'environment': os.environ,
        'csrf': get_token(request),
        'language': {
            'list': djangosettings.LANGUAGES,
            'code': translation.get_language(),
            'bidi': translation.get_language_bidi(),
        }
    }
