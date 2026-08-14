import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

# Update src/apps/catalog/models.py to add Supplier model and supplier FK to Product
models_file = BASE / "src/apps/catalog/models.py"
models_text = models_file.read_text(encoding="utf-8")

supplier_model_code = """
from django.conf import settings

class Supplier(models.Model):
    \"\"\"مدل تأمین‌کننده محلی و بومی (M4 - Persona 7: Mola)\"\"\"
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supplier_profile', verbose_name="حساب کاربری")
    title = models.CharField(max_length=150, verbose_name="نام کارگاه / تأمین‌کننده")
    contact_name = models.CharField(max_length=100, verbose_name="نام مسئول")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    city = models.CharField(max_length=100, verbose_name="شهر / منطقه")
    address = models.TextField(blank=True, verbose_name="نشانی کارگاه / مزرعه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")

    class Meta:
        verbose_name = "تأمین‌کننده"
        verbose_name_plural = "تأمین‌کنندگان"
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.city})"
"""

if "class Supplier" not in models_text:
    models_text = supplier_model_code + "\n" + models_text
    # Add supplier to Product
    models_text = models_text.replace(
        "class Product(models.Model):",
        "class Product(models.Model):\n    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='تأمین‌کننده')\n    supply_cost = models.PositiveBigIntegerField(default=0, verbose_name='قیمت خرید از تأمین‌کننده (تومان)')"
    )
    models_file.write_text(models_text, encoding="utf-8")
    print("✓ Added Supplier model and Product.supplier FK to catalog/models.py")

# Update src/apps/catalog/admin.py
admin_file = BASE / "src/apps/catalog/admin.py"
admin_text = admin_file.read_text(encoding="utf-8")
if "Supplier" not in admin_text:
    admin_text = admin_text.replace(
        "from .models import Category, Product, ProductImage, ContentBlock, ProductBlock",
        "from .models import Category, Product, ProductImage, ContentBlock, ProductBlock, Supplier"
    )
    supplier_admin = """

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['title', 'contact_name', 'phone', 'city', 'is_active', 'created_at']
    search_fields = ['title', 'contact_name', 'phone', 'city']
"""
    admin_text += supplier_admin
    admin_file.write_text(admin_text, encoding="utf-8")
    print("✓ Registered Supplier in catalog admin.py")

# Update views in apps/catalog to add Supplier Dashboard
views_file = BASE / "src/apps/catalog/views.py"
views_text = views_file.read_text(encoding="utf-8")
supplier_views_code = """
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.orders.models import OrderItem

@login_required
def supplier_dashboard_view(request):
    \"\"\"داشبورد اختصاصی تأمین‌کننده با تفکیک کامل دسترسی (M4 - D-051)\"\"\"
    if not hasattr(request.user, 'supplier_profile') and not request.user.is_superuser:
        raise PermissionDenied("دسترسی فقط برای تأمین‌کنندگان مجاز ریهان امکان‌پذیر است.")

    supplier = getattr(request.user, 'supplier_profile', None)
    if not supplier and request.user.is_superuser:
        # اگر ادمین اصلی خواست پنل را ببیند
        from .models import Supplier
        supplier = Supplier.objects.first()

    if supplier:
        items = OrderItem.objects.filter(product__supplier=supplier).select_related('order', 'product').order_by('-order__created_at')
        products = supplier.products.all()
    else:
        items = []
        products = []

    context = {
        'supplier': supplier,
        'order_items': items,
        'products': products
    }
    return render(request, 'catalog/supplier_dashboard.html', context)

@require_POST
@login_required
def supplier_update_tracking_view(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    supplier = getattr(request.user, 'supplier_profile', None)
    
    if not request.user.is_superuser and item.product.supplier != supplier:
        raise PermissionDenied()

    tracking_code = request.POST.get('tracking_code', '').strip()
    if tracking_code:
        order = item.order
        order.tracking_code = tracking_code
        order.status = 'shipped'
        order.save()
        messages.success(request, f"کد رهگیری برای سفارش {order.order_number} با موفقیت ثبت شد.")

    return redirect('supplier_dashboard')
"""
if "def supplier_dashboard_view" not in views_text:
    views_text += supplier_views_code
    views_file.write_text(views_text, encoding="utf-8")
    print("✓ Added supplier views to catalog/views.py")

# Update catalog/urls.py
urls_file = BASE / "src/apps/catalog/urls.py"
urls_text = urls_file.read_text(encoding="utf-8")
if "supplier_dashboard" not in urls_text:
    urls_text = urls_text.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('supplier/dashboard/', views.supplier_dashboard_view, name='supplier_dashboard'),\n    path('supplier/item/<int:item_id>/tracking/', views.supplier_update_tracking_view, name='supplier_update_tracking'),"
    )
    urls_file.write_text(urls_text, encoding="utf-8")
    print("✓ Added supplier routes to catalog/urls.py")

