"""
Admin Panel ماژول family_panel
منطبق بر D-018: کنترل کامل ادمین
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import ActivityLog, SiteSettings


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """مشاهده لاگ‌های فعالیت"""
    list_display = (
        'user_display', 'action', 'entity_type',
        'entity_id', 'ip_address', 'created_at'
    )
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('user__username', 'description')
    readonly_fields = (
        'id', 'user', 'action', 'description', 'entity_type',
        'entity_id', 'ip_address', 'user_agent', 'changes', 'created_at'
    )
    date_hierarchy = 'created_at'
    
    def user_display(self, obj):
        if obj.user.first_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.username
    user_display.short_description = 'کاربر'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """مدیریت تنظیمات سایت"""
    list_display = ('site_name', 'currency', 'updated_at')
    
    fieldsets = (
        ('تنظیمات عمومی', {
            'fields': ('site_name', 'site_tagline', 'currency')
        }),
        ('تنظیمات بصری', {
            'fields': ('primary_color', 'font_family')
        }),
        ('اطلاعات تماس', {
            'fields': ('contact_phone', 'contact_address')
        }),
        ('اطلاعات بانکی', {
            'fields': ('bank_card_number', 'bank_card_holder')
        }),
        ('تنظیمات سیستم', {
            'fields': ('low_stock_threshold',)
        }),
    )
    
    def has_add_permission(self, request):
        """فقط یک SiteSettings می‌تواند وجود داشته باشد"""
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)
