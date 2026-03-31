import logging
import random

from django import template

from core.utils import ShortUUID

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='randomchoice')
@register.simple_tag(name='randomchoice')
def choice(value):
    return random.choice(list(value)) if len(list(value)) > 0 else None


@register.filter(name='randomstring')
@register.simple_tag(name='randomstring')
def string(length=5, value='012345689ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnpqrstuvwxyz'):
    uuid = ShortUUID()
    uuid.set_alphabet(value)
    return uuid.random(length=length)
