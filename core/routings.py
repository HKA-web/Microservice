from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer
from django.urls import re_path as re_path

from core import consumers
from core.consumers.routers import RealtimeRouter

router = RealtimeRouter()

websocket_urlpatterns = [
    re_path(r'^ws/core/$', AsyncJsonWebsocketDemultiplexer.as_asgi()),
    re_path(r'^ws/subscribe/$', router.as_consumer().as_asgi(), name='subscribe'),
    re_path(f'^ws/notification/$', consumers.NotificationConsumer.as_asgi(), name='notification'),
    re_path(f'^ws/clock/$', consumers.ClockConsumer.as_asgi(), name='clock'),
    re_path(f'^ws/progress/$', consumers.ProgressConsumer.as_asgi(), name='progress'),
]
