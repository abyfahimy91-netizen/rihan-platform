import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

files = {
    BASE / "src/apps/orders/__init__.py": "",
    BASE / "src/apps/orders/apps.py": """from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    verbose_name = 'مدیریت سفارش‌ها و سبد خرید'
""",

    BASE / "src/apps/orders/models.py": """from django.db import models
from django.utils.crypto import get_random_string

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending_payment', 'در انتظار پرداخت'),
        ('payment_submitted', 'رسید ثبت‌شده / در حال بررسی'),
        ('confirmed', 'تأییدشده و آماده‌سازی'),
        ('shipped', 'ارسال‌شده به مقصد'),
        ('delivered', 'تحویل داده‌شده'),
        ('cancelled', 'لغوشده'),
    ]

    PAYMENT_METHODS = [
        ('card_to_card', 'کارت‌به‌کارت'),
        ('online_gateway', 'درگاه پرداخت آنلاین'),
    ]

    order_number = models.CharField(max_length=50, unique=True, editable=False, verbose_name="شماره سفارش")
    customer_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")
    customer_phone = models.CharField(max_length=20, verbose_name="شماره موبایل")
    customer_email = models.EmailField(blank=True, verbose_name="ایمیل (اختیاری)")
    
    province = models.CharField(max_length=100, verbose_name="استان")
    city = models.CharField(max_length=100, verbose_name="شهر")
    shipping_address = models.TextField(verbose_name="نشانی دقیق پستی")
    postal_code = models.CharField(max_length=20, verbose_name="کد پستی")
    customer_notes = models.TextField(blank=True, verbose_name="یادداشت سفارش")

    items_total = models.PositiveBigIntegerField(default=0, verbose_name="جمع اقلام (تومان)")
    shipping_cost = models.PositiveBigIntegerField(default=0, verbose_name="هزینه ارسال (D-046: لحاظ در قیمت کالا)")
    grand_total = models.PositiveBigIntegerField(default=0, verbose_name="مبلغ نهایی (تومان)")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment', verbose_name="وضعیت سفارش")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='card_to_card', verbose_name="روش پرداخت")
    tracking_code = models.CharField(max_length=100, blank=True, verbose_name="کد رهگیری پستی / باربری")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            random_suffix = get_random_string(length=5, allowed_chars='123456789ABCDEFGHJKLMNPQRSTUVWXYZ')
            self.order_number = f"RH-1405-{random_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سفارش {self.order_number} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="سفارش")
    product = models.ForeignKey('catalog.Product', on_delete=models.SET_NULL, null=True, related_name='order_items', verbose_name="محصول")
    product_title = models.CharField(max_length=255, verbose_name="عنوان محصول")
    product_sku = models.CharField(max_length=50, verbose_name="کد کالا")
    unit_price = models.PositiveBigIntegerField(verbose_name="قیمت واحد (تومان)")
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    subtotal = models.PositiveBigIntegerField(verbose_name="جمع ردیف (تومان)")

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_title} x {self.quantity}"
""",

    BASE / "src/apps/orders/cart.py": """from apps.catalog.models import Product

CART_SESSION_ID = 'rihan_cart'

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': int(product.price),
                'title': product.title,
                'slug': product.slug,
                'image_url': product.primary_image.image_url if product.primary_image else ''
            }
        if override_quantity:
            self.cart[product_id]['quantity'] = int(quantity)
        else:
            self.cart[product_id]['quantity'] += int(quantity)
        
        if self.cart[product_id]['quantity'] <= 0:
            self.remove(product)
        else:
            self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def save(self):
        self.session.modified = True

    def clear(self):
        if CART_SESSION_ID in self.session:
            del self.session[CART_SESSION_ID]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product
        for item in cart.values():
            if 'product' in item:
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(item['price'] * item['quantity'] for item in self.cart.values())

    def get_shipping_cost(self):
        # مصوبه D-046: هزینه ارسال در قیمت تمام‌شده کالا محاسبه شده است (پرداخت مازاد صفر)
        return 0

    def get_grand_total(self):
        return self.get_total_price() + self.get_shipping_cost()
""",

    BASE / "src/apps/orders/admin.py": """from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_title', 'product_sku', 'unit_price', 'quantity', 'subtotal']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'customer_phone', 'city', 'grand_total', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_phone', 'tracking_code']
    readonly_fields = ['order_number', 'items_total', 'shipping_cost', 'grand_total', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
""",

    BASE / "src/apps/orders/serializers.py": """from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_title', 'product_sku', 'unit_price', 'quantity', 'subtotal']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer_name', 'customer_phone', 'customer_email', 'province', 'city', 'shipping_address', 'postal_code', 'customer_notes', 'items_total', 'shipping_cost', 'grand_total', 'status', 'payment_method', 'tracking_code', 'created_at', 'items']
""",

    BASE / "src/apps/orders/views.py": """from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
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
    path('api/orders/create/', views.OrderCreateAPI.as_view(), name='api_order_create'),
]
""",

    BASE / "src/templates/orders/partials/cart_content.html": """<div class="bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm">
    {% if cart|length > 0 %}
    <div class="space-y-6">
        {% for item in cart %}
        <div class="flex items-center justify-between border-b border-gray-100 pb-6">
            <div class="flex items-center gap-4">
                {% if item.image_url %}
                <img src="{{ item.image_url }}" alt="{{ item.title }}" class="w-16 h-16 object-cover rounded-xl border border-gray-100">
                {% else %}
                <div class="w-16 h-16 bg-gray-50 rounded-xl flex items-center justify-center text-xl">🎁</div>
                {% endif %}
                <div>
                    <h3 class="text-sm font-bold text-gray-900">{{ item.title }}</h3>
                    <span class="text-xs text-gray-400 block mt-1">قیمت واحد: {{ item.price|floatformat:"0" }} تومان</span>
                </div>
            </div>

            <div class="flex items-center gap-6">
                <span class="text-xs font-semibold text-gray-700 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
                    تعداد: {{ item.quantity }}
                </span>
                <span class="text-sm font-extrabold text-rihan-900">
                    {{ item.total_price|floatformat:"0" }} <span class="text-xs font-normal text-gray-500">تومان</span>
                </span>
                <form hx-post="{% url 'cart_remove' product_id=item.product.id %}" hx-target="#cart-container" class="inline">
                    {% csrf_token %}
                    <button type="submit" class="text-gray-400 hover:text-red-600 transition text-sm px-2 py-1 rounded-md" title="حذف کالا">
                        ✕
                    </button>
                </form>
            </div>
        </div>
        {% endfor %}

        <!-- D-046: All-Inclusive Pricing Box -->
        <div class="bg-rihan-50 p-6 rounded-2xl border border-rihan-100 space-y-3 mt-8">
            <div class="flex justify-between text-xs text-gray-600">
                <span>جمع ارزش اقلام:</span>
                <span class="font-bold text-gray-900">{{ cart.get_total_price|floatformat:"0" }} تومان</span>
            </div>
            <div class="flex justify-between text-xs text-gray-600">
                <span>هزینه بسته‌بندی فاخر و ارسال:</span>
                <span class="font-bold text-green-700 bg-green-50 px-2 py-0.5 rounded border border-green-200">✓ در قیمت کالا لحاظ شده (پرداخت مازاد: ۰ تومان)</span>
            </div>
            <div class="border-t border-rihan-200 pt-3 flex justify-between text-base font-black text-rihan-900">
                <span>مبلغ نهایی قابل پرداخت:</span>
                <span>{{ cart.get_grand_total|floatformat:"0" }} تومان</span>
            </div>
            <p class="text-[11px] text-gray-500 text-center pt-2">✓ قیمت تمام‌شده و شفاف — هیچ هزینه پنهان یا پرداخت اضافی وجود ندارد (مصوبه D-046)</p>
        </div>

        <div class="flex justify-between items-center pt-4">
            <a href="{% url 'product_list' %}" class="text-xs text-gray-500 hover:text-rihan-800 transition">
                ← بازگشت و افزودن کالاهای دیگر
            </a>
            <a href="{% url 'checkout' %}" class="bg-rihan-900 hover:bg-rihan-800 text-white text-sm font-bold px-8 py-3.5 rounded-2xl shadow-md transition">
                تکمیل اطلاعات و تسویه‌حساب →
            </a>
        </div>
    </div>
    {% else %}
    <div class="text-center py-16">
        <span class="text-5xl block mb-4 text-gray-300">🛒</span>
        <h3 class="text-base font-bold text-gray-800">سبد خرید شما خالی است</h3>
        <p class="text-xs text-gray-500 mt-2">می‌توانید از کاتالوگ گزینش‌شده ریهان کالای مورد نظر خود را انتخاب فرمایید.</p>
        <a href="{% url 'product_list' %}" class="inline-block bg-rihan-900 hover:bg-rihan-800 text-white text-xs font-semibold px-6 py-3 rounded-xl mt-6 transition shadow-sm">
            مشاهده کاتالوگ محصولات
        </a>
    </div>
    {% endif %}
</div>
""",

    BASE / "src/templates/orders/cart.html": """{% extends 'base.html' %}
{% block title %}سبد خرید | ریهان{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
    <div class="mb-8 text-center sm:text-right">
        <h1 class="text-3xl font-extrabold text-rihan-900">سبد خرید شما</h1>
        <p class="text-gray-500 text-xs mt-1">شفافیت کامل مبالغ، بدون هزینه‌های غافلگیرکننده (مصوبه D-046)</p>
    </div>
    <div id="cart-container">
        {% include 'orders/partials/cart_content.html' %}
    </div>
</div>
{% endblock %}
""",

    BASE / "src/templates/orders/checkout.html": """{% extends 'base.html' %}
{% block title %}تسویه‌حساب و نهایی‌سازی سفارش | ریهان{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
    <div class="mb-8">
        <h1 class="text-2xl sm:text-3xl font-extrabold text-rihan-900">مشخصات گیرنده و نهایی‌سازی سفارش</h1>
        <p class="text-xs text-gray-500 mt-1">لطفاً نشانی دقیق پستی را جهت ارسال محترمانه و به موقع درج فرمایید.</p>
    </div>

    <form method="post" action="{% url 'checkout' %}" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {% csrf_token %}
        <div class="lg:col-span-2 bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm space-y-5">
            <h2 class="text-base font-bold text-gray-900 border-b border-gray-100 pb-3">اطلاعات تماس و نشانی</h2>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-1.5">نام و نام خانوادگی گیرنده *</label>
                    <input type="text" name="name" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="مثال: سارا محمدی">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-1.5">شماره موبایل جهت هماهنگی و پیامک رهگیری *</label>
                    <input type="tel" name="phone" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="09123456789">
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-1.5">استان *</label>
                    <input type="text" name="province" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="آذربایجان شرقی">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-gray-700 mb-1.5">شهر *</label>
                    <input type="text" name="city" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="تبریز">
                </div>
            </div>

            <div>
                <label class="block text-xs font-semibold text-gray-700 mb-1.5">نشانی پستی دقیق *</label>
                <textarea name="address" rows="3" required class="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="خیابان، کوچه، پلاک، واحد"></textarea>
            </div>

            <div>
                <label class="block text-xs font-semibold text-gray-700 mb-1.5">کد پستی ۱۰ رقمی *</label>
                <input type="text" name="postal_code" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="۵۱۳۴۵۶۷۸۹۰">
            </div>

            <div>
                <label class="block text-xs font-semibold text-gray-700 mb-1.5">توضیحات تحویل (اختیاری)</label>
                <input type="text" name="notes" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="مثال: تحویل در ساعات اداری">
            </div>
        </div>

        <div class="bg-white rounded-3xl border border-gray-100 p-6 shadow-sm flex flex-col justify-between h-fit space-y-6">
            <div>
                <h3 class="text-sm font-bold text-gray-900 border-b border-gray-100 pb-3">خلاصه فاکتور شفاف</h3>
                <div class="space-y-3 mt-4 text-xs text-gray-600">
                    <div class="flex justify-between">
                        <span>تعداد اقلام:</span>
                        <span class="font-bold text-gray-900">{{ cart|length }} عدد</span>
                    </div>
                    <div class="flex justify-between">
                        <span>جمع سفارش:</span>
                        <span class="font-bold text-gray-900">{{ cart.get_total_price|floatformat:"0" }} تومان</span>
                    </div>
                    <div class="flex justify-between">
                        <span>هزینه ارسال و بسته‌بندی:</span>
                        <span class="font-bold text-green-700">✓ لحاظ‌شده در قیمت کالا</span>
                    </div>
                    <div class="border-t border-gray-100 pt-3 flex justify-between text-sm font-black text-rihan-900">
                        <span>مبلغ نهایی و تمام‌شده:</span>
                        <span>{{ cart.get_grand_total|floatformat:"0" }} تومان</span>
                    </div>
                </div>

                <div class="mt-6 p-4 bg-rihan-50 rounded-2xl border border-rihan-100">
                    <span class="text-xs font-bold text-rihan-800 block">روش پرداخت:</span>
                    <span class="text-xs text-gray-600 block mt-1">💳 واریز کارت‌به‌کارت مستقیم (ثبت رسید در گام بعد)</span>
                </div>
            </div>

            <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-3.5 rounded-2xl shadow-md transition text-xs">
                ثبت نهایی سفارش و صدور شماره فاکتور
            </button>
        </div>
    </form>
</div>
{% endblock %}
""",

    BASE / "src/templates/orders/order_success.html": """{% extends 'base.html' %}
{% block title %}سفارش با موفقیت ثبت شد | ریهان{% endblock %}
{% block content %}
<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
    <div class="bg-white rounded-3xl border border-gray-100 p-8 sm:p-12 shadow-sm">
        <div class="w-16 h-16 bg-green-50 text-green-600 rounded-full flex items-center justify-center text-3xl mx-auto mb-4 border border-green-100">
            ✓
        </div>
        <h1 class="text-2xl font-black text-gray-900">سفارش شما با احترام ثبت گردید</h1>
        <p class="text-xs text-gray-500 mt-2">از حسن اعتماد شما به برند اصیل ریهان صمیمانه سپاسگزاریم.</p>

        <div class="bg-rihan-50 rounded-2xl border border-rihan-100 p-6 my-8 text-right space-y-3">
            <div class="flex justify-between items-center border-b border-rihan-200 pb-3">
                <span class="text-xs text-gray-600">شماره یکتای سفارش:</span>
                <span class="text-sm font-extrabold text-rihan-900 bg-white px-3 py-1 rounded-lg border border-rihan-200">{{ order.order_number }}</span>
            </div>
            <div class="flex justify-between text-xs text-gray-600">
                <span>نام تحویل‌گیرنده:</span>
                <span class="font-bold text-gray-900">{{ order.customer_name }}</span>
            </div>
            <div class="flex justify-between text-xs text-gray-600">
                <span>شماره تماس:</span>
                <span class="font-bold text-gray-900">{{ order.customer_phone }}</span>
            </div>
            <div class="flex justify-between text-xs text-gray-600">
                <span>نشانی ارسال:</span>
                <span class="font-bold text-gray-900">{{ order.province }}، {{ order.city }}، {{ order.shipping_address }}</span>
            </div>
            <div class="border-t border-rihan-200 pt-3 flex justify-between text-sm font-black text-rihan-900">
                <span>مبلغ نهایی قابل پرداخت:</span>
                <span>{{ order.grand_total|floatformat:"0" }} تومان</span>
            </div>
        </div>

        <div class="bg-amber-50 border border-amber-200 p-6 rounded-2xl text-right mb-8">
            <h3 class="text-xs font-bold text-amber-900 mb-2">💳 راهنمای واریز کارت‌به‌کارت:</h3>
            <p class="text-xs text-amber-800 leading-relaxed">
                لطفاً مبلغ <strong>{{ order.grand_total|floatformat:"0" }} تومان</strong> را به شماره کارت رسمی زیر واریز فرمایید:<br>
                <span class="font-mono font-bold text-base block my-2 text-gray-900 text-center tracking-widest bg-white py-2 rounded-xl border border-amber-200">۶۰۳۷ - ۹۹۷۵ - ۱۲۳۴ - ۵۶۷۸</span>
                <span class="text-center block text-xs text-gray-600">به نام: مدیریت پلتفرم ریهان (بانک ملی)</span>
            </p>
        </div>

        <div class="flex flex-wrap justify-center gap-4">
            <a href="{% url 'product_list' %}" class="bg-rihan-900 hover:bg-rihan-800 text-white text-xs font-semibold px-6 py-3 rounded-xl transition shadow-sm">
                بازگشت به صفحه کاتالوگ
            </a>
        </div>
    </div>
</div>
{% endblock %}
""",

    BASE / "tests/test_orders.py": """from django.test import TestCase, Client
from django.urls import reverse
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.orders.cart import Cart

class OrdersTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="ارگانیک", slug="organic")
        self.p = Product.objects.create(
            category=self.cat, title="عسل سبلان", slug="honey-sabalan",
            sku="RIHAN-H1", summary="عسل طبیعی", price=450000, compare_at_price=500000, stock=10
        )

    def test_order_creation_and_number(self):
        order = Order.objects.create(
            customer_name="سارا محمدی",
            customer_phone="09123456789",
            shipping_address="تبریز، خیابان ولیعصر",
            postal_code="5123456789",
            items_total=450000,
            shipping_cost=0,
            grand_total=450000
        )
        self.assertTrue(order.order_number.startswith("RH-1405-"))
        self.assertEqual(order.grand_total, 450000)

    def test_cart_and_checkout_views(self):
        c = Client()
        c.post(reverse('cart_add', kwargs={'product_id': self.p.id}), {'quantity': 2})
        res_cart = c.get(reverse('cart_detail'))
        self.assertEqual(res_cart.status_code, 200)

        res_post = c.post(reverse('checkout'), {
            'name': 'علی حسینی',
            'phone': '09129876543',
            'province': 'تهران',
            'city': 'تهران',
            'address': 'خیابان انقلاب',
            'postal_code': '1234567890'
        })
        self.assertEqual(res_post.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
"""
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# Update settings.py
settings_file = BASE / "src/rihan/settings.py"
settings_content = settings_file.read_text(encoding="utf-8")
if "'apps.orders'" not in settings_content:
    settings_content = settings_content.replace("'apps.catalog',", "'apps.catalog',\n    'apps.orders',")
    settings_file.write_text(settings_content, encoding="utf-8")

# Update urls.py
urls_file = BASE / "src/rihan/urls.py"
urls_content = urls_file.read_text(encoding="utf-8")
if "apps.orders.urls" not in urls_content:
    urls_content = urls_content.replace("path('', include('apps.catalog.urls')),", "path('', include('apps.catalog.urls')),\n    path('', include('apps.orders.urls')),")
    urls_file.write_text(urls_content, encoding="utf-8")

print("✓ All Module 2 files created successfully on host.")
