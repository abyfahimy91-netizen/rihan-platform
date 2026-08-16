"""
Decorators برای ماژول RBAC
منطبق بر ADR-002 و D-017

استفاده:
    @require_permission('product.create')
    def create_product(request):
        ...

    @require_role('family_admin', 'admin')
    def admin_panel(request):
        ...

    @require_family
    def family_view(request):
        ...
"""
from __future__ import annotations

import functools
import logging
from typing import Callable, Optional, Tuple, Union

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from .services import RoleService

logger = logging.getLogger(__name__)


def require_permission(
    permission: Union[str, Tuple[str, ...]],
    login_url: Optional[str] = None
):
    """
    Decorator برای بررسی مجوز.
    
    Args:
        permission: یک مجوز یا tuple ای از مجوزها (حداقل یکی کافی است)
        login_url: URL برای redirect در صورت عدم احراز هویت
        
    مثال:
        @require_permission('product.create')
        @require_permission(('product.create', 'product.edit'))  # OR
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        @login_required(login_url=login_url)
        def wrapped_view(request: HttpRequest, *args, **kwargs):
            # تبدیل به tuple
            perms = (permission,) if isinstance(permission, str) else permission
            
            # بررسی مجوزها (OR logic - حداقل یکی کافی است)
            for perm in perms:
                if RoleService.has_permission(request.user, perm):
                    return view_func(request, *args, **kwargs)
            
            # همه مجوزها رد شدند
            logger.warning(
                f"Permission denied for {request.user.username}: "
                f"required one of {perms}"
            )
            raise PermissionDenied(
                f"شما مجوز لازم برای این عملیات را ندارید."
            )
        
        return wrapped_view
    return decorator


def require_role(
    *role_codes: str,
    login_url: Optional[str] = None
):
    """
    Decorator برای بررسی نقش.
    
    Args:
        *role_codes: کدهای نقش‌های مجاز (OR logic)
        login_url: URL برای redirect
        
    مثال:
        @require_role('admin', 'family_admin')
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        @login_required(login_url=login_url)
        def wrapped_view(request: HttpRequest, *args, **kwargs):
            user_primary_role = RoleService.get_user_primary_role(request.user)
            
            if user_primary_role and user_primary_role.code in role_codes:
                return view_func(request, *args, **kwargs)
            
            # admin همیشه دسترسی دارد
            if RoleService.has_permission(request.user, '*'):
                return view_func(request, *args, **kwargs)
            
            logger.warning(
                f"Role denied for {request.user.username}: "
                f"required one of {role_codes}, "
                f"has {user_primary_role.code if user_primary_role else 'none'}"
            )
            raise PermissionDenied(
                f"نقش شما برای این بخش مجاز نیست."
            )
        
        return wrapped_view
    return decorator


# Decoratorهای آماده برای استفاده مکرر
require_family = require_role('family_admin', 'family_member', 'admin')
"""دسترسی فقط برای اعضای خانواده و مدیر"""

require_admin = require_role('admin')
"""دسترسی فقط برای مدیر"""

require_supplier = require_role('supplier', 'admin')
"""دسترسی برای تأمین‌کننده و مدیر"""

require_customer = require_role('customer', 'family_admin', 'family_member', 'admin')
"""دسترسی برای مشتری و خانواده"""
