"""
Models for Leads Module (M9)

Implements US-010: Product availability notifications
- Visitor can express interest in out-of-stock products
- Auto-notification when product becomes available
- Admin panel with Jalali dates
"""
import uuid
import re

from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone


class Lead(models.Model):
    """
    Lead for product availability notification (M9 - US-010)
    
    A lead is created when a visitor expresses interest in a product
    that is currently out of stock or low stock.
    """
    class LeadStatus(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار موجودی'
        NOTIFIED = 'NOTIFIED', 'اطلاع‌رسانی شد'
        CONVERTED = 'CONVERTED', 'تبدیل به خرید'
        CANCELLED = 'CANCELLED', 'لغو شد'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Who is interested
    phone_regex = RegexValidator(
        regex=r'^09[0-9]{9}$',
        message='شماره موبایل باید ۱۱ رقم و با ۰۹ شروع شود'
    )
    phone = models.CharField(
        max_length=11,
        validators=[phone_regex],
        verbose_name='شماره موبایل',
        db_index=True
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='نام (اختیاری)'
    )
    
    # Which product
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='leads',
        verbose_name='محصول',
        null=True, blank=True,
        help_text='اختیاری - اگر خالی باشد، سرنخ عمومی است'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.PENDING,
        verbose_name='وضعیت',
        db_index=True
    )
    
    # Notification tracking
    notified_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان اطلاع‌رسانی'
    )
    notification_method = models.CharField(
        max_length=20, blank=True,
        verbose_name='روش اطلاع‌رسانی',
        help_text='SMS, Email, etc.'
    )
    
    # Conversion tracking
    converted_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان تبدیل به خرید'
    )
    order = models.ForeignKey(
        'order.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='converted_from_leads',
        verbose_name='سفارش تبدیل‌شده'
    )
    
    # Admin notes
    admin_notes = models.TextField(
        blank=True,
        verbose_name='یادداشت ادمین'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')
    
    class Meta:
        verbose_name = 'سرنخ'
        verbose_name_plural = 'سرنخ‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'status']),
            models.Index(fields=['product', 'status']),
        ]
        constraints = [
            # One pending lead per phone per product
            models.UniqueConstraint(
                fields=['phone', 'product'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_lead_per_phone_product'
            ),
        ]
    
    def __str__(self):
        product_name = self.product.name if self.product else 'سرنخ عمومی'
        return f"{self.name or self.phone} - {product_name}"
    
    def notify(self, method='SMS'):
        """Mark lead as notified"""
        self.status = self.LeadStatus.NOTIFIED
        self.notified_at = timezone.now()
        self.notification_method = method
        self.save(update_fields=['status', 'notified_at', 'notification_method'])
    
    def convert(self, order):
        """Mark lead as converted to purchase"""
        self.status = self.LeadStatus.CONVERTED
        self.converted_at = timezone.now()
        self.order = order
        self.save(update_fields=['status', 'converted_at', 'order'])
    
    def cancel(self):
        """Cancel the lead"""
        self.status = self.LeadStatus.CANCELLED
        self.save(update_fields=['status'])
    
    @classmethod
    def can_create_lead(cls, phone, product=None):
        """
        Check if a new lead can be created.
        
        Rules:
        - No duplicate pending leads for same phone + product
        - Phone must be valid format
        """
        if not re.match(r'^09[0-9]{9}$', phone):
            return False, 'شماره موبایل نامعتبر است'
        
        if product:
            existing = cls.objects.filter(
                phone=phone,
                product=product,
                status=cls.LeadStatus.PENDING
            ).exists()
            if existing:
                return False, 'برای این محصول قبلاً ثبت شده است'
        
        return True, 'مجاز به ثبت'
    
    @classmethod
    def get_pending_leads_for_product(cls, product):
        """Get all pending leads for a specific product"""
        return cls.objects.filter(
            product=product,
            status=cls.LeadStatus.PENDING
        ).order_by('created_at')
# -*- coding: utf-8 -*-
"""D-125: مدل VisitorLead — سرنخ‌های بازدید انسانی سایت (از لاگ nginx)."""
import uuid

from django.db import models


class VisitorLead(models.Model):
    """هر IP انسانِ فیلترشده = یک سرنخ با مرحلهٔ قیف و وضعیت CRM.
    اطلاعات از snapshot تحلیل لاگ nginx وارد می‌شود (commands/import_log_leads)."""

    class Stage(models.TextChoices):
        HOME = 'HOME', 'بازدید ساده'
        PRODUCT = 'PRODUCT', 'مشاهده محصول'
        CART = 'CART', 'سبد خرید'
        CHECKOUT = 'CHECKOUT', 'تسویه حساب'
        PAYMENT = 'PAYMENT', 'صفحه پرداخت'
        CONVERTED = 'CONVERTED', 'خرید موفق'

    class LeadStatus(models.TextChoices):
        NEW = 'NEW', 'جدید (نیاز به پیگیری)'
        CONTACTED = 'CONTACTED', 'تماس گرفته شد'
        NOANSWER = 'NOANSWER', 'بدون پاسخ'
        LOST = 'LOST', 'از دست رفته'
        BUYER = 'BUYER', 'خریدار'
        JUNK = 'JUNK', 'تست/نامعتبر'

    StageRank = {'HOME': 1, 'PRODUCT': 2, 'CART': 3, 'CHECKOUT': 4, 'PAYMENT': 5, 'CONVERTED': 6}
    STAGES = [('HOME', 1, 'صفحه اصلی'), ('PRODUCT', 2, 'محصول'), ('CART', 3, 'سبد'),
              ('CHECKOUT', 4, 'تسویه'), ('PAYMENT', 5, 'پرداخت'), ('CONVERTED', 6, 'خرید')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip = models.GenericIPAddressField(unique=True, db_index=True, verbose_name='IP')

    country = models.CharField(max_length=60, blank=True, verbose_name='کشور')
    city = models.CharField(max_length=60, blank=True, verbose_name='شهر')
    isp = models.CharField(max_length=120, blank=True, verbose_name='ISP/اپراتور')
    is_vpn = models.BooleanField(default=False, verbose_name='مشکوک به VPN')

    device = models.CharField(max_length=20, blank=True, verbose_name='دستگاه')
    channel_first = models.CharField(max_length=40, blank=True, verbose_name='کانال ورود')
    channels = models.JSONField(default=list, blank=True, verbose_name='همهٔ کانال‌ها')

    first_seen = models.DateTimeField(null=True, blank=True, verbose_name='اولین بازدید')
    last_seen = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='آخرین بازدید')

    sessions_count = models.PositiveIntegerField(default=0, verbose_name='تعداد سشن')
    page_views = models.PositiveIntegerField(default=0, verbose_name='تعداد ویو')

    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.HOME,
                             db_index=True, verbose_name='مرحلهٔ قیف')
    stage_rank = models.PositiveSmallIntegerField(default=1, db_index=True)
    is_hot = models.BooleanField(default=False, verbose_name='سرنخ داغ')

    actions = models.JSONField(default=dict, blank=True, verbose_name='اقدام‌ها (POST)')
    order_refs = models.CharField(max_length=200, blank=True, verbose_name='سفارش‌ها در لاگ')
    orders_matched = models.JSONField(default=list, blank=True, verbose_name='سفارش‌های در DB')

    sessions = models.JSONField(default=list, blank=True, verbose_name='جزئیات سشن‌ها')

    status = models.CharField(max_length=12, choices=LeadStatus.choices,
                              default=LeadStatus.NEW, db_index=True, verbose_name='وضعیت CRM')
    admin_notes = models.TextField(blank=True, verbose_name=' یادداشت ادمین')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ به‌روزرسانی')

    class Meta:
        verbose_name = 'سرنخ بازدید'
        verbose_name_plural = 'سرنخ‌های بازدید'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['stage', 'status']),
            models.Index(fields=['-last_seen']),
        ]

    def __str__(self):
        loc = self.city or self.country or '؟'
        return f"{self.ip} — {loc} — {self.get_stage_display()}"

    @property
    def hot_active(self):
        """داغ و هنوز پیگیری‌ نشده."""
        return self.is_hot and self.status == self.LeadStatus.NEW
