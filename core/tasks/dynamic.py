import logging
import time
from functools import partial

from django.utils.module_loading import import_string as include
from huey import crontab as cron
from huey.api import TaskWrapper

import library.djangohuey as huey

logger = logging.getLogger(__name__)


@huey.db_periodic_task(cron(minute='*/5'), name='Startup All Periodic Task', )
def startup():
    pass


@huey.db_task(name='Periodic Task')
def periodic_task(wrapper, data=None, name=None, crontab=None, **kwargs):
    if crontab is None:
        crontab = dict(minute='*', hour='*', day='*', month='*', day_of_week='*', strict=False)
    if isinstance(wrapper, str):
        wrapper = include(wrapper)
    if data is None:
        data = dict()
    try:
        while isinstance(wrapper, TaskWrapper):
            wrapper = wrapper.func
        if name is None:
            name = f'''{' '.join(wrapper.__name__.split('_')).title()} Task'''
        wrapper = partial(wrapper, **data)
        huey.db_periodic_task(cron(**crontab), name=name, **kwargs)(wrapper)
        logger.info(f'Periodic task with name {name} created')
    except Exception as e:
        logger.error(str(e))


@huey.db_task(name='Executed Task')
def execute_task(wrapper, data=None, schedule=False, delay=0, blocking=False, **kwargs):
    if isinstance(wrapper, str):
        wrapper = include(wrapper)
    if data is None:
        data = dict()
    try:
        name = None
        while isinstance(wrapper, TaskWrapper):
            name = f'''{wrapper.name} Task: {str(time.time())}'''
            wrapper = wrapper.func
        if name is None:
            name = f'''{' '.join(wrapper.__name__.split('_')).title()} Task: {str(time.time())}'''
        wrapper = partial(wrapper, **data)
        wrapper = huey.db_task(name=name, **kwargs)(wrapper)
        if schedule:
            task = wrapper.schedule(**data, delay=delay)
        else:
            task = wrapper(**data)
        task(blocking=blocking)
        logger.info(f'Task with name {name} executed')
    except Exception as e:
        logger.error(str(e))
