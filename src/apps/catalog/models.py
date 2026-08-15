from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
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

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('product_detail', kwargs={'slug': self.slug})

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


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="محصول")
    image = models.ImageField(upload_to='products/', verbose_name="عکس")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="متن جایگزین")
    is_primary = models.BooleanField(default=False, verbose_name="عکس اصلی")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عکس محصول"
        verbose_name_plural = "عکس‌های محصول"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.title} - {self.alt_text or 'بدون عنوان'}"


class ContentBlock(models.Model):
    """
    سیستم بلوک‌محور برای روایت‌گری محصول (D-079)
    
    12 نوع بلوک:
    1. text - متن آزاد (Markdown/HTML)
    2. heading - عنوان (H2, H3, H4)
    3. image - تک عکس با caption
    4. gallery - گالری عکس‌ها
    5. video - ویدیو (آپلود یا لینک)
    6. link - لینک خارجی/داخلی
    7. quote - نقل قول با نویسنده
    8. table - جدول با ردیف‌ها
    9. spacer - فاصله‌گذار
    10. cta - دکمه اقدام
    11. trust_badges - Trust Badges
    12. related_products - محصولات مرتبط
    """
    
    BLOCK_TYPES = [
        ('text', 'متن آزاد'),
        ('heading', 'عنوان'),
        ('image', 'تک عکس'),
        ('gallery', 'گالری عکس'),
        ('video', 'ویدیو'),
        ('link', 'لینک'),
        ('quote', 'نقل قول'),
        ('table', 'جدول'),
        ('spacer', 'فاصله‌گذار'),
        ('cta', 'دکمه اقدام'),
        ('trust_badges', 'Trust Badges'),
        ('related_products', 'محصولات مرتبط'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='content_blocks', verbose_name="محصول")
    block_type = models.CharField(max_length=30, choices=BLOCK_TYPES, verbose_name="نوع بلوک")
    
    # فیلدهای عمومی
    title = models.CharField(max_length=200, blank=True, verbose_name="عنوان (اختیاری)")
    subtitle = models.CharField(max_length=255, blank=True, verbose_name="زیرعنوان (اختیاری)")
    
    # فیلدهای محتوایی
    content = models.TextField(blank=True, verbose_name="محتوای متنی (Markdown/HTML)")
    
    # فیلدهای media
    image = models.ImageField(upload_to='blocks/', blank=True, verbose_name="عکس")
    video_url = models.URLField(blank=True, verbose_name="لینک ویدیو (YouTube/Aparat)")
    video_file = models.FileField(upload_to='blocks/videos/', blank=True, verbose_name="فایل ویدیو")
    
    # فیلدهای link
    link_url = models.URLField(blank=True, verbose_name="لینک")
    link_text = models.CharField(max_length=100, blank=True, verbose_name="متن لینک")
    link_target = models.CharField(max_length=20, blank=True, choices=[('_blank', 'پنجره جدید'), ('_self', 'همان پنجره')], verbose_name="نحوه باز شدن")
    
    # فیلدهای quote
    quote_author = models.CharField(max_length=100, blank=True, verbose_name="نویسنده نقل قول")
    
    # فیلدهای table و gallery (JSON)
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="داده‌های تکمیلی (JSON)", help_text="برای gallery: لیست عکس‌ها، برای table: ردیف‌ها")
    
    # فیلدهای ظاهری
    css_class = models.CharField(max_length=100, blank=True, verbose_name="CSS Class سفارشی")
    background_color = models.CharField(max_length=20, blank=True, verbose_name="رنگ پس‌زمینه (hex)")
    
    # فیلدهای کنترل
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_full_width = models.BooleanField(default=False, verbose_name="تمام عرض")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "بلوک محتوایی محصول"
        verbose_name_plural = "بلوک‌های محتوایی محصولات"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.get_block_type_display()} - {self.product.title}"

    def get_template_name(self):
        """نام template برای rendering"""
        return f'catalog/blocks/{self.block_type}.html'

    def get_context(self):
        """Context برای template"""
        context = {
            'block': self,
            'title': self.title,
            'subtitle': self.subtitle,
            'content': self.content,
            'css_class': self.css_class,
            'is_full_width': self.is_full_width,
        }
        
        # افزودن فیلدهای خاص
        if self.image:
            context['image'] = self.image
        if self.video_url:
            context['video_url'] = self.video_url
        if self.video_file:
            context['video_file'] = self.video_file
        if self.link_url:
            context['link_url'] = self.link_url
            context['link_text'] = self.link_text
            context['link_target'] = self.link_target
        if self.quote_author:
            context['quote_author'] = self.quote_author
        if self.extra_data:
            context['extra_data'] = self.extra_data
        
        return context


class ProductBlock(models.Model):
    """نگاشت محصول و بلوک (برای اشتراک‌گذاری بلوک‌ها بین محصولات)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_block_links', verbose_name="محصول")
    content_block = models.ForeignKey(ContentBlock, on_delete=models.CASCADE, related_name='product_mappings', verbose_name="بلوک محتوایی")
    custom_title = models.CharField(max_length=200, blank=True, verbose_name="عنوان سفارشی این محصول")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "نگاشت محصول و بلوک"
        verbose_name_plural = "نگاشت‌های محصولات و بلوک‌ها"
        ordering = ['sort_order', 'id']
        unique_together = [['product', 'content_block']]

    def __str__(self):
        return f"{self.product.title} <-> {self.content_block.title}"


class ProductReview(models.Model):
    """مدل نظرات و امتیازات خریداران معتمد (M8 - D-044 & D-048)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="محصول")
    author_name = models.CharField(max_length=150, verbose_name="نام خریدار")
    author_phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس")
    author_email = models.EmailField(blank=True, verbose_name="ایمیل")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="امتیاز (۱-۵)"
    )
    title = models.CharField(max_length=200, blank=True, verbose_name="عنوان نظر")
    comment = models.TextField(verbose_name="متن نظر")
    order_number = models.CharField(max_length=50, blank=True, verbose_name="شماره سفارش")
    is_verified_buyer = models.BooleanField(default=False, verbose_name="خریدار تأییدشده")
    is_approved = models.BooleanField(default=False, verbose_name="تأییدشده برای انتشار")
    admin_response = models.TextField(blank=True, verbose_name="پاسخ ادمین")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "نظر محصول"
        verbose_name_plural = "نظرات محصولات"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author_name} - {self.product.title} ({self.rating}★)"


class LeadCapture(models.Model):
    """مدل سرنخ و درخواست محصول ناموجود (M9 - جریان C3)"""
    STATUS_CHOICES = [
        ('new', 'جدید'),
        ('contacted', 'تماس گرفته‌شده'),
        ('supplied', 'تأمین شده'),
        ('obsolete', 'منسوخ'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads', verbose_name="محصول ناموجود")
    name = models.CharField(max_length=150, verbose_name="نام")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    message = models.TextField(blank=True, verbose_name="پیام")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="وضعیت")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "سرنخ"
        verbose_name_plural = "سرنخ‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.product.title if self.product else 'محصول عمومی'} ({self.get_status_display()})"
