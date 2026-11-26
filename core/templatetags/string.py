import logging

from django import template
from django.utils import formats

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='stringreplace')
@register.simple_tag(name='stringreplace')
def replace(value, search, to=''):
    if not isinstance(search, list):
        search = [search]
    for find in search:
        value = value.replace(find, to)
    return value


@register.filter(name='nolocalize')
@register.simple_tag(name='nolocalize')
def replace(value, ):
    return str(formats.localize(value, use_l10n=False))
