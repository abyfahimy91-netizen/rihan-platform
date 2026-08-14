import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

files = {
    BASE / "src/apps/catalog/__init__.py": "",
    BASE / "src/apps/catalog/management/__init__.py": "",
    BASE / "src/apps/catalog/management/commands/__init__.py": "",

    BASE / "src/apps/catalog/apps.py": """from django.apps import AppConfig

class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.catalog'
    verbose_name = 'مدیریت کاتالوگ و محصولات'
""",

    BASE / "src/apps/catalog/models.py": """from django.db import models
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
""",

    BASE / "src/apps/catalog/admin.py": """from django.contrib import admin
from .models import Category, Product, ProductImage, ContentBlock

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'sort_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'sku', 'category', 'price', 'stock', 'is_available', 'is_featured']
    list_filter = ['category', 'is_available', 'is_featured']
    search_fields = ['title', 'sku']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline, ContentBlockInline]

@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'product', 'block_type', 'sort_order', 'is_active']
""",

    BASE / "src/apps/catalog/serializers.py": """from rest_framework import serializers
from .models import Category, Product, ProductImage, ContentBlock

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'alt_text', 'is_primary', 'sort_order']

class ContentBlockSerializer(serializers.ModelSerializer):
    block_type_display = serializers.CharField(source='get_block_type_display', read_only=True)
    class Meta:
        model = ContentBlock
        fields = ['id', 'block_type', 'block_type_display', 'title', 'subtitle', 'content', 'extra_data', 'sort_order']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'sort_order']

class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image_url = serializers.SerializerMethodField()
    has_discount = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'slug', 'sku', 'category', 'category_name', 'summary', 'price', 'compare_at_price', 'has_discount', 'discount_percent', 'stock', 'is_available', 'is_featured', 'primary_image_url']

    def get_primary_image_url(self, obj):
        img = obj.primary_image
        return img.image_url if img else None

class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    content_blocks = ContentBlockSerializer(many=True, read_only=True)
    schema_json_ld = serializers.CharField(source='get_schema_json_ld', read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ['meta_title', 'meta_description', 'images', 'content_blocks', 'schema_json_ld']
""",

    BASE / "src/apps/catalog/views.py": """from django.shortcuts import render, get_object_or_404
from rest_framework import generics
from .models import Category, Product, ContentBlock
from .serializers import CategorySerializer, ProductListSerializer, ProductDetailSerializer, ContentBlockSerializer

def product_list_view(request):
    categories = Category.objects.filter(is_active=True)
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    products = Product.objects.filter(is_available=True)
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if search_query:
        products = products.filter(title__icontains=search_query)

    context = {'categories': categories, 'products': products, 'selected_category': category_slug, 'search_query': search_query}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'catalog/partials/product_grid.html', context)
    return render(request, 'catalog/list.html', context)

def product_detail_view(request, slug):
    product = get_object_or_404(Product.objects.prefetch_related('images', 'content_blocks'), slug=slug, is_available=True)
    context = {'product': product, 'content_blocks': product.content_blocks.filter(is_active=True)}
    return render(request, 'catalog/detail.html', context)

class CategoryListAPI(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer

class ProductListAPI(generics.ListAPIView):
    serializer_class = ProductListSerializer
    def get_queryset(self):
        qs = Product.objects.filter(is_available=True)
        cat = self.request.query_params.get('category')
        if cat:
            qs = qs.filter(category__slug=cat)
        return qs

class ProductDetailAPI(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_available=True)
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'

class ContentBlockListAPI(generics.ListAPIView):
    serializer_class = ContentBlockSerializer
    def get_queryset(self):
        return ContentBlock.objects.filter(product__slug=self.kwargs.get('product_slug'), is_active=True)
""",

    BASE / "src/apps/catalog/urls.py": """from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list_view, name='product_list'),
    path('products/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('api/catalog/categories/', views.CategoryListAPI.as_view(), name='api_categories'),
    path('api/catalog/products/', views.ProductListAPI.as_view(), name='api_products'),
    path('api/catalog/products/<slug:slug>/', views.ProductDetailAPI.as_view(), name='api_product_detail'),
    path('api/catalog/products/<slug:product_slug>/blocks/', views.ContentBlockListAPI.as_view(), name='api_product_blocks'),
]
""",

    BASE / "src/apps/catalog/sitemaps.py": """from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Category

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_available=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('product_detail', kwargs={'slug': obj.slug})

class CategorySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return f"{reverse('product_list')}?category={obj.slug}"
""",

    BASE / "src/apps/catalog/management/commands/seed_catalog.py": """from django.core.management.base import BaseCommand
from apps.catalog.models import Category, Product, ProductImage, ContentBlock

class Command(BaseCommand):
    help = 'Seed catalog data'

    def handle(self, *args, **options):
        cat_food, _ = Category.objects.get_or_create(slug="authentic-foods", defaults={"name": "خوراکی‌های اصیل و سنتی", "icon": "🌿", "sort_order": 1})
        cat_spices, _ = Category.objects.get_or_create(slug="spices-saffron", defaults={"name": "زعفران و چاشنی‌های ناب", "icon": "✨", "sort_order": 2})

        p1, _ = Product.objects.get_or_create(
            slug="sabalan-natural-honey",
            defaults={
                "category": cat_food,
                "title": "عسل گون و کوهستان سبلان (خالص و خام)",
                "sku": "RIHAN-HONEY-01",
                "summary": "عسل دست‌چین‌شده از زنبورستان‌های دامنه‌های مرتفع سبلان با ساکارز زیر ۲ درصد و تضمین آزمایشگاهی.",
                "price": 480000,
                "compare_at_price": 550000,
                "stock": 25,
                "is_available": True,
                "is_featured": True,
                "meta_title": "خرید عسل طبیعی سبلان با برگه آزمایش | ریهان",
                "meta_description": "عسل کوهستان سبلان با ساکارز زیر ۲ درصد و مستقیم از زنبوردار معتمد."
            }
        )
        ProductImage.objects.get_or_create(product=p1, defaults={"image_url": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=800", "alt_text": "عسل طبیعی سبلان ریهان", "is_primary": True})
        ContentBlock.objects.get_or_create(product=p1, block_type="story", defaults={"title": "روایت اصالت و خاستگاه", "subtitle": "از مراتع ۲۰۰۰ متری سبلان تا سفره شما", "content": "این عسل از مراتع بکر سبلان برداشت شده و کاملاً خام و بدون حرارت است.", "sort_order": 1})
        ContentBlock.objects.get_or_create(product=p1, block_type="trust", defaults={"title": "تضمین اصالت و سلامت ریهان", "subtitle": "آزمایش‌شده در آزمایشگاه صنایع غذایی", "content": "ساکارز ۱.۴٪، بدون شکر تغذیه‌ای و با ضمانت بازگشت وجه.", "sort_order": 2})

        p2, _ = Product.objects.get_or_create(
            slug="qaenat-super-negin-saffron",
            defaults={
                "category": cat_spices,
                "title": "زعفران سوپر نگین صادراتی قائنات (مثقالی)",
                "sku": "RIHAN-SAFFRON-01",
                "summary": "کلاله‌های ضخیم و یکدست زعفران امسالی با رنگ‌دهی بالای ۲۵۰ و عطر سرمست‌کننده.",
                "price": 650000,
                "compare_at_price": 720000,
                "stock": 40,
                "is_available": True,
                "is_featured": True,
                "meta_title": "خرید زعفران سوپر نگین قائنات اصیل | ریهان",
                "meta_description": "زعفران سوپر نگین قائنات امسالی، قلم‌درشت و بدون خامی."
            }
        )
        ProductImage.objects.get_or_create(product=p2, defaults={"image_url": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=800", "alt_text": "زعفران سوپر نگین قائنات", "is_primary": True})
        ContentBlock.objects.get_or_create(product=p2, block_type="story", defaults={"title": "چرا این زعفران متمایز است؟", "subtitle": "دست‌چین سپیده‌دم از مزارع قائنات", "content": "برداشت قبل از طلوع آفتاب جهت حفظ حداکثری عطر و کروسین.", "sort_order": 1})

        self.stdout.write(self.style.SUCCESS("✓ Seed data loaded successfully."))
""",

    BASE / "tests/test_catalog.py": """from django.test import TestCase, Client
from django.urls import reverse
from apps.catalog.models import Category, Product, ContentBlock

class CatalogTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="ارگانیک", slug="organic")
        self.p = Product.objects.create(
            category=self.cat, title="عسل سبلان", slug="honey-sabalan",
            sku="RIHAN-H1", summary="عسل طبیعی", price=450000, compare_at_price=500000, stock=10
        )
        self.b = ContentBlock.objects.create(product=self.p, block_type="story", title="داستان عسل", content="متن داستان")

    def test_product_model(self):
        self.assertTrue(self.p.has_discount)
        self.assertEqual(self.p.discount_percent, 10)

    def test_views_and_apis(self):
        c = Client()
        self.assertEqual(c.get(reverse('product_list')).status_code, 200)
        self.assertEqual(c.get(reverse('product_detail', kwargs={'slug': self.p.slug})).status_code, 200)
        self.assertEqual(c.get(reverse('api_products')).status_code, 200)
"""
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created: {path.name}")

print("All module 1 files generated successfully.")
