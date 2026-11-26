import logging

from django import template

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='dictlookup')
@register.simple_tag(name='dictlookup')
def lookup(dictionary: dict, key):
    return dictionary.get(key)
