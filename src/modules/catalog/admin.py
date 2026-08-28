"""
Catalog Admin — پنل کامل مدیریت فروشگاه (محصولات، دسته‌ها، تامین‌کنندگان، موجودی)
منطبق بر US-018 (مدیریت محصولات)، US-023 (دسته‌بندی‌ها) و D-018 (کنترل کامل ادمین)
"""
import jdatetime
from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Category, Supplier, Product, ProductImage,
    Inventory, InventoryTransaction, ContentBlock, ProductVariant, ProductFaq,
)

from src.core.fa import money as fa_money, fa_digits as fa_dg


class ProductForm(forms.ModelForm):
    """فرم محصول — فیلدهای JSON خالی را به مقدار پیش‌فرض صحیح تبدیل می‌کند"""

    class Meta:
        model = Product
        fields = '__all__'

    def clean_metadata(self):
        return self.cleaned_data.get('metadata') or {}

    def clean_images(self):
        return self.cleaned_data.get('images') or []


class ContentBlockForm(forms.ModelForm):
    class Meta:
        model = ContentBlock
        fields = '__all__'

    def clean_content(self):
        return self.cleaned_data.get('content') or {}


def jalali(dt, fmt='%Y/%m/%d'):
    """تبدیل تاریخ به شمسی برای نمایش در لیست‌ها"""
    if not dt:
        return '-'
    return fa_dg(jdatetime.datetime.fromgregorian(datetime=dt).strftime(fmt))


def toman(value):
    try:
        num = fa_money(value)
    except (TypeError, ValueError):
        num = '۰'
    return format_html('<strong>{}</strong> <span style="color:#888;">تومان</span>', num)


# ═══════════════════════════════════════════════════════════════
# دسته‌بندی‌ها (US-023)
# ═══════════════════════════════════════════════════════════════

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'products_count', 'is_active_badge')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id', 'created_at', 'updated_at')

    def products_count(self, obj):
        count = obj.products.count()
        url = reverse('admin:catalog_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} محصول</a>', url, count)
    products_count.short_description = 'محصولات'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#28a745;font-weight:bold;">✓ فعال</span>')
        return format_html('<span style="color:#dc3545;font-weight:bold;">✗ غیرفعال</span>')
    is_active_badge.short_description = 'وضعیت'


