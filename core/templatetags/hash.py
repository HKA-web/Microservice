import hashlib
import logging

from django import template

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='hashmd5')
@register.simple_tag(name='hashmd5')
def md5(value):
    return hashlib.md5(value.encode()).hexdigest()

@register.filter(name='hashbase64')
@register.simple_tag(name='hashbase64')
def base64(value):
    import base64
    return base64.urlsafe_b64encode(value.encode()).decode()
