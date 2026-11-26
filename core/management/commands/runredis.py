import logging
import os
import subprocess
import sys

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Management command to run redis server'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}{os.linesep}''')
        os.environ['PATH'] += os.pathsep + os.pathsep.join(sys.path)
        args = dict()
        for path in filter(lambda path: os.path.exists(os.path.join(path, 'redis.conf')), sys.path):
            args['cwd'] = os.path.join(path)
        try:
            process = subprocess.Popen(
                'redis-server redis.conf',
                env=os.environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True,
                **args
            )
            from django.conf import settings as djangosettings
            with open(os.path.join(djangosettings.BASE_DIR.absolute(), f'data/{os.path.splitext(os.path.basename(__file__))[0]}.pid'), 'w') as pid:
                pid.write(str(process.pid))
            for outline in iter(process.stdout.readline, ''):
                self.stdout.write(str(outline))
            for outline in iter(process.stderr.readline, ''):
                self.stderr.write(str(outline))
        except KeyboardInterrupt as e:
            self.stdout.write('Stop redis server')
            logger.exception(e)
        except Exception as e:
            self.stdout.write('Redis server can''t be run')
            logger.exception(e)
        else:
            process.stdout.close()
            code = process.wait()
            if code:
                raise subprocess.CalledProcessError(code, 'Redis server run')
