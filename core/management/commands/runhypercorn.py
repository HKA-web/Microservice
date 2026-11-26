import logging
import multiprocessing
import os
from argparse import RawTextHelpFormatter
from django.conf import settings as djangosettings
from django.core.management.base import BaseCommand

from core import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''
Management command to run hypercorn
Example
👉 cwd runhypercorn'
👉 cwd runhypercorn -s True'
👉 cwd runhypercorn --reload=True'
👉 cwd runhypercorn --hosts=0.0.0.0,127.0.0.1 -p 8888'
👉 cwd runhypercorn -key cert/erpro.key -crt cert/erpro.crt'
'''

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--secure',
            action='store',
            default=False,
            help='Set run secure with ssl',
        )
        parser.add_argument(
            '--hosts',
            action='append',
            default=[os.environ.get('LOCAL_ADDRESS'), '0.0.0.0', '[::]'],
            dest='hosts',
            help='hosts list [,]',
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
            '--reload',
            action='store',
            default=False,
            help='Tells hypercorn to auto reloader',
        )

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        try:
            from django.core.management.commands import runserver
            import asyncio
            from hypercorn.config import Config
            from hypercorn.asyncio import serve
            from hypercorn.middleware import HTTPToHTTPSRedirectMiddleware
            from setup.asgi import application
            redirected = HTTPToHTTPSRedirectMiddleware(application, host=kwargs.get('hosts')[0])
            config = Config()
            config.bind = [f'''{host}:{kwargs.get('port')}''' for host in kwargs.get('hosts')]
            if kwargs.get('secure'):
                config.insecure_bind = [f'''{runserver.Command.default_addr}:{runserver.Command.default_port}''']
                config.keyfile = str(kwargs.get('keystore'))
                config.certfile = str(kwargs.get('certificate'))
            config.use_reloader = kwargs.get('reload')
            config.pid_path = os.path.join(settings.djangosettings.BASE_DIR.absolute(), f'data/{os.path.splitext(os.path.basename(__file__))[0]}.pid')
            config.loglevel = logging.getLevelName(logging.INFO)
            config.logconfig_dict = settings.djangosettings.LOGGING
            with open(os.path.join(settings.djangosettings.BASE_DIR.absolute(), f'data/{os.path.splitext(os.path.basename(__file__))[0]}.pid'), 'w') as pid:
                pid.write(str(multiprocessing.current_process().pid))
            import re as regex
            from importlib.metadata import version
            djangosettings.PROJECT.update(
                SERVER='Hypercorn',
                HYPERCORN=regex.sub(r'[^\d.]', '', version('hypercorn')),
            )
            if kwargs.get('secure'):
                asyncio.run(serve(redirected, config))
            else:
                asyncio.run(serve(application, config))
        except KeyboardInterrupt as e:
            self.stdout.write('Stop hypercorn server, ' + str(e))
            logger.exception(e)
        except Exception as e:
            self.stdout.write('Hypercorn server can''t be run, ' + str(e))
            logger.exception(e)
