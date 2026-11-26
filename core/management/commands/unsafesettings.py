import logging

from django.core.management.base import BaseCommand
from fastutils import cipherutils

from core import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Management command to decrypt setting value'''

    def add_arguments(self, parser):
        parser.add_argument('-c', '--cipher', dest='cipher', action='append', required=True, help='cipher value settings to unsafe')

    def handle(self, **options):
        ciphers = options.get('cipher')
        if len(ciphers) > 0:
            self.stdout.write(f'''Unsave settings has generated''')
        for cipher in ciphers:
            try:
                cipher = cipher[len(settings.PREFIX_SAFE):len(cipher) - len(settings.SUFFIX_SAFE)] if cipher.upper().startswith(settings.PREFIX_SAFE.upper()) and cipher.upper().endswith(settings.SUFFIX_SAFE.upper()) else cipher
                plain = cipherutils.AesCipher(password=settings.djangosettings.SECRET_KEY, result_encoder=cipherutils.HexlifyEncoder(), force_text=True).decrypt(cipher)
                self.stdout.write(f'''\t{settings.PREFIX_SAFE}{cipher}{settings.SUFFIX_SAFE}: {plain}''')
            except Exception as e:
                self.stderr.write(f'''\terror unsafe {settings.PREFIX_SAFE}{cipher}{settings.SUFFIX_SAFE}''')
                logger.exception(e)
