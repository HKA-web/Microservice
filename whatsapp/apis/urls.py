from django.urls import path, include
from rest_framework import routers

from whatsapp.apis import views #change this

router = routers.DefaultRouter()

app_name = 'api'
urlpatterns = [
    path('', include(router.urls), name='api'),
]
