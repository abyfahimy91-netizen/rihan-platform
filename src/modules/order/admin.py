"""
Order Admin - پنل مدیریت سفارشات و پرداخت‌های کارت‌به‌کارت
منطبق بر ADR-005 (manual review برای پرداخت کارت‌به‌کارت)

این پنل موقتی است تا M3 (پنل خانواده) ساخته شود.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.urls import reverse
from .models import Cart, CartItem, Order, OrderItem, Payment, Address
from src.core.fa import money as fa_money, jalali_datetime_str


# ═══════════════════════════════════════════════════════════════
# Admin برای سبد خرید
# ═══════════════════════════════════════════════════════════════

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'unit_price_at_add', 'added_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_or_session', 'items_count', 'total_amount', 'is_active', 'created_at_fa']
    list_filter = ['is_active', 'created_at']
    search_fields = ['id', 'session_key', 'user__username', 'user__email']
    readonly_fields = ['id', 'session_key', 'user', 'is_active', 'created_at', 'updated_at']
    inlines = [CartItemInline]
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'تعداد اقلام'
    
    def total_amount(self, obj):
        return fa_money(obj.subtotal) + ' تومان'
    total_amount.short_description = 'مبلغ کل'
    
    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ'
    created_at_fa.admin_order_field = 'created_at'

    def user_or_session(self, obj):
        if obj.user:
            return f"{obj.user.username} (کاربر)"
        return f"{obj.session_key[:8]}... (مهمان)"
    user_or_session.short_description = 'کاربر/مهمان'
    
    def has_add_permission(self, request):
        return False


# ═══════════════════════════════════════════════════════════════
# Admin برای سفارشات
# ═══════════════════════════════════════════════════════════════

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name_snapshot', 'quantity', 'unit_price_at_purchase', 'subtotal']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_display', 'status_badge',
        'total_amount', 'payment_status', 'items_count', 'created_at_fa'
    ]
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['order_number', 'guest_name', 'guest_phone', 'user__username']
    readonly_fields = [
        'id', 'order_number', 'subtotal', 'total_price', 'shipping_cost',
        'created_at', 'updated_at'
    ]
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('order_number', 'status', 'user')
        }),
        ('اطلاعات خریدار', {
            'fields': ('guest_name', 'guest_phone', 'guest_address', 'guest_postal_code')
        }),
        ('مبالغ', {
            'fields': ('subtotal', 'shipping_cost', 'total_price')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def customer_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return f"{obj.guest_name} (مهمان)"
    customer_display.short_description = 'خریدار'
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': '#6c757d',
            'PENDING': '#ffc107',
            'PAID': '#28a745',
            'PROCESSING': '#17a2b8',
            'SHIPPED': '#007bff',
            'DELIVERED': '#28a745',
            'CANCELLED': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:4px 12px; border-radius:12px; font-size:12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    status_badge.admin_order_field = 'status'
    
    def total_amount(self, obj):
        num = fa_money(obj.total_price)
        return format_html('<strong style="color:#2d5a2d;">{} تومان</strong>', num)
    total_amount.short_description = 'مبلغ نهایی'
    total_amount.admin_order_field = 'total_price'
    
    def payment_status(self, obj):
        payment = obj.payments.order_by('-created_at').first()
        if not payment:
            return format_html('<span style="color:#888;">-</span>')
        
        colors = {
            'PENDING': '#6c757d',
            'PENDING_REVIEW': '#ffc107',
            'SUCCESS': '#28a745',
            'FAILED': '#dc3545',
            'CANCELLED': '#dc3545',
        }
        color = colors.get(payment.status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:10px; font-size:11px;">{}</span>',
            color, payment.get_status_display()
        )
    payment_status.short_description = 'وضعیت پرداخت'
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'اقلام'

    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ ثبت'
    created_at_fa.admin_order_field = 'created_at'


# ═══════════════════════════════════════════════════════════════
# Admin برای پرداخت‌ها (پنل تایید کارت‌به‌کارت)
# ═══════════════════════════════════════════════════════════════

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_name', 'amount_display',
        'status_badge', 'gateway_badge', 'evidence_preview',
        'reviewed_by_name', 'created_at_fa'
    ]
    list_filter = ['status', 'gateway', 'created_at', 'reviewed_at']
    search_fields = ['order__order_number', 'sender_card_last4', 'order__guest_name']
    readonly_fields = [
        'id', 'order', 'amount', 'gateway', 'authority', 'ref_id',
        'sender_card_last4', 'transfer_time', 'receipt_image_preview',
        'reviewed_by', 'reviewed_at', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    actions = ['confirm_payment', 'reject_payment']
    
    fieldsets = (
        ('اطلاعات پرداخت', {
            'fields': ('id', 'order', 'amount', 'gateway', 'status')
        }),
        ('Evidence کارت‌به‌کارت (ثبت‌شده توسط مشتری)', {
            'fields': ('sender_card_last4', 'transfer_time', 'receipt_image_preview'),
            'classes': ('collapse',),
        }),
        ('تایید ادمین', {
            'fields': ('reviewed_by', 'reviewed_at', 'admin_notes'),
        }),
        ('شناسه‌های درگاه (برای درگاه‌های آنلاین)', {
            'fields': ('authority', 'ref_id'),
            'classes': ('collapse',),
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def order_number(self, obj):
        url = reverse('admin:order_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'شماره سفارش'
    order_number.admin_order_field = 'order__order_number'
    
    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ ثبت'
    created_at_fa.admin_order_field = 'created_at'

    def customer_name(self, obj):
        if obj.order.user:
            return obj.order.user.get_full_name() or obj.order.user.username
        return obj.order.guest_name or '(مهمان)'
    customer_name.short_description = 'مشتری'
    
    def amount_display(self, obj):
        return format_html(
            '<strong style="color:#2d5a2d; font-size:14px;">{}</strong> <span style="color:#888;">تومان</span>',
            fa_money(obj.amount)
        )
    amount_display.short_description = 'مبلغ'
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#6c757d',
            'PENDING_REVIEW': '#ffc107',
            'SUCCESS': '#28a745',
            'FAILED': '#dc3545',
            'CANCELLED': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    status_badge.admin_order_field = 'status'
    
    def gateway_badge(self, obj):
        colors = {
            'MANUAL': '#17a2b8',
            'MOCK': '#6c757d',
            'ZARINPAL': '#ffc107',
            'IDPAY': '#28a745',
        }
        color = colors.get(obj.gateway, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:10px; font-size:11px;">{}</span>',
            color, obj.get_gateway_display()
        )
    gateway_badge.short_description = 'درگاه'
    
    def evidence_preview(self, obj):
        if obj.gateway != 'MANUAL':
            return format_html('<span style="color:#888;">-</span>')
        
        if not obj.sender_card_last4:
            return format_html('<span style="color:#dc3545;">❌ evidence ثبت نشده</span>')
        
        parts = [f"****-{obj.sender_card_last4}"]
        if obj.transfer_time:
            parts.append(obj.transfer_time.strftime('%m/%d %H:%M'))
        if obj.receipt_image:
            parts.append("📎 رسید")
        
        return format_html(
            '<span style="color:#2d5a2d;">{}</span>',
            ' | '.join(parts)
        )
    evidence_preview.short_description = 'Evidence'
    
    def receipt_image_preview(self, obj):
        if obj.receipt_image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:400px; max-height:400px; border:1px solid #ddd; border-radius:8px;"/>'
                '</a>'
                '<br/><a href="{}" target="_blank" style="margin-top:10px; display:inline-block;">باز کردن تصویر کامل</a>',
                obj.receipt_image.url, obj.receipt_image.url, obj.receipt_image.url
            )
        return format_html('<span style="color:#888;">رسیدی آپلود نشده است</span>')
    receipt_image_preview.short_description = 'تصویر رسید'
    
    def reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.username
        return format_html('<span style="color:#888;">-</span>')
    reviewed_by_name.short_description = 'تاییدکننده'
    
    # Actions برای تایید/رد پرداخت
    @admin.action(description='✅ تایید پرداخت‌های انتخاب‌شده')
    def confirm_payment(self, request, queryset):
        """
        تایید پرداخت و تبدیل reservation به sale (مطابق D-045)
        از CheckoutService.confirm_payment استفاده می‌کند
        """
        from .checkout_service import CheckoutService
        
        confirmed_count = 0
        for payment in queryset.filter(status=Payment.PaymentStatus.PENDING_REVIEW):
            try:
                # استفاده از CheckoutService برای تایید کامل
                # Payment object مستقیم ارسال می‌شود تا evidence حفظ شود
                CheckoutService.confirm_payment(
                    order=payment.order,
                    payment=payment,  # ارسال مستقیم Payment
                    payment_data={
                        'notes': 'تایید از طریق پنل ادمین',
                    },
                    admin_user=request.user,
                )
                
                confirmed_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'خطا در تایید پرداخت {payment.id}: {str(e)}',
                    level='error'
                )
        
        if confirmed_count > 0:
            self.message_user(request, f'{confirmed_count} پرداخت با موفقیت تایید شد.')
    
    @admin.action(description='❌ رد پرداخت‌های انتخاب‌شده')
    def reject_payment(self, request, queryset):
        rejected_count = 0
        for payment in queryset.filter(status=Payment.PaymentStatus.PENDING_REVIEW):
            payment.reject(
                admin_user=request.user,
                notes='رد از طریق پنل ادمین. لطفاً با پشتیبانی تماس بگیرید.'
            )
            rejected_count += 1
        
        self.message_user(request, f'{rejected_count} پرداخت رد شد.')


# ═══════════════════════════════════════════════════════════════
# Admin برای آدرس‌ها
# ═══════════════════════════════════════════════════════════════

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'full_name', 'phone', 'city', 'address_type', 'is_default']
    list_filter = ['address_type', 'is_default', 'city']
    search_fields = ['title', 'full_name', 'phone', 'city', 'postal_code']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def has_add_permission(self, request):
        return False
