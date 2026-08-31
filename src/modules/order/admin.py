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
from .models import Cart, CartItem, Order, OrderItem, Payment, Address, BankAccount
from . import finance as _finance
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
    can_delete = False
    readonly_fields = ['product', 'product_name_snapshot', 'variant_title', 'quantity',
                       'unit_price_at_purchase', 'unit_cost_at_purchase', 'subtotal']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_display', 'status_badge',
        'total_amount', 'payment_status', 'items_count', 'settlement_badge',
        'created_at_fa', 'expires_at_fa'
    ]
    list_filter = ['status', 'settlement_status', 'created_at', 'updated_at']
    search_fields = ['order_number', 'guest_name', 'guest_phone', 'user__username']
    readonly_fields = [
        'id', 'order_number', 'subtotal', 'total_price', 'shipping_cost',
        'settlement_status',
        'created_at', 'updated_at'
    ]
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    actions = ['action_settle_suppliers']

    def has_delete_permission(self, request, obj=None):
        # D-112: حذف سفارش ممنوع است — رزرو موجودی آزاد نمی‌شود (قفل همیشگی کالا)
        # و سوابق مالی/پیامک/مرسوله یتیم می‌شوند. لغو سفارش فقط از مسیر سرویس/انقضا.
        return False

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
            'fields': ('created_at', 'updated_at', 'expires_at')
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

    # ── D-113: تسویه با تامین‌کننده ──

    def settlement_badge(self, obj):
        colors = {
            'NONE': '#b9c4bf',
            'PENDING': '#c8a24b',
            'PARTIAL': '#e08c2b',
            'SETTLED': '#0D3B2E',
        }
        color = colors.get(obj.settlement_status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:10px; font-size:11px;">{}</span>',
            color, obj.get_settlement_status_display()
        )
    settlement_badge.short_description = 'تسویه'
    settlement_badge.admin_order_field = 'settlement_status'

    @admin.action(description='💰 تسویه با تامین‌کننده (همه مرسوله‌های تامین‌کننده‌دار)')
    def action_settle_suppliers(self, request, queryset):
        settled = skipped = 0
        for order in queryset:
            n, s = _finance.settle_shipments(
                order.shipments.all(), request.user,
                note=f'تسویه گروهی از لیست سفارش‌ها توسط {request.user.get_username()}')
            settled += n
            skipped += s
        msg = f'{settled} مرسوله تسویه شد.'
        if skipped:
            msg += f' ({skipped} مورد نامعتبر/قبلاً تسویه‌شده رد شد)'
        self.message_user(request, msg)

    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ ثبت'
    created_at_fa.admin_order_field = 'created_at'

    def expires_at_fa(self, obj):
        """D-099: نمایش مهلت رزرو؛ نزدیک به پایان = نارنجی، گذشته = قرمز"""
        if not obj.expires_at or obj.status != 'PENDING':
            return '—'
        remaining = obj.remaining_seconds
        label = jalali_datetime_str(obj.expires_at)
        if remaining <= 0:
            return format_html('<span style="color:#c0392b;font-weight:700;">{} (منقضی)</span>', label)
        if remaining < 900:
            return format_html('<span style="color:#d68910;font-weight:700;">{} (نزدیک پایان)</span>', label)
        return label
    expires_at_fa.short_description = 'مهلت پرداخت'


# ═══════════════════════════════════════════════════════════════
# D-111 — اینلاین پرداخت‌ها داخل صفحه سفارش: رسید با یک کلیک باز می‌شود
# ═══════════════════════════════════════════════════════════════

