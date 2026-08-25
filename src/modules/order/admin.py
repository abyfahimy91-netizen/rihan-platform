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
        'total_amount', 'payment_status', 'items_count', 'created_at_fa', 'expires_at_fa'
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


# اتصال اینلاین به ادمین موجود سفارش
OrderAdmin.inlines = [*OrderAdmin.inlines, ShipmentInline]


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    formfield_overrides = {}  # placeholder تا فیلدهای سفارشی لازم نشود

    list_display = ['shipment_id_short', 'order_link', 'supplier_or_rihan', 'status_badge',
                    'carrier_label', 'tracking_code_ltr', 'notified_summary', 'shipped_at_fa']
    list_filter = ['status', 'fulfiller', 'carrier']
    search_fields = ['tracking_code', 'order__order_number', 'supplier__title']
    ordering = ['-created_at']
    autocomplete_fields = []
    readonly_fields = ['order', 'fulfiller', 'supplier', 'sent_to_supplier_at', 'last_notified_at',
                       'supplier_notified_count', 'created_at', 'updated_at', 'dispatch_preview']
    fieldsets = [
        ('مرسوله', {'fields': ['order', 'fulfiller', 'supplier', 'status', 'notes']}),
        ('ارسال (کد رهگیری)', {'fields': ['carrier', 'tracking_code', 'shipped_at', 'delivered_at']}),
        ('اطلاع‌رسانی به تامین‌کننده', {'fields': ['sent_to_supplier_at', 'last_notified_at', 'supplier_notified_count']}),
        ('📋 متن دستور ارسال محوله (کپی برای تامین‌کننده)', {'fields': ['dispatch_preview']}),
        ('زمان‌ها', {'classes': ['collapse'], 'fields': ['created_at', 'updated_at']}),
    ]
    actions = ['action_mark_delivered', 'action_resend_supplier_sms', 'action_resend_customer_sms']

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

    @admin.display(description='شرکت حمل')
    def carrier_label(self, obj):
        return obj.get_carrier_display()

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
