import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Type, List, Union

from asgiref.sync import async_to_sync
from django.http import Http404
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from core import consumers
from core.consumers.base import DefaultConsumer
from core.consumers.mixins import RealtimeMixin

KwargType = Dict[str, Union[int, str]]

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    id: int
    action: str
    kwargs: Dict[str, Union[int, str]]
    query: Dict[str, Union[int, str]]
    lookup: Dict[int, object]


class SubscriptionConsumer(DefaultConsumer):
    registry: Dict[str, Type[RealtimeMixin]] = dict()
    public = True

    def connect(self):
        if not self.public and not (
            self.scope.get('user') is not None
            and self.scope.get('user').is_authenticated
        ):
            self.close(code=4003)
        self.subscriptions: Dict[str, List[Subscription]] = dict()
        self.accept()

    def send_error(self, id, code, message):
        if not self.ismsgpack:
            self.send(
                text_data=json.dumps(dict(
                    type='error',
                    id=id,
                    code=code,
                    message=message,
                )),
            )
        else:
            self.send(
                bytes_data=self.pack(dict(
                    type='error',
                    id=id,
                    code=code,
                    message=message,
                ), ),
            )

    def send_broadcast(self, id, label, action, instance_data, renderer):
        logger.debug('Send %(data)s', dict(data=dict(id=id, label=label, action=action, instance_data=instance_data, )))
        if not self.ismsgpack:
            self.send(
                text_data=renderer.render(dict(
                    type='broadcast',
                    id=id,
                    model=label,
                    action=action,
                    instance=instance_data,
                ), ).decode('utf8'),
            )
        else:
            self.send(
                bytes_data=self.pack(dict(
                    type='broadcast',
                    id=id,
                    model=label,
                    action=action,
                    instance=instance_data,
                ), ),
            )

    def receive(self, text_data=None, bytes_data=None):
        if self.ismsgpack:
            return self.receive_data(content=self.unpack(bytes_data), )
        else:
            return super().receive(text_data, bytes_data)

    def receive_json(self, content: Dict[str, Any], **kwargs):
        return self.receive_data(content, **kwargs)

    def receive_data(self, content: Dict[str, Any], **kwargs):
        id = content.get('id', None)
        if id is None:
            return
        message_type = content.get('type', None)
        if message_type == 'subscribe':
            label = content.get('model')
            if label is None:
                self.send_error(id, 400, 'No model specified.')
                return
            if label not in self.registry:
                self.send_error(id, 404, f'Model {label} not registered for realtime updates.', )
                return
            action = content.get('action', None)
            if action is None or action not in ['list', 'retrieve']:
                self.send_error(id, 400, '`action` must be present and the value must be either `list` or `retrieve`.', )
            lookup_value = content.get('lookup', None)
            kwargs = content.get('kwargs', dict())
            for index, value in kwargs.items():
                if isinstance(value, str):
                    kwargs.update({index: value.split(',')})
            query = content.get('query', dict())
            for index, value in query.items():
                if isinstance(value, (dict, list)):
                    query.update({index: json.dumps(value, separators=(',', ':'), )})
            view = self.registry[label].from_scope(
                action, self.scope, kwargs, query
            )
            has_permission = True
            for permission in view.get_permissions():
                has_permission = has_permission and permission.has_permission(
                    view.request, view
                )
            if view.action == 'retrieve':
                view.kwargs.setdefault(view.lookup_field, lookup_value)
                try:
                    view.get_object()
                except Http404:
                    self.send_error(id, 404, '''Instance not found. Make sure 'lookup' is set to a valid pk''', )
                    return
                except (NotAuthenticated, PermissionDenied):
                    has_permission = False
            if not has_permission:
                self.send_error(id, 403, f'Unauthorized to subscribe to {label} for action {action}', )
                return
            group_name = consumers.Group(label)
            self.subscriptions.setdefault(group_name, []).append(
                Subscription(
                    id,
                    action=action,
                    kwargs=kwargs,
                    query=query,
                    lookup=dict({
                        instance['pk']: instance[view.lookup_field] for instance in view.get_queryset().filter(pk=lookup_value).values('pk', view.lookup_field)
                    }) if view.action == 'retrieve' else dict({
                        instance['pk']: instance[view.lookup_field] for instance in view.get_queryset().values('pk', view.lookup_field)
                    }),
                )
            )
            async_to_sync(self.channel_layer.group_add)(group_name, self.channel_name)
            self.groups.append(group_name)
        elif message_type == 'unsubscribe':
            try:
                group_name = [key for key, value in self.subscriptions.items() if id in [subscription.id for subscription in value]][0]
            except IndexError:
                self.send_error(id, 404, 'Attempted to unsubscribe for request ID before subscribing.', )
                return
            self.subscriptions[group_name] = [
                subscription
                for subscription in self.subscriptions[group_name]
                if subscription.id != id
            ]
            self.groups.remove(group_name)
            if (group_name not in self.groups):
                async_to_sync(self.channel_layer.group_discard)(group_name, self.channel_name)
            if len(self.subscriptions[group_name]) == 0:
                del self.subscriptions[group_name]
        else:
            self.send_error(id, 400, f'unknown message type `{message_type}`.')

    def model_saved(self, event):
        channel_name: str = event['channel_name']
        instance_pk: int = event['instance_pk']
        label: str = event['model']
        viewset_class = self.registry[label]
        for subscription in self.subscriptions[channel_name]:
            view = viewset_class.from_scope(
                subscription.action,
                self.scope,
                subscription.kwargs,
                subscription.query,
            )
            model = view.get_model_class()
            renderer = view.perform_content_negotiation(view.request)[0]
            is_existing_instance = instance_pk in subscription.lookup
            try:
                instance = view.filter_queryset(view.get_queryset()).get(pk=instance_pk, )
                action = consumers.Updated if is_existing_instance else consumers.Created
            except model.DoesNotExist:
                if not is_existing_instance:
                    return
                action = consumers.Deleted
                try:
                    instance = model.objects.get(pk=instance_pk)
                except model.DoesNotExist:
                    return self.model_deleted(event)
            serializer_class = view.get_serializer_class()
            instance_data = serializer_class(
                instance,
                expand=subscription.kwargs['expand'] if 'expand' in subscription.kwargs else [],
                fields=subscription.kwargs['fields'] if 'fields' in subscription.kwargs else [],
                omit=subscription.kwargs['omit'] if 'omit' in subscription.kwargs else [],
                context=dict(
                    request=view.request,
                    format='json',
                    view=view,
                ),
            ).data
            if action == consumers.Deleted:
                if view.lookup_field == 'pk' and 'id' in instance_data:
                    instance_data = {
                        view.lookup_field: getattr(instance, view.lookup_field),
                        'id': instance_data['id'],
                    }
                else:
                    instance_data = {
                        view.lookup_field: getattr(instance, view.lookup_field)
                    }
            if action == consumers.Deleted:
                del subscription.lookup[instance_pk]
            else:
                subscription.lookup[instance_pk] = getattr(instance, view.lookup_field, )
            self.send_broadcast(
                subscription.id,
                label,
                action,
                instance_data,
                renderer,
            )

    def model_deleted(self, event):
        channel_name: str = event['channel_name']
        instance_pk: int = event['instance_pk']
        label: str = event['model']
        viewset_class = self.registry[label]
        for subscription in self.subscriptions[channel_name]:
            view = viewset_class.from_scope(
                subscription.action,
                self.scope,
                subscription.kwargs,
                subscription.query,
            )
            renderer = view.perform_content_negotiation(view.request)[0]
            is_existing_instance = instance_pk in subscription.lookup
            if is_existing_instance:
                instance_data = {
                    view.lookup_field: subscription.lookup[instance_pk],
                    'id': instance_pk,
                }
                del subscription.lookup[instance_pk]
                self.send_broadcast(
                    subscription.id,
                    label,
                    consumers.Deleted,
                    instance_data,
                    renderer,
                )
