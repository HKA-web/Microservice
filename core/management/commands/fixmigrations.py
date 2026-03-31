import logging
import os

from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Management command to run fix all migrations'

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
                content = open(migration, 'r')
                recontent = []
                for line in content.readlines():
                    if not any(find in line.strip() for find in ['_contenttype_id']):
                        recontent.append(line)
                content.close()
                content = open(migration, 'w')
                content.writelines(recontent)
                content.close()
                self.stdout.write('Fix migration ' + migration)
        except KeyboardInterrupt as e:
            self.stdout.write('Stop fix all migrations')
            logger.exception(e)
        except Exception as e:
            self.stdout.write('Fix all migrations can''t be run')
            logger.exception(e)
        else:
            pass
