from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier, ProductReview, LeadCapture


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'sort_order']


class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 1
    fields = [
        'block_type', 'title', 'subtitle', 'content',
        'image', 'video_url', 'video_file',
        'link_url', 'link_text', 'link_target',
        'quote_author', 'extra_data',
        'css_class', 'background_color', 'is_full_width',
        'sort_order', 'is_active'
    ]
    
    class Media:
        css = {
            'all': ('admin/css/content_blocks.css',)
        }
        js = (
            'admin/js/jquery.min.js',
            'admin/js/jquery-ui.min.js',
            'admin/js/content_blocks.js',
        )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('sort_order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'sort_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['sort_order', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'sku', 'category', 'price', 'stock', 'is_available', 'is_featured', 'content_blocks_count']
    list_filter = ['category', 'is_available', 'is_featured', 'supplier']
    search_fields = ['title', 'sku', 'summary']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline, ContentBlockInline]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('title', 'slug', 'sku', 'category', 'supplier')
        }),
        ('قیمت و موجودی', {
            'fields': ('price', 'compare_at_price', 'supply_cost', 'stock', 'is_available', 'is_featured')
        }),
        ('توضیحات', {
            'fields': ('summary',)
        }),
        ('سئو', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_blocks_count(self, obj):
        count = obj.content_blocks.filter(is_active=True).count()
        return format_html('<span style="background: #0D3B2E; color: white; padding: 2px 8px; border-radius: 10px;">{}</span>', count)
    content_blocks_count.short_description = 'بلوک‌ها'
    
    class Media:
        css = {
            'all': ('admin/css/product_admin.css',)
        }


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'product', 'block_type', 'sort_order', 'is_active', 'created_at']
    list_filter = ['block_type', 'is_active', 'product__category']
    search_fields = ['title', 'content', 'product__title']
    list_editable = ['sort_order', 'is_active']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('نوع و محصول', {
            'fields': ('product', 'block_type')
        }),
        ('محتوا', {
            'fields': ('title', 'subtitle', 'content')
        }),
        ('Media', {
            'fields': ('image', 'video_url', 'video_file'),
            'classes': ('collapse',)
        }),
        ('لینک', {
            'fields': ('link_url', 'link_text', 'link_target'),
            'classes': ('collapse',)
        }),
        ('نقل قول', {
            'fields': ('quote_author',),
            'classes': ('collapse',)
        }),
        ('داده‌های تکمیلی', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('ظاهر', {
            'fields': ('css_class', 'background_color', 'is_full_width'),
            'classes': ('collapse',)
        }),
        ('کنترل', {
            'fields': ('sort_order', 'is_active')
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'product__category')
    
    @method_decorator(csrf_exempt)
    def reorder_blocks(self, request):
        """API برای reorder بلوک‌ها با drag & drop"""
        if request.method == 'POST':
            try:
                import json
                data = json.loads(request.body)
                block_ids = data.get('block_ids', [])
                
                for index, block_id in enumerate(block_ids):
                    ContentBlock.objects.filter(id=block_id).update(sort_order=index)
                
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reorder-blocks/', self.reorder_blocks, name='reorder_blocks'),
        ]
        return custom_urls + urls


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['title', 'contact_name', 'phone', 'city', 'is_active', 'created_at']
    search_fields = ['title', 'contact_name', 'phone', 'city']
    list_filter = ['is_active', 'city']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'author_name', 'rating', 'is_verified_buyer', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'is_verified_buyer', 'rating', 'created_at']
    search_fields = ['author_name', 'comment', 'order_number', 'product__title']
    readonly_fields = ['created_at']
    actions = ['approve_reviews', 'reject_reviews']

    @admin.action(description="تأیید و انتشار عمومی نظرات انتخاب‌شده")
    def approve_reviews(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f"{count} نظر تأیید شد")

    @admin.action(description="رد نظرات انتخاب‌شده")
    def reject_reviews(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f"{count} نظر رد شد")


@admin.register(LeadCapture)
class LeadCaptureAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'product', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'phone', 'email', 'message']
    list_editable = ['status']
    readonly_fields = ['created_at']
    actions = ['mark_as_contacted', 'mark_as_supplied', 'mark_as_obsolete']

    @admin.action(description="علامت‌گذاری به عنوان تماس گرفته‌شده")
    def mark_as_contacted(self, request, queryset):
        count = queryset.update(status='contacted')
        self.message_user(request, f"{count} سرنخ به عنوان تماس گرفته‌شده علامت‌گذاری شد")

    @admin.action(description="علامت‌گذاری به عنوان تأمین شده")
    def mark_as_supplied(self, request, queryset):
        count = queryset.update(status='supplied')
        self.message_user(request, f"{count} سرنخ به عنوان تأمین شده علامت‌گذاری شد")

    @admin.action(description="علامت‌گذاری به عنوان منسوخ")
    def mark_as_obsolete(self, request, queryset):
        count = queryset.update(status='obsolete')
        self.message_user(request, f"{count} سرنخ به عنوان منسوخ علامت‌گذاری شد")
