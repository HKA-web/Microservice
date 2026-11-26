import logging
import os
import typing
import re as regex
from collections import namedtuple

from django.db.utils import (DEFAULT_DB_ALIAS as DatabaseAlias, load_backend, )
from django.core import checks
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.middleware import request
from core.utils import ShortUUID
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


class IdentifierField(models.CharField, ):
    description = _('String auto numbering with custom prefix')

    def __init__(
        self,
        *args,
        company: typing.AnyStr = None,
        part: typing.AnyStr = '',
        length: int = 10,
        prefix: typing.AnyStr = None,
        suffix: typing.AnyStr = '',
        repeater: typing.AnyStr = '0',
        counter: int = 1,
        using: str = DatabaseAlias,
        **kwargs,
    ):
        kwargs.setdefault('max_length', 255)
        super().__init__(*args, **kwargs, )
        self.company = company
        self.part = part
        self.length = length
        self.prefix = prefix
        self.suffix = suffix
        self.repeater = repeater
        self.counter = counter
        self.using = using
        self.properties = dict()

    def deconstruct(self, ):
        name, path, args, kwargs = super().deconstruct()
        kwargs['company'] = self.company
        kwargs['part'] = self.part
        kwargs['length'] = self.length
        kwargs['prefix'] = self.prefix
        kwargs['suffix'] = self.suffix
        kwargs['repeater'] = self.repeater
        kwargs['counter'] = self.counter
        kwargs['using'] = self.using
        return name, path, args, kwargs

    def check(self, **kwargs, ):
        return [
            *super().check(**kwargs, ),
            *self.check_attribute(**kwargs, ),
        ]

    def get_default(self, ):
        if not hasattr(self, '_default'):
            self._default = self._get_default()
        return self._default

    def pre_save(self, model_instance, add, ):
        if self.company is None and request().session is not None and False:
            self.company = request().session.get('company', djangosettings.PROJECT.get('NAME'))
        else:
            self.company = djangosettings.PROJECT.get('NAME')
        self.properties = dict(
            application=model_instance._meta.app_label,
            model=model_instance._meta.model.__name__,
        )
        from authentication.models import ContentType
        content_type = ContentType.objects.get_for_model(model_instance._meta.model)
        value = getattr(model_instance, self.attname, '')
        from library.simplehistory.models import HistoricalChanges
        if add and not len(value) > 0 and HistoricalChanges.__name__.lower() not in (
            base.__name__.lower() for base in model_instance.__class__.__bases__
        ):
            from core.models import Company
            company = Company.objects.get(pk=self.company, )
            from core.models import Sequence
            sequence, created = Sequence.objects.get_or_create(
                company=company,
                content_type=content_type,
                defaults=dict(
                    company=company,
                    content_type=content_type,
                    part=self.part,
                    length=self.length,
                    prefix=self.prefix,
                    suffix=self.suffix,
                    repeater=self.repeater,
                    counter=self.counter,
                    properties=self.properties,
                    description=_('<p>Used for auto numbering model %(model)s on application %(application)s</p>' % self.properties),
                    read_only=True,
                    enable=True,
                ),
            )

            def format(data: str, ):
                return data.format(  # refer to: https://pyformat.info/
                    environment=namedtuple('Environment', os.environ.keys(), rename=True, )(*os.environ.values(), ),
                    setting=djangosettings,
                    now=timezone.now(),  # example: {now:%Y-%m-%d %H:%M}
                    user=request().user,
                    session=request().session,
                    sequence=sequence,
                    model=model_instance,
                ).upper().strip() if data is not None else ''

            from core.models import SequenceData
            sequence_data, created = SequenceData.objects.get_or_create(
                sequence=sequence,
                part=format(sequence.part),
                defaults=dict(
                    sequence=sequence,
                    part=format(sequence.part),
                    current=0,
                )
            )
            from core.models import SequenceNumber
            sequence_number = SequenceNumber(
                sequence=sequence,
                part=format(sequence.part),
                owner=request().user,
                number='',
            )
            SequenceNumber.objects.filter(
                sequence=sequence_number.sequence,
                part=sequence_number.part,
                owner=sequence_number.owner,
            ).delete()
            sequence_number.save()
            sequence_data.current = (sequence_data.current if sequence_data.current is not None else 0) + sequence.counter
            sequence_number.number = f'{format(sequence.prefix)}{format(sequence_number.part)}{sequence.repeater * (sequence.length - len(format(sequence.prefix) + format(sequence_number.part) + str(sequence_data.current)))}{sequence_data.current}{format(sequence.suffix)}'
            pattern = regex.compile(f'''[{djangosettings.NUMBERING_PATTERN}]+''')
            if not regex.fullmatch(pattern, sequence_number.number):
                raise Exception(_('Generated numbers %(number)s do not match the pattern') % dict(number=sequence_number.number, ))
            if sequence.length < len(sequence_number.number):
                from core.models import Notification
                Notification.objects.create(
                    notification_name=_('Sequence Over Length'),
                    platform=Notification.Platform.erpro,
                    content=_(u'Sequence %(object_name)s has exceeded the limit <br/>Number %(number)s length is %(number_length)s <br/>Allocation is %(sequence_length)s') % dict(
                        object_name=model_instance._meta.object_name,
                        number=sequence_number.number,
                        number_length=len(sequence_number.number),
                        sequence_length=sequence.length,
                    ),
                    toast=True,
                    icon=Notification.Icon.warning,
                    owner=sequence_number.owner,
                )
            sequence_data.save(update_fields=['current'])
            sequence_number.save(update_fields=['number'])
            value = sequence_number.number
            logger.debug(f'''Set default value {value} to model {model_instance._meta.db_table.replace('"', '')} field {self.attname}''')
            setattr(model_instance, self.attname, value)
        else:
            logger.debug(f'''Model {model_instance._meta.db_table.replace('"', '')} field {self.attname} with value {value}''')
        return value

    def check_attribute(self, **kwargs, ):
        message = []
        if self.company is not None:
            message.append(
                checks.Warning(
                    '''Attribut 'company' is set, this will only use for one company. Recomended set to None for use session active Company''',
                    obj=self,
                    id='IdentifierInfo.W001',
                )
            )
        if self.prefix is None:
            message.append(
                checks.Error(
                    '''Attribut 'prefix' must set''',
                    obj=self,
                    id='IdentifierField.E001',
                )
            )
        return message


class ShortUUIDField(models.CharField, ):
    description = _('A short UUID field')

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.length = kwargs.pop('length', 22)
        self.prefix = kwargs.pop('prefix', '')
        if 'max_length' not in kwargs:
            kwargs.update(max_length=self.length + len(self.prefix), )
        self.alphabet = kwargs.pop('alphabet', None)
        super().__init__(*args, **kwargs)

    def deconstruct(self, ):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update(
            alphabet=self.alphabet,
            length=self.length,
            prefix=self.prefix,
        )
        return name, path, args, kwargs

    def get_default(self, ):
        if not hasattr(self, '_default'):
            self._default = self._get_default()
        return self._default

    def pre_save(self, model_instance, add, ):
        value = getattr(model_instance, self.attname, '')
        if add and not len(value) > 0:
            value = self.prefix + ShortUUID(alphabet=self.alphabet).random(
                length=self.length
            )
            logger.debug(f'''Set default value {value} to model {model_instance._meta.db_table.replace('"', '')} field {self.attname}''')
            setattr(model_instance, self.attname, value)
        else:
            logger.debug(f'''Model {model_instance._meta.db_table.replace('"', '')} field {self.attname} with value {value}''')
        return value
