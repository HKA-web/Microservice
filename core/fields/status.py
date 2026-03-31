import logging

from django.conf import settings as djangosettings
from django.utils.translation import gettext_lazy as _

from core.middleware import request
from library.modelutils.fields import StatusField as StatusFields

logger = logging.getLogger(__name__)


class StatusField(StatusFields):
    def __init__(self, *args, **kwargs):
        self.transition = bool(kwargs.pop('transition', True))
        self.prepares = kwargs.pop('prepares', ())
        defaults = dict(choices_name='Status')
        defaults.update(kwargs)
        super(StatusField, self).__init__(*args, **defaults)

    def prepare_class(self, sender, **kwargs):
        super(StatusField, self).prepare_class(sender, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname, '')
        return value
