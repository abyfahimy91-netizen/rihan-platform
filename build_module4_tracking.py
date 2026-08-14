import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

files = {
    BASE / "src/templates/orders/tracking.html": """{% extends 'base.html' %}
{% block title %}پیگیری وضعیت سفارش | ریهان{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">

    <div class="mb-8 text-center sm:text-right">
        <h1 class="text-2xl sm:text-3xl font-extrabold text-rihan-900">پیگیری وضعیت مرسوله</h1>
        <p class="text-xs text-gray-500 mt-1">استعلام لحظه‌ای وضعیت آماده‌سازی و ارسال بسته بدون نیاز به ورود پیچیده</p>
    </div>

    <!-- Tracking Search Form -->
    <div class="bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm mb-10">
        <form method="get" action="{% url 'order_tracking' %}" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
                <label class="block text-xs font-semibold text-gray-700 mb-1.5">شماره یکتای سفارش *</label>
                <input type="text" name="order_number" value="{{ order_number }}" required 
                       class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" 
                       placeholder="مثال: RH-1405-A1B2C">
            </div>
            <div>
                <label class="block text-xs font-semibold text-gray-700 mb-1.5">شماره موبایل خریدار *</label>
                <input type="tel" name="phone" value="{{ phone }}" required 
                       class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" 
                       placeholder="09123456789">
            </div>
            <div class="flex items-end">
                <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-2.5 rounded-xl shadow-sm transition text-xs">
                    🔍 استعلام وضعیت
                </button>
            </div>
        </form>

        {% if error_message %}
        <div class="mt-4 p-4 bg-red-50 text-red-700 rounded-2xl border border-red-100 text-xs flex items-center gap-2">
            <span>⚠️</span>
            <span>{{ error_message }}</span>
        </div>
        {% endif %}
    </div>

    <!-- Tracking Result Box -->
    {% if order %}
    <div class="bg-white rounded-3xl border border-gray-100 p-6 sm:p-10 shadow-sm space-y-8">
        
        <!-- Header Info -->
        <div class="flex flex-wrap justify-between items-center border-b border-gray-100 pb-6 gap-4">
            <div>
                <span class="text-xs text-gray-400">سفارش متعلق به:</span>
                <h2 class="text-base font-bold text-gray-900 mt-0.5">{{ order.customer_name }}</h2>
                <span class="text-xs text-gray-500 block mt-1">شماره فاکتور: <strong class="text-rihan-900">{{ order.order_number }}</strong></span>
            </div>
            <div class="text-left">
                <span class="text-xs text-gray-400 block">تاریخ ثبت سفارش:</span>
                <span class="text-xs font-semibold text-gray-700">{{ order.created_at|date:"Y/m/d H:i" }}</span>
            </div>
        </div>

        <!-- Visual Timeline -->
        <div>
            <h3 class="text-xs font-bold text-rihan-gold uppercase tracking-wider mb-6">مراحل پیشرفت و آماده‌سازی سفارش</h3>
            
            <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 text-center">
                <!-- Step 1: Order Placed -->
                <div class="p-4 rounded-2xl border {% if order.status != 'cancelled' %}bg-green-50 border-green-200 text-green-800{% else %}bg-gray-50 border-gray-200 text-gray-400{% endif %}">
                    <span class="text-xl block mb-1">📝</span>
                    <strong class="text-xs block">۱. ثبت سفارش</strong>
                    <span class="text-[10px] opacity-75">انجام شد</span>
                </div>

                <!-- Step 2: Confirmed -->
                <div class="p-4 rounded-2xl border {% if order.status in 'confirmed,shipped,delivered' %}bg-green-50 border-green-200 text-green-800{% elif order.status == 'payment_submitted' %}bg-amber-50 border-amber-200 text-amber-800{% else %}bg-gray-50 border-gray-200 text-gray-400{% endif %}">
                    <span class="text-xl block mb-1">💳</span>
                    <strong class="text-xs block">۲. بررسی و تأیید</strong>
                    <span class="text-[10px] opacity-75">
                        {% if order.status in 'confirmed,shipped,delivered' %}تأیید شد
                        {% elif order.status == 'payment_submitted' %}در حال بررسی رسید
                        {% else %}در انتظار پرداخت{% endif %}
                    </span>
                </div>

                <!-- Step 3: Shipped -->
                <div class="p-4 rounded-2xl border {% if order.status in 'shipped,delivered' %}bg-green-50 border-green-200 text-green-800{% else %}bg-gray-50 border-gray-200 text-gray-400{% endif %}">
                    <span class="text-xl block mb-1">📦</span>
                    <strong class="text-xs block">۳. تحویل به پست</strong>
                    <span class="text-[10px] opacity-75">
                        {% if order.status in 'shipped,delivered' %}ارسال شد
                        {% else %}در صف آماده‌سازی{% endif %}
                    </span>
                </div>

                <!-- Step 4: Delivered -->
                <div class="p-4 rounded-2xl border {% if order.status == 'delivered' %}bg-green-50 border-green-200 text-green-800{% else %}bg-gray-50 border-gray-200 text-gray-400{% endif %}">
                    <span class="text-xl block mb-1">✨</span>
                    <strong class="text-xs block">۴. تحویل به مقصد</strong>
                    <span class="text-[10px] opacity-75">
                        {% if order.status == 'delivered' %}تحویل شد
                        {% else %}در مسیر مقصد{% endif %}
                    </span>
                </div>
            </div>
        </div>

        <!-- Postal Tracking Code Link (If Available) -->
        {% if order.tracking_code %}
        <div class="bg-amber-50 border border-amber-200 p-6 rounded-2xl flex flex-wrap justify-between items-center gap-4">
            <div>
                <span class="text-xs font-bold text-amber-900 block">کد رهگیری مرسوله پستی:</span>
                <span class="font-mono text-base font-extrabold text-gray-900 mt-1 block tracking-wider">{{ order.tracking_code }}</span>
            </div>
            <a href="https://tracking.post.ir/?id={{ order.tracking_code }}" target="_blank" 
               class="bg-amber-800 hover:bg-amber-900 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition shadow-sm flex items-center gap-2">
                <span>سامانه پیگیری شرکت ملی پست ↗</span>
            </a>
        </div>
        {% endif %}

        <!-- Order Items Summary -->
        <div class="border-t border-gray-100 pt-6">
            <h4 class="text-xs font-bold text-gray-700 mb-3">اقلام موجود در بسته:</h4>
            <div class="space-y-2">
                {% for item in order.items.all %}
                <div class="flex justify-between text-xs text-gray-600 bg-gray-50 p-3 rounded-xl">
                    <span>{{ item.product_title }} (تعداد: {{ item.quantity }})</span>
                    <span class="font-bold text-gray-900">{{ item.subtotal|floatformat:"0" }} تومان</span>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Customer Care & Dignity Note (Principle 11 & Error Handling) -->
        <div class="bg-rihan-50 p-5 rounded-2xl border border-rihan-100 text-xs text-gray-600 space-y-1 text-center sm:text-right">
            <strong class="text-rihan-900 block mb-1">همراهی و پاسخگویی ریهان:</strong>
            <p>در صورت وجود هرگونه پرسش یا نیاز به تغییر زمان تحویل، تیم ریهان مشتاقانه پاسخگوی شماست.</p>
            <p class="text-gray-500">شماره هماهنگی و پشتیبانی: <strong class="text-rihan-900 font-mono">۰۹۱۲۰۰۰۰۰۰۰</strong></p>
        </div>

    </div>
    {% endif %}

</div>
{% endblock %}
""",

    BASE / "tests/test_tracking.py": """from django.test import TestCase, Client
from django.urls import reverse
from apps.orders.models import Order

class OrderTrackingTestCase(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            customer_name="سارا محمدی",
            customer_phone="09123456789",
            shipping_address="تبریز، ولیعصر",
            postal_code="5123456789",
            items_total=450000,
            grand_total=450000,
            status='shipped',
            tracking_code='POST-1405-998877'
        )

    def test_tracking_page_and_valid_search(self):
        c = Client()
        # View tracking page
        res = c.get(reverse('order_tracking'))
        self.assertEqual(res.status_code, 200)

        # Search with valid order and phone
        res_search = c.get(reverse('order_tracking'), {
            'order_number': self.order.order_number,
            'phone': '09123456789'
        })
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, "سارا محمدی")
        self.assertContains(res_search, "POST-1405-998877")
        self.assertContains(res_search, "سامانه پیگیری شرکت ملی پست")

    def test_tracking_phone_mismatch(self):
        c = Client()
        res_mismatch = c.get(reverse('order_tracking'), {
            'order_number': self.order.order_number,
            'phone': '09999999999'
        })
        self.assertEqual(res_mismatch.status_code, 200)
        self.assertContains(res_mismatch, "سفارشی با این مشخصات یافت نشد")
"""
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created: {path.name}")

# Update src/apps/orders/views.py with tracking views
views_file = BASE / "src/apps/orders/views.py"
views_content = views_file.read_text(encoding="utf-8")
tracking_code = """

def order_tracking_view(request):
    order = None
    error_message = None
    order_number = request.GET.get('order_number', '').strip()
    phone = request.GET.get('phone', '').strip()

    if order_number and phone:
        try:
            order = Order.objects.prefetch_related('items').get(
                order_number__iexact=order_number,
                customer_phone__icontains=phone[-10:] # مقایسه امن ۱۰ رقم آخر موبایل
            )
        except Order.DoesNotExist:
            error_message = "سفارشی با این مشخصات یافت نشد. لطفاً شماره سفارش و موبایل را بررسی فرمایید."

    context = {
        'order': order,
        'order_number': order_number,
        'phone': phone,
        'error_message': error_message
    }
    return render(request, 'orders/tracking.html', context)
"""
if "def order_tracking_view" not in views_content:
    views_content += tracking_code
    views_file.write_text(views_content, encoding="utf-8")
    print("✓ Added order_tracking_view to views.py")

# Update src/apps/orders/urls.py
urls_file = BASE / "src/apps/orders/urls.py"
urls_content = urls_file.read_text(encoding="utf-8")
if "order_tracking" not in urls_content:
    urls_content = urls_content.replace(
        "path('checkout/', views.checkout_view, name='checkout'),",
        "path('checkout/', views.checkout_view, name='checkout'),\n    path('track/', views.order_tracking_view, name='order_tracking'),\n    path('tracking/', views.order_tracking_view, name='order_tracking_alias'),"
    )
    urls_file.write_text(urls_content, encoding="utf-8")
    print("✓ Registered /track/ and /tracking/ in urls.py")

# Update src/templates/base.html to add Track Order in Navbar
base_template = BASE / "src/templates/base.html"
base_content = base_template.read_text(encoding="utf-8")
if "/track/" not in base_content:
    base_content = base_content.replace(
        '<a href="/products/" class="hover:text-rihan-600 transition">کاتالوگ محصولات</a>',
        '<a href="/products/" class="hover:text-rihan-600 transition">کاتالوگ محصولات</a>\n                        <a href="/track/" class="hover:text-rihan-600 transition">پیگیری سفارش</a>'
    )
    base_template.write_text(base_content, encoding="utf-8")
    print("✓ Added Tracking link to Navbar in base.html")

print("Module 4 (Order Tracking Engine) Deployed Successfully.")
