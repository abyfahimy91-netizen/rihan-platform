from django.db import models
from django.conf import settings
import json

class Supplier(models.Model):
    """مدل تأمین‌کننده محلی و بومی (M4 - Persona 7: Mola)"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supplier_profile', verbose_name="حساب کاربری")
    title = models.CharField(max_length=150, verbose_name="نام کارگاه / تأمین‌کننده")
    contact_name = models.CharField(max_length=100, verbose_name="نام مسئول")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    city = models.CharField(max_length=100, verbose_name="شهر / منطقه")
    address = models.TextField(blank=True, verbose_name="نشانی کارگاه / مزرعه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")

    class Meta:
        verbose_name = "تأمین‌کننده"
        verbose_name_plural = "تأمین‌کنندگان"
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.city})"


class Category(models.Model):
    name = models.CharField(max_length=150, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    icon = models.CharField(max_length=50, blank=True, verbose_name="آیکون")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Product(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="تأمین‌کننده")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name="دسته‌بندی")
    title = models.CharField(max_length=255, verbose_name="عنوان محصول")
    slug = models.SlugField(max_length=280, unique=True, allow_unicode=True, verbose_name="اسلاگ سئو")
    sku = models.CharField(max_length=50, unique=True, verbose_name="کد کالا (SKU)")
    summary = models.TextField(verbose_name="چکیده و معرفی کوتاه")
    price = models.PositiveBigIntegerField(verbose_name="قیمت (تومان)")
    compare_at_price = models.PositiveBigIntegerField(null=True, blank=True, verbose_name="قیمت قبل از تخفیف (تومان)")
    supply_cost = models.PositiveBigIntegerField(default=0, verbose_name="قیمت خرید از تأمین‌کننده (تومان)")
    stock = models.PositiveIntegerField(default=10, verbose_name="موجودی انبار")
    is_available = models.BooleanField(default=True, verbose_name="موجود برای خرید")
    is_featured = models.BooleanField(default=False, verbose_name="محصول منتخب صفحه اصلی")
    
    meta_title = models.CharField(max_length=150, blank=True, verbose_name="عنوان سئو")
    meta_description = models.CharField(max_length=250, blank=True, verbose_name="توضیحات سئو")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.sku})"

    @property
    def has_discount(self):
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def discount_percent(self):
        if self.has_discount:
            diff = self.compare_at_price - self.price
            return int((diff / self.compare_at_price) * 100)
        return 0

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if not img:
            img = self.images.first()
        return img

    
    @property
    def approved_reviews(self):
        return self.reviews.filter(is_approved=True)

    @property
    def average_rating(self):
        reviews = self.approved_reviews
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 5.0

    @property
    def reviews_count(self):
        return self.approved_reviews.count()

    def get_schema_json_ld(self):
        schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": self.title,
            "description": self.summary,
            "sku": self.sku,
            "offers": {
                "@type": "Offer",
                "priceCurrency": "IRR",
                "price": self.price * 10,
                "availability": "https://schema.org/InStock" if self.stock > 0 and self.is_available else "https://schema.org/OutOfStock",
                "itemCondition": "https://schema.org/NewCondition"
            }
        }
        if self.primary_image and self.primary_image.image_url:
            schema["image"] = self.primary_image.image_url
        return json.dumps(schema, ensure_ascii=False)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="محصول")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="آدرس تصویر")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="متن جایگزین")
    is_primary = models.BooleanField(default=False, verbose_name="تصویر اصلی")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ['-is_primary', 'sort_order']

    def __str__(self):
        return f"Image for {self.product.title}"


class ContentBlock(models.Model):
    BLOCK_TYPES = [
        ('story', 'روایت اصالت و داستان محصول'),
        ('features', 'ویژگی‌ها و نکات برجسته'),
        ('trust', 'تضمین کیفیت و اعتماد'),
        ('faq', 'پرسش‌های متداول'),
        ('comparison', 'جدول مقایسه و انتخاب'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='content_blocks', verbose_name="محصول")
    block_type = models.CharField(max_length=30, choices=BLOCK_TYPES, verbose_name="نوع بلوک")
    title = models.CharField(max_length=200, verbose_name="عنوان بلوک")
    subtitle = models.CharField(max_length=255, blank=True, verbose_name="زیرعنوان")
    content = models.TextField(verbose_name="محتوای متنی")
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="داده‌های تکمیلی")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "بلوک محتوایی محصول"
        verbose_name_plural = "بلوک‌های محتوایی محصولات"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"[{self.get_block_type_display()}] {self.title}"


class ProductBlock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_block_links', verbose_name="محصول")
    content_block = models.ForeignKey(ContentBlock, on_delete=models.CASCADE, related_name='product_mappings', verbose_name="بلوک محتوایی")
    custom_title = models.CharField(max_length=200, blank=True, verbose_name="عنوان سفارشی این محصول")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "نگاشت محصول و بلوک (ProductBlock)"
        verbose_name_plural = "نگاشت‌های محصولات و بلوک‌ها (ProductBlocks)"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.title} <-> {self.content_block.title}"


class ProductReview(models.Model):
    """مدل نظرات و امتیازات خریداران معتمد (M8 - D-044 & D-048)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="محصول")
    author_name = models.CharField(max_length=150, verbose_name="نام خریدار")
    author_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس")
    order_number = models.CharField(max_length=50, blank=True, verbose_name="شماره سفارش مرتبط")
    rating = models.PositiveSmallIntegerField(choices=[(i, f"{i} ستاره") for i in range(1, 6)], default=5, verbose_name="امتیاز (۱ تا ۵)")
    comment = models.TextField(verbose_name="متن نظر و تجربه خرید")
    
    is_approved = models.BooleanField(default=False, verbose_name="تأییدشده جهت نمایش عمومی")
    is_verified_buyer = models.BooleanField(default=False, verbose_name="خریدار تأییدشده")
    
    admin_reply = models.TextField(blank=True, verbose_name="پاسخ رسمی مدیریت ریهان")
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پاسخ ادمین")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")

    class Meta:
        verbose_name = "نظر محصول (M8)"
        verbose_name_plural = "نظرات و امتیازات محصولات"
        ordering = ['-created_at']

    def __str__(self):
        return f"نظر {self.author_name} برای {self.product.title} ({self.rating} ستاره)"


