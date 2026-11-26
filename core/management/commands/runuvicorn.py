import logging
import multiprocessing
import os
from argparse import RawTextHelpFormatter
from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

from core import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = f'''
Management command to run uvicorn
Example
👉 cwd runuvicorn'
👉 cwd runuvicorn --host=0.0.0.0 -p 8888'
👉 cwd runuvicorn --workers=10'
👉 cwd runuvicorn --reload=True'
👉 cwd runuvicorn -key cert/erpro.key -crt cert/erpro.crt'
'''

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            action='store',
            default='0.0.0.0',
            dest='host',
            help='Set https ssl host',
        )
        parser.add_argument(
            '-p',
            '--port',
            action='store',
            default=getattr(djangosettings, 'PORT', 8008),
            help='Set https ssl port',
        )
        parser.add_argument(
            '-key',
            '--keystore',
            action='store',
            default='cert/erpro.key',
            help='Set https ssl keystore file',
        )
        parser.add_argument(
            '-crt',
            '--certificate',
            action='store',
            default='cert/erpro.crt',
            help='Set https ssl certificate file',
        )
        parser.add_argument(
            '--workers',
            action='store',
            default=1,
            help='Set workers',
        )
        parser.add_argument(
            '--reload',
            action='store',
            default=False,
            help='Tells uvicorn to auto reloader',
        )

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        try:
            import asyncio
            from uvicorn.config import Config
            from uvicorn.server import Server
            from setup.asgi import application
            server = Server(Config(
                application,
                host=kwargs.get('host'),
                port=int(kwargs.get('port')),
                ssl_keyfile=kwargs.get('keystore'),
                ssl_certfile=kwargs.get('certificate'),
                reload=kwargs.get('reload'),
                lifespan='off',
                log_config=settings.djangosettings.LOGGING,
                log_level=logging.INFO,
                workers=int(kwargs.get('workers')),
            ))
            with open(os.path.join(settings.djangosettings.BASE_DIR.absolute(), f'data/{os.path.splitext(os.path.basename(__file__))[0]}.pid'), 'w') as pid:
                pid.write(str(multiprocessing.current_process().pid))
            import re as regex
            from importlib.metadata import version
            djangosettings.PROJECT.update(
                SERVER='Uvicorn',
                UVICORN=regex.sub(r'[^\d.]', '', version('uvicorn')),
            )
            server.run()
        except KeyboardInterrupt as e:
            self.stdout.write('Stop uvicorn server, ' + str(e))
            logger.exception(e)
        except Exception as e:
            self.stdout.write('Uvicorn server can''t be run, ' + str(e))
            logger.exception(e)
