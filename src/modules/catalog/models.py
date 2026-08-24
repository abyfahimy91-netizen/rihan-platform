import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("نام دسته", max_length=150)
    slug = models.SlugField("نامک (آدرس)", max_length=180, unique=True, allow_unicode=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='دسته والد'
    )
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField("عنوان / نام تامین‌کننده", max_length=150)
    city = models.CharField("شهر", max_length=100)
    phone = models.CharField("تلفن همراه", max_length=11, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplier_profile',
        verbose_name='کاربر سیستمی مرتبط',
    )

    class Meta:
        verbose_name = "تامین‌کننده"
        verbose_name_plural = "تامین‌کنندگان"

    def __str__(self):
        return self.title


class Product(models.Model):
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('active', 'فعال (منتشر شده)'),
        ('inactive', 'غیرفعال (مخفی)'),
        ('out_of_stock', 'ناموجود'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField("نامک (آدرس صفحه)", max_length=100, unique=True, allow_unicode=True)
    name = models.CharField("نام محصول", max_length=150)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='دسته‌بندی'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='تامین‌کننده'
    )
    unit = models.CharField("واحد فروش (مثلا کیلوگرم)", max_length=20, blank=True)
    base_price = models.DecimalField(
        verbose_name="قیمت پایه (تومان)",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    shipping_cost = models.DecimalField(
        verbose_name="هزینه ارسال (تومان)",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    margin_percent = models.DecimalField(
        verbose_name="حاشیه سود (درصد)",
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    final_price = models.DecimalField(
        verbose_name="قیمت نهایی (خودکار محاسبه می‌شود)",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    short_description = models.TextField("توضیح کوتاه (نمایش در لیست)")
    origin_story = models.TextField(verbose_name="داستان محصول")
    long_description = models.TextField("توضیحات کامل", blank=True)
    seo_title = models.CharField("عنوان سئو", max_length=60, blank=True, null=True)
    seo_description = models.CharField("توضیح سئو", max_length=160, blank=True, null=True)
    seo_keywords = models.JSONField("کلمات کلیدی سئو", blank=True, null=True)
    images = models.JSONField("تصاویر (مدیریت از بخش گالری)", default=list, blank=True)
    metadata = models.JSONField("متادیتا (فنی)", default=dict, blank=True)
    status = models.CharField(
        "وضعیت انتشار",
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    is_featured = models.BooleanField("نمایش در صفحه اصلی", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def calculate_final_price(self):
        try:
            margin = float(self.base_price) * (float(self.margin_percent) / 100)
            return Decimal(str(float(self.base_price) + float(self.shipping_cost) + margin))
        except (TypeError, ValueError):
            return Decimal('0')

    def save(self, *args, **kwargs):
        if self.base_price:
            self.final_price = self.calculate_final_price()
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.status = 'inactive'
        self.save()


class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Physical Stock"
    )
    unit = models.CharField("واحد", max_length=20, blank=True)
    low_stock_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Low Stock Threshold"
    )
    reserved_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Reserved Stock"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "موجودی انبار"
        verbose_name_plural = "موجودی انبار"

    def __str__(self):
        return f"Inventory for {self.product.name}"

    @property
    def available_quantity(self):
        return max(Decimal('0'), self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self):
        if self.low_stock_threshold > 0:
            return self.available_quantity <= self.low_stock_threshold
        threshold = max(
            Decimal('2'),
            Decimal(str(self.quantity)) * Decimal('0.2')
        )
        return self.available_quantity <= threshold

    def can_reserve(self, qty):
        return self.available_quantity >= qty

    def reserve(self, qty):
        if not self.can_reserve(qty):
            raise ValueError("موجودی کافی نیست")
        self.reserved_quantity += qty
        self.save()

    def release_reservation(self, qty):
        self.reserved_quantity = max(Decimal('0'), self.reserved_quantity - qty)
        self.save()

    def confirm_sale(self, qty):
        self.quantity = max(Decimal('0'), self.quantity - qty)
        self.reserved_quantity = max(Decimal('0'), self.reserved_quantity - qty)
        self.save()

    def add_stock(self, qty):
        self.quantity += qty
        self.save()

    def return_stock(self, qty):
        self.quantity += qty
        self.save()


class InventoryTransaction(models.Model):
    CHANGE_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('reservation', 'Reservation'),
        ('release', 'Release'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='Reference ID')
    stock_before = models.DecimalField(max_digits=10, decimal_places=2)
    stock_after = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )

    class Meta:
        verbose_name = "تراکنش موجودی"
        verbose_name_plural = "تاریخچه موجودی انبار"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.change_type}: {self.quantity_change} ({self.created_at})"

    @classmethod
    def create_transaction(cls, inventory, change_type, quantity_change, reason,
                          reference_type=None, reference_id=None, user=None):
        stock_before = inventory.quantity
        inventory.save()
        stock_after = inventory.quantity

        return cls.objects.create(
            inventory=inventory,
            change_type=change_type,
            quantity_change=quantity_change,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            stock_before=stock_before,
            stock_after=stock_after,
            created_by=user
        )


class ContentBlock(models.Model):
    BLOCK_TYPES = [
        ('text', 'Text'),
        ('heading', 'Heading'),
        ('image', 'Image'),
        ('gallery', 'Gallery'),
        ('video', 'Video'),
        ('link', 'Link'),
        ('quote', 'Quote'),
        ('table', 'Table'),
        ('spacer', 'Spacer'),
        ('cta', 'Call to Action'),
        ('trust_badges', 'Trust Badges'),
        ('related_products', 'Related Products'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='direct_blocks'
    )
    block_type = models.CharField("نوع بلوک", max_length=50, choices=BLOCK_TYPES)
    content = models.JSONField("محتوای بلوک", default=dict, blank=True)
    sort_order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order']
        verbose_name = "بلوک محتوای صفحه"
        verbose_name_plural = "بلوک‌های محتوای صفحات"

    def __str__(self):
        return f"{self.block_type} block"


class ProductBlock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_blocks'
    )
    block = models.ForeignKey(
        ContentBlock,
        on_delete=models.CASCADE,
        related_name='product_links'
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'block'],
                name='unique_product_block_link'
            )
        ]


