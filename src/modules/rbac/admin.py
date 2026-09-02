"""
Admin Panel ماژول RBAC
منطبق بر D-018 (کنترل کامل ادمین)
"""
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import Role, UserRole



# ─────────────────────────────────────────────────────────────
# RBAC-PERM-14050611: کاتالوگ مجوزها با عنوان فارسی — چک‌لیست به‌جای JSON
# ─────────────────────────────────────────────────────────────
PERMISSION_CATALOG = [
    ('⭐ دسترسی ویژه', [
        ('*', '★ دسترسی کامل — همه‌چیز (فقط مدیر کل)'),
    ]),
    ('🛍 محصولات', [
        ('product.view', 'دیدن محصولات'),
        ('product.create', 'ایجاد محصول جدید'),
        ('product.edit', 'ویرایش محصولات'),
        ('product.delete', 'حذف محصولات'),
    ]),
    ('🧾 سفارش‌ها', [
        ('order.view', 'دیدن همه سفارش‌ها'),
        ('order.view_own', 'دیدن فقط سفارش‌های خودم (تامین‌کننده)'),
        ('order.create', 'ثبت سفارش'),
        ('order.edit', 'ویرایش سفارش‌ها'),
        ('order.delete', 'حذف سفارش‌ها'),
    ]),
    ('🚚 تامین‌کنندگان', [
        ('supplier.view', 'دیدن تامین‌کنندگان'),
        ('supplier.create', 'ایجاد تامین‌کننده'),
        ('supplier.edit', 'ویرایش تامین‌کنندگان'),
    ]),
    ('💰 مالی', [
        ('finance.view', 'دیدن اطلاعات مالی'),
        ('finance.report', 'دریافت گزارش‌های مالی'),
    ]),
    ('👥 کاربران', [
        ('user.view', 'دیدن کاربران'),
        ('user.edit', 'ویرایش کاربران'),
    ]),
    ('👤 پروفایل شخصی', [
        ('profile.view', 'دیدن پروفایل خودم'),
        ('profile.edit', 'ویرایش پروفایل خودم'),
    ]),
]
_ALL_KNOWN = {code for _g, items in PERMISSION_CATALOG for code, _t in items}


class RoleAdminForm(forms.ModelForm):
    """چک‌لیست فارسی مجوزها — کدهای ناشناختهٔ قبلی هم به‌صورت «سایر» حفظ می‌شوند"""
    perms = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='مجوزهای این نقش',
        help_text='هر مجوز را که می‌خواهید این نقش داشته باشد تیک بزنید.',
    )

    class Meta:
        model = Role
        fields = ('name', 'code', 'description', 'is_system')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = list(self.instance.permissions or []) if self.instance and self.instance.pk else []
        # کدهای موجود در دیتابیس که در کاتالوگ نیستند — نباید گم شوند
        unknown = [(c, f'سایر (دستی): {c}') for c in current if c not in _ALL_KNOWN]
        self.fields['perms'].choices = list(PERMISSION_CATALOG) + [('سایر', unknown)] if unknown else list(PERMISSION_CATALOG)
        self.initial['perms'] = current

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.permissions = list(self.cleaned_data.get('perms') or [])
        if commit:
            obj.save()
        return obj


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """مدیریت نقش‌ها"""
    form = RoleAdminForm
    list_display = (
        'name', 'code', 'permissions_count_badge',
        'users_count', 'is_system_badge', 'updated_at'
    )
    list_filter = ('is_system',)
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at', 'users_count', 'permissions_json_view')
    ordering = ['name']

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('id', 'name', 'code', 'description', 'is_system')
        }),
        ('مجوزها (چک‌لیست)', {
            'fields': ('perms',),
        }),
        ('JSON خام (فقط نمایش)', {
            'fields': ('permissions_json_view',),
            'classes': ('collapse',),
            'description': 'محتوای ذخیره‌شدهٔ واقعی — از طریق چک‌لیست بالا ویرایش می‌شود',
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='JSON ذخیره‌شده')
    def permissions_json_view(self, obj):
        import json as _json
        return _json.dumps(obj.permissions or [], ensure_ascii=False, indent=1)

    def get_fieldsets(self, request, obj=None):
        # در صفحهٔ «افزودن»، JSON خالی است — نمایشش لازم نیست
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            fieldsets = [f for f in fieldsets if 'permissions_json_view' not in f[1].get('fields', ())]
        return fieldsets
    
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
