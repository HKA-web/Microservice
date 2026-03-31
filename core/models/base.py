import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from library.modelutils import FieldTracker as Tracker, Choices
from library.modelutils.fields import MonitorField
from library.modelutils.models import (
    TimeStampedModel as TimeStamped,
    SoftDeletableModel as SoftDeletable,
)
from library.simplehistory.models import HistoricalRecords as History
from library.treebeard.al_tree import AL_Node
from library.treebeard.mp_tree import MP_Node
from library.treebeard.ns_tree import NS_Node

logger = logging.getLogger(__name__)

MaterializedPathTree = MP_Node
AdjacencyListTree = AL_Node
NestedSetTree = NS_Node

__all__: [
    Tracker,
    MonitorField,
    History,
    MaterializedPathTree,
    AdjacencyListTree,
    NestedSetTree,
]


class Base64:
    @staticmethod
    def encode(string):
        import base64
        encoded = base64.urlsafe_b64encode(string.encode())
        return encoded.rstrip(b'=').decode()

    @staticmethod
    def decode(string):
        import base64
        padding = 4 - (len(string) % 4)
        string = string + ('=' * padding)
        return base64.urlsafe_b64decode(string).decode()


class Base64PkDecodeError(Exception):
    def __init__(self, msg='Failed to decrypt hex, invalid input.'):
        super(Base64PkDecodeError, self).__init__(msg)


class Base64PkManager(models.Manager):
    def get(self, base64pk, **kwargs):
        return self.get(pk=Base64.decode(base64pk), **kwargs)


class Base64PkQuerySet(models.QuerySet):
    def filter(self, *args, **kwargs):
        if 'base64pk' in kwargs:
            base64pk = kwargs.pop('base64pk')
            try:
                assert base64pk is not None
                kwargs['pk'] = Base64.decode(base64pk)
            except (AssertionError, Base64PkDecodeError):
                return self.none()
        return super(Base64PkQuerySet, self).filter(*args, **kwargs)


class Base64PkModel(models.Model):
    class Meta:
        abstract = True

    hexobjects = Base64PkManager.from_queryset(Base64PkQuerySet)()

    @property
    def base64pk(self):
        if isinstance(self._meta.pk, (models.IntegerField, models.AutoField, models.SmallAutoField, models.BigIntegerField, models.BigAutoField,)):
            return Base64.encode(str(self.pk))
        return Base64.encode(self.pk)


class Base64PkConverter:
    name = 'base64pk'
    regex = '[^/]+'

    def to_python(self, value):
        return Base64.decode(value)

    def to_url(self, value):
        return Base64.encode(value)


class BaseStatus(object):
    Status = Choices(
        ('draft', _('Draft')),
        ('published', _('Published')),
        ('approved', _('Approved')),
        ('canceled', _('Canceled')),
    )


class Base(BaseStatus, TimeStamped, SoftDeletable, Base64PkModel, ):
    read_only = models.BooleanField(
        default=False,
        verbose_name=_('read only'),
        help_text=_('Used for disable modification'),
    )
    enable = models.BooleanField(
        default=False,
        verbose_name=_('enable'),
        help_text=_('Used for usable'),
    )
    properties = models.JSONField(
        default=dict,
        verbose_name=_('properties'),
        help_text=_('Used for other field value'),
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('description'),
        help_text=_('Used for remark'),
    )

    class Meta:
        abstract = True