class PaymentInline(admin.TabularInline):
    """پرداخت‌های سفارش — فقط خواندنی؛ لینک مستقیم مشاهده رسید"""
    model = Payment
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ['created_at_fa_inline', 'status_display_inline', 'gateway',
              'amount_display_inline', 'last4_inline', 'receipt_link_inline']
    readonly_fields = fields
    verbose_name = "پرداخت"
    verbose_name_plural = "پرداخت‌های این سفارش (رسید را با کلیک ببینید)"

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='تاریخ')
    def created_at_fa_inline(self, obj):
        return jalali_datetime_str(obj.created_at) if obj and obj.pk else '-'

    @admin.display(description='وضعیت پرداخت')
    def status_display_inline(self, obj):
        if not obj or not obj.pk:
            return '-'
        colors = {
            'PENDING': '#6c757d', 'PENDING_REVIEW': '#c8a24b',
            'SUCCESS': '#28a745', 'FAILED': '#dc3545', 'CANCELLED': '#dc3545',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:10px;font-size:11px;">{}</span>',
            colors.get(obj.status, '#666'), obj.get_status_display())

    @admin.display(description='مبلغ', )
    def amount_display_inline(self, obj):
        return f'{fa_money(obj.amount)} تومان' if obj and obj.pk else '-'

    @admin.display(description='۴ رقم کارت')
    def last4_inline(self, obj):
        return obj.sender_card_last4 or '-' if obj and obj.pk else '-'

    @admin.display(description='رسید')
    def receipt_link_inline(self, obj):
        if obj and obj.pk and obj.receipt_image:
            return format_html(
                '<a href="{}" target="_blank" style="font-weight:bold;">📎 مشاهده رسید</a>',
                obj.receipt_image.url)
        return format_html('<span style="color:#888;">—</span>')


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
            # D-111: لینک کلیک‌شدنی برای مشاهده رسید
            parts.append(format_html(
                '<a href="{}" target="_blank" style="font-weight:bold;">📎 مشاهده رسید</a>',
                obj.receipt_image.url))
        
        return format_html(
            '<span style="color:#2d5a2d;">{}</span>',
            format_html(' | '.join(['{}'] * len(parts)), *parts)
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


# ═══════════════════════════════════════════════════════════════
# Admin حساب‌های بانکی مقصد (پرداخت کارت‌به‌کارت)
# ═══════════════════════════════════════════════════════════════

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = [
        'bank_name', 'card_grouped_display', 'card_holder',
        'label', 'sort_order', 'is_active', 'created_at_fa',
    ]
    list_editable = ['sort_order', 'is_active']
    list_filter = ['is_active', 'bank_name']
    search_fields = ['bank_name', 'card_number', 'card_holder', 'label']
    readonly_fields = ['created_at']

    fieldsets = (
        ('اطلاعات حساب مقصد', {
            'fields': ('bank_name', 'card_number', 'card_holder', 'iban'),
            'description': 'این اطلاعات در صفحه پرداخت مشتری با دکمه کپی نمایش داده می‌شود.',
        }),
        ('نمایش', {
            'fields': ('label', 'sort_order', 'is_active'),
            'description': 'با «ترتیب نمایش» مشخص کنید کدام کارت اول دیده شود. غیرفعال = مخفی از سایت.',
        }),
    )

    def card_grouped_display(self, obj):
        return format_html(
            '<span dir="ltr" style="font-family:monospace;font-weight:600;">{}</span>',
            obj.card_grouped,
        )
    card_grouped_display.short_description = 'شماره کارت'

    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ'

# ═══════════════════════════════════════════════════════════════════
# D-105 — ادمین مرسوله‌ها + لاگ اطلاع‌رسانی
# جریان: پرداخت تایید شد → مرسوله‌ها خودکار ساخته می‌شوند؛ اینجا مدیریت/پیگیری
# ═══════════════════════════════════════════════════════════════════

from django.urls import reverse as _admin_reverse
from django.utils.safestring import mark_safe

from .models import Shipment, ShipmentItem, NotificationLog
from . import fulfillment as _fulfillment


class ShipmentInline(admin.TabularInline):
    """مرسوله‌های سفارش — فقط خواندنی؛ ویرایش از صفحه اختصاصی مرسوله"""
    model = Shipment
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ['shipment_link', 'supplier_or_rihan', 'status', 'carrier', 'tracking_code', 'shipped_at_fa_inline']
    readonly_fields = ['shipment_link', 'supplier_or_rihan', 'status', 'carrier', 'tracking_code', 'shipped_at_fa_inline']
    verbose_name = "مرسوله"
    verbose_name_plural = "مرسوله‌های این سفارش"

    @admin.display(description='مرسوله')
    def shipment_link(self, obj):
        if not obj or not obj.pk:
            return '-'
        url = _admin_reverse('admin:order_shipment_change', args=[obj.pk])
        label = f'#{str(obj.pk)[:8].upper()}'
        return format_html('<a href="{}"><b>{}</b></a>', url, label)

    @admin.display(description='ارسال توسط')
    def supplier_or_rihan(self, obj):
        if not obj:
            return '-'
        return obj.supplier.title if obj.supplier_id else 'ریهان'

    @admin.display(description='زمان ارسال')
    def shipped_at_fa_inline(self, obj):
        from src.core.fa import jalali_human
        return jalali_human(obj.shipped_at) if obj and obj.shipped_at else '-'


# اتصال اینلاین‌ها به ادمین موجود سفارش (D-111: پرداخت‌ها هم داخل صفحه سفارش)
OrderAdmin.inlines = [*OrderAdmin.inlines, PaymentInline, ShipmentInline]


# ── D-111: فرم اعتبارسنجی مرسوله در ادمین — کد رهگیری استاندارد + الزامات «سایر» ──
from django import forms as _django_forms


class ShipmentAdminForm(_django_forms.ModelForm):
    class Meta:
        model = Shipment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        carrier = (self.instance.carrier if self.instance and self.instance.pk else
                   (self.data.get('carrier') if self.data else '') or 'POST')
        hint = _fulfillment.carrier_code_hint(carrier)
        if hint:
            self.fields['tracking_code'].help_text = (
                f'فرمت استاندارد: {hint}')
        self.fields['other_carrier_name'].help_text = 'فقط وقتی شرکت حمل «سایر» است لازم می‌شود'
        self.fields['other_carrier_person'].help_text = 'مثلاً نام راننده/پیک — برای حالت «سایر» الزامی'
        self.fields['other_carrier_phone'].help_text = 'برای حالت «سایر» الزامی — به مشتری نمایش داده می‌شود'

    def clean(self):
        cleaned = super().clean()
        carrier = cleaned.get('carrier')
        code = cleaned.get('tracking_code') or ''
        try:
            cleaned['tracking_code'] = _fulfillment.validate_tracking_code(carrier, code)
        except _fulfillment.FulfillmentError as e:
            self.add_error('tracking_code', str(e))
        if carrier == Shipment.Carrier.OTHER:
            for field, label in (
                ('other_carrier_name', 'نام شرکت حمل'),
                ('other_carrier_person', 'نام ارسال‌کننده/راننده'),
                ('other_carrier_phone', 'شماره تماس حمل‌کننده'),
            ):
                if not (cleaned.get(field) or '').strip():
                    self.add_error(field, f'در حالت «سایر»، {label} الزامی است.')
        return cleaned


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    form = ShipmentAdminForm  # D-111: اعتبارسنجی استاندارد کد رهگیری + الزامات «سایر»

    list_display = ['shipment_id_short', 'order_link', 'supplier_or_rihan', 'status_badge',
                    'sla_status', 'carrier_label', 'tracking_code_ltr', 'payable_display', 'settlement_badge',
                    'notified_summary', 'shipped_at_fa']
    list_filter = ['status', 'fulfiller', 'carrier', 'settlement_status']
    search_fields = ['tracking_code', 'order__order_number', 'supplier__title']
    ordering = ['-created_at']
    autocomplete_fields = []
    readonly_fields = ['order', 'fulfiller', 'supplier', 'sent_to_supplier_at', 'last_notified_at',
                       'supplier_notified_count', 'created_at', 'updated_at', 'dispatch_preview',
                       'customer_sms_preview',
                       'settlement_status', 'settled_amount', 'settled_at', 'settled_by',
                       'payable_preview']
    fieldsets = [
        ('مرسوله', {'fields': ['order', 'fulfiller', 'supplier', 'status', 'notes']}),
        ('ارسال (کد رهگیری)', {'fields': [
            'carrier', 'tracking_code',
            'other_carrier_name', 'other_carrier_person', 'other_carrier_phone',
            'shipped_at', 'delivered_at'],
            'description': 'کد رهگیری باید با فرمت استاندارد شرکت حمل مطابقت داشته باشد. '
                           'برای «سایر»: نام شرکت، نام ارسال‌کننده و شماره تماس الزامی است و به مشتری نمایش داده می‌شود.'}),
        ('💸 هزینه‌های واقعی ارسال (D-113)', {'fields': [
            'post_cost', 'post_paid_by', 'other_costs', 'other_costs_note', 'other_paid_by'],
            'description': 'هزینه پست/باربری و سایر هزینه‌ها (بسته‌بندی، برچسب و…) را دستی وارد کنید. '
                           'هر کدام که «تامین‌کننده» پرداخت کرده باشد در تسویه به او برگردانده می‌شود؛ '
                           'آن‌ها که «ریهان» پرداخت کرده فقط در گزارش سود حساب می‌شوند.'}),
        ('💰 تسویه با تامین‌کننده', {'fields': [
            'payable_preview', 'settlement_status', 'settled_amount', 'settled_at',
            'settled_by', 'settlement_note'],
            'description': 'مبلغ قابل پرداخت به‌صورت خودکار محاسبه می‌شود: قیمت خرید اقلام + '
                           'هزینه‌های پیش‌پرداخت تامین‌کننده. تسویه از اکشن‌های لیست یا سفارش انجام شود تا مبلغ snapshot گردد.',
            'classes': ['collapse']}),
        ('اطلاع‌رسانی به تامین‌کننده', {'fields': ['sent_to_supplier_at', 'last_notified_at', 'supplier_notified_count']}),
        ('📋 متن دستور ارسال محوله (کپی برای تامین‌کننده)', {'fields': ['dispatch_preview']}),
        ('📱 متن پیامک مشتری (کپی و ارسال دستی)', {'fields': ['customer_sms_preview'],
            'description': 'تا وقتی پنل پیامکی فعال نشده، این متن را کپی کنید و با گوشی خودتان به مشتری بفرستید. '
                           'پس از فعال‌شدن پنل پیامکی، همین پیام به‌صورت خودکار ارسال می‌شود.'}),
        ('زمان‌ها', {'classes': ['collapse'], 'fields': ['created_at', 'updated_at']}),
    ]
    actions = ['action_mark_delivered', 'action_resend_supplier_sms', 'action_resend_customer_sms',
               'action_settle', 'action_reopen_settlement']

    # ── ستون‌های لیست ──
    @admin.display(description='مرسوله', ordering='id')
    def shipment_id_short(self, obj):
        return f'#{str(obj.pk)[:8].upper()}'

    @admin.display(description='سفارش', ordering='order__order_number')
    def order_link(self, obj):
        url = _admin_reverse('admin:order_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)

    @admin.display(description='ارسال توسط')
    def supplier_or_rihan(self, obj):
        return obj.supplier.title if obj.supplier_id else 'ریهان'

    @admin.display(description='وضعیت')
    def status_badge(self, obj):
        colors = {
            Shipment.Status.NEW: '#c8a24b',
            Shipment.Status.SHIPPED: '#28a745',
            Shipment.Status.DELIVERED: '#0D3B2E',
            Shipment.Status.CANCELED: '#999999',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;">{}</span>',
            colors.get(obj.status, '#666'), obj.get_status_display())

    @admin.display(description='مهلت ارسال')
    def sla_status(self, obj):
        """D-119: دیرکرد مرسوله‌های نزد تامین‌کننده — قرمز اگر از مهلت گذشته باشد"""
        if obj.status != Shipment.Status.NEW:
            return '—'
        hours = int(obj.hours_since_assignment)
        if obj.is_overdue:
            return format_html(
                '<span style="background:#b3261e;color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;">'
                '🔴 دیرکرد {} ساعت</span>', fa_money(hours))
        return format_html(
            '<span style="color:#6d6a60;">⏳ {} ساعت</span>', fa_money(hours))

    @admin.display(description='شرکت حمل')
    def carrier_label(self, obj):
        return obj.carrier_full_label

    @admin.display(description='کد رهگیری')
    def tracking_code_ltr(self, obj):
        if not obj.tracking_code:
            return format_html('<span style="color:#c00;">ثبت نشده</span>')
        return format_html('<span dir="ltr" style="font-family:monospace;">{}</span>', obj.tracking_code)

    @admin.display(description='اطلاع‌رسانی')
    def notified_summary(self, obj):
        if not obj.supplier_id:
            return '—'
        if obj.sent_to_supplier_at:
            from src.core.fa import jalali_human
            return f'✅ ×{obj.supplier_notified_count} | {jalali_human(obj.last_notified_at)}'
        return format_html('<span style="color:#c00;">هنوز اطلاع داده نشده</span>')

    @admin.display(description='زمان ارسال')
    def shipped_at_fa(self, obj):
        from src.core.fa import jalali_human
        return jalali_human(obj.shipped_at) if obj.shipped_at else '-'

    # ── D-113: ستون‌ها و اکشن‌های مالی ──

    @admin.display(description='قابل پرداخت تامین‌کننده')
    def payable_display(self, obj):
        payable = obj.supplier_payable
        if payable == 0:
            return format_html('<span style="color:#999;">—</span>')
        settled = obj.settlement_status == Shipment.SettlementStatus.SETTLED
        color = '#0D3B2E' if settled else '#b3261e'
        label = 'تسویه شده' if settled else fa_money(payable)
        return format_html('<strong style="color:{};">{} تومان</strong>', color, label)

    @admin.display(description='وضعیت تسویه')
    def settlement_badge(self, obj):
        colors = {
            Shipment.SettlementStatus.UNSETTLED: '#c8a24b',
            Shipment.SettlementStatus.SETTLED: '#0D3B2E',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:10px;font-size:11px;">{}</span>',
            colors.get(obj.settlement_status, '#666'), obj.get_settlement_status_display())

    @admin.display(description='مبلغ قابل پرداخت (محاسبه خودکار)')
    def payable_preview(self, obj):
        if not obj or not obj.pk:
            return '— پس از ذخیره محاسبه می‌شود —'
        f = _finance.shipment_financials(obj)
        return format_html(
            '<div dir="rtl" style="line-height:2.2;font-size:13px;">'
            'قیمت خرید اقلام: <b>{} تومان</b><br>'
            'هزینه‌های پیش‌پرداخت تامین‌کننده: <b>{} تومان</b><br>'
            'هزینه‌های پرداخت‌شده توسط ریهان (فقط گزارش سود): {} تومان<br>'
            '<span style="font-size:15px;color:#0D3B2E;">قابل پرداخت به تامین‌کننده: '
            '<b>{} تومان</b></span></div>',
            fa_money(f['items_cost']), fa_money(f['supplier_extra']),
            fa_money(f['rihan_extra']), fa_money(f['payable']))

    @admin.action(description='💰 تسویه شد (با snapshot مبلغ فعلی)')
    def action_settle(self, request, queryset):
        settled, skipped = _finance.settle_shipments(
            queryset, request.user,
            note=f'تسویه از لیست مرسوله‌ها توسط {request.user.get_username()}')
        msg = f'{settled} مرسوله تسویه شد.'
        if skipped:
            msg += f' ({skipped} مورد نامعتبر یا قبلاً تسویه‌شده رد شد)'
        self.message_user(request, msg)

    @admin.action(description='↩️ بازکردن تسویه (مثلاً مرجوعی)')
    def action_reopen_settlement(self, request, queryset):
        reopened, skipped = _finance.reopen_shipments(queryset, request.user)
        msg = f'{reopened} تسویه باز شد.'
        if skipped:
            msg += f' ({skipped} مورد اصلاً تسویه نبود)'
        self.message_user(request, msg)

    # ── متن دستور ارسال با دکمه کپی ──
    @admin.display(description='متن آماده ارسال به تامین‌کننده')
    def dispatch_preview(self, obj):
        if not obj or not obj.pk:
            return '-'
        text = _fulfillment.dispatch_instruction_text(obj)
        copy_js = (
            '<script>'
            'document.addEventListener("click",function(e){'
            'var b=e.target.closest(".rihan-copy-dispatch");if(!b)return;'
            'var t=document.getElementById("rihan-dispatch-text");if(!t)return;'
            'var txt=t.textContent.trim();'
            'var done=function(){var o=b.textContent;b.textContent="\u2705 \u06a9\u067e\u06cc \u0634\u062f";'
            'setTimeout(function(){b.textContent=o},1800)};'
            'if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt).then(done);}else{'
            'var r=document.createRange();r.selectNodeContents(t);var s=window.getSelection();s.removeAllRanges();s.addRange(r);'
            'try{document.execCommand("copy");done();}catch(err){}}});'
            '</script>'
        )
        button = '<button type="button" class="button rihan-copy-dispatch">\U0001f4cb \u06a9\u067e\u06cc \u0645\u062a\u0646 \u062f\u0633\u062a\u0648\u0631 \u0627\u0631\u0633\u0627\u0644</button>'
        pre = format_html(
            '<pre dir="rtl" id="rihan-dispatch-text" '
            'style="white-space:pre-wrap;background:#FAF7F0;padding:14px;border-radius:10px;'
            'border:1px solid #ddd;line-height:1.9;font-size:13px;">{}</pre>', text)
        return format_html('{}{}{}', mark_safe(button), pre, mark_safe(copy_js))

    # ── D-124: متن پیامک دستی مشتری — کپی و ارسال با گوشی ادمین ──
    @admin.display(description='متن آماده پیامک به مشتری')
    def customer_sms_preview(self, obj):
        if not obj or not obj.pk:
            return '-'
        has_code = bool(obj.tracking_code)
        is_other = obj.carrier == Shipment.Carrier.OTHER
        if not has_code and not is_other:
            return format_html(
                '<span style="color:#b3261e;">هنوز کد رهگیری ثبت نشده — پس از ذخیره کد (یا کامل‌کردن '
                'جزئیات شرکت حمل «سایر»)، متن پیامک اینجا ساخته می‌شود.</span>')

        text = _fulfillment.manual_customer_sms_text(obj)
        auto = _fulfillment.sms_auto_send_available()
        if auto:
            note = ('✅ سرویس پیامک فعال است؛ پیامک به‌صورت خودکار ارسال شده/می‌شود — '
                    'این متن فقط برای ارسال مجدد دستی است.')
        else:
            note = ('⚠️ پنل پیامکی هنوز فعال نیست — دکمه کپی را بزنید و متن را با گوشی خودتان '
                    'به شماره مشتری پیامک کنید.')

        copy_js = (
            '<script>'
            'document.addEventListener("click",function(e){'
            'var b=e.target.closest(".rihan-copy-sms");if(!b)return;'
            'var t=document.getElementById("rihan-sms-text");if(!t)return;'
            'var txt=t.textContent.trim();'
            'var done=function(){var o=b.textContent;b.textContent="\u2705 \u06a9\u067e\u06cc \u0634\u062f";'
            'setTimeout(function(){b.textContent=o},1800)};'
            'if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt).then(done);}else{'
            'var r=document.createRange();r.selectNodeContents(t);var s=window.getSelection();s.removeAllRanges();s.addRange(r);'
            'try{document.execCommand("copy");done();}catch(err){}}});'
            '</script>'
        )
        button = '<button type="button" class="button rihan-copy-sms">\U0001f4cb \u06a9\u067e\u06cc \u0645\u062a\u0646 \u067e\u06cc\u0627\u0645\u06a9</button>'
        test_link = ''
        if has_code:
            test_link = format_html(
                ' · <a href="{}" target="_blank">👁 تست لینک پیگیری (سامانه با کد پرشده باز می‌شود)</a>',
                _fulfillment.short_tracking_link(obj.tracking_code))
        pre = format_html(
            '<pre dir="rtl" id="rihan-sms-text" '
            'style="white-space:pre-wrap;background:#FAF7F0;padding:14px;border-radius:10px;'
            'border:1px solid #ddd;line-height:2;font-size:13px;">{}</pre>', text)
        return format_html(
            '<div dir="rtl" style="line-height:2.1;font-size:13px;margin-bottom:8px;">{}</div>'
            '<div>{} <span style="color:#888;">({} کاراکتر)</span>{}</div>{}{}',
            note, mark_safe(button), fa_money(len(text)), test_link, pre, mark_safe(copy_js))

    # ── اکشن‌ها ──
    @admin.action(description='✅ علامت‌گذاری «تحویل داده شد»')
    def action_mark_delivered(self, request, queryset):
        n = 0
        for shipment in queryset.exclude(status=Shipment.Status.DELIVERED):
            _fulfillment.mark_delivered(shipment, user=request.user)
            n += 1
        self.message_user(request, f'{n} مرسوله تحویل‌شده علامت خورد.')

    @admin.action(description='📨 ارسال دوباره پیامک به تامین‌کننده')
    def action_resend_supplier_sms(self, request, queryset):
        ok = fail = 0
        for shipment in queryset.filter(fulfiller=Shipment.FulfillerType.SUPPLIER).exclude(supplier=None):
            if _fulfillment.send_supplier_assignment_sms(shipment):
                ok += 1
            else:
                fail += 1
        msg = f'{ok} پیامک موفق'
        if fail:
            msg += f'، {fail} ناموفق (جزئیات در «لاگ اطلاع‌رسانی»)'
        self.message_user(request, msg)

    @admin.action(description='📩 ارسال/ارسال مجدد پیامک رهگیری به مشتری')
    def action_resend_customer_sms(self, request, queryset):
        ok = skip = 0
        for shipment in queryset.exclude(tracking_code=''):
            phone = _fulfillment.customer_phone(shipment.order)
            sent = _fulfillment._send_sms(
                'CUSTOMER_SHIPPED', phone,
                _fulfillment.customer_shipped_text(shipment),
                order=shipment.order, shipment=shipment)
            ok += int(bool(sent))
            skip += int(not sent)
        self.message_user(request, f'{ok} پیامک ارسال شد، {skip} ناموفق/بدون شماره.')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['kind_label', 'recipient', 'success_icon', 'detail', 'order_number', 'created_at']
    list_filter = ['kind', 'success']
    search_fields = ['recipient', 'order__order_number', 'detail']
    ordering = ['-created_at']

    @admin.display(description='نوع')
    def kind_label(self, obj):
        return obj.get_kind_display()

    @admin.display(description='نتیجه', boolean=True)
    def success_icon(self, obj):
        return obj.success

    @admin.display(description='سفارش')
    def order_number(self, obj):
        return obj.order.order_number if obj.order_id else '-'
