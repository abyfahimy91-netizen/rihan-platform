import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

# Update src/apps/orders/admin.py
admin_content = """from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from .models import Order, OrderItem
from .views import admin_order_invoice_view

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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/invoice/', self.admin_site.admin_view(admin_order_invoice_view), name='order_invoice'),
        ]
        return custom_urls + urls

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
        url = reverse('admin:order_invoice', args=[obj.id])
        return format_html('<a href="{}" target="_blank" style="color: #7c5e38; font-weight: bold;">چاپ فاکتور 🖨️</a>', url)

    @admin.display(description="چاپ فاکتور رسمی")
    def invoice_button(self, obj):
        url = reverse('admin:order_invoice', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank" style="background: #23180c; color: #fff; padding: 6px 14px; border-radius: 8px; text-decoration: none;">مشاهده و چاپ فاکتور بسته 🖨️</a>', url)

    @admin.action(description="تأیید سفارش‌های انتخاب‌شده (آماده‌سازی بسته)")
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, "سفارش‌های انتخاب‌شده با موفقیت تأیید شدند.")

    @admin.action(description="تغییر وضعیت به ارسال‌شده")
    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, "وضعیت سفارش‌های انتخاب‌شده به ارسال‌شده تغییر یافت.")
"""
(BASE / "src/apps/orders/admin.py").write_text(admin_content, encoding="utf-8")

# Update tests/test_family_admin.py
test_content = """from django.test import TestCase, Client
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
        # Guest redirected to admin login
        res_guest = c.get(reverse('admin:order_invoice', args=[self.order.id]))
        self.assertEqual(res_guest.status_code, 302)

        # Admin accesses printable invoice (200 OK)
        c.force_login(self.admin_user)
        res_admin = c.get(reverse('admin:order_invoice', args=[self.order.id]))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, "سماق هوراند")
        self.assertContains(res_admin, "مریم کارمند")
        self.assertContains(res_admin, self.order.order_number)
"""
(BASE / "tests/test_family_admin.py").write_text(test_content, encoding="utf-8")

print("✓ Native Admin get_urls integration completed.")
