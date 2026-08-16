import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        ordering = ['name']

    def __str__(self):
        return self.name

class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تأمین"

    def __str__(self):
        return self.title

class Product(models.Model):
    STATUS_CHOICES = [('draft', 'جمناا'), ('active', 'فعال'), ('inactive', 'خسمال'), ('out_of_stock', 'ناموجد')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    unit = models.CharField(max_length=20, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    margin_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    short_description = models.TextField()
    origin_story = models.TextField(verbose_name="داستان مبدأ")
    long_description = models.TextField(blank=True)
    seo_title = models.CharField(max_length=60, blank=True, null=True)
    seo_description = models.CharField(max_length=160, blank=True, null=True)
    seo_keywords = models.JSONField(blank=True, null=True)
    images = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "محصول"
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        if self.base_price:
            try:
                margin = float(self.base_price) * (float(self.margin_percent) / 100)
                self.final_price = float(self.base_price) + float(self.shipping_cost) + margin
            except (TypeError, ValueError):
                pass
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.status = 'inactive'
        self.save()
