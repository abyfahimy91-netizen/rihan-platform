"""
مدل‌های ماژول پنل خانواده ریهان (M3)
منطبق بر:
- MVP-SCOPE.md بخش M3
- USER-STORIES.md (US-017, US-025, US-026, US-027)
- TRUST-CHECKLIST.md (چک‌لیست اعتماد ۷ موردی)
- DECISIONS.md (D-006, D-075, D-079)
- معیارهای پذیرش M3

نسخه: 2.0 (بازنویسی کامل مطابق مستندات)
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ActivityLog(models.Model):
    """
    لاگ فعالیت‌های پنل خانواده.
    
    منطبق بر US-026: مشاهده لاگ فعالیت‌ها
    معیارهای پذیرش:
    - لاگ: ورود / تغییر محصول / تأیید سفارش / تغییر ماژول
    - نمایش: چه کسی + چه کاری + چه زمانی + از کجا
    - فیلتر بر اساس کاربر و بازه زمانی
    """
    
    ACTION_CHOICES = [
        ('login', 'ورود'),
        ('logout', 'خروج'),
        ('create', 'ایجاد'),
        ('update', 'ویرایش'),
        ('delete', 'حذف'),
        ('publish', 'انتشار'),
        ('approve', 'تأیید'),
        ('reject', 'رد'),
        ('add_member', 'افزودن عضو'),
        ('remove_member', 'حذف عضو'),
        ('admin_deactivate', 'غیرفعال‌سازی ادمین'),
        ('admin_activate', 'فعال‌سازی ادمین'),
        ('change_settings', 'تغییر تنظیمات'),
        ('order_approve', 'تأیید سفارش'),
        ('order_reject', 'رد سفارش'),
        ('review_approve', 'تأیید نظر'),
        ('review_reject', 'رد نظر'),
        ('review_reply', 'پاسخ به نظر'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name='کاربر'
    )
    
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name='نوع فعالیت'
    )
    
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='توضیحات'
    )
    
    entity_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='نوع موجودیت',
        help_text='مثال: product, order, review, user'
    )
    
    entity_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='شناسه موجودیت'
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='آی‌پی'
    )
    
    user_agent = models.TextField(
        blank=True,
        default='',
        verbose_name='User Agent'
    )
    
    changes = models.JSONField(
        null=True,
        blank=True,
        verbose_name='تغییرات',
        help_text='تغییرات اعمال شده به صورت JSON'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
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
            models.Index(fields=['entity_type', 'entity_id']),
        ]
    
    def __str__(self):
        user_name = self.user.username if self.user else 'سیستم'
        return f"{user_name} - {self.get_action_display()} - {self.created_at}"


class SiteSettings(models.Model):
    """
    تنظیمات سایت.
    
    منطبق بر US-027: تنظیمات سایت
    معیارهای پذیرش:
    - نام سایت + شعار + توضیحات
    - شماره کارت + نام صاحب حساب
    - شماره تماس + آدرس
    - متن‌های ثابت (درباره ما، سیاست مرجوعی)
    - ذخیره با یک کلیک
    
    فقط یک نمونه می‌تواند وجود داشته باشد (Singleton).
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    
    # اطلاعات عمومی
    site_name = models.CharField(
        max_length=100,
        blank=True,
        default='ریحان',
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
        blank=True,
        default='تومان',
        verbose_name='واحد پول'
    )
    
    # تنظیمات بصری
    primary_color = models.CharField(
        max_length=20,
        blank=True,
        default='#8B4513',
        verbose_name='رنگ اصلی'
    )
    font_family = models.CharField(
        max_length=50,
        blank=True,
        default='Vazir',
        verbose_name='فونت'
    )
    
    # اطلاعات تماس (Trust Checklist)
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
    support_hours = models.CharField(
        max_length=50,
        blank=True,
        default='11 صبح تا 7 عصر',
        verbose_name='ساعات پاسخگویی'
    )
    office_city = models.CharField(
        max_length=50,
        blank=True,
        default='تبریز',
        verbose_name='شهر دفتر'
    )
    office_province = models.CharField(
        max_length=50,
        blank=True,
        default='آذربایجان شرقی',
        verbose_name='استان دفتر'
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
        verbose_name='صاحب کارت'
    )
    
    # تنظیمات سیستم
    low_stock_threshold = models.IntegerField(
        default=5,
        verbose_name='آستانه موجودی کم'
    )
    
    # متن‌های ثابت
    about_us_text = models.TextField(
        blank=True,
        default='',
        verbose_name='متن درباره ما'
    )
    return_policy_text = models.TextField(
        blank=True,
        default='',
        verbose_name='متن سیاست مرجوعی'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخرین به‌روزرسانی'
    )
    
    class Meta:
        app_label = 'family_panel'
        verbose_name = 'تنظیمات سایت'
        verbose_name_plural = 'تنظیمات سایت'
    
    def __str__(self):
        return f"تنظیمات {self.site_name}"
    
    @classmethod
    def get_settings(cls):
        """
        دریافت تنظیمات (ایجاد اگر وجود نداشته باشد).
        الگوی Singleton برای تنظیمات سایت.
        """
        settings_obj, created = cls.objects.get_or_create(
            id=uuid.UUID('00000000-0000-0000-0000-000000000001'),
            defaults={
                'site_name': 'ریحان',
                'currency': 'تومان',
                'primary_color': '#8B4513',
                'font_family': 'Vazir',
                'support_hours': '11 صبح تا 7 عصر',
                'office_city': 'تبریز',
                'office_province': 'آذربایجان شرقی',
                'low_stock_threshold': 5,
            }
        )
        return settings_obj


