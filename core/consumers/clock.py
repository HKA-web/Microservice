import json
import logging
import zoneinfo

from channels.layers import get_channel_layer
from django.utils import timezone

from core.consumers.base import DefaultAsyncConsumer

logger = logging.getLogger(__name__)


class ClockConsumer(DefaultAsyncConsumer, ):
    async def connect(self):
        self.user = self.scope.get('user')
        await self.channel_layer.group_add(
            f'clock',
            self.channel_name
        )
        await self.accept()

    async def send_data(self, event, ):
        datetimezone = timezone.now().astimezone(zoneinfo.ZoneInfo(self.user.timezone))
        offsite = datetimezone.strftime('%z')
        data = dict(
            zone=dict(id=self.user.timezone, offset=f'{offsite[0:3]}:{offsite[3:]}'),
            date=datetimezone.strftime('%Y-%m-%d'),
            time=datetimezone.strftime('%H:%M:%S.%f'),
            datetime=datetimezone.strftime('%Y-%m-%d %H:%M:%S.%f'),
            datetimezone=datetimezone.strftime(f'%Y-%m-%d %H:%M:%S.%f{offsite[0:3]}:{offsite[3:]}'),
        )
        if not self.ismsgpack:
            await self.send(
                text_data=json.dumps(data, ),
            )
        else:
            await self.send(
                bytes_data=self.pack(data, ),
            )
