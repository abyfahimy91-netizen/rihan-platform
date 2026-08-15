"""
M13: Visual Identity URLs
"""
from django.urls import path
from .views import HomeView

app_name = 'visual_identity'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
]
