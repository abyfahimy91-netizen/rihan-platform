"""
ماژول ۱: کاتالوگ محصول (M1)
منطبق بر ADR-002 (معماری دیتابیس) و D-079 (بازگشت به ایده اصلی)
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    """دسته‌بندی محصولات"""
    name = models.CharField(max_length=150, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    icon = models.CharField(max_length=50, blank=True, verbose_name="آیکون")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

class Supplier(models.Model):
    """مدل تأمین‌کننده (M4 - در اینجا برای حفظ سادگی روابط، قرار داده شده است)"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supplier_profile')
    title = models.CharField(max_length=150, verbose_name="نام کارگاه / تأمین‌کننده")
    contact_name = models.CharField(max_length=100, verbose_name="نام مسئول")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    city = models.CharField(max_length=100, verbose_name="شهر / منطقه")
    address = models.TextField(blank=True, verbose_name="نشانی کارگاه / مزرعه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تأمین‌کننده"
        verbose_name_plural = "تأمین‌کنندگان"
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.city})"

class Product(models.Model):
    """
    مدل محصول (منطبق بر ADR-002 و D-079)
    - UUID به عنوان Primary Key
    - شفافیت قیمت (D-080)
    - روایت‌گری محصول (D-079)
    - سئو از روز اول (D-079)
    """
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('out_of_stock', 'ناموجود'),
    ]

    # شناسه یکتا (UUID PK - ADR-002)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # اطلاعات پایه
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True, verbose_name="اسلاگ URL")
    name = models.CharField(max_length=150, verbose_name="نام محصول")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name="دسته‌بندی")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="تأمین‌کننده")
    unit = models.CharField(max_length=20, blank=True, verbose_name="واحد (مثلا: بسته، کیلو)")
    
    # شفافیت قیمت (D-080 - قیمت تمام‌شده شفاف)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="قیمت پایه (تومان)")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="سهم هزینه ارسال")
    margin_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="حاشیه سود (%)")
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="قیمت نهایی (تومان)")
    
    # روایت‌گری محصول (D-079)
    short_description = models.TextField(verbose_name="توضیح کوتاه")
    origin_story = models.TextField(verbose_name="داستان مبدأ (اجباری - D-079)", help_text="روایت اصالت و منبع محصول")
    long_description = models.TextField(blank=True, verbose_name="توضیح کامل")
    
    # سئو (D-079 - سئو از روز اول)
    seo_title = models.CharField(max_length=60, blank=True, null=True, verbose_name="عنوان سئو (حداکثر ۶۰ کاراکتر)")
    seo_description = models.CharField(max_length=160, blank=True, null=True, verbose_name="توضیح سئو (حداکثر ۱۶۰ کاراکتر)")
    seo_keywords = models.JSONField(blank=True, null=True, verbose_name="کلمات کلیدی سئو (JSON Array)")
    
    # متادیتا و وضعیت
    metadata = models.JSONField(default=dict, blank=True, verbose_name="اطلاعات منعطف")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    is_featured = models.BooleanField(default=False, verbose_name="محصول ویژه")
    
    # تاریخچه و Soft Delete (ADR-002)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان حذف (Soft Delete)")

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('product_detail', kwargs={'slug': self.slug})

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.status = 'inactive'
        self.save()
