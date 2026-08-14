from django.urls import path
from .views import health_check, home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('api/health/', health_check, name='health_check'),
]
