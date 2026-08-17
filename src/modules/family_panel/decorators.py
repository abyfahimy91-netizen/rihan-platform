"""
Decorators ماژول family_panel
منطبق بر ADR-006 (OTP) + M5 (RBAC)

این decorators یک لایه اضافی روی decorators های M5 هستند.
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

from src.modules.rbac.decorators import require_role
from .services import FamilyService


def require_family(view_func):
    """
    Decorator برای دسترسی به پنل خانواده.
    
    استفاده:
        @require_family
        def family_dashboard(request):
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not FamilyService.is_family_member(request.user):
            raise PermissionDenied(
                "شما دسترسی به پنل خانواده را ندارید."
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# Decoratorهای تخصصی‌تر
require_main_admin = require_role('admin')
"""دسترسی فقط برای ادمین اصلی"""

require_family_admin = require_role('family_admin', 'admin')
"""دسترسی برای ادمین خانواده و ادمین اصلی"""

require_family_member = require_role(
    'family_admin', 'family_member', 'admin'
)
"""دسترسی برای تمام اعضای خانواده"""
