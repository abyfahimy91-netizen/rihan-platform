import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

files = {
    BASE / "src/apps/payments/__init__.py": "",
    BASE / "src/apps/payments/gateways/__init__.py": "",

    BASE / "src/apps/payments/apps.py": """from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'
    verbose_name = 'مدیریت پرداخت‌ها و امور مالی'
""",

    BASE / "src/apps/payments/models.py": """from django.db import models
from django.utils import timezone

class Payment(models.Model):
    GATEWAY_TYPES = [
        ('card_to_card', 'کارت‌به‌کارت'),
        ('online_gateway', 'درگاه آنلاین'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار واریز'),
        ('submitted', 'رسید ثبت‌شده / در حال بررسی'),
        ('verified', 'تأییدشده'),
        ('rejected', 'ردشده'),
    ]

    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='payment', verbose_name="سفارش")
    amount = models.PositiveBigIntegerField(verbose_name="مبلغ تراکنش (تومان)")
    gateway_type = models.CharField(max_length=30, choices=GATEWAY_TYPES, default='card_to_card', verbose_name="روش پرداخت")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت پرداخت")
    
    receipt_image = models.ImageField(upload_to='receipts/%Y/%m/', null=True, blank=True, verbose_name="تصویر فیش واریزی")
    transaction_reference = models.CharField(max_length=100, blank=True, verbose_name="شماره پیگیری / ارجاع")
    card_last_four = models.CharField(max_length=4, blank=True, verbose_name="۴ رقم آخر کارت واریزکننده")
    destination_card = models.CharField(max_length=50, default='۶۰۳۷-۹۹۷۵-۱۲۳۴-۵۶۷۸', verbose_name="شماره کارت مقصد")
    
    admin_notes = models.TextField(blank=True, verbose_name="توضیحات و بررسی ادمین")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تأیید")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"پرداخت سفارش {self.order.order_number} ({self.get_status_display()})"
""",

    BASE / "src/apps/payments/gateways/base.py": """from abc import ABC, abstractmethod

class BasePaymentGateway(ABC):
    @abstractmethod
    def initiate_payment(self, order):
        pass

    @abstractmethod
    def verify_payment(self, payment, **kwargs):
        pass
""",

    BASE / "src/apps/payments/gateways/card_to_card.py": """from django.utils import timezone
from .base import BasePaymentGateway
from apps.payments.models import Payment

class CardToCardGateway(BasePaymentGateway):
    def initiate_payment(self, order):
        payment, _ = Payment.objects.get_or_create(
            order=order,
            defaults={'amount': order.grand_total, 'gateway_type': 'card_to_card', 'status': 'pending'}
        )
        return payment

    def submit_receipt(self, payment, receipt_image=None, reference='', card_last_four=''):
        payment.status = 'submitted'
        if receipt_image:
            payment.receipt_image = receipt_image
        payment.transaction_reference = reference
        payment.card_last_four = card_last_four
        payment.save()
        
        # به‌روزرسانی وضعیت سفارش به رسید ثبت‌شده
        order = payment.order
        order.status = 'payment_submitted'
        order.save()
        return payment

    def verify_payment(self, payment, admin_user=None, notes=''):
        payment.status = 'verified'
        payment.verified_at = timezone.now()
        if notes:
            payment.admin_notes = notes
        payment.save()

        # تغییر خودکار وضعیت سفارش به تأییدشده
        order = payment.order
        order.status = 'confirmed'
        order.save()
        return payment
""",

    BASE / "src/apps/payments/admin.py": """from django.contrib import admin
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
""",

    BASE / "src/apps/payments/views.py": """from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.orders.models import Order
from .models import Payment
from .gateways.card_to_card import CardToCardGateway

@require_POST
def upload_receipt_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    gw = CardToCardGateway()
    payment = gw.initiate_payment(order)

    receipt_file = request.FILES.get('receipt_image')
    reference = request.POST.get('reference', '').strip()
    card_last_four = request.POST.get('card_last_four', '').strip()

    if receipt_file or reference:
        gw.submit_receipt(
            payment=payment,
            receipt_image=receipt_file,
            reference=reference,
            card_last_four=card_last_four
        )
        messages.success(request, "رسید واریزی شما با موفقیت ثبت شد و در حال بررسی توسط مدیریت است.")
    else:
        messages.error(request, "لطفاً تصویر فیش یا شماره پیگیری تراکنش را وارد فرمایید.")

    return redirect('order_success', order_number=order_number)
""",

    BASE / "src/apps/payments/urls.py": """from django.urls import path
from . import views

urlpatterns = [
    path('payments/receipt/upload/<str:order_number>/', views.upload_receipt_view, name='upload_receipt'),
]
""",

    BASE / "tests/test_payments.py": """from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.gateways.card_to_card import CardToCardGateway

class PaymentsTestCase(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            customer_name="سارا محمدی",
            customer_phone="09123456789",
            shipping_address="تبریز",
            postal_code="5123456789",
            items_total=500000,
            grand_total=500000
        )

    def test_card_to_card_lifecycle(self):
        gw = CardToCardGateway()
        payment = gw.initiate_payment(self.order)
        self.assertEqual(payment.amount, 500000)
        self.assertEqual(payment.status, 'pending')

        # Submit receipt
        img = SimpleUploadedFile("receipt.jpg", b"sample_image_bytes", content_type="image/jpeg")
        gw.submit_receipt(payment, receipt_image=img, reference="12345678", card_last_four="9988")
        
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, 'submitted')
        self.assertEqual(self.order.status, 'payment_submitted')

        # Verify payment by admin
        gw.verify_payment(payment)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, 'verified')
        self.assertEqual(self.order.status, 'confirmed')
"""
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created: {path.name}")

# Update settings.py
settings_file = BASE / "src/rihan/settings.py"
settings_content = settings_file.read_text(encoding="utf-8")
if "'apps.payments'" not in settings_content:
    settings_content = settings_content.replace("'apps.accounts',", "'apps.accounts',\n    'apps.payments',")
    settings_file.write_text(settings_content, encoding="utf-8")
    print("✓ Registered apps.payments in settings.py")

# Update urls.py
urls_file = BASE / "src/rihan/urls.py"
urls_content = urls_file.read_text(encoding="utf-8")
if "apps.payments.urls" not in urls_content:
    urls_content = urls_content.replace("path('', include('apps.accounts.urls')),", "path('', include('apps.accounts.urls')),\n    path('', include('apps.payments.urls')),")
    urls_file.write_text(urls_content, encoding="utf-8")
    print("✓ Registered payments urls in urls.py")

# Update order_success.html with Receipt Upload Form
order_success_template = BASE / "src/templates/orders/order_success.html"
order_success_content = """{% extends 'base.html' %}
{% block title %}سفارش با موفقیت ثبت شد | ریهان{% endblock %}
{% block content %}
<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
    <div class="bg-white rounded-3xl border border-gray-100 p-8 sm:p-12 shadow-sm">
        <div class="w-16 h-16 bg-green-50 text-green-600 rounded-full flex items-center justify-center text-3xl mx-auto mb-4 border border-green-100">
            ✓
        </div>
        <h1 class="text-2xl font-black text-gray-900">سفارش شما با احترام ثبت گردید</h1>
        <p class="text-xs text-gray-500 mt-2">از حسن اعتماد شما به برند اصیل ریهان صمیمانه سپاسگزاریم.</p>

        {% if messages %}
        <div class="my-6 space-y-2 text-right">
            {% for message in messages %}
            <div class="p-3.5 rounded-2xl text-xs {% if message.tags == 'success' %}bg-green-50 text-green-800 border border-green-200{% else %}bg-red-50 text-red-800 border border-red-200{% endif %}">
                {{ message }}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="bg-rihan-50 rounded-2xl border border-rihan-100 p-6 my-6 text-right space-y-3">
            <div class="flex justify-between items-center border-b border-rihan-200 pb-3">
                <span class="text-xs text-gray-600">شماره یکتای سفارش:</span>
                <span class="text-sm font-extrabold text-rihan-900 bg-white px-3 py-1 rounded-lg border border-rihan-200 font-mono">{{ order.order_number }}</span>
            </div>
            <div class="flex justify-between text-xs text-gray-600">
                <span>نام تحویل‌گیرنده:</span>
                <span class="font-bold text-gray-900">{{ order.customer_name }}</span>
            </div>
            <div class="flex justify-between text-xs text-gray-600">
                <span>وضعیت سفارش:</span>
                <span class="font-bold text-rihan-900">{{ order.get_status_display }}</span>
            </div>
            <div class="border-t border-rihan-200 pt-3 flex justify-between text-sm font-black text-rihan-900">
                <span>مبلغ قابل پرداخت:</span>
                <span>{{ order.grand_total|floatformat:"0" }} تومان</span>
            </div>
        </div>

        <!-- Card to Card Instruction Box (ADR-005) -->
        <div class="bg-amber-50 border border-amber-200 p-6 rounded-2xl text-right mb-6">
            <h3 class="text-xs font-bold text-amber-900 mb-2">💳 راهنمای واریز کارت‌به‌کارت:</h3>
            <p class="text-xs text-amber-800 leading-relaxed">
                لطفاً مبلغ <strong>{{ order.grand_total|floatformat:"0" }} تومان</strong> را به شماره کارت رسمی زیر واریز فرمایید:<br>
                <span class="font-mono font-bold text-base block my-2 text-gray-900 text-center tracking-widest bg-white py-2 rounded-xl border border-amber-200">۶۰۳۷ - ۹۹۷۵ - ۱۲۳۴ - ۵۶۷۸</span>
                <span class="text-center block text-xs text-gray-600">به نام: مدیریت پلتفرم ریهان (بانک ملی)</span>
            </p>
        </div>

        <!-- Receipt Upload Form (M11) -->
        <div class="bg-white border border-gray-200 p-6 rounded-2xl text-right mb-8 shadow-sm">
            <h3 class="text-xs font-bold text-gray-900 mb-2">📤 ثبت رسید واریزی (تأیید سریع سفارش):</h3>
            <p class="text-[11px] text-gray-500 mb-4 leading-relaxed">پس از واریز، می‌توانید تصویر فیش یا شماره پیگیری را در این بخش بارگذاری فرمایید تا سفارش شما فوراً در صف بسته‌بندی قرار گیرد.</p>
            
            <form method="post" action="{% url 'upload_receipt' order_number=order.order_number %}" enctype="multipart/form-data" class="space-y-4">
                {% csrf_token %}
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-[11px] font-semibold text-gray-700 mb-1">۴ رقم آخر کارت واریزکننده</label>
                        <input type="text" name="card_last_four" maxlength="4" class="w-full bg-gray-50 border border-gray-200 rounded-xl p-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="مثال: ۱۲۳۴">
                    </div>
                    <div>
                        <label class="block text-[11px] font-semibold text-gray-700 mb-1">شماره ارجاع / پیگیری بانکی</label>
                        <input type="text" name="reference" class="w-full bg-gray-50 border border-gray-200 rounded-xl p-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="مثال: ۹۸۷۶۵۴۳۲۱">
                    </div>
                </div>
                <div>
                    <label class="block text-[11px] font-semibold text-gray-700 mb-1">تصویر فیش / اسکرین‌شات واریزی</label>
                    <input type="file" name="receipt_image" accept="image/*" class="w-full bg-gray-50 border border-gray-200 rounded-xl p-2 text-xs text-gray-700 focus:outline-none">
                </div>
                <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-3 rounded-xl transition text-xs shadow-sm">
                    ثبت و ارسال فیش برای تأیید حسابداری ↗
                </button>
            </form>
        </div>

        <div class="flex flex-wrap justify-center gap-4">
            <a href="{% url 'order_tracking' %}?order_number={{ order.order_number }}&phone={{ order.customer_phone }}" class="bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold px-6 py-3 rounded-xl transition">
                رهگیری لحظه‌ای وضعیت سفارش →
            </a>
            <a href="{% url 'product_list' %}" class="bg-rihan-900 hover:bg-rihan-800 text-white text-xs font-semibold px-6 py-3 rounded-xl transition shadow-sm">
                بازگشت به کاتالوگ
            </a>
        </div>
    </div>
</div>
{% endblock %}
"""
order_success_template.write_text(order_success_content, encoding="utf-8")
print("✓ Updated order_success.html with Receipt Upload Form")

print("Module M11 (Payment Abstraction) Deployed Successfully.")
