"""Views ماژول family_panel"""
from .dashboard import (
    dashboard_view,
    dashboard_summary_view,
    dashboard_alerts_view,
)
from .admin_management import (
    list_family_members,
    add_family_member,
    deactivate_family_member,
    reactivate_family_member,
)
from .activity_log import (
    activity_log_list,
    activity_log_stats,
)

__all__ = [
    # Dashboard
    'dashboard_view',
    'dashboard_summary_view',
    'dashboard_alerts_view',
    # Admin Management
    'list_family_members',
    'add_family_member',
    'deactivate_family_member',
    'reactivate_family_member',
    # Activity Log
    'activity_log_list',
    'activity_log_stats',
]
