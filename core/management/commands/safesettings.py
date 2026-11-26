import logging

from django.core.management.base import BaseCommand
from fastutils import cipherutils

from core import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Management command to encrypt setting value'''

    def add_arguments(self, parser):
        parser.add_argument('-p', '--plain', dest='plain', action='append', required=True, help='plain value settings to safe')

    def handle(self, **options):
        plains = options.get('plain')
        if len(plains) > 0:
            self.stdout.write(f'''Safe settings has generated''')
        for plain in plains:
            try:
                cipher = f'''{settings.PREFIX_SAFE}{cipherutils.AesCipher(password=settings.djangosettings.SECRET_KEY, result_encoder=cipherutils.HexlifyEncoder(), force_text=True).encrypt(plain)}{settings.SUFFIX_SAFE}'''
                self.stdout.write(f'''\t{plain}: {cipher}''')
            except Exception as e:
                self.stderr.write(f'''\terror safe {plain}''')
                logger.exception(e)
