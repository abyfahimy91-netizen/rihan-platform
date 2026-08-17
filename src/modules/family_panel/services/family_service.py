"""
Family Service برای مدیریت ادمین‌های خانواده
منطبق بر ADR-006 (OTP) + M5 (RBAC)

این سرویس یک wrapper روی M10 (Auth) + M5 (RBAC) است.
- احراز هویت: M10 (OTP)
- نقش‌ها: M5 (RBAC) - family_admin, admin, observer
"""
from __future__ import annotations

import logging
from typing import List, Optional

from django.contrib.auth import get_user_model

from src.modules.rbac.services import RoleService
from ..models import ActivityLog

logger = logging.getLogger(__name__)

User = get_user_model()


class FamilyService:
    """
    سرویس مدیریت پنل خانواده.
    
    اصل: ادمین‌های خانواده = کاربران عادی با نقش family_admin/admin
    
    ورود: با OTP (M10)
    نقش: از RBAC (M5)
    """
    
    FAMILY_ROLES = ['family_admin', 'family_member', 'admin', 'observer']
    
    @classmethod
    def is_family_member(cls, user) -> bool:
        """بررسی اینکه آیا کاربر عضو خانواده است"""
        if not user or not user.is_authenticated:
            return False
        
        primary_role = RoleService.get_user_primary_role(user)
        if not primary_role:
            return False
        
        return primary_role.code in cls.FAMILY_ROLES
    
    @classmethod
    def get_family_members(cls) -> List[User]:
        """دریافت لیست اعضای خانواده"""
        from src.modules.rbac.models import UserRole
        user_roles = UserRole.objects.filter(
            role__code__in=cls.FAMILY_ROLES,
            is_primary=True
        ).select_related('user', 'role')
        
        return [ur.user for ur in user_roles]
    
    @classmethod
    def add_family_member(
        cls,
        phone: str,
        first_name: str,
        last_name: str,
        role_code: str = 'family_admin',
        granted_by=None
    ) -> User:
        """
        افزودن عضو خانواده.
        
        Args:
            phone: شماره موبایل (username در M10)
            first_name: نام
            last_name: نام خانوادگی
            role_code: کد نقش (family_admin, family_member, observer)
            granted_by: اعطاکننده نقش
            
        Returns:
            User ایجاد شده
        """
        if role_code not in cls.FAMILY_ROLES:
            raise ValueError(f"Invalid role: {role_code}")
        
        # ایجاد یا دریافت کاربر (بر اساس شماره موبایل)
        user, created = User.objects.get_or_create(
            username=phone,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True,
            }
        )
        
        if not created:
            # به‌روزرسانی اطلاعات
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=['first_name', 'last_name'])
        
        # اعطای نقش family
        RoleService.assign_role(
            user=user,
            role_code=role_code,
            granted_by=granted_by,
            is_primary=True
        )
        
        logger.info(f"Added family member: {phone} with role {role_code}")
        return user
    
    @classmethod
    def deactivate_family_member(cls, user, deactivated_by=None) -> None:
        """غیرفعال‌سازی عضو خانواده (حذف نرم)"""
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        # ثبت در ActivityLog
        ActivityLog.objects.create(
            user=deactivated_by or user,
            action='admin_deactivate',
            description=f"غیرفعال‌سازی {user.username}",
            entity_type='user',
            entity_id=str(user.pk),
        )
        
        logger.info(f"Deactivated family member: {user.username}")
    
    @classmethod
    def log_activity(
        cls,
        user,
        action: str,
        description: str = '',
        entity_type: str = '',
        entity_id: str = '',
        ip_address: str = None,
        user_agent: str = '',
        changes: dict = None
    ) -> ActivityLog:
        """ثبت لاگ فعالیت ادمین خانواده"""
        return ActivityLog.objects.create(
            user=user,
            action=action,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes or {},
        )
