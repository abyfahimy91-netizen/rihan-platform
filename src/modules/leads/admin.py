"""
Admin panel for Leads Module (M9)

Features:
- Jalali (Shamsi) date display
- Bulk actions: notify, cancel
- Filters by status, product
- Search by phone, name, product
"""
import jdatetime
from django.contrib import admin
from django.utils.html import format_html

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """Admin panel for product leads"""
    
    list_display = (
        'phone_display',
        'name_display',
        'product_display',
        'status_display',
        'created_jalali',
        'action_buttons',
    )
    
    list_filter = (
        'status',
        'created_at',
        'product',
    )
    
    search_fields = (
        'phone',
        'name',
        'product__name',
    )
    
    readonly_fields = (
        'id',
        'phone',
        'name',
        'product',
        'created_jalali_full',
        'notified_jalali_full',
        'converted_jalali_full',
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('اطلاعات سرنخ', {
            'fields': (
                'id',
                'phone',
                'name',
                'product',
            )
        }),
        ('وضعیت', {
            'fields': (
                'status',
                'notification_method',
                'order',
            )
        }),
        ('یادداشت', {
            'fields': (
                'admin_notes',
            )
        }),
        ('تاریخ‌ها (شمسی)', {
            'fields': (
                'created_jalali_full',
                'notified_jalali_full',
                'converted_jalali_full',
            )
        }),
        ('تاریخ‌ها (میلادی)', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['notify_leads', 'cancel_leads', 'mark_as_converted']
    
    def phone_display(self, obj):
        """Display phone with link"""
        return format_html('<code>{}</code>', obj.phone)
    phone_display.short_description = 'موبایل'
    
    def name_display(self, obj):
        """Display name or 'بدون نام'"""
        return obj.name or '-'
    name_display.short_description = 'نام'
    
    def product_display(self, obj):
        """Display product name"""
        if obj.product:
            return obj.product.name
        return 'سرنخ عمومی'
    product_display.short_description = 'محصول'
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'PENDING': 'orange',
            'NOTIFIED': 'blue',
            'CONVERTED': 'green',
            'CANCELLED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'وضعیت'
    
    def created_jalali(self, obj):
        """Display creation date in Jalali format"""
        if obj.created_at:
            jalali = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jalali.strftime('%Y/%m/%d %H:%M')
        return '-'
    created_jalali.short_description = 'تاریخ ثبت'
    
    def created_jalali_full(self, obj):
        """Display full creation date in Jalali"""
        if obj.created_at:
            jalali = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jalali.strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'
    created_jalali_full.short_description = 'تاریخ ثبت (شمسی)'
    
    def notified_jalali_full(self, obj):
        """Display notification date in Jalali"""
        if obj.notified_at:
            jalali = jdatetime.datetime.fromgregorian(datetime=obj.notified_at)
            return jalali.strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'
    notified_jalali_full.short_description = 'تاریخ اطلاع‌رسانی (شمسی)'
    
    def converted_jalali_full(self, obj):
        """Display conversion date in Jalali"""
        if obj.converted_at:
            jalali = jdatetime.datetime.fromgregorian(datetime=obj.converted_at)
            return jalali.strftime('%Y/%m/%d ساعت %H:%M:%S')
        return '-'
    converted_jalali_full.short_description = 'تاریخ تبدیل به خرید (شمسی)'
    
    def action_buttons(self, obj):
        """Display action buttons"""
        if obj.status == 'PENDING':
            return format_html(
                '<span style="color: orange;">⏳ در انتظار</span>'
            )
        elif obj.status == 'NOTIFIED':
            return format_html(
                '<span style="color: blue;">📨 اطلاع‌رسانی شده</span>'
            )
        elif obj.status == 'CONVERTED':
            return format_html(
                '<span style="color: green;">✅ تبدیل شده</span>'
            )
        return format_html(
            '<span style="color: red;">❌ لغو شده</span>'
        )
    action_buttons.short_description = 'وضعیت فعلی'
    
    def notify_leads(self, request, queryset):
        """Bulk notify selected leads"""
        count = 0
        for lead in queryset.filter(status='PENDING'):
            lead.notify(method='MANUAL')
            count += 1
        self.message_user(request, f'{count} سرنخ به‌عنوان اطلاع‌رسانی شده علامت‌گذاری شد')
    notify_leads.short_description = 'علامت‌گذاری به‌عنوان اطلاع‌رسانی شده'
    
    def cancel_leads(self, request, queryset):
        """Bulk cancel selected leads"""
        count = queryset.filter(status='PENDING').update(status='CANCELLED')
        self.message_user(request, f'{count} سرنخ لغو شد')
    cancel_leads.short_description = 'لغو سرنخ‌های انتخاب‌شده'
    
    def mark_as_converted(self, request, queryset):
        """Bulk mark as converted (for testing)"""
        from django.utils import timezone
        count = queryset.update(
            status='CONVERTED',
            converted_at=timezone.now()
        )
        self.message_user(request, f'{count} سرنخ به‌عنوان تبدیل‌شده علامت‌گذاری شد')
    mark_as_converted.short_description = 'علامت‌گذاری به‌عنوان تبدیل‌شده'


# ══════════════════════════════════════════════════════════════════
# D-125: پنل مدیریت سرنخ‌های بازدید (VisitorLead)
# ══════════════════════════════════════════════════════════════════
from .models import VisitorLead


@admin.register(VisitorLead)
class VisitorLeadAdmin(admin.ModelAdmin):
    """مدیریت سرنخ‌های بازدید: فیلتر بر اساس مرحلهٔ قیف/وضعیت/دستگاه + جستجو."""

    list_display = (
        'ip',
        'location_display',
        'device',
        'channel_first',
        'stage_display',
        'page_views',
        'sessions_count',
        'last_seen_jalali',
        'status_display',
    )
    list_filter = ('stage', 'status', 'device', 'is_vpn', 'country')
    search_fields = ('ip', 'city', 'isp', 'order_refs', 'admin_notes')
    ordering = ('-last_seen',)
    list_per_page = 50
    actions = ['mark_contacted', 'mark_lost', 'mark_buyer', 'mark_junk']

    readonly_fields = (
        'ip', 'country', 'city', 'isp', 'is_vpn', 'device', 'channel_first',
        'channels', 'first_seen', 'last_seen', 'sessions_count', 'page_views',
        'stage', 'stage_rank', 'is_hot', 'actions', 'order_refs',
        'orders_matched', 'sessions', 'created_at', 'updated_at',
    )

    fieldsets = (
        ('اطلاعات بازدیدکننده', {'fields': ('ip', 'country', 'city', 'isp', 'is_vpn',
                                            'device', 'channel_first', 'channels')}),
        ('قیف خرید', {'fields': ('stage', 'is_hot', 'page_views', 'sessions_count',
                                 'first_seen', 'last_seen', 'actions', 'order_refs',
                                 'orders_matched')}),
        ('وضعیت پیگیری (قابل ویرایش)', {'fields': ('status', 'admin_notes')}),
        ('جزئیات فنی', {'fields': ('sessions', 'stage_rank', 'created_at', 'updated_at'),
                        'classes': ('collapse',)}),
    )

    def has_add_permission(self, request):
        return False

    def location_display(self, obj):
        return f"{obj.city or '؟'} / {obj.isp or '؟'}"
    location_display.short_description = 'موقعیت'

    def stage_display(self, obj):
        colors = {'HOME': 'gray', 'PRODUCT': '#1F6F9C', 'CART': 'orange',
                  'CHECKOUT': '#d95f02', 'PAYMENT': 'red', 'CONVERTED': 'green'}
        mark = '🔥 ' if obj.hot_active else ''
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            colors.get(obj.stage, 'gray'), mark, obj.get_stage_display())
    stage_display.short_description = 'مرحله'

    def status_display(self, obj):
        colors = {'NEW': 'red', 'CONTACTED': 'orange', 'NOANSWER': 'gray',
                  'LOST': 'gray', 'BUYER': 'green', 'JUNK': 'gray'}
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>',
                           colors.get(obj.status, 'gray'), obj.get_status_display())
    status_display.short_description = 'وضعیت CRM'

    def last_seen_jalali(self, obj):
        if obj.last_seen:
            j = jdatetime.datetime.fromgregorian(datetime=obj.last_seen)
            return j.strftime('%Y/%m/%d %H:%M')
        return '-'
    last_seen_jalali.short_description = 'آخرین بازدید'

    def mark_contacted(self, request, queryset):
        n = queryset.update(status=VisitorLead.LeadStatus.CONTACTED)
        self.message_user(request, f'{n} سرنخ «تماس گرفته شد» شد.')
    mark_contacted.short_description = 'علامت‌گذاری: تماس گرفته شد'

    def mark_lost(self, request, queryset):
        n = queryset.update(status=VisitorLead.LeadStatus.LOST)
        self.message_user(request, f'{n} سرنخ «از دست رفته» شد.')
    mark_lost.short_description = 'علامت‌گذاری: از دست رفته'

    def mark_buyer(self, request, queryset):
        n = queryset.update(status=VisitorLead.LeadStatus.BUYER)
        self.message_user(request, f'{n} سرنخ «خریدار» شد.')
    mark_buyer.short_description = 'علامت‌گذاری: خریدار'

    def mark_junk(self, request, queryset):
        n = queryset.update(status=VisitorLead.LeadStatus.JUNK)
        self.message_user(request, f'{n} سرنخ «تست/نامعتبر» شد.')
    mark_junk.short_description = 'علامت‌گذاری: تست/نامعتبر'
