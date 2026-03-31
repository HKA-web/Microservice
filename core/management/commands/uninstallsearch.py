import logging

from django.core.management.base import BaseCommand

from core.utils.search import get_backend

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Destroys the database indices needed by Search.'

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1))
        backend = get_backend()
        if not backend.requires_installation:
            if verbosity >= 2:
                self.stdout.write('Your search backend does not require installation.\n')
        elif backend.is_installed():
            backend.do_uninstall()
            if verbosity >= 2:
                self.stdout.write('Search has been successfully uninstalled.\n')
        else:
            if verbosity >= 2:
                self.stdout.write('Search is not installed.\n')
