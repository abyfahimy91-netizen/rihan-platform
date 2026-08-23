"""ادمین تنظیمات سایت — فرم تک‌صفحه‌ای مرتب با بخش‌بندی واضح."""
from django.contrib import admin

from .models import SiteSettings


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
        }),
        ('🌐 شبکه‌های اجتماعی', {
            'fields': ('instagram_url', 'telegram_url', 'whatsapp_number'),
            'classes': ('collapse',),
        }),
        ('🦶 فوتر سایت', {
            'fields': ('footer_tagline', 'footer_description', 'footer_copyright'),
            'classes': ('collapse',),
        }),
    )

    list_display = ('site_name', 'updated_at')

    def has_add_permission(self, request):
        # فقط وقتی هیچ رکوردی نیست اجازه ساخت بده
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        from django.contrib import messages
        messages.success(request, '✅ تنظیمات ذخیره شد و بلافاصله روی سایت اعمال می‌شود.')
        return super().response_change(request, obj)