# ═══════════════════════════════════════════════════════════════
# تامین‌کنندگان
# ═══════════════════════════════════════════════════════════════

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'phone', 'linked_user',
                    'products_count', 'is_active_badge')
    list_filter = ('city', 'is_active')
    search_fields = ('title', 'city', 'phone', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at')

    fieldsets = (
        ('اطلاعات تامین‌کننده', {
            'fields': ('title', 'city', 'phone', 'is_active')
        }),
        ('دسترسی به پنل تامین‌کننده (/supplier/)', {
            'description': 'برای اینکه این تامین‌کننده بتواند با پنل خود وارد شود: '
                           '۱) یک کاربر بسازید ۲) در «نقش‌های کاربر» نقش supplier را به او بدهید '
                           '۳) همان کاربر را اینجا انتخاب کنید.',
            'fields': ('user',),
        }),
    )

    def linked_user(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">👤 {}</a>', url, obj.user.username)
        return format_html('<span style="color:#dc3545;">بدون دسترسی پنل</span>')
    linked_user.short_description = 'کاربر پنل'

    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'محصولات'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#28a745;font-weight:bold;">✓ فعال</span>')
        return format_html('<span style="color:#dc3545;font-weight:bold;">✗ غیرفعال</span>')
    is_active_badge.short_description = 'وضعیت'


# ═══════════════════════════════════════════════════════════════
# این‌لاین‌های صفحه محصول
# ═══════════════════════════════════════════════════════════════

class ProductImageInline(admin.TabularInline):
    """آپلود عکس‌های محصول — خودکار در سایت نمایش داده می‌شود"""
    model = ProductImage
    extra = 2
    fields = ('preview', 'image', 'caption', 'sort_order')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:60px;border-radius:6px;border:1px solid #ddd;"/>',
                obj.image.url
            )
        return '-'
    preview.short_description = 'پیش‌نمایش'


class InventoryFormSet(forms.models.BaseInlineFormSet):
    """فرم‌ست موجودی — تداخل با سیگنال خودکار مدل را حل می‌کند"""

    def save_new(self, form, commit=True):
        # سیگنال پس از ساخت محصول خودش ردیف موجودی می‌سازد؛
        # به‌جای رکورد تکراری، همان ردیف با مقادیر فرم به‌روزرسانی می‌شود.
        obj = super().save_new(form, commit=False)
        existing = Inventory.objects.filter(product=obj.product).first()
        if existing:
            for f in ('quantity', 'unit', 'low_stock_threshold'):
                val = form.cleaned_data.get(f)
                if val not in (None, ''):
                    setattr(existing, f, val)
            obj = existing
        if commit:
            obj.save()
        return obj


class InventoryInline(admin.StackedInline):
    """مدیریت موجودی انبار همراه خود محصول"""
    model = Inventory
    formset = InventoryFormSet
    max_num = 1
    can_delete = False
    fields = ('quantity', 'unit', 'low_stock_threshold', 'reserved_quantity')
    readonly_fields = ('reserved_quantity',)
    verbose_name = 'موجودی انبار'
    verbose_name_plural = '📦 موجودی انبار (محصول واریانت‌دار = خودکار مجموع بسته‌ها)'

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'reserved_quantity':
            kwargs['help_text'] = 'رزرو شده برای سفارش‌های در انتظار (سیستمی — دست نزنید)'
        if db_field.name == 'quantity':
            kwargs['help_text'] = 'موجودی فیزیکی فعلی — با هر فروش خودکار کم می‌شود'
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class ContentBlockInline(admin.TabularInline):
    """بلوک‌های محتوای صفحه محصول (متن، گالری، نشان اعتماد و...)"""
    model = ContentBlock
    fk_name = 'product'
    extra = 0
    fields = ('block_type', 'sort_order', 'is_active')
    verbose_name = 'بلوک محتوا'
    verbose_name_plural = '🧩 بلوک‌های صفحه محصول (ترتیب نمایش)'


# ═══════════════════════════════════════════════════════════════
# محصولات (US-018) — قلب پنل
# ═══════════════════════════════════════════════════════════════

class ProductFaqInline(admin.TabularInline):
    """سوالات متداول اختصاصی محصول — بخش ۶ صفحه فروش (D-104)"""
    model = ProductFaq
    extra = 1
    fields = ('question', 'answer', 'sort_order', 'is_active')
    verbose_name = "سوال متداول"
    verbose_name_plural = "❓ سوالات متداول این محصول (رفع ابهام قبل از خرید)"


class ProductVariantInline(admin.TabularInline):
    """واریانت‌های محصول — D-094"""
    model = ProductVariant
    extra = 2
    fields = ["title", "color_name", "color_hex", "price", "cost_price", "is_default", "unit",
              "stock_quantity", "low_stock_threshold", "is_active", "sort_order"]
    verbose_name = "بسته / سایز (گزینه قابل خرید)"
    verbose_name_plural = "📦 بسته‌ها / سایزها / رنگ‌ها (هر ردیف یک گزینه خرید)"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = (
        'thumb', 'name', 'category', 'supplier',
        'price_display', 'stock_display', 'status_badge', 'edit_button',
        'featured_star', 'created_jalali',
    )
    list_filter = ('status', 'category', 'is_featured', 'created_at')
    search_fields = ('name', 'slug', 'short_description')
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'
    list_per_page = 25
    actions = ('activate_products', 'deactivate_products',
               'feature_products', 'unfeature_products', 'soft_delete_products')

    @admin.display(description="عملیات")
    def edit_button(self, obj):
        from django.urls import reverse as _rev
        from django.utils.html import format_html
        u = _rev("admin:catalog_product_change", args=[obj.pk])
        q = chr(39)
        h = "<a class=" + q + "rihan-edit-btn" + q + " href=" + q + str(u) + q + ">ویرایش</a>"
        return format_html(h)

    inlines = [ProductVariantInline, ProductImageInline, InventoryInline, ContentBlockInline, ProductFaqInline]

    fieldsets = (
        ('📝 اطلاعات اصلی', {
            'fields': ('name', 'slug', 'category', 'supplier', 'unit', 'status', 'is_featured'),
        }),
        ('💰 قیمت‌گذاری', {
            'description': 'قیمت‌ها از بخش «📦 بسته‌ها/سایزها» پایین همین صفحه مدیریت می‌شود: '
                           'قیمت فروش هر گزینه + قیمت خرید آن. فرمول قدیمی (قیمت پایه/ارسال/حاشیه) حذف شد (D-113).',
            'fields': ('compare_at_price',),
        }),
        ('🛒 صفحه فروش اقناعی (D-104)', {
            'description': 'تیتر نتیجه‌محور بالای نام محصول نمایش داده می‌شود. سه تعهد زیر دکمه خرید ثابت است: ۷ روز ضمانت بازگشت، ارسال بیمه‌شده، بسته‌بندی محرمانه.',
            'fields': ('result_headline',),
        }),
        ('🎯 فیلتر شفاف مخاطب', {
            'classes': ('collapse',),
            'description': 'هر خط یک مورد. ستون سبز: این کالا برای چه کسی است. ستون قرمز: صادقانه چه کسی نخرد.',
            'fields': ('fit_for', 'not_fit_for'),
        }),
        ('🔍 داستان گزینش و مقاله سئو', {
            'classes': ('collapse',),
            'description': 'قواعد متن: خط خالی=پاراگراف، #=تیتر، -=فهرست، ۱.=شماره‌ای، >=نقل‌قول',
            'fields': ('curation_story', 'deep_dive'),
        }),
        ('📄 توضیحات', {
            'fields': ('short_description', 'long_description', 'origin_story'),
        }),
        ('🔍 سئو (بهینه‌سازی موتور جستجو)', {
            'classes': ('collapse',),
            'fields': ('seo_title', 'seo_description', 'seo_keywords'),
        }),
        ('⚙️ پیشرفته', {
            'classes': ('collapse',),
            'fields': ('metadata', 'id', 'created_at', 'updated_at', 'deleted_at'),
        }),
    )

    readonly_fields = ('share_count', 'id', 'created_at', 'updated_at', 'deleted_at')

    # ─── ستون‌های لیست ───

    def thumb(self, obj):
        first = obj.gallery.first()
        if first and first.image:
            return format_html(
                '<img src="{}" style="width:44px;height:44px;object-fit:cover;border-radius:8px;"/>',
                first.image.url
            )
        return format_html('<div style="width:44px;height:44px;background:#f0f0f0;'
                           'border-radius:8px;text-align:center;line-height:44px;">🌿</div>')
    thumb.short_description = ''

    def price_display(self, obj):
        return toman(obj.display_price)
    price_display.short_description = 'قیمت نمایشی'
    price_display.admin_order_field = 'final_price'

    def stock_display(self, obj):
        inv = getattr(obj, 'inventory', None)
        if not inv:
            return format_html('<span style="color:#dc3545;">بدون موجودی!</span>')
        avail = inv.available_quantity
        unit = inv.unit or obj.unit or ''
        num = fa_money(avail)
        if avail <= 0:
            return format_html('<span style="background:#dc3545;color:#fff;padding:3px 10px;'
                               'border-radius:10px;font-size:12px;">ناموجود</span>')
        if inv.is_low_stock:
            return format_html('<span style="background:#ffc107;color:#333;padding:3px 10px;'
                               'border-radius:10px;font-size:12px;">⚠️ کم: {} {}</span>',
                               num, unit)
        return format_html('{} {}', num, unit)
    stock_display.short_description = 'موجودی قابل فروش'

    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d', 'active': '#28a745',
            'inactive': '#dc3545', 'out_of_stock': '#ffc107',
        }
        labels = {'draft': 'پیش‌نویس', 'active': 'فعال',
                  'inactive': 'غیرفعال', 'out_of_stock': 'ناموجود'}
        return format_html(
            '<span style="background:{};color:#fff;padding:4px 12px;border-radius:12px;'
            'font-size:12px;font-weight:bold;">{}</span>',
            colors.get(obj.status, '#888'), labels.get(obj.status, obj.status)
        )
    status_badge.short_description = 'وضعیت انتشار'
    status_badge.admin_order_field = 'status'

    def featured_star(self, obj):
        if obj.is_featured:
            return format_html('<span style="color:#f39c12;font-size:16px;" title="در صفحه اصلی">★</span>')
        return ''
    featured_star.short_description = 'صفحه اصلی'

    def created_jalali(self, obj):
        return jalali(obj.created_at)
    created_jalali.short_description = 'تاریخ ثبت'

    def view_on_site(self, obj):
        return reverse('catalog:product_detail', kwargs={'slug': obj.slug})

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'supplier', 'inventory'
        ).prefetch_related('gallery')

    # ─── عملیات گروهی ───

    @admin.action(description='✅ فعال‌سازی (انتشار در سایت)')
    def activate_products(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} محصول منتشر شد.')

    @admin.action(description='⏸ غیرفعال‌سازی (مخفی از سایت)')
    def deactivate_products(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} محصول مخفی شد.')

    @admin.action(description='★ نمایش در صفحه اصلی')
    def feature_products(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} محصول به صفحه اصلی رفت.')

    @admin.action(description='☆ حذف از صفحه اصلی')
    def unfeature_products(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} محصول از صفحه اصلی حذف شد.')

    @admin.action(description='🗑 حذف نرم (مخفی + حفظ داده — توصیه‌شده)')
    def soft_delete_products(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(deleted_at=timezone.now(), status='inactive')
        self.message_user(request, f'{updated} محصول حذف نرم شد (داده‌ها حفظ شد).')


# ═══════════════════════════════════════════════════════════════
# عکس‌های محصول (مدیریت مستقل در صورت نیاز)
# ═══════════════════════════════════════════════════════════════

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'product_link', 'caption', 'sort_order', 'uploaded_jalali')
    list_filter = ('product',)
    search_fields = ('product__name', 'caption')
    readonly_fields = ('id', 'created_at')

    def thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:50px;border-radius:6px;"/>', obj.image.url)
        return '-'
    thumb.short_description = 'عکس'

    def product_link(self, obj):
        url = reverse('admin:catalog_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = 'محصول'

    def uploaded_jalali(self, obj):
        return jalali(obj.created_at)
    uploaded_jalali.short_description = 'تاریخ'


# ═══════════════════════════════════════════════════════════════
# موجودی انبار — نمای کلی + هشدار کمبود
# ═══════════════════════════════════════════════════════════════

class LowStockFilter(admin.SimpleListFilter):
    title = 'وضعیت موجودی'
    parameter_name = 'stock_state'

    def lookups(self, request, model_admin):
        return (
            ('low', '⚠️ کم‌موجود'),
            ('out', '❌ ناموجود'),
            ('ok', '✅ سالم'),
        )

    def queryset(self, request, queryset):
        ids_low, ids_out, ids_ok = [], [], []
        for inv in queryset:
            avail = inv.available_quantity
            if avail <= 0:
                ids_out.append(inv.id)
            elif inv.is_low_stock:
                ids_low.append(inv.id)
            else:
                ids_ok.append(inv.id)
        mapping = {'low': ids_low, 'out': ids_out, 'ok': ids_ok}
        return queryset.filter(id__in=mapping.get(self.value(), []))


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product_link', 'quantity', 'reserved', 'available_display',
                    'unit', 'threshold', 'state_badge', 'updated_jalali')
    list_filter = (LowStockFilter,)
    search_fields = ('product__name',)
    readonly_fields = ('id', 'reserved_quantity', 'created_at', 'updated_at')

    fieldsets = (
        ('📦 موجودی', {
            'fields': ('product', 'quantity', 'unit', 'low_stock_threshold'),
            'description': '«رزرو شده» توسط سیستم برای سفارش‌های در انتظار پرداخت رزرو می‌شود؛ '
                           'موجودی قابل فروش = موجودی منهای رزرو شده.',
        }),
        ('سیستمی', {'fields': ('reserved_quantity', 'id', 'created_at', 'updated_at'),
                    'classes': ('collapse',)}),
    )

    def product_link(self, obj):
        url = reverse('admin:catalog_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = 'محصول'

    def reserved(self, obj):
        return fa_money(obj.reserved_quantity)
    reserved.short_description = 'رزرو شده'

    def available_display(self, obj):
        return fa_money(obj.available_quantity)
    available_display.short_description = 'قابل فروش'
    available_display.admin_order_field = 'quantity'

    def threshold(self, obj):
        return fa_money(obj.low_stock_threshold)
    threshold.short_description = 'حد هشدار'

    def state_badge(self, obj):
        avail = obj.available_quantity
        if avail <= 0:
            return format_html('<span style="background:#dc3545;color:#fff;padding:3px 10px;'
                               'border-radius:10px;font-size:12px;">❌ ناموجود</span>')
        if obj.is_low_stock:
            return format_html('<span style="background:#ffc107;color:#333;padding:3px 10px;'
                               'border-radius:10px;font-size:12px;">⚠️ کم‌موجود</span>')
        return format_html('<span style="background:#28a745;color:#fff;padding:3px 10px;'
                           'border-radius:10px;font-size:12px;">✅ سالم</span>')
    state_badge.short_description = 'وضعیت'

    def updated_jalali(self, obj):
        return jalali(obj.updated_at, '%Y/%m/%d %H:%M')
    updated_jalali.short_description = 'آخرین تغییر'


# ═══════════════════════════════════════════════════════════════
# تراکنش‌های موجودی — فقط خواندنی (گزارش دگرگشت انبار)
# ═══════════════════════════════════════════════════════════════

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('inventory', 'change_type', 'quantity_change',
                    'stock_before', 'stock_after', 'reason', 'jalali_date')
    list_filter = ('change_type', 'created_at')
    search_fields = ('inventory__product__name', 'reason')
    date_hierarchy = 'created_at'
    readonly_fields = [f.name for f in InventoryTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def jalali_date(self, obj):
        return jalali(obj.created_at, '%Y/%m/%d %H:%M')
    jalali_date.short_description = 'تاریخ'


# ═══════════════════════════════════════════════════════════════
# بلوک‌های محتوا — مدیریت مستقل (پیوند محصول ↔ بلوک)
# ═══════════════════════════════════════════════════════════════

@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    form = ContentBlockForm
    list_display = ('block_label', 'product_link', 'sort_order', 'is_active_badge')
    list_filter = ('block_type', 'is_active')
    search_fields = ('product__name',)
    readonly_fields = ('id', 'created_at', 'updated_at')

    fieldsets = (
        ('بلوک', {
            'fields': ('product', 'block_type', 'sort_order', 'is_active'),
        }),
        ('محتوای JSON', {
            'description': 'محتوای ساختاریافته بلوک — مثلا برای تصویر: '
                           '{"image_url": "/media/...", "alt_text": "توضیح"}',
            'fields': ('content',),
        }),
    )

    BLOCK_LABELS = {
        'text': '📝 متن', 'heading': '🔖 تیتر', 'image': '🖼 تصویر',
        'gallery': '🎞 گالری', 'video': '🎬 ویدیو', 'link': '🔗 لینک',
        'quote': '❝ نقل‌قول', 'table': '📊 جدول', 'spacer': '⬜ فاصله',
        'cta': '📣 دعوت به اقدام', 'trust_badges': '🛡 نشان اعتماد',
        'related_products': '🧺 محصولات مرتبط',
    }

    def block_label(self, obj):
        return self.BLOCK_LABELS.get(obj.block_type, obj.block_type)
    block_label.short_description = 'نوع بلوک'

    def product_link(self, obj):
        if not obj.product:
            return '-'
        url = reverse('admin:catalog_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = 'محصول'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#28a745;">✓</span>')
        return format_html('<span style="color:#dc3545;">✗</span>')
    is_active_badge.short_description = 'فعال'
