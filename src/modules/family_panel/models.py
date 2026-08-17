"""
مدل‌های ماژول پنل خانواده ریهان (M3)

اصلاح شده مطابق ADR-006:
- ❌ FamilyAdmin حذف شد (همه کاربران از M10 Auth استفاده می‌کنند)
- ✅ تشخیص ادمین خانواده از طریق M5 (RBAC)
- ✅ ورود با OTP (نه username + password)

مدل‌ها:
- ActivityLog: لاگ فعالیت‌های ادمین (US-026)
- SiteSettings: تنظیمات سایت (US-027)
"""
from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ActivityLog(models.Model):
    """
    لاگ فعالیت‌های ادمین‌های خانواده.
    
    منطبق بر US-026:
    - چه کسی، چه کاری، چه زمانی، از کجا
    - فیلتر بر اساس کاربر و بازه زمانی
    
    نکته: کاربر از مدل User جنگو (M10) است.
    """
    
    ACTION_CHOICES = [
        ('login', 'ورود به پنل'),
        ('logout', 'خروج از پنل'),
        ('product_create', 'ایجاد محصول'),
        ('product_update', 'ویرایش محصول'),
        ('product_delete', 'حذف محصول'),
        ('order_view', 'مشاهده سفارش'),
        ('order_update', 'به‌روزرسانی سفارش'),
        ('order_approve', 'تأیید سفارش'),
        ('order_reject', 'رد سفارش'),
        ('review_approve', 'تأیید نظر'),
        ('review_reject', 'رد نظر'),
        ('settings_update', 'تغییر تنظیمات'),
        ('admin_create', 'ایجاد ادمین'),
        ('admin_update', 'ویرایش ادمین'),
        ('admin_deactivate', 'غیرفعال‌سازی ادمین'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='family_activity_logs',
        verbose_name='کاربر',
        help_text='کاربر از M10 (Auth) - نقش از M5 (RBAC)'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='نوع عملیات'
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='توضیحات'
    )
    entity_type = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='نوع موجودیت',
        help_text='مثال: product, order, review'
    )
    entity_id = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='شناسه موجودیت'
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
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='تغییرات'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='تاریخ'
    )
    
    class Meta:
        app_label = 'family_panel'
        verbose_name = 'لاگ فعالیت'
        verbose_name_plural = 'لاگ‌های فعالیت'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user} - {self.get_action_display()} - {self.created_at}"


