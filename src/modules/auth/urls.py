from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet

app_name = 'auth'

router = DefaultRouter()
router.register(r'', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
]
