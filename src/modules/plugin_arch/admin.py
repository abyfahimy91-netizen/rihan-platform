"""
M14: Admin Interface for Plugin Management
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Plugin, FeatureFlag, PluginHook, EventLog, AdminActivityLog
from .core import PluginRegistry, log_admin_activity


@admin.register(Plugin)
class PluginAdmin(admin.ModelAdmin):
    """مدیریت ماژول‌ها"""
    
    list_display = [
        'name', 'display_name', 'version', 
        'status_badge', 'is_system', 'updated_at'
    ]
    list_filter = ['status', 'is_system']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'manifest_display']
    
    actions = ['enable_plugins', 'disable_plugins']
    
    def status_badge(self, obj):
        colors = {
            'active': '#2D6A4F',
            'inactive': '#9B2C2C',
            'error': '#C9A961',
        }
        color = colors.get(obj.status, '#5C5C5C')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    
    def manifest_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.manifest_data, indent=2, ensure_ascii=False))
    manifest_display.short_description = 'Manifest Data'
    
    def enable_plugins(self, request, queryset):
        count = 0
        for plugin in queryset:
            if not plugin.is_system:
                plugin.enable()
                count += 1
        log_admin_activity(
            user=request.user,
            action='enable',
            resource_type='Plugin',
            description=f"{count} ماژول فعال شد",
            request=request,
        )
        self.message_user(request, f"✅ {count} ماژول فعال شد")
    enable_plugins.short_description = "فعال‌سازی ماژول‌های انتخاب‌شده"
    
    def disable_plugins(self, request, queryset):
        count = 0
        for plugin in queryset:
            if not plugin.is_system:
                plugin.disable()
                count += 1
        log_admin_activity(
            user=request.user,
            action='disable',
            resource_type='Plugin',
            description=f"{count} ماژول غیرفعال شد",
            request=request,
        )
        self.message_user(request, f"⏸️ {count} ماژول غیرفعال شد")
    disable_plugins.short_description = "غیرفعال‌سازی ماژول‌های انتخاب‌شده"


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    """مدیریت Feature Flags"""
    
    list_display = ['name', 'category', 'enabled_badge', 'updated_by', 'updated_at']
    list_filter = ['category', 'enabled']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['enable_flags', 'disable_flags']
    
    def enabled_badge(self, obj):
        color = '#2D6A4F' if obj.enabled else '#9B2C2C'
        icon = '✅' if obj.enabled else '❌'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, icon
        )
    enabled_badge.short_description = 'وضعیت'
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        log_admin_activity(
            user=request.user,
            action='update' if change else 'create',
            resource_type='FeatureFlag',
            resource_id=obj.id,
            description=f"Flag {obj.name} = {'فعال' if obj.enabled else 'غیرفعال'}",
            request=request,
        )
    
    def enable_flags(self, request, queryset):
        count = queryset.update(enabled=True)
        log_admin_activity(
            user=request.user,
            action='enable',
            resource_type='FeatureFlag',
            description=f"{count} flag فعال شد",
            request=request,
        )
        self.message_user(request, f"✅ {count} flag فعال شد")
    enable_flags.short_description = "فعال‌سازی flags انتخاب‌شده"
    
    def disable_flags(self, request, queryset):
        count = queryset.update(enabled=False)
        log_admin_activity(
            user=request.user,
            action='disable',
            resource_type='FeatureFlag',
            description=f"{count} flag غیرفعال شد",
            request=request,
        )
        self.message_user(request, f"⏸️ {count} flag غیرفعال شد")
    disable_flags.short_description = "غیرفعال‌سازی flags انتخاب‌شده"


@admin.register(PluginHook)
class PluginHookAdmin(admin.ModelAdmin):
    """مدیریت Hook ها"""
    
    list_display = ['plugin', 'event_type', 'handler_path', 'priority', 'enabled']
    list_filter = ['event_type', 'enabled', 'plugin']
    search_fields = ['handler_path', 'plugin__name']


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    """مشاهده Event Logs (read-only)"""
    
    list_display = ['event_type', 'level_badge', 'short_message', 'user', 'created_at']
    list_filter = ['level', 'event_type', 'created_at']
    search_fields = ['message', 'event_type']
    readonly_fields = ['event_type', 'level', 'message', 'data', 'user', 
                       'ip_address', 'created_at']
    date_hierarchy = 'created_at'
    
    def level_badge(self, obj):
        colors = {
            'debug': '#5C5C5C',
            'info': '#2D6A4F',
            'warning': '#C9A961',
            'error': '#9B2C2C',
            'critical': '#9B2C2C',
        }
        color = colors.get(obj.level, '#5C5C5C')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.level.upper()
        )
    level_badge.short_description = 'سطح'
    
    def short_message(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    short_message.short_description = 'پیام'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    """مشاهده Activity Logs (read-only)"""
    
    list_display = ['user', 'action_badge', 'resource_type', 
                    'resource_id', 'short_description', 'created_at']
    list_filter = ['action', 'resource_type', 'user', 'created_at']
    search_fields = ['user__username', 'description', 'resource_type']
    readonly_fields = ['user', 'action', 'resource_type', 'resource_id',
                       'description', 'old_value', 'new_value', 
                       'ip_address', 'user_agent', 'created_at']
    date_hierarchy = 'created_at'
    
    def action_badge(self, obj):
        colors = {
            'login': '#2D6A4F',
            'logout': '#5C5C5C',
            'create': '#2D6A4F',
            'update': '#C9A961',
            'delete': '#9B2C2C',
            'approve': '#2D6A4F',
            'reject': '#9B2C2C',
            'enable': '#2D6A4F',
            'disable': '#5C5C5C',
        }
        color = colors.get(obj.action, '#5C5C5C')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'عملیات'
    
    def short_description(self, obj):
        desc = obj.description or '-'
        return desc[:80] + '...' if len(desc) > 80 else desc
    short_description.short_description = 'توضیحات'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
