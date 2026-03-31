import logging
import time
from datetime import datetime, timezone

from django.apps import apps
from django.db import router, connections
from django.db.models.fields import (
    AutoField,
    SmallAutoField,
    BigAutoField,
)
from huey import crontab

import library.djangohuey as huey

logger = logging.getLogger(__name__)


@huey.db_task(crontab(minute='*/30', hour='11,23'), name='Process Set Value Auto Field Task', )
def process():
    for model in [model for model in apps.get_models() if model._meta.managed and len([field for field in model._meta.get_fields() if isinstance(field, (AutoField, SmallAutoField, BigAutoField,))]) > 0]:
        for field in [field for field in model._meta.get_fields() if isinstance(field, (AutoField, SmallAutoField, BigAutoField,))]:
            connection = connections[router.db_for_read(model)]
            cursor = connection.cursor()
            cursor.execute('SELECT pg_get_serial_sequence(%s, %s)', (field.model._meta.db_table.replace('"', ''), field.attname,))
            sequence = cursor.fetchone()[0]
            cursor.execute('SELECT nextval(%s)', (sequence,))
            value = cursor.fetchone()[0]
            if datetime.fromtimestamp(value / 1000).date() < datetime.now(timezone.utc).date():
                cursor.execute('SELECT setval(%s, %s, TRUE)', (sequence, int(round(time.time() * 1000)),))
                value = cursor.fetchone()[0]
                logger.debug('Set value ')
                logger.debug('Set value %s to Sequence %s.%s', value, field.model._meta.db_table.replace('"', ''), field.attname, )
