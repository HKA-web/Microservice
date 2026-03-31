import datetime
import decimal
import uuid

import msgpack
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncJsonWebsocketConsumer, WebsocketConsumer, JsonWebsocketConsumer
from django.conf import settings as djangosettings
from django.utils.duration import duration_iso_string
from django.utils.functional import Promise
from django.utils.timezone import is_aware


class MsgPackEncoder:

    @property
    def ismsgpack(self):
        return getattr(djangosettings, 'CHANNEL_MSGPACK', False)

    def default(self, object):
        if isinstance(object, datetime.datetime):
            formated = object.isoformat()
            if object.microsecond:
                formated = formated[:23] + formated[26:]
            if formated.endswith('+00:00'):
                formated = formated[:-6] + 'Z'
            return formated
        elif isinstance(object, datetime.date):
            return object.isoformat()
        elif isinstance(object, datetime.time):
            if is_aware(object):
                raise ValueError('''JSON can't represent timezone aware times.''')
            formated = object.isoformat()
            if object.microsecond:
                formated = formated[:12]
            return formated
        elif isinstance(object, datetime.timedelta):
            return duration_iso_string(object)
        elif isinstance(object, (decimal.Decimal, uuid.UUID, Promise)):
            return str(object)
        else:
            return object

    def pack(self, object):
        return msgpack.packb(object, default=self.default, )

    def unpack(self, object):
        return msgpack.unpackb(object, )


Consumer = WebsocketConsumer if getattr(djangosettings, 'CHANNEL_MSGPACK', False) else JsonWebsocketConsumer
AsyncConsumer = AsyncWebsocketConsumer if getattr(djangosettings, 'CHANNEL_MSGPACK', False) else AsyncJsonWebsocketConsumer


class DefaultConsumer(Consumer, MsgPackEncoder, ):
    pass


class DefaultAsyncConsumer(AsyncConsumer, MsgPackEncoder, ):
    pass