# Create Template: src/templates/catalog/supplier_dashboard.html
template_file = BASE / "src/templates/catalog/supplier_dashboard.html"
template_content = """{% extends 'base.html' %}
{% block title %}داشبورد اختصاصی تأمین‌کننده | ریهان{% endblock %}
{% block content %}
<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
    
    <div class="flex flex-wrap justify-between items-center mb-8 border-b border-gray-100 pb-4 gap-4">
        <div>
            <span class="text-xs text-rihan-gold font-bold uppercase tracking-wider">پنل اختصاصی همکاران تأمین</span>
            <h1 class="text-2xl font-black text-rihan-900 mt-1">{{ supplier.title }}</h1>
            <p class="text-xs text-gray-500 mt-0.5">مسئول محترم: <strong>{{ supplier.contact_name }}</strong> ({{ supplier.city }})</p>
        </div>
        <a href="{% url 'logout' %}" class="text-xs text-red-600 bg-red-50 hover:bg-red-100 px-4 py-2 rounded-xl font-semibold transition border border-red-100">
            خروج از پنل
        </a>
    </div>

    {% if messages %}
    <div class="mb-6 space-y-2">
        {% for message in messages %}
        <div class="p-3.5 rounded-2xl text-xs {% if message.tags == 'success' %}bg-green-50 text-green-800 border border-green-200{% else %}bg-red-50 text-red-800 border border-red-200{% endif %}">
            {{ message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Order Items for this Supplier (2 Cols) -->
        <div class="lg:col-span-2 bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm">
            <h2 class="text-base font-bold text-gray-900 mb-4">سفارش‌های نیازمند آماده‌سازی و ارسال</h2>
            <p class="text-xs text-gray-500 mb-6 leading-relaxed">فهرست اقلامی که خریداران سفارش داده‌اند. لطفاً پس از بسته‌بندی فاخر و تحویل به پست/تیپاکس، کد رهگیری را ثبت فرمایید.</p>

            {% if order_items %}
            <div class="space-y-6">
                {% for item in order_items %}
                <div class="border border-gray-100 rounded-2xl p-5 bg-gray-50 space-y-4">
                    <div class="flex flex-wrap justify-between items-center border-b border-gray-200 pb-3 gap-2">
                        <div>
                            <span class="text-xs text-gray-400">شماره سفارش:</span>
                            <span class="text-xs font-bold text-rihan-900 font-mono">{{ item.order.order_number }}</span>
                        </div>
                        <span class="text-xs px-3 py-1 rounded-full font-bold bg-white border border-gray-200">
                            {{ item.order.get_status_display }}
                        </span>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700">
                        <div>
                            <span class="text-gray-400 block">کالای درخواستی:</span>
                            <strong class="text-sm text-gray-900">{{ item.product_title }}</strong>
                            <span class="block text-rihan-gold font-bold mt-0.5">تعداد: {{ item.quantity }} عدد</span>
                        </div>
                        <div>
                            <span class="text-gray-400 block">تحویل‌گیرنده:</span>
                            <strong class="text-gray-900">{{ item.order.customer_name }}</strong> ({{ item.order.customer_phone }})
                        </div>
                    </div>

                    <div class="bg-white p-3.5 rounded-xl border border-gray-200 text-xs text-gray-700">
                        <strong class="text-gray-900 block mb-1">نشانی مقصد خریدار:</strong>
                        {{ item.order.province }}، {{ item.order.city }}، {{ item.order.shipping_address }} (کد پستی: {{ item.order.postal_code }})
                        {% if item.order.customer_notes %}
                        <p class="text-amber-800 text-[11px] mt-1">یادداشت: {{ item.order.customer_notes }}</p>
                        {% endif %}
                    </div>

                    <!-- Tracking Submission Form -->
                    <form method="post" action="{% url 'supplier_update_tracking' item_id=item.id %}" class="flex gap-2 pt-1">
                        {% csrf_token %}
                        <input type="text" name="tracking_code" value="{{ item.order.tracking_code }}" required 
                               class="flex-1 bg-white border border-gray-300 rounded-xl px-3 py-2 text-xs text-gray-900 font-mono focus:outline-none focus:border-rihan-gold" 
                               placeholder="کد رهگیری مرسوله پستی / تیپاکس">
                        <button type="submit" class="bg-rihan-900 hover:bg-rihan-800 text-white text-xs font-bold px-4 py-2 rounded-xl transition shadow-sm">
                            ثبت کد رهگیری ↗
                        </button>
                    </form>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="text-center py-12">
                <span class="text-4xl block mb-2 text-gray-300">📦</span>
                <p class="text-xs text-gray-500">در حال حاضر سفارش جدیدی برای کالاهای شما در انتظار ارسال نیست.</p>
            </div>
            {% endif %}
        </div>

        <!-- Supplier Products & Inventory (1 Col) -->
        <div class="bg-white rounded-3xl border border-gray-100 p-6 shadow-sm h-fit space-y-4">
            <h3 class="text-sm font-bold text-gray-900 border-b border-gray-100 pb-3">کالاهای ثبت‌شده شما</h3>
            <p class="text-[11px] text-gray-500">فهرست اقلامی که تحت نام و اصالت کارگاه شما در ریهان عرضه می‌شود:</p>

            <div class="space-y-3">
                {% for prod in products %}
                <div class="bg-gray-50 p-3.5 rounded-xl border border-gray-100 text-xs flex justify-between items-center">
                    <div>
                        <strong class="text-gray-900 block">{{ prod.title }}</strong>
                        <span class="text-[10px] text-gray-400 font-mono">SKU: {{ prod.sku }}</span>
                    </div>
                    <div class="text-left">
                        <span class="text-xs font-bold text-gray-800 block">موجودی: {{ prod.stock }}</span>
                        <span class="text-[10px] text-green-700">✓ فعال در کاتالوگ</span>
                    </div>
                </div>
                {% empty %}
                <p class="text-xs text-gray-400 text-center py-4">هنوز محصولی منتسب نشده است.</p>
                {% endfor %}
            </div>
        </div>

    </div>
</div>
{% endblock %}
"""
template_file.write_text(template_content, encoding="utf-8")
print("✓ Created src/templates/catalog/supplier_dashboard.html")

