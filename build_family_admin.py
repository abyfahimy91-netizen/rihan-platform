import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

files = {
    BASE / "src/apps/orders/admin.py": """from django.contrib import admin
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
""",

    BASE / "src/apps/orders/views.py": """from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework import generics, status
from rest_framework.response import Response
from apps.catalog.models import Product
from .models import Order, OrderItem
from .cart import Cart
from .serializers import OrderSerializer

def cart_detail_view(request):
    cart = Cart(request)
    context = {'cart': cart}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'orders/partials/cart_content.html', context)
    return render(request, 'orders/cart.html', context)

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_available=True)
    quantity = int(request.POST.get('quantity', 1))
    cart.add(product=product, quantity=quantity)
    if request.headers.get('HX-Request'):
        return render(request, 'orders/partials/cart_content.html', {'cart': cart})
    return redirect('cart_detail')

@require_POST
def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    if request.headers.get('HX-Request'):
        return render(request, 'orders/partials/cart_content.html', {'cart': cart})
    return redirect('cart_detail')

def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('product_list')

    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        province = request.POST.get('province')
        city = request.POST.get('city')
        address = request.POST.get('address')
        postal_code = request.POST.get('postal_code')
        notes = request.POST.get('notes', '')

        if name and phone and address and postal_code:
            order = Order.objects.create(
                customer_name=name,
                customer_phone=phone,
                province=province or 'نامشخص',
                city=city or 'نامشخص',
                shipping_address=address,
                postal_code=postal_code,
                customer_notes=notes,
                items_total=cart.get_total_price(),
                shipping_cost=0,
                grand_total=cart.get_grand_total(),
                status='pending_payment',
                payment_method='card_to_card'
            )

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_title=item['product'].title,
                    product_sku=item['product'].sku,
                    unit_price=item['price'],
                    quantity=item['quantity'],
                    subtotal=item['total_price']
                )

            cart.clear()
            return redirect('order_success', order_number=order.order_number)

    context = {'cart': cart}
    return render(request, 'orders/checkout.html', context)

def order_success_view(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number)
    return render(request, 'orders/order_success.html', {'order': order})

@staff_member_required
def admin_order_invoice_view(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id)
    return render(request, 'admin/orders/invoice.html', {'order': order})

class OrderCreateAPI(generics.CreateAPIView):
    serializer_class = OrderSerializer
    def create(self, request, *args, **kwargs):
        cart = Cart(request)
        if len(cart) == 0:
            return Response({"error": "سبد خرید خالی است."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save(
            items_total=cart.get_total_price(),
            shipping_cost=0,
            grand_total=cart.get_grand_total(),
            status='pending_payment'
        )
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                product_title=item['product'].title,
                product_sku=item['product'].sku,
                unit_price=item['price'],
                quantity=item['quantity']
            )
        cart.clear()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
""",

    BASE / "src/apps/orders/urls.py": """from django.urls import path
from . import views

urlpatterns = [
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/success/<str:order_number>/', views.order_success_view, name='order_success'),
    path('admin/orders/<int:order_id>/invoice/', views.admin_order_invoice_view, name='admin_order_invoice'),
    path('api/orders/create/', views.OrderCreateAPI.as_view(), name='api_order_create'),
]
""",

    BASE / "src/templates/admin/orders/invoice.html": """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>فاکتور سفارش {{ order.order_number }} | پلتفرم ریهان</title>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
        body {
            font-family: 'Vazirmatn', Tahoma, sans-serif;
            background: #fff;
            color: #23180c;
            padding: 30px;
            font-size: 13px;
        }
        .invoice-box {
            max-width: 800px;
            margin: auto;
            border: 1px solid #eee;
            padding: 30px;
            border-radius: 16px;
        }
        .header-table, .items-table {
            width: 100%;
            border-collapse: collapse;
        }
        .header-table td {
            vertical-align: top;
        }
        .items-table th {
            background: #fbf9f6;
            border-bottom: 2px solid #c5a059;
            padding: 10px;
            text-align: right;
        }
        .items-table td {
            padding: 12px 10px;
            border-bottom: 1px solid #f0f0f0;
        }
        .total-box {
            margin-top: 20px;
            text-align: left;
        }
        .footer-note {
            margin-top: 40px;
            padding-top: 15px;
            border-top: 1px dashed #c5a059;
            text-align: center;
            font-size: 11px;
            color: #7c5e38;
        }
        @media print {
            .no-print { display: none; }
            body { padding: 0; }
            .invoice-box { border: none; }
        }
    </style>
</head>
<body>
    <div class="no-print" style="max-width: 800px; margin: 0 auto 20px; text-align: left;">
        <button onclick="window.print()" style="background: #23180c; color: #fff; border: none; padding: 8px 18px; border-radius: 8px; cursor: pointer; font-family: inherit;">🖨️ چاپ فاکتور مرسوله</button>
    </div>

    <div class="invoice-box">
        <table class="header-table">
            <tr>
                <td>
                    <h2 style="margin: 0; color: #23180c;">پلتفرم ریهان (RIHAN)</h2>
                    <p style="margin: 5px 0; color: #7c5e38; font-size: 12px;">فروشگاه آنلاین اعتمادمحور با گزینش اصیل‌ترین کالاها</p>
                </td>
                <td style="text-align: left;">
                    <h3 style="margin: 0; color: #7c5e38;">شماره فاکتور: {{ order.order_number }}</h3>
                    <p style="margin: 5px 0; color: #888;">تاریخ ثبت: {{ order.created_at|date:"Y/m/d H:i" }}</p>
                </td>
            </tr>
        </table>

        <div style="background: #fbf9f6; padding: 15px; border-radius: 12px; margin: 20px 0;">
            <strong>مشخصات تحویل‌گیرنده:</strong><br>
            نام خریدار: {{ order.customer_name }} | شماره تماس: {{ order.customer_phone }}<br>
            نشانی مقصد: {{ order.province }}، {{ order.city }}، {{ order.shipping_address }} (کد پستی: {{ order.postal_code }})
            {% if order.customer_notes %}
            <br><strong>یادداشت خریدار:</strong> {{ order.customer_notes }}
            {% endif %}
        </div>

        <table class="items-table">
            <thead>
                <tr>
                    <th>ردیف</th>
                    <th>عنوان کالا</th>
                    <th>کد کالا (SKU)</th>
                    <th>قیمت واحد</th>
                    <th>تعداد</th>
                    <th>جمع ردیف</th>
                </tr>
            </thead>
            <tbody>
                {% for item in order.items.all %}
                <tr>
                    <td>{{ forloop.counter }}</td>
                    <td><strong>{{ item.product_title }}</strong></td>
                    <td>{{ item.product_sku }}</td>
                    <td>{{ item.unit_price|floatformat:"0" }} تومان</td>
                    <td>{{ item.quantity }}</td>
                    <td>{{ item.subtotal|floatformat:"0" }} تومان</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="total-box">
            <p style="margin: 5px 0;">جمع ارزش اقلام: <strong>{{ order.items_total|floatformat:"0" }} تومان</strong></p>
            <p style="margin: 5px 0; color: #198754;">هزینه ارسال و بسته‌بندی ویژه: <strong>✓ لحاظ‌شده در قیمت تمام‌شده کالا</strong></p>
            <h3 style="margin: 10px 0; color: #23180c;">مبلغ کل فاکتور: {{ order.grand_total|floatformat:"0" }} تومان</h3>
            <p style="font-size: 11px; color: #666;">روش پرداخت: {{ order.get_payment_method_display }} | وضعیت: {{ order.get_status_display }}</p>
        </div>

        <div class="footer-note">
            از اینکه ریهان را برای خرید برگزیدید صمیمانه سپاسگزاریم.<br>
            تضمین اصالت کالا و حفظ کرامت مشتریان، تعهد بنیادین و همیشگی خانواده ریهان است.
        </div>
    </div>
</body>
</html>
""",

    BASE / "tests/test_family_admin.py": """from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem

User = get_user_model()

class FamilyAdminTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_test', email='admin@rihan.local', password='AdminTest1405Pass!'
        )
        self.cat = Category.objects.create(name="سوغات", slug="souvenir")
        self.p = Product.objects.create(
            category=self.cat, title="سماق هوراند", slug="somagh-hurand",
            sku="RIHAN-SM-01", summary="سماق طبیعی هوراند", price=250000, stock=20
        )
        self.order = Order.objects.create(
            customer_name="مریم کارمند",
            customer_phone="09141112233",
            shipping_address="تبریز، خیابان آزادی",
            postal_code="5166677889",
            items_total=250000,
            grand_total=250000,
            status='payment_submitted'
        )
        OrderItem.objects.create(
            order=self.order, product=self.p, product_title=self.p.title,
            product_sku=self.p.sku, unit_price=250000, quantity=1, subtotal=250000
        )

    def test_admin_invoice_access(self):
        c = Client()
        # Guest cannot access invoice
        res_guest = c.get(reverse('admin_order_invoice', args=[self.order.id]))
        self.assertEqual(res_guest.status_code, 302)

        # Admin can access printable invoice
        c.force_login(self.admin_user)
        res_admin = c.get(reverse('admin_order_invoice', args=[self.order.id]))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, "سماق هوراند")
        self.assertContains(res_admin, "مریم کارمند")
"""
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created: {path.name}")

# Customizing Admin Site Header & Title in urls.py
urls_file = BASE / "src/rihan/urls.py"
urls_content = urls_file.read_text(encoding="utf-8")
admin_branding = """
admin.site.site_header = "سامانه مدیریت و پنل خانواده ریهان"
admin.site.site_title = "پنل خانواده ریهان"
admin.site.index_title = "داشبورد مدیریت سفارش‌ها و کاتالوگ"
"""
if "admin.site.site_header" not in urls_content:
    urls_content += admin_branding
    urls_file.write_text(urls_content, encoding="utf-8")
    print("✓ Customized Django Admin Branding")

print("Family Admin Module 3 Deployed Successfully.")
