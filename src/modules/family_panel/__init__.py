"""
ماژول پنل خانواده ریهان (M3)
منطبق بر ADR-006 (OTP) + M5 (RBAC)
"""


def __getattr__(name):
    """Lazy imports"""
    if name == 'FamilyService':
        from .services import FamilyService
        return FamilyService
    if name == 'ActivityLog':
        from .models import ActivityLog
        return ActivityLog
    if name == 'SiteSettings':
        from .models import SiteSettings
        return SiteSettings
    if name in ('require_family', 'require_main_admin',
                'require_family_admin', 'require_family_member'):
        from . import decorators
        return getattr(decorators, name)
    
    raise AttributeError(f"module 'src.modules.family_panel' has no attribute {name!r}")


__all__ = [
    'FamilyService',
    'ActivityLog',
    'SiteSettings',
    'require_family',
    'require_main_admin',
    'require_family_admin',
    'require_family_member',
]
