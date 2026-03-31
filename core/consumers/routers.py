import logging
from typing import Dict, Type

from core.consumers.mixins import RealtimeMixin
from core.consumers.subscription import SubscriptionConsumer

logger = logging.getLogger(__name__)


class RealtimeRouter:
    def __init__(self, public=True, uid='default'):
        self.registry: Dict[str, Type[RealtimeMixin]] = dict()
        self.uid = uid
        self.public = public

    def register_all(self, views):
        for viewset in views:
            self.register(viewset)

    def register(self, view):
        if not hasattr(view, 'register_signal_handler'):
            raise RuntimeError(f'View {view.__name__} passed to RealtimeRouter does not have RealtimeMixin applied.')
        label = view.register_signal_handler(self.uid)
        if label in self.registry:
            raise RuntimeWarning('You should not register two realitime views for the same model.')
        self.registry[label] = view

    def as_consumer(self):
        return type('BoundSubscriptionConsumer', (SubscriptionConsumer,), dict(registry=self.registry, public=self.public, ), )
