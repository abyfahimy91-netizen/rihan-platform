from django.urls import path
from .views import health_check, home_view, about_view

urlpatterns = [
    path('', home_view, name='home'),
    path('about/', about_view, name='about'),
    path('api/health/', health_check, name='health_check'),
]
