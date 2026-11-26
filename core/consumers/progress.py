import json
import logging

from core.consumers.base import DefaultAsyncConsumer

logger = logging.getLogger(__name__)


class ProgressConsumer(DefaultAsyncConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        if self.ismsgpack:
            return await self.receive_data(content=self.unpack(bytes_data), )
        else:
            return await super().receive(text_data, bytes_data)

    async def receive_json(self, content, **kwargs):
        return await self.receive_data(content, **kwargs)

    async def receive_data(self, content, **kwargs):
        await self.channel_layer.group_add(
            f'progress.{self.user.base64pk}.{content.get('path', None)}',
            self.channel_name
        )

    async def send_data(self, event, ):
        # data can contains dict(path=, message='Donwloading', of='body', shadow=True, showIndicator=True, showPane=True, shading=True, show=True)
        data = event['data']
        if not self.ismsgpack:
            await self.send(
                text_data=json.dumps(data, ),
            )
        else:
            await self.send(
                bytes_data=self.pack(data, ),
            )
