import logging
import os
import subprocess
import sys

from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Management command to make translations project and applications'

    def add_arguments(self, parser):
        parser.add_argument('-a', '--application', dest='application', action='append', required=False, help='application name to translate')

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        applications = kwargs.get('application') or []
        try:
            parameter = [
                f'''--keep-pot''',
                f'''--no-wrap''',
                f'''--all''',
                f'''--ignore=env/*''',
                f'''--ignore=bin/*''',
                f'''--ignore=*/vendor/*''',
                f'''--ignore=*/admin/*''',
                f'''--ignore=*/index/*''',
                f'''--ignore=*/node_modules/*''',
                f'''--ignore=*/local_modules/*''',
                f'''--ignore=data/*''',
                f'''--ignore=empty/*''',
                f'''--ignore=assets/*''',
                f'''--ignore=library/*''',
            ]
            os.makedirs(os.path.join(djangosettings.BASE_DIR, 'locale'), exist_ok=True)
            for module in djangosettings.INSTALLED_MODULE:
                parameter.append(f'--ignore={module}/*')
                os.makedirs(os.path.join(djangosettings.BASE_DIR, module, 'locale'), exist_ok=True)
            command = f'''{sys.executable} manage.py makemessages --domain=django {' '.join(parameter)} --extension=html,py,xml'''
            logger.info('Make messages for %s, call: %s', 'project', command)
            process = subprocess.Popen(
                command,
                env=os.environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=djangosettings.BASE_DIR,
                shell=True,
            )
            for outline in iter(process.stdout.readline, ''):
                self.stdout.write(str(outline))
            for outline in iter(process.stderr.readline, ''):
                self.stderr.write(str(outline))
            command = f'''{sys.executable} manage.py makemessages --domain=djangojs {' '.join(parameter)} --extension=js,jsx,ts'''
            logger.info('Make messages for %s, call: %s', 'project', command)
            process = subprocess.Popen(
                command,
                env=os.environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=djangosettings.BASE_DIR,
                shell=True,
            )
            for outline in iter(process.stdout.readline, ''):
                self.stdout.write(str(outline))
            for outline in iter(process.stderr.readline, ''):
                self.stderr.write(str(outline))
            parameter = [
                f'''--keep-pot''',
                f'''--no-wrap''',
                f'''--all''',
                f'''--ignore=env/*''',
                f'''--ignore=bin/*''',
                f'''--ignore=vendor/*''',
                f'''--ignore=*/admin/*''',
                f'''--ignore=*/index/*''',
                f'''--ignore=node_modules/*''',
                f'''--ignore=local_modules/*''',
                f'''--ignore=data/*''',
                f'''--ignore=empty/*''',
                f'''--ignore=assets/*''',
                f'''--ignore=library/*''',
                f'''--ignore=dist/**''',
                f'''--ignore=node/util/i18n.js''',
            ]
            for module in [module for module in djangosettings.INSTALLED_MODULE if module in applications] if len(applications) > 0 else djangosettings.INSTALLED_MODULE:
                command = f'''{sys.executable} ..\\manage.py makemessages --domain=django {' '.join(parameter)} --extension=html,py,xml'''
                logger.info('Make messages for %s, call: %s', module, command)
                process = subprocess.Popen(
                    command,
                    env=os.environ,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    cwd=os.path.join(djangosettings.BASE_DIR, module),
                    shell=True,
                )
                for outline in iter(process.stdout.readline, ''):
                    self.stdout.write(str(outline))
                for outline in iter(process.stderr.readline, ''):
                    self.stderr.write(str(outline))
                command = f'''{sys.executable} ..\\manage.py makemessages --domain=djangojs {' '.join(parameter)} --extension=js,jsx,ts'''
                logger.info('Make messages for %s, call: %s', module, command)
                process = subprocess.Popen(
                    command,
                    env=os.environ,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    cwd=os.path.join(djangosettings.BASE_DIR, module),
                    shell=True,
                )
                for outline in iter(process.stdout.readline, ''):
                    self.stdout.write(str(outline))
                for outline in iter(process.stderr.readline, ''):
                    self.stderr.write(str(outline))
        except KeyboardInterrupt as e:
            self.stderr.write('Stop make locale')
            logger.exception(e)
        except Exception as e:
            self.stderr.write('Make locale can''t be run')
            logger.exception(e)
        else:
            process.stdout.close()
            process.stderr.close()
            code = process.wait()
            if code:
                raise subprocess.CalledProcessError(code, 'Make locale')
