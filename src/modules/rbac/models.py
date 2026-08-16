"""
مدل‌های ماژول RBAC ریهان (M5)
منطبق بر ADR-002 بخش ۲.۱ و ۲.۳

مدل‌ها:
- Role: نقش‌های سیستمی
- UserRole: ارتباط M2M بین کاربر و نقش
"""
from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Role(models.Model):
    """
    نقش سیستمی.
    
    منطبق بر ADR-002 بخش ۲.۱:
    - id: UUID PK
    - name: نام نقش
    - code: کد فنی یکتا
    - permissions: لیست مجوزها (JSONB)
    - is_system: نقش سیستمی (غیرقابل حذف)
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه نقش'
    )
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='نام نقش',
        help_text='مثال: مدیر، عضو خانواده، تأمین‌کننده'
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='کد فنی',
        help_text='مثال: admin, family_admin, customer'
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='توضیحات'
    )
    permissions = models.JSONField(
        default=list,
        blank=True,
        verbose_name='لیست مجوزها',
        help_text='مثال: ["product.create", "order.view"]'
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name='نقش سیستمی',
        help_text='نقش‌های سیستمی قابل حذف نیستند'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخرین به‌روزرسانی'
    )
    
    class Meta:
        app_label = 'rbac'
        verbose_name = 'نقش'
        verbose_name_plural = 'نقش‌ها'
        ordering = ['name']
    
    def __str__(self) -> str:
        return self.name
    
    def has_permission(self, permission: str) -> bool:
        """بررسی داشتن یک مجوز خاص"""
        return permission in self.permissions
    
    def add_permission(self, permission: str) -> None:
        """افزودن مجوز"""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.save(update_fields=['permissions', 'updated_at'])
    
    def remove_permission(self, permission: str) -> None:
        """حذف مجوز"""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.save(update_fields=['permissions', 'updated_at'])


class UserRole(models.Model):
    """
    ارتباط بین کاربر و نقش (Many-to-Many).
    
    منطبق بر ADR-002 بخش ۲.۳:
    - user_id: FK به User
    - role_id: FK به Role
    - granted_by: کاربر اعطاکننده
    - is_primary: نقش اصلی (در MVP هر کاربر یک نقش اصلی دارد)
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='roles',
        verbose_name='کاربر'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='نقش'
    )
    granted_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='تاریخ اعطا'
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_roles',
        verbose_name='اعطاکننده'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='نقش اصلی',
        help_text='در MVP هر کاربر یک نقش اصلی دارد'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    
    class Meta:
        app_label = 'rbac'
        verbose_name = 'نقش کاربر'
        verbose_name_plural = 'نقش‌های کاربران'
        ordering = ['-is_primary', '-granted_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'role'],
                name='unique_user_role'
            ),
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_primary=True),
                name='unique_primary_role_per_user'
            ),
        ]
    
    def __str__(self) -> str:
        primary = " (اصلی)" if self.is_primary else ""
        return f"{self.user.username} - {self.role.name}{primary}"
