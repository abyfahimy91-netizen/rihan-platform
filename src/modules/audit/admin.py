from django.contrib import admin

from src.core.fa import jalali_datetime_str

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'entity_type', 'entity_id', 'user_id', 'created_at_fa']
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['entity_type', 'entity_id', 'user_id']
    readonly_fields = ['id', 'user_id', 'action', 'entity_type', 'entity_id', 'old_values', 'new_values', 'ip_address', 'device_user_agent', 'created_at']
    ordering = ['-created_at']

    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ'
    created_at_fa.admin_order_field = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
