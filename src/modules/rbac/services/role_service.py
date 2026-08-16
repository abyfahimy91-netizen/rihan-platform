"""
Role Service برای ماژول RBAC
منطبق بر ADR-002 و D-017

FIX: استفاده از update_or_create به‌جای get_or_create در assign_role
"""
from __future__ import annotations

import logging
from typing import List, Optional

from django.contrib.auth import get_user_model

from ..models import Role, UserRole

logger = logging.getLogger(__name__)

User = get_user_model()


class RoleService:
    """
    سرویس مدیریت نقش‌ها.
    
    منطبق بر ADR-002:
    - نقش‌های سیستمی پیش‌فرض
    - هر کاربر یک نقش اصلی (MVP)
    """
    
    # نقش‌های سیستمی پیش‌فرض (ADR-002 بخش ۲.۱)
    SYSTEM_ROLES = [
        {
            'name': 'مشتری',
            'code': 'customer',
            'description': 'مشتری عادی با دسترسی به پروفایل و سفارش‌ها',
            'permissions': ['profile.view', 'profile.edit', 'order.view', 'order.create'],
            'is_system': True,
        },
        {
            'name': 'مدیر',
            'code': 'admin',
            'description': 'مدیر سیستم با دسترسی کامل',
            'permissions': ['*'],
            'is_system': True,
        },
        {
            'name': 'مدیر خانواده',
            'code': 'family_admin',
            'description': 'مدیر خانواده (بنیان‌گذار و همسر)',
            'permissions': [
                'product.view', 'product.create', 'product.edit', 'product.delete',
                'order.view', 'order.edit', 'order.delete',
                'supplier.view', 'supplier.create', 'supplier.edit',
                'finance.view', 'finance.report',
                'user.view', 'user.edit',
            ],
            'is_system': True,
        },
        {
            'name': 'عضو خانواده',
            'code': 'family_member',
            'description': 'عضو خانواده (بچه‌ها در آینده)',
            'permissions': [
                'product.view', 'product.edit',
                'order.view', 'order.edit',
            ],
            'is_system': True,
        },
        {
            'name': 'ناظر',
            'code': 'observer',
            'description': 'ناظر با دسترسی فقط مشاهده',
            'permissions': [
                'product.view', 'order.view', 'supplier.view', 'finance.view',
            ],
            'is_system': True,
        },
        {
            'name': 'تأمین‌کننده',
            'code': 'supplier',
            'description': 'تأمین‌کننده با دسترسی محدود به سفارش‌های خودش',
            'permissions': [
                'order.view_own', 'product.view',
            ],
            'is_system': True,
        },
    ]
    
    @classmethod
    def create_system_roles(cls) -> int:
        """
        ایجاد نقش‌های سیستمی پیش‌فرض.
        
        Returns:
            تعداد نقش‌های ایجاد شده
        """
        created = 0
        for role_data in cls.SYSTEM_ROLES:
            role, was_created = Role.objects.get_or_create(
                code=role_data['code'],
                defaults=role_data
            )
            if was_created:
                created += 1
                logger.info(f"Created system role: {role.name}")
        
        return created
    
    @classmethod
    def get_role_by_code(cls, code: str) -> Optional[Role]:
        """دریافت نقش بر اساس کد"""
        try:
            return Role.objects.get(code=code)
        except Role.DoesNotExist:
            return None
    
    @classmethod
    def assign_role(
        cls,
        user,
        role_code: str,
        granted_by=None,
        is_primary: bool = True
    ):
        """
        اعطای نقش به کاربر.
        
        FIX: استفاده از update_or_create به‌جای get_or_create
        تا is_primary همیشه به‌روز شود.
        
        Args:
            user: کاربر
            role_code: کد نقش
            granted_by: اعطاکننده
            is_primary: نقش اصلی (در MVP باید True باشد)
            
        Returns:
            UserRole ایجاد یا به‌روز شده
        """
        role = cls.get_role_by_code(role_code)
        if not role:
            raise ValueError(f"Role '{role_code}' not found")
        
        # در MVP، اگر is_primary=True، ابتدا نقش اصلی قبلی را غیرفعال کن
        if is_primary:
            UserRole.objects.filter(user=user, is_primary=True).update(is_primary=False)
        
        # FIX: update_or_create به‌جای get_or_create
        user_role, created = UserRole.objects.update_or_create(
            user=user,
            role=role,
            defaults={
                'granted_by': granted_by,
                'is_primary': is_primary,
            }
        )
        
        if created:
            logger.info(f"Assigned role '{role.name}' to {user.username}")
        else:
            logger.info(f"Updated role '{role.name}' for {user.username} (is_primary={is_primary})")
        
        return user_role
    
    @classmethod
    def get_user_primary_role(cls, user) -> Optional[Role]:
        """دریافت نقش اصلی کاربر"""
        try:
            user_role = UserRole.objects.get(user=user, is_primary=True)
            return user_role.role
        except UserRole.DoesNotExist:
            return None
    
    @classmethod
    def get_user_roles(cls, user) -> List[Role]:
        """دریافت تمام نقش‌های کاربر"""
        return [ur.role for ur in UserRole.objects.filter(user=user)]
    
    @classmethod
    def has_permission(cls, user, permission: str) -> bool:
        """
        بررسی داشتن مجوز.
        
        Args:
            user: کاربر
            permission: مجوز (مثال: 'product.create')
            
        Returns:
            True اگر کاربر مجوز را دارد
        """
        primary_role = cls.get_user_primary_role(user)
        if not primary_role:
            return False
        
        # نقش admin همه مجوزها را دارد
        if '*' in primary_role.permissions:
            return True
        
        return permission in primary_role.permissions
    
    @classmethod
    def revoke_role(cls, user, role_code: str) -> bool:
        """
        لغو نقش کاربر.
        
        Returns:
            True اگر نقش لغو شد
        """
        role = cls.get_role_by_code(role_code)
        if not role:
            return False
        
        deleted_count, _ = UserRole.objects.filter(
            user=user, role=role
        ).delete()
        
        return deleted_count > 0
