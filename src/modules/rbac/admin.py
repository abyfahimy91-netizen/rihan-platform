"""
Admin Panel ماژول RBAC
منطبق بر D-018 (کنترل کامل ادمین)
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Role, UserRole


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """مدیریت نقش‌ها"""
    list_display = (
        'name', 'code', 'permissions_count_badge',
        'users_count', 'is_system_badge', 'updated_at'
    )
    list_filter = ('is_system',)
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at', 'users_count')
    ordering = ['name']
    
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('id', 'name', 'code', 'description', 'is_system')
        }),
        ('مجوزها', {
            'fields': ('permissions',),
            'description': 'لیست مجوزها به‌صورت JSON (مثال: ["product.create", "order.view"])'
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def permissions_count_badge(self, obj):
        count = len(obj.permissions) if obj.permissions else 0
        color = '#28a745' if count > 0 else '#dc3545'
        return format_html(
            f'<span style="color: {color}; font-weight: bold;">{count} مجوز</span>'
        )
    permissions_count_badge.short_description = 'تعداد مجوزها'
    
    def users_count(self, obj):
        return obj.user_roles.count()
    users_count.short_description = 'تعداد کاربران'
    
    def is_system_badge(self, obj):
        if obj.is_system:
            return format_html(
                '<span style="color: #dc3545;">سیستمی (حذف ممنوع)</span>'
            )
        return format_html('<span style="color: #28a745;">قابل حذف</span>')
    is_system_badge.short_description = 'نوع'
    
    def has_delete_permission(self, request, obj=None):
        """حذف فقط برای نقش‌های غیرسیستمی"""
        if obj and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """مدیریت نقش‌های کاربران"""
    list_display = (
        'user', 'role', 'is_primary_badge',
        'granted_by', 'granted_at'
    )
    list_filter = ('role', 'is_primary', 'granted_at')
    search_fields = (
        'user__username', 'user__first_name', 'user__last_name',
        'role__name'
    )
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user', 'granted_by')
    ordering = ['-is_primary', '-granted_at']
    
    actions = ['make_primary', 'make_secondary']
    
    def is_primary_badge(self, obj):
        if obj.is_primary:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">★ اصلی</span>'
            )
        return format_html('<span style="color: #6c757d;">ثانویه</span>')
    is_primary_badge.short_description = 'وضعیت'
    
    def make_primary(self, request, queryset):
        """تبدیل به نقش اصلی"""
        for user_role in queryset:
            # غیرفعال کردن نقش اصلی قبلی
            UserRole.objects.filter(
                user=user_role.user,
                is_primary=True
            ).exclude(pk=user_role.pk).update(is_primary=False)
            # فعال کردن این
            user_role.is_primary = True
            user_role.save(update_fields=['is_primary'])
        self.message_user(
            request,
            f"{queryset.count()} نقش به‌عنوان اصلی تنظیم شد"
        )
    make_primary.short_description = "تنظیم به‌عنوان نقش اصلی"
    
    def make_secondary(self, request, queryset):
        """تبدیل به نقش ثانویه"""
        count = queryset.update(is_primary=False)
        self.message_user(request, f"{count} نقش به ثانویه تبدیل شد")
    make_secondary.short_description = "تنظیم به‌عنوان نقش ثانویه"
