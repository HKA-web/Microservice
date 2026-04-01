import logging

from django.shortcuts import render
from django.views import View
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


class IndexView(View):
    def get(self, request):
        return render(request, 'index.html', dict(
        ))
