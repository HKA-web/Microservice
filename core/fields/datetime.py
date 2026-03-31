import logging

from django.db import models

logger = logging.getLogger(__name__)


class DateTimeWithautTZField(models.DateTimeField):
    def db_type(self, connection):
        if connection.vendor == 'postgresql':
            return 'timestamp'
        else:
            return super(DateTimeWithautTZField, self).db_type(connection)


class AutoCreatedField(DateTimeWithautTZField):
    def __init__(self, *args, **kwargs):
        from django.utils import timezone
        kwargs.setdefault('editable', False)
        kwargs.setdefault('default', timezone.now)
        super().__init__(*args, **kwargs)


class AutoLastModifiedField(AutoCreatedField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super().__init__(*args, **kwargs)

    def get_default(self):
        if not hasattr(self, '_default'):
            self._default = self._get_default()
        return self._default

    def pre_save(self, model_instance, add):
        from django.utils import timezone
        if not add:
            value = timezone.now()
            setattr(model_instance, self.attname, value)
            return value
        return None
