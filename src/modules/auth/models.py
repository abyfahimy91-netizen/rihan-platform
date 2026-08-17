"""
مدل‌های ماژول احراز هویت ریهان (M10)
منطبق بر ADR-006: احراز هویت Passwordless

مدل‌ها:
- PhoneOTP: کدهای یکبارمصرف ۶ رقمی
- DeviceToken: توکن‌های Device Remembering
- LoginAttempt: لاگ تلاش‌های ورود (برای Rate Limiting)
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PhoneOTP(models.Model):
    """
    کد یکبارمصرف ۶ رقمی برای احراز هویت.
    
    منطبق بر ADR-006 بخش ۲:
    - طول کد: ۶ رقم
    - طول عمر: ۲ دقیقه
    - تعداد تلاش: ۳ بار
    - ذخیره‌سازی: hash (bcrypt)
    """
    
    phone = models.CharField(
        max_length=11,
        db_index=True,
        verbose_name='شماره موبایل',
        help_text='فرمت ایرانی: ۰۹xxxxxxxxx'
    )
    otp_hash = models.CharField(
        max_length=128,
        verbose_name='هش OTP',
        help_text='hash شده با bcrypt'
    )
    attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='تعداد تلاش‌ها'
    )
    max_attempts = models.PositiveSmallIntegerField(
        default=3,
        verbose_name='حداکثر تلاش مجاز'
    )
    expires_at = models.DateTimeField(
        verbose_name='زمان انقضا',
        help_text='پیش‌فرض: ۲ دقیقه از زمان ایجاد'
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='زمان تأیید'
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='قفل موقت تا',
        help_text='پس از ۳ تلاش ناموفق: ۳۰ دقیقه'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='زمان ایجاد'
    )
    
    class Meta:
        app_label = 'rihan_auth'
        verbose_name = 'کد یکبارمصرف'
        verbose_name_plural = 'کدهای یکبارمصرف'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"OTP for {self.phone[:4]}***{self.phone[-4:]}"
    
    @property
    def is_expired(self) -> bool:
        """آیا OTP منقضی شده است؟"""
        return timezone.now() > self.expires_at
    
    @property
    def is_locked(self) -> bool:
        """آیا حساب قفل موقت دارد؟"""
        if self.locked_until is None:
            return False
        return timezone.now() < self.locked_until
    
    @property
    def attempts_left(self) -> int:
        """تعداد تلاش‌های باقی‌مانده"""
        return max(0, self.max_attempts - self.attempts)
    
    def can_verify(self) -> bool:
        """آیا امکان تأیید وجود دارد؟"""
        return not self.is_expired and not self.is_locked and self.attempts_left > 0
    
    def increment_attempts(self) -> None:
        """افزایش تعداد تلاش‌ها"""
        self.attempts += 1
        if self.attempts >= self.max_attempts:
            # قفل موقت ۳۰ دقیقه
            self.locked_until = timezone.now() + timedelta(minutes=30)
        self.save(update_fields=['attempts', 'locked_until'])
    
    def mark_verified(self) -> None:
        """علامت‌گذاری به‌عنوان تأیید شده"""
        self.verified_at = timezone.now()
        self.save(update_fields=['verified_at'])


class DeviceToken(models.Model):
    """
    توکن Device Remembering.
    
    منطبق بر ADR-006 بخش ۲.۲:
    - طول عمر: ۳۰ روز
    - فرمت: UUID v4
    - محدودیت: حداکثر ۵ دستگاه per کاربر
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه توکن'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        verbose_name='کاربر'
    )
    token_hash = models.CharField(
        max_length=128,
        unique=True,
        verbose_name='هش توکن',
        help_text='hash شده با bcrypt'
    )
    device_fingerprint = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='اثر انگشت دستگاه'
    )
    user_agent = models.TextField(
        blank=True,
        default='',
        verbose_name='User Agent'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='آدرس IP'
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخرین استفاده'
    )
    expires_at = models.DateTimeField(
        verbose_name='زمان انقضا',
        help_text='پیش‌فرض: ۳۰ روز از آخرین استفاده'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال است؟'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='زمان ایجاد'
    )
    
    class Meta:
        app_label = 'rihan_auth'
        verbose_name = 'توکن دستگاه'
        verbose_name_plural = 'توکن‌های دستگاه'
        ordering = ['-last_used_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self) -> str:
        return f"Device {self.id} for {self.user}"
    
    @property
    def is_expired(self) -> bool:
        """آیا توکن منقضی شده است؟"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """آیا توکن معتبر است؟"""
        return self.is_active and not self.is_expired
    
    def refresh_expiry(self) -> None:
        """تمدید انقضا (با هر ورود موفق)"""
        self.expires_at = timezone.now() + timedelta(days=30)
        self.last_used_at = timezone.now()
        self.save(update_fields=['expires_at', 'last_used_at'])
    
    def revoke(self) -> None:
        """ابطال توکن"""
        self.is_active = False
        self.save(update_fields=['is_active'])
    
    @classmethod
    def get_active_count(cls, user) -> int:
        """تعداد توکن‌های فعال کاربر"""
        return cls.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
    
    @classmethod
    def cleanup_old_tokens(cls, user) -> None:
        """حذف توکن‌های قدیمی (اگر بیش از ۵ دستگاه باشد)"""
        MAX_DEVICES = 5
        active_tokens = cls.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-last_used_at')
        
        if active_tokens.count() > MAX_DEVICES:
            # حذف قدیمی‌ترین‌ها
            tokens_to_remove = active_tokens[MAX_DEVICES:]
            tokens_to_remove.update(is_active=False)


class LoginAttempt(models.Model):
    """
    لاگ تلاش‌های ورود (برای Rate Limiting و AuditLog).
    
    منطبق بر ADR-006 بخش ۴:
    - درخواست OTP per شماره: ۳ بار در ۱۰ دقیقه
    - درخواست OTP per IP: ۱۰ بار در ساعت
    """
    
    ACTION_CHOICES = [
        ('otp_request', 'درخواست OTP'),
        ('otp_verify_success', 'تأیید موفق OTP'),
        ('otp_verify_failed', 'تأیید ناموفق OTP'),
        ('device_login', 'ورود با DeviceToken'),
        ('password_login', 'ورود با رمز پشتیبان'),
        ('logout', 'خروج'),
        ('lockout', 'قفل موقت'),
    ]
    
    phone = models.CharField(
        max_length=11,
        db_index=True,
        verbose_name='شماره موبایل'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='نوع عملیات'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='آدرس IP'
    )
    user_agent = models.TextField(
        blank=True,
        default='',
        verbose_name='User Agent'
    )
    success = models.BooleanField(
        default=False,
        verbose_name='موفق بود؟'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_attempts',
        verbose_name='کاربر'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='زمان'
    )
    
    class Meta:
        app_label = 'rihan_auth'
        verbose_name = 'تلاش ورود'
        verbose_name_plural = 'تلاش‌های ورود'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} {self.action} - {self.phone}"
    
    @classmethod
    def get_recent_attempts(
        cls,
        phone: str = None,
        ip: str = None,
        minutes: int = 10
    ) -> int:
        """تعداد تلاش‌های اخیر (برای Rate Limiting)"""
        since = timezone.now() - timedelta(minutes=minutes)
        queryset = cls.objects.filter(created_at__gte=since)
        
        if phone:
            queryset = queryset.filter(phone=phone)
        if ip:
            queryset = queryset.filter(ip_address=ip)
        
        return queryset.count()
