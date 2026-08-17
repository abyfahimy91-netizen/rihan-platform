import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=11, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.title


class Product(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('out_of_stock', 'Out of Stock'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    unit = models.CharField(max_length=20, blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    short_description = models.TextField()
    origin_story = models.TextField(verbose_name="Origin Story")
    long_description = models.TextField(blank=True)
    seo_title = models.CharField(max_length=60, blank=True, null=True)
    seo_description = models.CharField(max_length=160, blank=True, null=True)
    seo_keywords = models.JSONField(blank=True, null=True)
    images = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
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
    unit = models.CharField(max_length=20, blank=True)
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
        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"

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
            raise ValueError("Insufficient stock")
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
    reference_id = models.UUIDField(null=True, blank=True)
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
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"
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
    block_type = models.CharField(max_length=50, choices=BLOCK_TYPES)
    content = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order']

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
