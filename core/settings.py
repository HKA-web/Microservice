import inspect
import logging
import sys

from django.conf import settings as djangosettings
from fastutils import cipherutils

from core.apps import ApplicationConfig

logger = logging.getLogger(__name__)

DEFAULTS = dict(
    SCHEMA=ApplicationConfig.name,
    PREFIX_SAFE='ENC(',
    SUFFIX_SAFE=')',
    FIELD_ENCRYPTION_KEYS=[
        'f164ec6bd6fbc4aef5647abc15199da0f9badcc1d2127bde2087ae0d794a9a0b',
    ],
    CHANNEL_MSGPACK=True,
)
__all__ = list(DEFAULTS)


def load():
    module = sys.modules[__name__]
    for name, default in DEFAULTS.items():
        setattr(module, name, getattr(djangosettings, ApplicationConfig.name.upper(), {}).get(name, default))


load()


def safe(data):
    if isinstance(data, dict):
        for key in list(data.keys()):
            data[key] = safe(data[key])
    elif isinstance(data, list):
        for index in range(len(data)):
            data[index] = safe(data[index])
    elif isinstance(data, str):
        from core import settings
        if data.upper().startswith(settings.PREFIX_SAFE.upper()) and data.upper().endswith(settings.SUFFIX_SAFE.upper()):
            data = data[len(settings.PREFIX_SAFE):len(data) - len(settings.SUFFIX_SAFE)]
        try:
            plain = cipherutils.AesCipher(password=djangosettings.SECRET_KEY, result_encoder=cipherutils.HexlifyEncoder(), force_text=True).decrypt(data)
            if plain:
                return safe(plain)
        except:
            pass
    return data


def safesettings():
    frame = inspect.currentframe()
    globals = frame.f_back.f_globals
    safe(globals)
