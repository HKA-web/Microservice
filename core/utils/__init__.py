from django.db.models import Model

from core.utils.database import config, parse, create
from core.utils.shortuuid import ShortUUID
from core.utils.lodash import lodash
from core.utils import strings
from core.utils import stringcase as StringCase


def key_value(data: list):
    return [dict(key=key, value=value) for key, value in data]


__all__ = [
    lodash,
    config,
    parse,
    strings,
    create,
    ShortUUID,
    key_value,
    StringCase,
]
