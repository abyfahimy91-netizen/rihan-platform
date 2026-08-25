"""ادمین تنظیمات سایت و سوالات متداول — فرم تک‌صفحه‌ای مرتب با بخش‌بندی واضح."""
from django.contrib import admin

from .models import FaqItem, SiteSettings

from src.core.fa import jalali_datetime_str


MARKUP_HELP = (
    'قواعد نوشتن: خط خالی = پاراگراف جدید | خطی که با «#» شروع شود = تیتر بخش | '
    'خطوطی که با «-» شروع شوند = فهرست نقطه‌ای | '
    'خطوطی که با «۱.» «۲.» شروع شوند = فهرست شماره‌ای | '
    'خطی که با «>» شروع شود = نقل‌قول برجسته.'
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('🏷 برند', {
            'fields': ('site_name',),
        }),
        ('🏠 صفحه اصلی (بخش اول سایت)', {
            'fields': (
                'hero_badge', 'hero_title', 'hero_subtitle',
                'hero_quote', 'featured_title',
            ),
            'description': 'این متن‌ها دقیقاً همان چیزی است که بازدیدکننده در بالای صفحه اصلی می‌بیند.',
        }),
        ('📢 نوار اطلاعیه', {
            'fields': ('announcement_active', 'announcement_text'),
            'description': 'نوار رنگی بالای همه صفحات سایت برای خبرهای مهم (مثل ارسال رایگان).',
        }),
        ('📞 اطلاعات تماس', {
            'fields': ('contact_phone', 'contact_email', 'contact_address', 'contact_hours'),
            'description': 'این اطلاعات در صفحه «تماس با ما»، صفحه «درباره ما» و فوتر استفاده می‌شود.',
        }),
        ('🌐 شبکه‌های اجتماعی', {
            'fields': ('instagram_url', 'telegram_url', 'whatsapp_number'),
            'classes': ('collapse',),
        }),
        ('📄 محتوای صفحه درباره ما', {
            'fields': ('about_title', 'about_body'),
            'description': MARKUP_HELP,
            'classes': ('collapse',),
        }),
        ('↩️ محتوای صفحه سیاست مرجوعی', {
            'fields': ('return_policy_title', 'return_policy_body'),
            'description': MARKUP_HELP,
            'classes': ('collapse',),
        }),
        ('❓ صفحه سوالات متداول', {
            'fields': ('faq_intro',),
            'description': 'خود سوال‌ها و جواب‌ها را از بخش جداگانه «سوالات متداول» در همین پنل مدیریت کنید.',
            'classes': ('collapse',),
        }),
        ('🛡 تعهدهای زیر دکمه خرید', {
            'fields': ('buy_commitments',),
            'description': 'هر خط یک تعهد — در صفحه محصول، زیر دکمه خرید نمایش داده می‌شود. (مثلاً: ۷ روز ضمانت بازگشت وجه)',
            'classes': ('collapse',),
        }),
        ('🛡 نشان‌های اعتماد صفحه محصول', {
            'fields': ('trust_badges',),
            'description': 'هر خط یک نشان با قالب «عنوان | زیرنویس» — بالای توضیحات صفحه محصول. شماره تلفن و پیام‌رسان‌های ردیف «ارتباط مستقیم» از فیلدهای تماس همین صفحه (شماره تلفن/تلگرام/واتساپ/اینستاگرام) گرفته می‌شود.',
            'classes': ('collapse',),
        }),
        ('📨 پیامک سفارشات (فعال/غیرفعال)', {
            'fields': ('sms_notify_suppliers', 'sms_notify_customers'),
            'description': 'D-106: سیستم پیامک موازی است — تا وقتی خط ارسال آماده نیست، هر دو را خاموش بگذارید؛ هیچ پیامکی تلاش نمی‌شود و فقط در «لاگ اطلاع‌رسانی» سفارشات ثبت می‌شود. بعد از فعال‌شدن خط کاوه‌نگار، همین‌جا روشن کنید.',
            'classes': ('collapse',),
        }),
        ('✉️ قالب پیامک‌ها (پیشرفته)', {
            'fields': ('brand_name_latin', 'sms_text_customer_shipped', 'sms_text_supplier_assign'),
            'description': 'برند لاتین در همه پیامک‌ها استفاده می‌شود. قالب‌ها خالی = پیش‌فرض سیستم. متغیرهای مجاز: {order_number} {carrier} {tracking_code} {link} {items} {brand}',
            'classes': ('collapse',),
        }),
        ('🔗 اشتراک‌گذاری محصولات', {
            'fields': ('share_message_text', 'share_hashtags'),
            'description': 'متن اول پیامی که مشتری با تلگرام/واتساپ/استوری می‌فرستد. بعد از آن نام محصول، لینک کوتاه تمیز (rihan360.ir/p/کد) و هشتگ‌ها خودکار اضافه می‌شود.',
            'classes': ('collapse',),
        }),
        ('🦶 فوتر سایت', {
            'fields': ('footer_tagline', 'footer_description', 'footer_copyright'),
            'classes': ('collapse',),
        }),
    )

    list_display = ('site_name', 'updated_at_fa')

    def updated_at_fa(self, obj):
        return jalali_datetime_str(obj.updated_at)
    updated_at_fa.short_description = 'آخرین بروزرسانی'

    def has_add_permission(self, request):
        # فقط وقتی هیچ رکوردی نیست اجازه ساخت بده
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        from django.contrib import messages
        messages.success(request, '✅ تنظیمات ذخیره شد و بلافاصله روی سایت اعمال می‌شود.')
        return super().response_change(request, obj)


@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    """مدیریت سوالات متداول — هر سوال یک کارت جمع‌شونده در صفحه /faq/"""
    list_display = ('question', 'sort_order', 'is_active', 'created_at_fa')
    list_editable = ('sort_order', 'is_active')
    list_display_links = ('question',)
    search_fields = ('question', 'answer')
    fields = ('question', 'answer', 'sort_order', 'is_active')

    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ ایجاد'

    def response_add(self, request, obj):
        from django.contrib import messages
        messages.success(request, f'✅ سوال «{obj.question}» ثبت شد و در صفحه سوالات متداول سایت نمایش داده می‌شود.')
        return super().response_add(request, obj)
