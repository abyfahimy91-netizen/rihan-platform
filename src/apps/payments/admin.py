from django.contrib import admin
from django.utils.html import format_html
from .models import Payment
from .gateways.card_to_card import CardToCardGateway

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'amount_display', 'gateway_type', 'status_badge', 'card_last_four', 'transaction_reference', 'receipt_preview', 'created_at']
    list_filter = ['status', 'gateway_type', 'created_at']
    search_fields = ['order__order_number', 'order__customer_name', 'transaction_reference', 'card_last_four']
    readonly_fields = ['order', 'amount', 'created_at', 'updated_at', 'verified_at', 'receipt_large_preview']
    actions = ['approve_receipt_payments', 'reject_receipt_payments']

    @admin.display(description="مبلغ")
    def amount_display(self, obj):
        return f"{obj.amount:,} تومان"

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'submitted': '#0d6efd',
            'verified': '#198754',
            'rejected': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )

    @admin.display(description="تصویر فیش")
    def receipt_preview(self, obj):
        if obj.receipt_image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height: 40px; border-radius: 6px; border: 1px solid #ddd;" /></a>', obj.receipt_image.url, obj.receipt_image.url)
        return "-"

    @admin.display(description="پیش‌نمایش بزرگ فیش")
    def receipt_large_preview(self, obj):
        if obj.receipt_image:
            return format_html('<img src="{}" style="max-width: 350px; border-radius: 12px; border: 1px solid #ccc;" />', obj.receipt_image.url)
        return "تصویری بارگذاری نشده است."

    @admin.action(description="تأیید نهایی پرداخت و تأیید سفارش (Approve)")
    def approve_receipt_payments(self, request, queryset):
        gw = CardToCardGateway()
        for payment in queryset:
            gw.verify_payment(payment, admin_user=request.user)
        self.message_user(request, "پرداخت‌های انتخاب‌شده تأیید و وضعیت سفارش‌ها به تأییدشده تغییر یافت.")

    @admin.action(description="رد پرداخت‌های نامعتبر (Reject)")
    def reject_receipt_payments(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, "پرداخت‌های انتخاب‌شده رد شدند.")
