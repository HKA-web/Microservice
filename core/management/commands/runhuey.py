import logging
import os
from multiprocessing import current_process

from library.djangohuey.management.commands import djangohuey as RunHuey

logger = logging.getLogger(__name__)


class Command(RunHuey.Command):
    help = 'Management command to run huey task queue'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'''{os.linesep}{self.help}{os.linesep}''')
        from django.conf import settings as djangosettings
        from library.djangohuey import (on_startup, signal)
        from library.hueymonitor.tasks import (startup_handler, store_signals)
        self.stdout.write(f'''Queue default: 👉 {djangosettings.HUEYS['default']}''')
        self.stdout.write(f'''Queue available''')
        for key, queue in djangosettings.HUEYS['queues'].items():
            self.stdout.write(f'''👉 {key}, run with parameter --queue {key}''')
            signal(queue=key, )(store_signals)
            on_startup(queue=key, )(startup_handler)
        self.stdout.write(f'''{os.linesep}{os.linesep}''')
        with open(os.path.join(djangosettings.BASE_DIR.absolute(), f'data/{os.path.splitext(os.path.basename(__file__))[0]}{kwargs.get('queue') if kwargs.get('queue') is not None else ''}.pid'), 'w') as pid:
            pid.write(str(current_process().pid))
        super(Command, self).handle(self, args, **kwargs)
