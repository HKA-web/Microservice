import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django import template

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='progressshow')
@register.simple_tag(name='progressshow', takes_context=True, )
def show(context, path, message=None, of=None, shadow=True, show_indicator=True, show_pane=True, shading=True):
    user = context['request'].user
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(f'progress.{user.base64pk}.{path}', dict(
        type='send.data',
        data=dict(message=message, of=of, shadow=shadow, showIndicator=show_indicator, showPane=show_pane, shading=shading, show=True),
    ))


@register.filter(name='progresshide')
@register.simple_tag(name='progresshide', takes_context=True, )
def hide(context, path):
    user = context['request'].user
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(f'progress.{user.base64pk}.{path}', dict(
        type='send.data',
        data=dict(show=False),
    ))
