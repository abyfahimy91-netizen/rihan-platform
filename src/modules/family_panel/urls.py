"""
URLs ماژول family_panel
منطبق بر US-017, US-026, US-027
"""
from django.urls import path
from .views import (
    dashboard_view,
    dashboard_summary_view,
    dashboard_alerts_view,
)

app_name = 'family_panel'

urlpatterns = [
    # داشبورد (US-017)
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/summary/', dashboard_summary_view, name='dashboard-summary'),
    path('dashboard/alerts/', dashboard_alerts_view, name='dashboard-alerts'),
]
