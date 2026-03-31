import logging
import os

from django import template

logger = logging.getLogger(__name__)

register = template.Library()

@register.filter
@register.simple_tag()
def environment(key):
    return os.environ.get(key, None)
