import logging
import os

import yaml
from django.core.management.base import BaseCommand

from core import settings
from core.utils import ShortUUID

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Management command to generate secret key'''

    def add_arguments(self, parser):
        parser.add_argument('-l', '--length', dest='length', action='store', default=100, help='length scret key [default: %(default)s]')

    def handle(self, **options):
        length = options.get('length')
        with open(os.path.join(settings.djangosettings.BASE_DIR, 'erpro.yaml')) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
            fallbacks = config['SECRET_KEY_FALLBACKS'] if 'SECRET_KEY_FALLBACKS' in config else []
            fallbacks.append(config['SECRET_KEY'])
            config.update(dict(
                SECRET_KEY=ShortUUID().random(length=length),
                SECRET_KEY_FALLBACKS=fallbacks,
            ))
        with open(os.path.join(settings.djangosettings.BASE_DIR, 'erpro.yaml'), 'w') as file:
            yaml.dump(config, file)
        self.stdout.write(f'''Secret key has generated to {os.path.join(settings.djangosettings.BASE_DIR, 'erpro.yaml')}''')