@receiver(post_save, sender=Product)
def create_inventory_for_product(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.get_or_create(
            product=instance,
            defaults={
                'quantity': 0,
                'reserved_quantity': 0,
                'unit': instance.unit or '',
                'low_stock_threshold': 2,
            }
        )


class ProductImage(models.Model):
    """عکس‌های محصول — از پنل ادمین آپلود می‌شود و خودکار در سایت نمایش داده می‌شود"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gallery'
    )
    image = models.ImageField(
        upload_to='products/%Y/%m/',
        verbose_name='فایل تصویر',
    )
    caption = models.CharField(max_length=255, blank=True, verbose_name='متن جایگزین (Alt)')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'created_at']
        verbose_name = "عکس محصول"
        verbose_name_plural = "گالری تصاویر محصولات"

    def __str__(self):
        return f"تصویر {self.sort_order} — {self.product.name}"


def _sync_product_images_json(product):
    """به‌روزرسانی JSON images محصول از روی گالری تا قالب سایت بدون تغییر کار کند"""
    urls = [pi.image.url for pi in product.gallery.all()]
    if list(product.images or []) != urls:
        Product.objects.filter(pk=product.pk).update(images=urls)


@receiver(post_save, sender=ProductImage)
def sync_images_on_save(sender, instance, **kwargs):
    _sync_product_images_json(instance.product)


@receiver(post_delete, sender=ProductImage)
def sync_images_on_delete(sender, instance, **kwargs):
    if instance.product_id:
        try:
            product = Product.objects.get(pk=instance.product_id)
            _sync_product_images_json(product)
        except Product.DoesNotExist:
            pass


class ProductVariant(models.Model):
    """واریانت محصول — D-094: بسته وزنی/سایز/رنگ با قیمت و موجودی مستقل (الگوی Shopify)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='variants', verbose_name="محصول")
    title = models.CharField(max_length=120,
                             verbose_name="عنوان گزینه (مثلاً بسته ۵۰۰ گرمی یا L / آبی)")
    color_name = models.CharField(max_length=50, blank=True, default='',
                                  verbose_name="نام رنگ (اختیاری)")
    color_hex = models.CharField(max_length=9, blank=True, default='',
                                 verbose_name="کد رنگ (اختیاری، مثل #AA2233)")
    price = models.DecimalField(max_digits=12, decimal_places=0,
                                verbose_name="قیمت این گزینه (تومان)")
    unit = models.CharField(max_length=30, default='بسته', verbose_name="واحد نمایش")
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="موجودی")
    reserved_quantity = models.PositiveIntegerField(default=0, editable=False,
                                                    verbose_name="رزرو شده")
    low_stock_threshold = models.PositiveIntegerField(default=5,
                                                      verbose_name="آستانه هشدار کمبود")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "واریانت محصول"
        verbose_name_plural = "واریانت‌های محصولات"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} — {self.title}"

    @property
    def available_quantity(self):
        return max(0, int(self.stock_quantity) - int(self.reserved_quantity))

    @property
    def is_in_stock(self):
        return self.available_quantity > 0

@receiver(post_save, sender=ProductVariant)
@receiver(post_delete, sender=ProductVariant)
def sync_parent_inventory(sender, instance, **kwargs):
    """D-094: برای محصولات واریانت‌دار، موجودی انبار والد همیشه = مجموع بسته‌هاست"""
    sync_parent_inventory_for(instance.product_id)


def sync_parent_inventory_for(product_id):
    from src.modules.catalog.models import Inventory as _Inv
    totals = ProductVariant.objects.filter(product_id=product_id).aggregate(
        s=models.Sum("stock_quantity"), r=models.Sum("reserved_quantity"))
    if totals["s"] is None:
        return  # محصول بدون واریانت: انبار والد مستقل می‌ماند
    inv, created = _Inv.objects.get_or_create(product_id=product_id, defaults={"quantity": 0})
    inv.quantity = totals["s"]
    inv.reserved_quantity = totals["r"] or 0
    inv.save(update_fields=["quantity", "reserved_quantity"])
