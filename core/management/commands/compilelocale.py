import logging
import os
import subprocess
import sys

from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Management command to compile translated project and applications'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        try:
            parameter = [
                f'''--ignore=env/*''',
                f'''--ignore=bin/*''',
                f'''--ignore=*/vendor/*''',
                f'''--ignore=*/admin/*''',
                f'''--ignore=*/index/*''',
                f'''--ignore=*/node_modules/*''',
                f'''--ignore=*/local_modules/*''',
                f'''--ignore=data/*''',
                f'''--ignore=assets/*''',
                f'''--ignore=library/*''',
            ]
            command = f'''{sys.executable} manage.py compilemessages {' '.join(parameter)}'''
            logger.info('Call %s', command)
            process = subprocess.Popen(
                command,
                env=os.environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=djangosettings.BASE_DIR,
                encoding='cp437',
                shell=True,
            )
            for outline in iter(process.stdout.readline, ''):
                self.stdout.write(str(outline))
            for outline in iter(process.stderr.readline, ''):
                self.stderr.write(str(outline))
        except KeyboardInterrupt as e:
            self.stderr.write('Stop compile locale')
            logger.exception(e)
        except Exception as e:
            self.stderr.write('Compile locale can''t be run')
            logger.exception(e)
        else:
            process.stdout.close()
            process.stderr.close()
            code = process.wait()
            if code:
                raise subprocess.CalledProcessError(code, 'Compile locale')
