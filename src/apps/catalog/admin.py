from django.contrib import admin
from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier, ProductReview

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


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'author_name', 'rating', 'is_verified_buyer', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'is_verified_buyer', 'rating', 'created_at']
    search_fields = ['author_name', 'comment', 'order_number', 'product__title']
    readonly_fields = ['created_at']
    actions = ['approve_reviews', 'reject_reviews']

    @admin.action(description="تأیید و انتشار عمومی نظرات انتخاب‌شده")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "نظرات انتخاب‌شده با موفقیت تأیید و منتشر شدند.")

    @admin.action(description="عدم تأیید / پنهان‌سازی نظرات")
    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, "نظرات انتخاب‌شده پنهان شدند.")
