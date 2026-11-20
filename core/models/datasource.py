import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from core import settings
from core.fields import ShortUUIDField, StatusField, EncryptedCharField
from core.models.base import Base, History, Tracker

logger = logging.getLogger(__name__)


class Datasource(Base):
    datasource_id = ShortUUIDField(
        length=25,
        primary_key=True,
        verbose_name=_('datasource id'),
        help_text=_('Used for identity'),
    )
    datasource_name = models.CharField(
        unique=True,
        verbose_name=_('datasource name'),
        help_text=_('Used for view'),
    )
    engine = models.CharField(
        null=True,
        verbose_name=_('engine'),
        help_text=_('Used for engine database for connect'),
    )
    database = models.CharField(
        verbose_name=_('database'),
        help_text=_('Used for database name'),
    )
    user = models.CharField(
        null=True,
        verbose_name=_('user'),
        help_text=_('Used for user database for connect'),
    )
    password = EncryptedCharField(
        null=True,
        verbose_name=_('password'),
        help_text=_('Used for password database for connect'),
    )
    host = models.CharField(
        null=True,
        verbose_name=_('host'),
        help_text=_('Used for host or ip address database for connect'),
    )
    port = models.IntegerField(
        null=True,
        verbose_name=_('port'),
        help_text=_('Used for port database for connect'),
    )
    url = models.TextField(
        null=True,
        verbose_name=_('url'),
        help_text=_('Used for url string connection'),
    )
    status = StatusField(transition=False)
    tracker = Tracker()
    history = History(
        bases=[Base],
        table_name=u'\"history\".\"{}_datasource\"'.format(settings.SCHEMA),
        verbose_name=_('History Data Source'),
        excluded_fields=['modified'],
    )

    class Meta:
        managed = True
        db_table = u'\"{}\".\"datasource\"'.format(settings.SCHEMA)
        verbose_name = _('Data Source')

    def connection(self):
        from django.conf import settings as djangosettings
        from core.utils import parse, create
        value = dict(
            NAME=self.database,
            **self.properties,
        )
        if self.engine is not None:
            value['ENGINE'] = self.engine
        if self.user is not None:
            value['USER'] = self.user
        if self.password is not None:
            value['PASSWORD'] = self.password
        if self.host is not None:
            value['HOST'] = self.host
        if self.port is not None:
            value['PORT'] = self.port
        if self.url:
            value = dict(
                **parse(url=self.url),
                **self.properties,
            )
        djangosettings.DATABASES[self.datasource_id] = value
        return create(self.datasource_id)
