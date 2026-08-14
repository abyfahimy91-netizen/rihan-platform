from django.db import models
import json

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
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name="دسته‌بندی")
    title = models.CharField(max_length=255, verbose_name="عنوان محصول")
    slug = models.SlugField(max_length=280, unique=True, allow_unicode=True, verbose_name="اسلاگ سئو")
    sku = models.CharField(max_length=50, unique=True, verbose_name="کد کالا (SKU)")
    summary = models.TextField(verbose_name="چکیده و معرفی کوتاه")
    price = models.PositiveBigIntegerField(verbose_name="قیمت (تومان)")
    compare_at_price = models.PositiveBigIntegerField(null=True, blank=True, verbose_name="قیمت قبل از تخفیف (تومان)")
    stock = models.PositiveIntegerField(default=10, verbose_name="موجودی انبار")
    is_available = models.BooleanField(default=True, verbose_name="موجود برای خرید")
    is_featured = models.BooleanField(default=False, verbose_name="محصول منتخب صفحه اصلی")
    meta_title = models.CharField(max_length=150, blank=True, verbose_name="عنوان سئو")
    meta_description = models.CharField(max_length=250, blank=True, verbose_name="توضیحات سئو")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

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