class ProductDraft(models.Model):
    """
    پیش‌نویس محصول با Trust Checklist.
    
    منطبق بر TRUST-CHECKLIST.md بخش ۱۰.۱:
    قبل از انتشار هر محصول، ادمین باید این چک‌لیست را تأیید کند:
    - عکس اصلی واقعی (حداقل ۱ عکس)
    - داستان مبدأ محصول (۲-۴ جمله واقعی)
    - قیمت نهایی (شامل هزینه ارسال)
    - شفافیت سیاست‌ها (۳ سیاست کلیدی)
    - اطلاعات تماس واقعی (حداقل ۲ راه)
    - نظرات یا حالت «اولین نفر»
    - حضور فیزیکی (شهر + ساعات کاری)
    """
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('ready', 'آماده انتشار'),
        ('published', 'منتشر شده'),
        ('rejected', 'رد شده'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    
    # اتصال به Product (M1)
    product_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='شناسه محصول'
    )
    product_name = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='نام محصول'
    )
    
    # وضعیت
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='وضعیت'
    )
    
    # Trust Checklist - ۷ مورد مطابق TRUST-CHECKLIST.md
    # ۱. عکس اصلی واقعی
    has_real_photo = models.BooleanField(
        default=False,
        verbose_name='عکس اصلی واقعی دارد'
    )
    photo_count = models.IntegerField(
        default=0,
        verbose_name='تعداد عکس‌ها'
    )
    
    # ۲. داستان مبدأ محصول
    has_origin_story = models.BooleanField(
        default=False,
        verbose_name='داستان مبدأ دارد'
    )
    origin_story_text = models.TextField(
        blank=True,
        default='',
        verbose_name='متن داستان مبدأ',
        help_text='۲-۴ جمله واقعی از مبدأ محصول'
    )
    
    # ۳. قیمت نهایی
    has_final_price = models.BooleanField(
        default=False,
        verbose_name='قیمت نهایی دارد'
    )
    final_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='قیمت نهایی (تومان)'
    )
    
    # ۴. شفافیت سیاست‌ها
    has_policy_transparency = models.BooleanField(
        default=False,
        verbose_name='شفافیت سیاست‌ها دارد'
    )
    
    # ۵. اطلاعات تماس واقعی
    has_real_contact = models.BooleanField(
        default=False,
        verbose_name='اطلاعات تماس واقعی دارد'
    )
    
    # ۶. نظرات یا حالت «اولین نفر»
    has_reviews_or_empty_state = models.BooleanField(
        default=False,
        verbose_name='نظرات یا حالت خالی دارد'
    )
    
    # ۷. حضور فیزیکی
    has_physical_presence = models.BooleanField(
        default=False,
        verbose_name='حضور فیزیکی دارد'
    )
    
    # محتوای بلوک‌محور (M14)
    content_blocks = models.JSONField(
        default=list,
        blank=True,
        verbose_name='بلوک‌های محتوا'
    )
    
    # کاربران
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_drafts',
        verbose_name='ایجادکننده'
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_drafts',
        verbose_name='منتشرکننده'
    )
    
    # تاریخ‌ها
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
        verbose_name = 'پیش‌نویس محصول'
        verbose_name_plural = 'پیش‌نویس‌های محصول'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"پیش‌نویس {self.product_name or 'بدون نام'} - {self.get_status_display()}"
    
    def is_trust_checklist_complete(self):
        """
        بررسی تکمیل چک‌لیست اعتماد (۷ مورد).
        منطبق بر TRUST-CHECKLIST.md بخش ۱۰.۱
        """
        return all([
            self.has_real_photo,
            self.has_origin_story,
            self.has_final_price,
            self.has_policy_transparency,
            self.has_real_contact,
            self.has_reviews_or_empty_state,
            self.has_physical_presence,
        ])
    
    def can_publish(self):
        """بررسی امکان انتشار"""
        return self.is_trust_checklist_complete() and self.status == 'ready'
    
    def get_trust_checklist_status(self):
        """دریافت وضعیت چک‌لیست اعتماد"""
        return {
            'has_real_photo': self.has_real_photo,
            'has_origin_story': self.has_origin_story,
            'has_final_price': self.has_final_price,
            'has_policy_transparency': self.has_policy_transparency,
            'has_real_contact': self.has_real_contact,
            'has_reviews_or_empty_state': self.has_reviews_or_empty_state,
            'has_physical_presence': self.has_physical_presence,
            'is_complete': self.is_trust_checklist_complete(),
            'missing_items': self.get_missing_trust_items(),
        }
    
    def get_missing_trust_items(self):
        """دریافت لیست موارد ناقص چک‌لیست"""
        missing = []
        if not self.has_real_photo:
            missing.append('عکس اصلی واقعی')
        if not self.has_origin_story:
            missing.append('داستان مبدأ محصول')
        if not self.has_final_price:
            missing.append('قیمت نهایی')
        if not self.has_policy_transparency:
            missing.append('شفافیت سیاست‌ها')
        if not self.has_real_contact:
            missing.append('اطلاعات تماس واقعی')
        if not self.has_reviews_or_empty_state:
            missing.append('نظرات یا حالت خالی')
        if not self.has_physical_presence:
            missing.append('حضور فیزیکی')
        return missing


