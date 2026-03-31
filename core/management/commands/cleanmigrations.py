import logging
import os

from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Management command to run clean all migrations'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        migrations = []
        for module in djangosettings.INSTALLED_MODULE:
            for (path, dirs, files) in os.walk(os.path.join(djangosettings.BASE_DIR, module, 'migrations')):
                for file in files:
                    if os.path.isfile(os.path.join(path, file)) and file.endswith('.py') and file not in ['__init__.py', '0000_schema.py']:
                        migrations.append(os.path.join(path, file))
        try:
            for migration in migrations:
                os.remove(migration)
                self.stdout.write('Remove migration ' + migration)
        except KeyboardInterrupt as e:
            self.stdout.write('Stop clean all migrations, ' + str(e))
            logger.exception(e)
        except Exception as e:
            self.stdout.write('Clean all migrations can''t be run ' + str(e))
            logger.exception(e)
        else:
            pass
