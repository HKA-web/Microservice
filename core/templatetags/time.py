import hashlib
import json
import logging

from django import template
from django.conf import settings as djangosettings

from library import timeago

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='timeago')
@register.simple_tag(name='timeago')
def ago(value, locale=djangosettings.LANGUAGE_CODE):
    return timeago.format(value, locale=locale)
