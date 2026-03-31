import logging

from django.core.management.base import BaseCommand

from core.utils import search

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'List all registed models by Search.'

    def handle(self, *args, **options):
        self.stdout.write('The following models are registed for the Search search engine:\n')
        for model in search.get_registered_models():
            self.stdout.write('👉 %s.%s\n' % (model._meta.app_label, model.__name__, ))