class SiteSettings(models.Model):
    """
    تنظیمات سایت (singleton).
    
    منطبق بر US-027:
    - رنگ، فونت، نام، واحد
    - شماره کارت + نام صاحب حساب
    - شماره تماس + آدرس
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    # تنظیمات عمومی
    site_name = models.CharField(
        max_length=100,
        default='ریهان',
        verbose_name='نام سایت'
    )
    site_tagline = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='شعار سایت'
    )
    currency = models.CharField(
        max_length=10,
        default='تومان',
        verbose_name='واحد پول'
    )
    
    # تنظیمات بصری
    primary_color = models.CharField(
        max_length=7,
        default='#2c3e50',
        verbose_name='رنگ اصلی'
    )
    font_family = models.CharField(
        max_length=50,
        default='Vazir',
        verbose_name='فونت'
    )
    
    # اطلاعات تماس
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='شماره تماس'
    )
    contact_address = models.TextField(
        blank=True,
        default='',
        verbose_name='آدرس'
    )
    
    # اطلاعات بانکی
    bank_card_number = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='شماره کارت'
    )
    bank_card_holder = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='نام صاحب حساب'
    )
    
    # تنظیمات سیستم
    low_stock_threshold = models.PositiveSmallIntegerField(
        default=5,
        verbose_name='آستانه موجودی کم'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخرین به‌روزرسانی'
    )
    
    class Meta:
        app_label = 'family_panel'
        verbose_name = 'تنظیمات سایت'
        verbose_name_plural = 'تنظیمات سایت'
    
    def __str__(self) -> str:
        return f"تنظیمات سایت ({self.site_name})"
    
    def save(self, *args, **kwargs):
        """Singleton: فقط یک رکورد SiteSettings وجود داشته باشد"""
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError("فقط یک SiteSettings می‌تواند وجود داشته باشد")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls) -> 'SiteSettings':
        """
        دریافت تنظیمات (singleton).
        
        FIX: استفاده از objects.first() به‌جای get_or_create با UUID متغیر
        """
        settings = cls.objects.first()
        if settings is None:
            settings = cls.objects.create()
        return settings


class ProductContent(models.Model):
    """
    محتوای بلوک‌محور محصول.
    
    منطبق بر US-055:
    - هر محصول می‌تواند تعداد نامحدود بلوک داشته باشد
    - ذخیره draft و published
    - اتصال به M14 BlockRegistry برای اعتبارسنجی
    
    نکته: product_id فعلاً INTEGER است.
    پس از بازنویسی M1، به FK تبدیل می‌شود.
    """
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    product_id = models.IntegerField(
        db_index=True,
        verbose_name='شناسه محصول',
        help_text='در آینده به FK محصول (M1) تبدیل می‌شود'
    )
    blocks = models.JSONField(
        default=list,
        blank=True,
        verbose_name='لیست بلوک‌ها',
        help_text='لیست بلوک‌ها به ترتیب نمایش'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='وضعیت'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_product_contents',
        verbose_name='ایجادکننده'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_product_contents',
        verbose_name='آخرین ویرایش‌کننده'
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ انتشار'
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
        app_label = 'family_panel'
        verbose_name = 'محتوای محصول'
        verbose_name_plural = 'محتوای محصولات'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['product_id'],
                condition=models.Q(status__in=['draft', 'published']),
                name='unique_active_content_per_product'
            ),
        ]
    
    def __str__(self) -> str:
        return f"محتوای محصول {self.product_id} ({self.get_status_display()})"
    
    @property
    def blocks_count(self) -> int:
        return len(self.blocks) if self.blocks else 0
    
    def add_block(self, block_type: str, data: dict, order: int = None) -> dict:
        """افزودن بلوک جدید"""
        if self.blocks is None:
            self.blocks = []
        
        if order is None:
            order = len(self.blocks)
        
        block = {
            'id': str(uuid.uuid4()),
            'type': block_type,
            'order': order,
            'data': data,
        }
        self.blocks.append(block)
        return block
    
    def get_block(self, block_id: str) -> dict:
        """دریافت یک بلوک بر اساس ID"""
        if not self.blocks:
            return None
        for block in self.blocks:
            if block.get('id') == block_id:
                return block
        return None
    
    def update_block(self, block_id: str, data: dict) -> bool:
        """به‌روزرسانی داده‌های یک بلوک"""
        block = self.get_block(block_id)
        if block:
            block['data'] = data
            return True
        return False
    
    def remove_block(self, block_id: str) -> bool:
        """حذف یک بلوک"""
        if not self.blocks:
            return False
        original_count = len(self.blocks)
        self.blocks = [b for b in self.blocks if b.get('id') != block_id]
        return len(self.blocks) < original_count
    
    def reorder_blocks(self, block_ids: list) -> bool:
        """تغییر ترتیب بلوک‌ها"""
        if not self.blocks:
            return False
        
        # ساخت دیکشنری از بلوک‌ها بر اساس ID
        blocks_dict = {b['id']: b for b in self.blocks}
        
        # بررسی اینکه همه IDها وجود دارند
        for block_id in block_ids:
            if block_id not in blocks_dict:
                return False
        
        # به‌روزرسانی ترتیب
        new_blocks = []
        for order, block_id in enumerate(block_ids):
            block = blocks_dict[block_id]
            block['order'] = order
            new_blocks.append(block)
        
        self.blocks = new_blocks
        return True
