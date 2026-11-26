import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from huey import crontab

import library.djangohuey as huey

logger = logging.getLogger(__name__)


@huey.db_periodic_task(crontab(minute='*'), name='Process Clock Task', )
def process():
    layer = get_channel_layer()
    async_to_sync(layer.group_send)('clock', dict(
        type='send.data',
        data={},
    ))
