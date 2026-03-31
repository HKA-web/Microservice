import logging

from django import template
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='settingsdjango')
@register.simple_tag(name='settingsdjango')
def settings(key):
    def helper(dictionary, key):
        current = dictionary
        for chunk in key.split('.'):
            current = current.get(chunk, None)
        return current
    try:
        return djangosettings[key]
    except Exception as e:
        value = helper(djangosettings.__dict__['_wrapped'].__dict__, key)
        return getattr(djangosettings, key) if value is None else value
