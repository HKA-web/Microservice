import logging

from django.urls import path, include
from rest_framework import routers

from core.apis import views #change this

logger = logging.getLogger(__name__)

router = routers.DefaultRouter()


app_name = 'api'
urlpatterns = [
    path('', include(router.urls)),
]