import logging

from django.core.management.base import BaseCommand

from core.utils.search import get_backend

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creates the database indices needed by Search.'

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1))
        backend = get_backend()
        if not backend.requires_installation:
            if verbosity >= 2:
                self.stdout.write('Your search backend does not require installation.\n')
        elif backend.is_installed():
            if verbosity >= 2:
                self.stdout.write('Search is already installed.\n')
        else:
            backend.do_install()
            if verbosity >= 2:
                self.stdout.write('Search has been successfully installed.\n')
