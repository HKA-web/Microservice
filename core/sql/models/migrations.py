import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from library.modelutils.fields import AutoCreatedField

logger = logging.getLogger(__name__)


class DjangoMigrations(models.Model, ):
    app = models.CharField()
    name = models.CharField()
    applied = AutoCreatedField()

    class Meta:
        managed = False
        db_table = u'\"django_migrations\"'
        unique_together = ()
        verbose_name = _('Used store django migrations')