class SensitiveOperation(models.Model):
    """
    عملیات حساس با تأیید دو مرحله‌ای.
    
    منطبق بر معیار پذیرش M3:
    "تأیید دو مرحله‌ای برای عملیات حساس (حذف محصول، تغییر قیمت)"
    
    عملیات حساس:
    - حذف محصول
    - تغییر قیمت
    - حذف کاربر
    - تغییر تنظیمات حیاتی
    """
    
    OPERATION_CHOICES = [
        ('delete_product', 'حذف محصول'),
        ('change_price', 'تغییر قیمت'),
        ('delete_user', 'حذف کاربر'),
        ('change_critical_settings', 'تغییر تنظیمات حیاتی'),
        ('publish_product', 'انتشار محصول'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار تأیید'),
        ('approved', 'تأیید شده'),
        ('rejected', 'رد شده'),
        ('expired', 'منقضی شده'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='شناسه'
    )
    
    operation_type = models.CharField(
        max_length=30,
        choices=OPERATION_CHOICES,
        verbose_name='نوع عملیات'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='وضعیت'
    )
    
    # چه کسی درخواست داده
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sensitive_operations_requested',
        verbose_name='درخواست‌دهنده'
    )
    
    # چه کسی تأیید کرده
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sensitive_operations_approved',
        verbose_name='تأییدکننده'
    )
    
    # جزئیات عملیات
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='توضیحات'
    )
    
    entity_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='نوع موجودیت'
    )
    
    entity_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='شناسه موجودیت'
    )
    
    # داده‌های عملیات
    operation_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='داده‌های عملیات'
    )
    
    # تاریخ‌ها
    requested_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='تاریخ درخواست'
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ تأیید'
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ انقضا'
    )
    
    class Meta:
        app_label = 'family_panel'
        verbose_name = 'عملیات حساس'
        verbose_name_plural = 'عملیات‌های حساس'
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.get_status_display()}"
    
    def is_expired(self):
        """بررسی انقضای عملیات"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
    
    def can_approve(self, user):
        """بررسی امکان تأیید توسط کاربر"""
        if self.status != 'pending':
            return False
        if self.is_expired():
            return False
        # تأییدکننده نباید همان درخواست‌دهنده باشد
        if self.requested_by and user == self.requested_by:
            return False
        return True


class ProductContent(models.Model):
    """
    محتوای بلوک‌محور محصولات (US-055)
    
    Proxy model برای مدیریت بلوک‌های محتوا در پنل خانواده.
    هر محصول یک ProductContent دارد که بلوک‌های محتوایی آن را نگه می‌دارد.
    """
    product = models.OneToOneField(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='content_blocks'
    )
    
    # بلوک‌ها به صورت JSON ذخیره می‌شوند
    blocks = models.JSONField(
        default=list,
        help_text='لیست بلوک‌های محتوا به صورت JSON'
    )
    
    # وضعیت انتشار
    is_published = models.BooleanField(
        default=False,
        help_text='آیا محتوا منتشر شده است؟'
    )
    
    # تاریخچه
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='زمان آخرین انتشار'
    )
    
    # متادیتا
    draft_title = models.CharField(
        max_length=200,
        blank=True,
        help_text='عنوان پیش‌نویس'
    )
    
    class Meta:
        verbose_name = 'محتوای محصول'
        verbose_name_plural = 'محتواهای محصولات'
    
    def __str__(self):
        return f'محتوای {self.product.name}'
    
    def get_blocks(self):
        """دریافت لیست بلوک‌ها"""
        return self.blocks if self.blocks else []
    
    def set_blocks(self, blocks):
        """تنظیم لیست بلوک‌ها"""
        self.blocks = blocks
        self.save(update_fields=['blocks', 'updated_at'])
    
    def publish(self):
        """انتشار محتوا"""
        from django.utils import timezone
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at', 'updated_at'])
    
    def unpublish(self):
        """لغو انتشار"""
        self.is_published = False
        self.save(update_fields=['is_published', 'updated_at'])
