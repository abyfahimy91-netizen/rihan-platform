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


# ═══════════════════════════════════════════════════════════════
# تنظیمات ورود + سرویس‌دهنده‌های پیامک (D-103)
# ═══════════════════════════════════════════════════════════════

from django import forms

from .models import AuthSettings, SmsProvider

from src.core.fa import jalali_datetime_str


class SmsProviderAdminForm(forms.ModelForm):
    """کلید API به‌صورت ماسک‌شده — خالی بگذاری = حفظ کلید قبلی"""
    api_key = forms.CharField(
        label='کلید API',
        widget=forms.PasswordInput(render_value=False, attrs={'dir': 'ltr', 'autocomplete': 'new-password'}),
        required=False,
        help_text='برای حفظ کلید ذخیره‌شده‌ی فعلی، این کادر را خالی بگذارید.',
    )

    class Meta:
        model = SmsProvider
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        key = (cleaned.get('api_key') or '').strip()
        if not key and self.instance and self.instance.pk:
            # ویرایش بدون تایپ کلید جدید → کلید قبلی حفظ می‌شود
            cleaned['api_key'] = self.instance.api_key
        elif not key:
            self.add_error('api_key', 'کلید API الزامی است (از پنل سرویس‌دهنده بگیرید).')
        return cleaned


@admin.register(AuthSettings)
class AuthSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('🚪 روش‌های ورود', {
            'fields': ('otp_enabled', 'password_enabled', 'default_method'),
            'description': 'حداقل یکی از دو روش باید فعال بماند. «روش پیش‌فرض» تعیین می‌کند صفحه ورود ابتدا کدام روش را نشان دهد.',
        }),
        ('🔢 رفتار کد یکبارمصرف', {
            'fields': ('otp_ttl_minutes', 'otp_max_attempts', 'show_code_on_sms_fail'),
            'classes': ('collapse',),
            'description': '«نمایش کد در صفحه» فقط برای تست یا اضطرار است؛ در بهره‌برداری واقعی خاموشش کنید.',
        }),
    )
    list_display = ('__str__', 'updated_at_fa')

    def updated_at_fa(self, obj):
        return jalali_datetime_str(obj.updated_at)
    updated_at_fa.short_description = 'آخرین تغییر'

    def has_add_permission(self, request):
        return not AuthSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        from django.contrib import messages
        messages.success(request, '✅ تنظیمات ورود ذخیره شد و بلافاصله اعمال می‌شود.')
        return super().response_change(request, obj)


@admin.register(SmsProvider)
class SmsProviderAdmin(admin.ModelAdmin):
    form = SmsProviderAdminForm
    list_display = (
        'name', 'provider_type_badge', 'is_active_badge',
        'priority', 'last_status_short', 'last_used_at_fa',
    )
    list_editable = ('priority',)
    list_display_links = ('name',)
    actions = ('activate_selected',)
    readonly_fields = ('last_status', 'last_used_at')
    fieldsets = (
        ('📡 هویت سرویس', {
            'fields': ('name', 'provider_type'),
        }),
        ('🔑 اطلاعات اتصال', {
            'fields': ('api_key', 'otp_template', 'sender'),
            'description': 'کلید API را از پنل سرویس‌دهنده بگیرید (کاوه‌نگار: kavenegar.com → تنظیمات → کلید API). قالب تأییدیه باید متغیر %token داشته باشد.',
        }),
        ('⚡ فعال‌سازی و جایگزینی خودکار', {
            'fields': ('is_active', 'priority'),
            'description': 'فقط یک سرویس فعال می‌ماند (با فعال‌کردن این، بقیه خودکار خاموش می‌شوند). اگر سرویس فعال قطع شود، بقیه به ترتیب اولویت خودکار امتحان می‌شوند.',
        }),
        ('🩺 وضعیت آخرین ارسال', {
            'fields': ('last_status', 'last_used_at'),
            'classes': ('collapse',),
        }),
    )

    def provider_type_badge(self, obj):
        return obj.get_provider_type_display()
    provider_type_badge.short_description = 'نوع'

    def is_active_badge(self, obj):
        return format_html(
            '<span style="color:{};font-weight:800;">{}</span>',
            '#28a745' if obj.is_active else '#999',
            '✅ فعال' if obj.is_active else '— غیرفعال',
        )
    is_active_badge.short_description = 'وضعیت'

    def last_status_short(self, obj):
        return obj.last_status or '—'
    last_status_short.short_description = 'آخرین وضعیت ارسال'

    def last_used_at_fa(self, obj):
        return jalali_datetime_str(obj.last_used_at) if obj.last_used_at else '—'
    last_used_at_fa.short_description = 'آخرین استفاده'

    def activate_selected(self, request, queryset):
        for row in queryset:
            row.is_active = True
            row.save()  # مدل خودش بقیه را غیرفعال می‌کند
        self.message_user(request, '✅ سرویس انتخاب‌شده فعال شد و بقیه خودکار غیرفعال شدند.')
    activate_selected.short_description = '⚡ فعال‌سازی سرویس انتخاب‌شده'
