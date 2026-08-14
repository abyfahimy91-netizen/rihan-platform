from django.contrib import admin
from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier

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

class ProductBlockInline(admin.TabularInline):
    model = ProductBlock
    extra = 1

@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'product', 'block_type', 'sort_order', 'is_active']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['title', 'contact_name', 'phone', 'city', 'is_active', 'created_at']
    search_fields = ['title', 'contact_name', 'phone', 'city']
