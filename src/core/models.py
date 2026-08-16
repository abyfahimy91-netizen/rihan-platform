"""
مدل‌های هسته ریهان
- FeatureFlag: سوئیچ فعال/غیرفعال ماژول‌ها و ویژگی‌ها
منطبق بر:
- ADR-004 (Feature Flags)
- ADR-002 (AuditLog)
- D-023, D-069

نکته مهم درباره is_system:
- is_system=True: پرچم‌های حیاتی سیستمی (غیرقابل حذف، قابل غیرفعال‌سازی فقط توسط superuser)
- is_system=False: پرچم‌های عادی (قابل مدیریت کامل توسط ادمین)
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class FeatureFlag(models.Model):
    """
    Feature Flag برای فعال/غیرفعال کردن ماژول‌ها و ویژگی‌ها از پنل ادمین.
    تغییر فوری بدون نیاز به redeploy.
    """

    class Category(models.TextChoices):
        MODULE = 'MODULE', 'ماژول کامل (M1 تا M14)'
        FEATURE = 'FEATURE', 'ویژگی خاص در یک ماژول'
        EXPERIMENT = 'EXPERIMENT', 'آزمایش A/B'
        SYSTEM = 'SYSTEM', 'سیستمی (فقط ادمین‌های ارشد)'

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='کد یکتا',
        help_text='مثال: MODULE_CATALOG, FEATURE_REVIEW_RATING'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='نام نمایشی',
        help_text='مثال: ماژول کاتالوگ محصول'
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='توضیحات'
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.FEATURE,
        verbose_name='دسته‌بندی'
    )
    is_enabled = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='فعال است؟'
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name='سیستمی (حذف ممنوع)',
        help_text='اگر true باشد، حذف از ادمین غیرممکن است'
    )
    rollout_percentage = models.PositiveSmallIntegerField(
        default=100,
        verbose_name='درصد rollout',
        help_text='0 تا 100 - برای انتشار تدریجی'
    )
    metadata = models.JSONField(
        blank=True,
        default=dict,
        verbose_name='داده‌های اضافی'
    )
    enabled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='زمان فعال‌سازی'
    )
    disabled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='زمان غیرفعال‌سازی'
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
        app_label = 'core'
        verbose_name = 'پرچم قابلیت'
        verbose_name_plural = 'پرچم‌های قابلیت'
        ordering = ['category', 'code']
        indexes = [
            models.Index(fields=['is_enabled', 'category']),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_enabled else "✗"
        return f"{status} {self.code} ({self.name})"

    def enable(self, user=None) -> None:
        """فعال‌سازی پرچم و ثبت لاگ"""
        if not self.is_enabled:
            self.is_enabled = True
            self.enabled_at = timezone.now()
            self.disabled_at = None
            self.save(update_fields=['is_enabled', 'enabled_at', 'disabled_at', 'updated_at'])
            self._log_change('enabled', user)

    def disable(self, user=None) -> None:
        """
        غیرفعال‌سازی پرچم و ثبت لاگ.
        برای پرچم‌های سیستمی، فقط superuser می‌تواند غیرفعال کند.
        """
        if self.is_system:
            # برای پرچم‌های سیستمی، بررسی دسترسی superuser
            if user is None or not getattr(user, 'is_superuser', False):
                raise ValueError(
                    f"Cannot disable system flag '{self.code}' without superuser access"
                )
        if self.is_enabled:
            self.is_enabled = False
            self.disabled_at = timezone.now()
            self.save(update_fields=['is_enabled', 'enabled_at', 'disabled_at', 'updated_at'])
            self._log_change('disabled', user)

    def toggle(self, user=None) -> bool:
        """
        تغییر وضعیت پرچم.
        برای پرچم‌های سیستمی، فقط superuser می‌تواند تغییر دهد.
        """
        if self.is_system:
            if user is None or not getattr(user, 'is_superuser', False):
                raise ValueError(
                    f"Cannot toggle system flag '{self.code}' without superuser access"
                )
        if self.is_enabled:
            self.disable(user=user)
            return False
        else:
            self.enable(user=user)
            return True

    def _log_change(self, action: str, user=None) -> None:
        """ثبت تغییر در AuditLog (منطبق بر ADR-002)"""
        try:
            AuditLog.objects.create(
                user=user,
                action=action,
                entity_type='feature_flag',
                entity_id=self.pk,
                changes={'code': self.code, 'is_enabled': self.is_enabled}
            )
        except Exception:
            # اگر AuditLog هنوز آماده نباشد، لاگ نمی‌کنیم
            pass


class AuditLog(models.Model):
    """
    لاگ ممیزی برای ردیابی تغییرات مهم
    منطبق بر ADR-002 بخش ۲.۱۷
    """
    ACTION_CHOICES = [
        ('create', 'ایجاد'),
        ('update', 'به‌روزرسانی'),
        ('delete', 'حذف'),
        ('enabled', 'فعال شد'),
        ('disabled', 'غیرفعال شد'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='کاربر'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='نوع عملیات'
    )
    entity_type = models.CharField(
        max_length=50,
        verbose_name='نوع موجودیت',
        help_text='مثال: feature_flag, product, order'
    )
    entity_id = models.CharField(
        max_length=50,
        verbose_name='شناسه موجودیت'
    )
    changes = models.JSONField(
        blank=True,
        default=dict,
        verbose_name='تغییرات'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='آدرس IP'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='تاریخ'
    )

    class Meta:
        app_label = 'core'
        verbose_name = 'لاگ ممیزی'
        verbose_name_plural = 'لاگ‌های ممیزی'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self) -> str:
        user_str = self.user or 'System'
        return f"{user_str} - {self.action} on {self.entity_type}:{self.entity_id}"
