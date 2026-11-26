import logging

from django.core import management
from django.utils import timezone

import library.djangohuey as huey
from core.management.commands import collecticon

logger = logging.getLogger(__name__)


@huey.db_task(name='Process Collect Icon Task', )
def process_collect(user, ):
    begin = timezone.now()
    management.call_command(collecticon.Command(), )
    end = timezone.now()
    duration = end - begin
