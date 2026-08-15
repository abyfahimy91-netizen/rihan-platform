"""
M14: Plugin Architecture Models

Models برای:
- Plugin: اطلاعات ماژول‌ها
- FeatureFlag: flags با persistence
- PluginHook: event registrations  
- EventLog: لاگ همه events
- AdminActivityLog: tracking فعالیت‌های ادمین (برای M5)
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class Plugin(models.Model):
    """
    اطلاعات یک ماژول/پلاگین
    
    هر ماژول در src/modules/ باید یک رکورد در این جدول داشته باشد.
    """
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('error', 'خطا'),
    ]
    
    name = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="نام ماژول",
        help_text="مثلاً: M1, M2, catalog, orders"
    )
    
    display_name = models.CharField(
        max_length=100,
        verbose_name="نام نمایشی",
        help_text="مثلاً: کاتالوگ محصولات"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )
    
    version = models.CharField(
        max_length=20,
        default="1.0.0",
        verbose_name="نسخه"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="وضعیت"
    )
    
    is_system = models.BooleanField(
        default=False,
        verbose_name="سیستمی",
        help_text="ماژول‌های سیستمی قابل غیرفعال‌سازی نیستند"
    )
    
    manifest_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="داده‌های manifest.yaml"
    )
    
    enabled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ فعال‌سازی"
    )
    
    disabled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ غیرفعال‌سازی"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "ماژول/پلاگین"
        verbose_name_plural = "ماژول‌ها/پلاگین‌ها"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.display_name} ({self.version})"
    
    def enable(self):
        """فعال‌سازی ماژول"""
        if self.is_system:
            raise ValueError(f"ماژول سیستمی {self.name} قابل غیرفعال‌سازی نیست")
        self.status = 'active'
        self.enabled_at = timezone.now()
        self.disabled_at = None
        self.save()
    
    def disable(self):
        """غیرفعال‌سازی ماژول"""
        if self.is_system:
            raise ValueError(f"ماژول سیستمی {self.name} قابل غیرفعال‌سازی نیست")
        self.status = 'inactive'
        self.disabled_at = timezone.now()
        self.save()
    
    @property
    def is_enabled(self) -> bool:
        return self.status == 'active'


class FeatureFlag(models.Model):
    """
    Feature Flag با persistence در database
    
    برخلاف نسخه قبلی که فقط env var بود، اینجا در DB ذخیره می‌شود
    و از پنل ادمین قابل تغییر است.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="نام flag",
        help_text="مثلاً: FEATURE_SMS_OTP_LOGIN"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )
    
    enabled = models.BooleanField(
        default=False,
        verbose_name="فعال"
    )
    
    category = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="دسته‌بندی",
        help_text="مثلاً: payment, auth, ui"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="آخرین تغییر توسط"
    )
    
    class Meta:
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"
        ordering = ['category', 'name']
    
    def __str__(self):
        status = "✅" if self.enabled else "❌"
        return f"{status} {self.name}"
    
    def toggle(self, user=None):
        """تغییر وضعیت flag"""
        self.enabled = not self.enabled
        if user:
            self.updated_by = user
        self.save()
        return self.enabled


class PluginHook(models.Model):
    """
    Hook registration برای event system
    
    هر پلاگین می‌تواند برای events مختلف handler ثبت کند.
    """
    EVENT_TYPES = [
        ('order.created', 'ایجاد سفارش'),
        ('order.paid', 'پرداخت سفارش'),
        ('order.shipped', 'ارسال سفارش'),
        ('order.delivered', 'تحویل سفارش'),
        ('user.login', 'ورود کاربر'),
        ('user.register', 'ثبت‌نام کاربر'),
        ('product.created', 'ایجاد محصول'),
        ('product.updated', 'به‌روزرسانی محصول'),
        ('review.created', 'ایجاد نظر'),
        ('review.approved', 'تأیید نظر'),
        ('lead.created', 'ایجاد سرنخ'),
        ('inventory.low', 'موجودی کم'),
    ]
    
    plugin = models.ForeignKey(
        Plugin,
        on_delete=models.CASCADE,
        related_name='hooks',
        verbose_name="ماژول"
    )
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name="نوع event"
    )
    
    handler_path = models.CharField(
        max_length=200,
        verbose_name="مسیر handler",
        help_text="مثلاً: modules.catalog.hooks.on_product_created"
    )
    
    priority = models.IntegerField(
        default=100,
        verbose_name="اولویت",
        help_text="عدد کمتر = اولویت بالاتر"
    )
    
    enabled = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plugin Hook"
        verbose_name_plural = "Plugin Hooks"
        ordering = ['event_type', 'priority']
        unique_together = [['plugin', 'event_type', 'handler_path']]
    
    def __str__(self):
        return f"{self.plugin.name} -> {self.event_type}"


class EventLog(models.Model):
    """
    لاگ همه events سیستم
    
    برای debugging و audit trail
    """
    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    event_type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="نوع event"
    )
    
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='info',
        verbose_name="سطح"
    )
    
    message = models.TextField(
        verbose_name="پیام"
    )
    
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="داده‌های اضافی"
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="کاربر"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="تاریخ"
    )
    
    class Meta:
        verbose_name = "Event Log"
        verbose_name_plural = "Event Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['level', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.event_type} - {self.created_at:%Y-%m-%d %H:%M}"


class AdminActivityLog(models.Model):
    """
    Activity tracking برای ادمین‌ها (مورد نیاز M3 و M5)
    
    مطابق USER-PERSONAS.md، فعالیت هر ادمین باید قابل ردیابی باشد.
    """
    ACTION_TYPES = [
        ('login', 'ورود'),
        ('logout', 'خروج'),
        ('create', 'ایجاد'),
        ('update', 'ویرایش'),
        ('delete', 'حذف'),
        ('approve', 'تأیید'),
        ('reject', 'رد'),
        ('enable', 'فعال‌سازی'),
        ('disable', 'غیرفعال‌سازی'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_activities',
        verbose_name="ادمین"
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name="عملیات"
    )
    
    resource_type = models.CharField(
        max_length=50,
        verbose_name="نوع منبع",
        help_text="مثلاً: Product, Order, User"
    )
    
    resource_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="شناسه منبع"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )
    
    old_value = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="مقدار قبلی"
    )
    
    new_value = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="مقدار جدید"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP"
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="تاریخ"
    )
    
    class Meta:
        verbose_name = "لاگ فعالیت ادمین"
        verbose_name_plural = "لاگ‌های فعالیت ادمین"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.resource_type} ({self.created_at:%Y-%m-%d %H:%M})"
