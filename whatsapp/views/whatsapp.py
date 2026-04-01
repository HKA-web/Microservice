import logging

from django.shortcuts import render
from django.views import View
from django.conf import settings as djangosettings

logger = logging.getLogger(__name__)


class WhatsappView(View):
    def get(self, request):
        session_id = request.GET.get('session', '6285648007953')
        return render(request, 'whatsapp/index.html', dict(
            session_id= session_id,
            API_DOCS= getattr(djangosettings, 'WHATSAPP', {}).get('DOCS', ''),
        ))
