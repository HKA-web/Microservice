from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ApplicationConfig(AppConfig):
    name = 'core.sql'
    verbose_name = _('Helper To Migrate SQL File From All Module')
