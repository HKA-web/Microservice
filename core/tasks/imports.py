import logging

from django.conf import settings as djangosettings
from django.db.models import Q, Model
from django.utils import timezone, formats
from django.utils.translation import gettext_lazy as _

import library.djangohuey as huey
from core.utils import StringCase
from library import timeago

logger = logging.getLogger(__name__)


@huey.db_task(name='Process Import Task', )
def process(user, models: Model, datas: list, schemas: dict, extras: list, skip: bool, ):
    begin = timezone.now()
    duplicates = []
    for data in datas:
        defaults = {}
        for key, value in data.items():
            defaults.update({schemas[key]['attribute']: value, })
        filters = []
        for extra in extras:
            if extra.get('unique', False):
                filter = {}
                for meta in extra.get('meta', []):
                    filter.update({meta: data.get(meta), })
                filters.append(Q(**filter, _connector=Q.AND))
        instances = models.objects.filter(Q(*filters, _connector=Q.OR))
        if len(instances) > 0:
            duplicates.append(data)
            if skip:
                continue
            for instance in instances:
                for key, value in defaults.items():
                    setattr(instance, key, value)
                instance.save()
        else:
            models.objects.create(**defaults)
    end = timezone.now()
    duration = end - begin
