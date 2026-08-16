"""
RBAC Middleware - بررسی مجوزها در سطح request
منطبق بر ADR-006 بخش ۱۰ (شفاف‌سازی Middleware)
"""
from __future__ import annotations

import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RbacMiddleware:
    """
    Middleware سبک برای RBAC.
    
    این Middleware:
    - request.user را از Session/DeviceToken می‌خواند (قبلاً توسط AuthMiddleware تنظیم شده)
    - نقش اصلی کاربر را در request.primary_role ذخیره می‌کند
    - مجوزهای کاربر را در request.permissions ذخیره می‌کند
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # اضافه کردن اطلاعات RBAC به request
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                from ..services import RoleService
                primary_role = RoleService.get_user_primary_role(request.user)
                request.primary_role = primary_role
                request.permissions = primary_role.permissions if primary_role else []
            except Exception:
                request.primary_role = None
                request.permissions = []
        else:
            request.primary_role = None
            request.permissions = []
        
        return self.get_response(request)
