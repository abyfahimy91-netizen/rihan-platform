from django.contrib import admin
from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier, ProductReview, LeadCapture

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


@admin.register(LeadCapture)
class LeadCaptureAdmin(admin.ModelAdmin):
    list_display = ['phone', 'requested_item_display', 'full_name', 'status_badge', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['phone', 'full_name', 'requested_product_name', 'product__title']
    readonly_fields = ['created_at']
    actions = ['mark_in_progress', 'mark_supplied', 'mark_rejected']

    @admin.display(description="کالای درخواستی")
    def requested_item_display(self, obj):
        if obj.product:
            return f"کالای ناموجود: {obj.product.title}"
        return obj.requested_product_name or "کالای سفارشی"

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {
            'new': '#0d6efd',
            'in_progress': '#ffc107',
            'supplied': '#198754',
            'rejected': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )

    @admin.action(description="تغییر وضعیت به: در حال پیگیری تأمین")
    def mark_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
        self.message_user(request, "سرنخ‌های انتخاب‌شده در حال پیگیری قرار گرفتند.")

    @admin.action(description="تغییر وضعیت به: تأمین شد و اطلاع‌رسانی گردید")
    def mark_supplied(self, request, queryset):
        queryset.update(status='supplied')
        self.message_user(request, "سرنخ‌های انتخاب‌شده به عنوان تأمین‌شده علامت‌گذاری شدند.")
