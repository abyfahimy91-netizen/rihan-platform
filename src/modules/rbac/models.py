"""
M5: RBAC (Role-Based Access Control) Models

منطبق بر:
- USER-STORIES.md: US-016 (ورود به پنل ادمین)
- USER-PERSONAS.md: P4, P5, P6
- D-079: برند مستقل
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Role(models.Model):
    """
    نقش‌های سیستم
    
    سه نقش پیش‌فرض:
    - super_admin: عبدالحسین (P4) - دسترسی کامل
    - admin: همسر (P5) - دسترسی بالا
    - staff: بچه‌ها/کمکی (P6) - دسترسی محدود
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="نام نقش"
    )
    
    display_name = models.CharField(
        max_length=100,
        verbose_name="نام نمایشی"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )
    
    is_system = models.BooleanField(
        default=False,
        verbose_name="سیستمی",
        help_text="نقش‌های سیستمی قابل حذف نیستند"
    )
    
    session_duration_hours = models.IntegerField(
        default=8,
        verbose_name="مدت جلسه (ساعت)",
        help_text="طبق US-016: ۸ ساعت"
    )
    
    max_login_attempts = models.IntegerField(
        default=5,
        verbose_name="حداکثر تلاش ورود",
        help_text="طبق US-016: ۵ بار"
    )
    
    lockout_duration_minutes = models.IntegerField(
        default=15,
        verbose_name="مدت قفل (دقیقه)",
        help_text="طبق US-016: ۱۵ دقیقه"
    )
    
    permissions = models.ManyToManyField(
        'Permission',
        blank=True,
        related_name='roles',
        verbose_name="مجوزها"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.display_name})"


class Permission(models.Model):
    """
    مجوزهای granular
    
    هر ماژول می‌تواند چندین permission داشته باشد.
    مثال: catalog.view, catalog.create, catalog.update, catalog.delete
    """
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="کد مجوز",
        help_text="مثلاً: catalog.view"
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name="نام مجوز"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )
    
    module = models.CharField(
        max_length=50,
        verbose_name="ماژول",
        help_text="مثلاً: catalog, orders, users"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "مجوز"
        verbose_name_plural = "مجوزها"
        ordering = ['module', 'code']
        indexes = [
            models.Index(fields=['module', 'code']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class UserProfile(models.Model):
    """
    پروفایل توسعه‌یافته کاربر (One-to-One با User)
    
    شامل اطلاعات RBAC و security
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="کاربر"
    )
    
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        verbose_name="نقش"
    )
    
    # Security fields
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name="تلاش‌های ناموفق ورود"
    )
    
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="قفل تا"
    )
    
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="آخرین IP ورود"
    )
    
    last_login_user_agent = models.TextField(
        blank=True,
        verbose_name="آخرین User Agent"
    )
    
    # Activity tracking
    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="یادداشت‌ها"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"
    
    def __str__(self):
        return f"{self.user.username} - {self.role.display_name}"
    
    def is_locked(self) -> bool:
        """بررسی قفل بودن حساب"""
        if not self.locked_until:
            return False
        return timezone.now() < self.locked_until
    
    def lock(self):
        """قفل کردن حساب برای مدت مشخص"""
        lock_minutes = self.role.lockout_duration_minutes
        self.locked_until = timezone.now() + timedelta(minutes=lock_minutes)
        self.save()
    
    def unlock(self):
        """باز کردن قفل حساب"""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save()
    
    def record_failed_login(self):
        """ثبت تلاش ناموفق ورود"""
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= self.role.max_login_attempts:
            self.lock()
        
        self.save()
    
    def record_successful_login(self, request=None):
        """ثبت ورود موفق"""
        self.failed_login_attempts = 0
        self.locked_until = None
        
        if request:
            self.last_login_ip = self._get_client_ip(request)
            self.last_login_user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        self.save()
        
        # تنظیم session duration
        if request:
            request.session.set_expiry(
                self.role.session_duration_hours * 3600
            )
    
    def has_permission(self, permission_code: str) -> bool:
        """بررسی داشتن یک مجوز خاص"""
        return self.role.permissions.filter(code=permission_code).exists()
    
    def has_module_access(self, module_name: str) -> bool:
        """بررسی دسترسی به یک ماژول"""
        return self.role.permissions.filter(module=module_name).exists()
    
    def _get_client_ip(self, request) -> str:
        """دریافت IP کاربر"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class LoginAttempt(models.Model):
    """
    لاگ تلاش‌های ورود (برای security audit)
    """
    username = models.CharField(
        max_length=150,
        verbose_name="نام کاربری"
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name="IP"
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    success = models.BooleanField(
        verbose_name="موفق"
    )
    
    failure_reason = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="دلیل شکست",
        help_text="مثلاً: invalid_password, account_locked, user_not_found"
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان"
    )
    
    class Meta:
        verbose_name = "تلاش ورود"
        verbose_name_plural = "تلاش‌های ورود"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['username', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]
    
    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.username} from {self.ip_address} at {self.timestamp:%Y-%m-%d %H:%M}"
