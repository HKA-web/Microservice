import logging
import multiprocessing
import os
from argparse import RawTextHelpFormatter

from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''
Management command to run daphne
Example
👉 cwd daphne
👉 cwd daphne -p 8888
👉 cwd daphne -s True
👉 cwd daphne -s True -key cert/erpro.key -crt cert/erpro.crt
'''

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--port',
            action='store',
            default=getattr(djangosettings, 'PORT', 8008),
            help='Set https ssl port'
        )
        parser.add_argument(
            '-s',
            '--secure',
            action='store',
            default=False,
            help='Set run secure with ssl',
        )
        parser.add_argument(
            '-key',
            '--keystore',
            action='store',
            default='cert/erpro.key',
            help='Set path to keystore file'
        )
        parser.add_argument(
            '-crt',
            '--certificate',
            action='store',
            default='cert/erpro.crt',
            help='Set path to certificate file'
        )

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        try:
            from daphne.cli import CommandLineInterface
            with open(os.path.join(djangosettings.BASE_DIR.absolute(), f'data/{os.path.splitext(os.path.basename(__file__))[0]}.pid'), 'w') as pid:
                pid.write(str(multiprocessing.current_process().pid))
            import re as regex
            from importlib.metadata import version
            djangosettings.PROJECT.update(
                SERVER='Daphne',
                DAPHNE=regex.sub(r'[^\d.]', '', version('daphne')),
            )
            port = str(kwargs.get('port') or getattr(djangosettings, 'PORT', 8008))
            if kwargs.get('secure', False):
                CommandLineInterface().run((
                    'setup.asgi:application',
                    '--endpoint', f'''ssl:{port}:privateKey={str(kwargs.get('keystore'))}:certKey={str(kwargs.get('certificate'))}''',
                ))
            else:
                endpoint = []
                hosts = djangosettings.ALLOWED_HOSTS if len(djangosettings.ALLOWED_HOSTS) > 0 else [os.environ.get('LOCAL_ADDRESS'), ]
                if '*' in hosts or '0.0.0.0' in hosts:
                    endpoint.extend(['--endpoint', f'tcp:port={port}:interface=0.0.0.0'])
                else:
                    for host in hosts:
                        endpoint.extend(['--endpoint', f'tcp:port={port}:interface={host}'])
                CommandLineInterface().run(('setup.asgi:application',) + tuple(endpoint))
        except KeyboardInterrupt as e:
            self.stdout.write('Stop daphne server, ' + str(e))
            logger.exception(e)
        except Exception as e:
            self.stdout.write('Daphne server can''t be run, ' + str(e))
            logger.exception(e)