class LeadCapture(models.Model):
    """مدل ثبت سرنخ و درخواست کالای ناموجود یا اختصاصی (M9 - Flow C3 & MVP-SCOPE)"""
    STATUS_CHOICES = [
        ('new', 'درخواست جدید'),
        ('in_progress', 'در حال پیگیری و گزینش تأمین‌کننده'),
        ('supplied', 'تأمین‌شده و اطلاع‌رسانی‌شده'),
        ('rejected', 'عدم امکان تأمین / بسته شده'),
    ]

    full_name = models.CharField(max_length=150, blank=True, verbose_name="نام و نام خانوادگی")
    phone = models.CharField(max_length=20, verbose_name="شماره موبایل")
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads', verbose_name="محصول ناموجود کاتالوگ")
    requested_product_name = models.CharField(max_length=200, blank=True, verbose_name="عنوان کالای درخواستی")
    notes = models.TextField(blank=True, verbose_name="توضیحات و ویژگی‌های خاص")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new', verbose_name="وضعیت پیگیری")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت و اقدامات ادمین")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")

    class Meta:
        verbose_name = "سرنخ / درخواست محصول (M9)"
        verbose_name_plural = "سرنخ‌ها و درخواست‌های محصولات"
        ordering = ['-created_at']

    def __str__(self):
        prod = self.product.title if self.product else (self.requested_product_name or "کالای درخواستی")
        return f"درخواست {prod} از {self.phone} ({self.get_status_display()})"
