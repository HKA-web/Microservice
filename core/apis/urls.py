import logging

from django.urls import path, include
from rest_framework import routers

from core.apis import views

logger = logging.getLogger(__name__)

router = routers.DefaultRouter()
router.register(r'datasource', views.DatasourceViewSet, basename='datasource')

app_name = 'api'
urlpatterns = [
    path('', include(router.urls)),
]