# Create Unit Tests: tests/test_suppliers.py
test_file = BASE / "tests/test_suppliers.py"
test_code = """from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.catalog.models import Category, Product, Supplier
from apps.orders.models import Order, OrderItem

User = get_user_model()

class SupplierModuleTestCase(TestCase):
    def setUp(self):
        self.supplier_user = User.objects.create_user(username='09149998877', password='SupplierPass1405!')
        self.supplier = Supplier.objects.create(
            user=self.supplier_user,
            title="کارگاه خشکبار هوراند (مولا)",
            contact_name="مولا",
            phone="09149998877",
            city="هوراند"
        )
        self.cat = Category.objects.create(name="خشکبار", slug="dry-fruits")
        self.p1 = Product.objects.create(
            category=self.cat, supplier=self.supplier, title="سماق سرخ هوراند",
            slug="red-somagh", sku="RIHAN-SM-RED", summary="سماق اصل",
            price=280000, supply_cost=200000, stock=30
        )
        self.order = Order.objects.create(
            customer_name="مریم کارمند",
            customer_phone="09121112233",
            shipping_address="تبریز، خیابان آزادی",
            postal_code="5123456789",
            items_total=280000,
            grand_total=280000,
            status='confirmed'
        )
        self.item = OrderItem.objects.create(
            order=self.order, product=self.p1, product_title=self.p1.title,
            product_sku=self.p1.sku, unit_price=280000, quantity=1, subtotal=280000
        )

    def test_supplier_dashboard_and_data_isolation(self):
        c = Client()
        # Unauthorized access blocked
        res_guest = c.get(reverse('supplier_dashboard'))
        self.assertEqual(res_guest.status_code, 302)

        # Supplier logs in and sees his items
        c.force_login(self.supplier_user)
        res_supplier = c.get(reverse('supplier_dashboard'))
        self.assertEqual(res_supplier.status_code, 200)
        self.assertContains(res_supplier, "سماق سرخ هوراند")
        self.assertContains(res_supplier, "مریم کارمند")
        self.assertContains(res_supplier, "تبریز، خیابان آزادی")

    def test_supplier_tracking_update(self):
        c = Client()
        c.force_login(self.supplier_user)
        res = c.post(reverse('supplier_update_tracking', args=[self.item.id]), {
            'tracking_code': 'TIPAX-HURAND-1002'
        })
        self.assertEqual(res.status_code, 302)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.tracking_code, 'TIPAX-HURAND-1002')
        self.assertEqual(self.order.status, 'shipped')
"""
test_file.write_text(test_code, encoding="utf-8")
print("✓ Created tests/test_suppliers.py")

print("All Module M4 Files Deployed.")
