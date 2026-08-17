"""
URLs ماژول family_panel
منطبق بر US-017, US-025, US-026, US-027
"""
from django.urls import path
from .views import (
    # Dashboard
    dashboard_view,
    dashboard_summary_view,
    dashboard_alerts_view,
    # Admin Management
    list_family_members,
    add_family_member,
    deactivate_family_member,
    reactivate_family_member,
    # Activity Log
    activity_log_list,
    activity_log_stats,
)

app_name = 'family_panel'

urlpatterns = [
    # داشبورد (US-017)
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/summary/', dashboard_summary_view, name='dashboard-summary'),
    path('dashboard/alerts/', dashboard_alerts_view, name='dashboard-alerts'),
    
    # مدیریت کاربران خانواده (US-025)
    path('members/', list_family_members, name='list-members'),
    path('members/add/', add_family_member, name='add-member'),
    path('members/deactivate/', deactivate_family_member, name='deactivate-member'),
    path('members/reactivate/', reactivate_family_member, name='reactivate-member'),
    
    # لاگ فعالیت‌ها (US-026)
    path('activity-log/', activity_log_list, name='activity-log'),
    path('activity-log/stats/', activity_log_stats, name='activity-log-stats'),
]
