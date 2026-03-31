import logging

from django.shortcuts import render
from django.views import View

logger = logging.getLogger(__name__)


class IndexView(View):
    def get(self, request):
        greeting = {
            'title': 'Dashboard',
            'pageview': 'Nazox',
        }
        return render(request, 'index.html', greeting)
