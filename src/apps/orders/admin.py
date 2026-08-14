from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_title', 'product_sku', 'unit_price', 'quantity', 'subtotal']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'customer_phone', 'city', 'grand_total_display', 'status_badge', 'created_at', 'invoice_link']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_phone', 'tracking_code', 'shipping_address']
    readonly_fields = ['order_number', 'items_total', 'shipping_cost', 'grand_total', 'created_at', 'updated_at', 'invoice_button']
    inlines = [OrderItemInline]
    actions = ['mark_as_confirmed', 'mark_as_shipped']

    @admin.display(description="مبلغ نهایی")
    def grand_total_display(self, obj):
        return f"{obj.grand_total:,} تومان"

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {
            'pending_payment': '#6c757d',
            'payment_submitted': '#0d6efd',
            'confirmed': '#6f42c1',
            'shipped': '#198754',
            'delivered': '#0f5132',
            'cancelled': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description="فاکتور")
    def invoice_link(self, obj):
        url = reverse('admin_order_invoice', args=[obj.id])
        return format_html('<a href="{}" target="_blank" style="color: #7c5e38; font-weight: bold;">چاپ فاکتور 🖨️</a>', url)

    @admin.display(description="چاپ فاکتور رسمی")
    def invoice_button(self, obj):
        url = reverse('admin_order_invoice', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank" style="background: #23180c; color: #fff; padding: 6px 14px; border-radius: 8px; text-decoration: none;">مشاهده و چاپ فاکتور بسته 🖨️</a>', url)

    @admin.action(description="تأیید سفارش‌های انتخاب‌شده (آماده‌سازی بسته)")
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, "سفارش‌های انتخاب‌شده با موفقیت تأیید شدند.")

    @admin.action(description="تغییر وضعیت به ارسال‌شده")
    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, "وضعیت سفارش‌های انتخاب‌شده به ارسال‌شده تغییر یافت.")
