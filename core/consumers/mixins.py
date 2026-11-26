import logging
from functools import partial
from io import BytesIO
from typing import Type

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.handlers.asgi import ASGIRequest
from django.db import transaction
from django.db.models import Model
from django.db.models.signals import post_save, post_delete
from django.utils.decorators import classonlymethod
from django.utils.http import urlencode

from core import consumers

logger = logging.getLogger(__name__)


def save_handler(sender, instance, *args, **kwargs):
    label = sender._meta.label
    channel_layer = get_channel_layer()
    group_name = consumers.Group(label)
    connection = transaction.get_connection()

    def callback(group_name, instance):
        async_to_sync(channel_layer.group_send)(group_name, dict(
            type='model.saved',
            model=label,
            instance_pk=instance.pk,
            channel_name=group_name,
        ), )

    transaction.on_commit(partial(callback, group_name, instance))


def delete_handler(sender, instance, *args, **kwargs):
    label = sender._meta.label
    channel_layer = get_channel_layer()
    group_name = consumers.Group(label)
    connection = transaction.get_connection()

    def callback(group_name, instance):
        async_to_sync(channel_layer.group_send)(group_name, dict(
            type='model.deleted',
            model=label,
            instance_pk=instance.pk,
            channel_name=group_name,
        ), )

    if connection.in_atomic_block:
        callback(group_name, instance)
    else:
        transaction.on_commit(partial(callback, group_name, instance))


class RealtimeMixin(object):
    def get_model_class(self) -> Type[Model]:
        assert getattr(self, 'queryset', None) is not None or hasattr(self, 'get_queryset'), (f'''{self.__class__.__name__} does not define a .queryset attribute and so no backing model could be determined. Views must provide .queryset attribute in order to be realtime-compatible.''')
        assert getattr(self, 'queryset', None) is not None, (f'''{self.__class__.__name__} only defines a dynamic .get_queryset() method and so no backing model could be determined. Provide a sentinel queryset of the form queryset = Model.queryset.none() to your view class in order to be realtime-compatible.''')
        return self.queryset.model

    @classmethod
    def register_signal_handler(cls, dispatch_uid):
        viewset = cls()
        model_class = viewset.get_model_class()
        post_save.connect(save_handler, sender=model_class, dispatch_uid=f'rest-live')
        post_delete.connect(delete_handler, sender=model_class, dispatch_uid=f'rest-live')
        return viewset.get_model_class()._meta.label

    @classonlymethod
    def from_scope(cls, viewset_action, scope, kwargs, query):
        self = cls()
        self.format_kwarg = None
        self.action_map = dict()
        self.args = []
        self.kwargs = kwargs
        base_request = ASGIRequest(
            {**scope, 'method': 'GET', 'query_string': urlencode(query)},
            BytesIO(),
        )
        base_request.user = scope.get('user', None)
        base_request.session = scope.get('session', None)
        self.request = self.initialize_request(base_request)
        self.action = viewset_action
        return self
