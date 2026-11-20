import logging

from django.shortcuts import render
from django.views import View
from django.contrib.sites.models import Site
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


class IndexView(View):
    def get(self, request):
        port = getattr(djangosettings, 'WHATSAPP', {}).get('PORT')
        domain = Site.objects.get_current().domain
        docs_url = f"http://{domain}:{port}/docs/"
        return render(request, 'index.html', dict(
            WHATSAPP_DOCS=docs_url,
        ))
