import logging

from django.conf import settings
from django.urls import path, include, re_path

from core import views #change this

logger = logging.getLogger(__name__)

app_name = 'core'
urlpatterns = [

    path('api/', include('core.apis.urls')),
]