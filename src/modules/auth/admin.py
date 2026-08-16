"""
Admin Panel ماژول احراز هویت
منطبق بر ADR-006 بخش ۷: کنترل کامل ادمین

بخش‌ها:
- مدیریت کاربران و وضعیت ورود
- لیست DeviceTokenهای فعال
- مشاهده IP، user agent، زمان آخرین ورود
- ابطال دستی DeviceToken
- قفل دستی کاربر
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import PhoneOTP, DeviceToken, LoginAttempt


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    """مدیریت کدهای یکبارمصرف"""
    list_display = (
        'phone_masked', 'attempts', 'max_attempts',
        'is_expired_badge', 'is_locked_badge', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('phone',)
    readonly_fields = (
        'phone', 'otp_hash', 'attempts', 'max_attempts',
        'expires_at', 'verified_at', 'locked_until', 'created_at'
    )
    ordering = ('-created_at',)
    
    def phone_masked(self, obj):
        """نمایش ماسک شده شماره (ADR-006 بخش ۹)"""
        if len(obj.phone) >= 8:
            return f"{obj.phone[:4]}***{obj.phone[-4:]}"
        return obj.phone
    phone_masked.short_description = 'شماره موبایل'
    
    def is_expired_badge(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: #dc3545;">منقضی</span>')
        return format_html('<span style="color: #28a745;">معتبر</span>')
    is_expired_badge.short_description = 'وضعیت'
    
    def is_locked_badge(self, obj):
        if obj.is_locked:
            return format_html('<span style="color: #dc3545;">قفل</span>')
        return format_html('<span style="color: #28a745;">باز</span>')
    is_locked_badge.short_description = 'قفل'
    
    def has_add_permission(self, request):
        return False  # فقط سیستم می‌تواند اضافه کند
    
    def has_change_permission(self, request, obj=None):
        return False  # فقط مشاهده


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """مدیریت توکن‌های دستگاه"""
    list_display = (
        'user', 'device_fingerprint', 'ip_address',
        'last_used_at', 'expires_at', 'is_active_badge'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'device_fingerprint', 'ip_address')
    readonly_fields = (
        'id', 'user', 'token_hash', 'device_fingerprint',
        'user_agent', 'ip_address', 'last_used_at',
        'expires_at', 'is_active', 'created_at'
    )
    ordering = ('-last_used_at',)
    actions = ['revoke_tokens']
    
    def is_active_badge(self, obj):
        if obj.is_active and not obj.is_expired:
            return format_html('<span style="color: #28a745;">فعال</span>')
        elif obj.is_expired:
            return format_html('<span style="color: #ffc107;">منقضی</span>')
        return format_html('<span style="color: #dc3545;">باطل</span>')
    is_active_badge.short_description = 'وضعیت'
    
    def revoke_tokens(self, request, queryset):
        """ابطال توکن‌های انتخاب‌شده"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} توکن باطل شد")
    revoke_tokens.short_description = "ابطال توکن‌های انتخاب‌شده"
    
    def has_add_permission(self, request):
        return False  # فقط سیستم می‌تواند اضافه کند


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """مشاهده تلاش‌های ورود"""
    list_display = (
        'phone_masked', 'action', 'success_badge',
        'ip_address', 'created_at'
    )
    list_filter = ('action', 'success', 'created_at')
    search_fields = ('phone', 'ip_address')
    readonly_fields = (
        'phone', 'action', 'ip_address', 'user_agent',
        'success', 'user', 'created_at'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    def phone_masked(self, obj):
        """نمایش ماسک شده شماره"""
        if len(obj.phone) >= 8:
            return f"{obj.phone[:4]}***{obj.phone[-4:]}"
        return obj.phone
    phone_masked.short_description = 'شماره موبایل'
    
    def success_badge(self, obj):
        if obj.success:
            return format_html('<span style="color: #28a745;">✓ موفق</span>')
        return format_html('<span style="color: #dc3545;">✗ ناموفق</span>')
    success_badge.short_description = 'نتیجه'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False  # لاگ‌ها قابل حذف نیستند (ADR-006 بخش ۷)
