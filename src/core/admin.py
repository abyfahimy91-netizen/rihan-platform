"""
Admin Panel برای ماژول core
- مدیریت Feature Flags
- مشاهده Audit Logs
- مشاهده Event History
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count

from .models import FeatureFlag, AuditLog


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    """مدیریت پرچم‌های قابلیت"""
    list_display = (
        'code', 'name', 'category', 'is_enabled_badge',
        'is_system', 'rollout_percentage', 'updated_at'
    )
    list_filter = ('category', 'is_enabled', 'is_system')
    search_fields = ('code', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'enabled_at', 'disabled_at')
    ordering = ('category', 'code')

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('code', 'name', 'description', 'category')
        }),
        ('وضعیت', {
            'fields': ('is_enabled', 'is_system', 'rollout_percentage', 'metadata')
        }),
        ('زمان‌بندی', {
            'fields': ('enabled_at', 'disabled_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['enable_flags', 'disable_flags', 'clear_cache_action']

    def is_enabled_badge(self, obj):
        if obj.is_enabled:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ فعال</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">✗ غیرفعال</span>'
        )
    is_enabled_badge.short_description = 'وضعیت'

    def enable_flags(self, request, queryset):
        for flag in queryset:
            try:
                flag.enable(user=request.user)
            except ValueError as e:
                self.message_user(request, f"خطا: {e}", level='error')
                return
        self.message_user(request, f"{queryset.count()} پرچم فعال شد")
    enable_flags.short_description = "فعال‌سازی پرچم‌های انتخاب‌شده"

    def disable_flags(self, request, queryset):
        for flag in queryset:
            try:
                flag.disable(user=request.user)
            except ValueError as e:
                self.message_user(request, f"خطا: {e}", level='error')
                return
        self.message_user(request, f"{queryset.count()} پرچم غیرفعال شد")
    disable_flags.short_description = "غیرفعال‌سازی پرچم‌های انتخاب‌شده"

    def clear_cache_action(self, request, queryset):
        from .services import FeatureFlagService
        FeatureFlagService.clear_cache()
        self.message_user(request, "کش پرچم‌ها پاکسازی شد")
    clear_cache_action.short_description = "پاکسازی کش"

    def has_delete_permission(self, request, obj=None):
        """حذف فقط برای پرچم‌های غیرسیستمی"""
        if obj and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """نمایش لاگ‌های ممیزی (فقط خواندنی)"""
    list_display = (
        'created_at', 'user', 'action', 'entity_type', 'entity_id'
    )
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('user__username', 'entity_type', 'entity_id')
    readonly_fields = (
        'user', 'action', 'entity_type', 'entity_id',
        'changes', 'ip_address', 'created_at'
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False  # فقط سیستم می‌تواند اضافه کند

    def has_change_permission(self, request, obj=None):
        return False  # فقط مشاهده

    def has_delete_permission(self, request, obj=None):
        return False  # حذف ممنوع

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_and_continue'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)
