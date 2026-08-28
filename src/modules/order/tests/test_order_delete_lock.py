# -*- coding: utf-8 -*-
"""D-112 — ممنوعیت حذف سفارش در ادمین

حذف سفارش/قلم سفارش رزرو موجودی را آزاد نمی‌کند → کالا برای همیشه قفل می‌شود
(فاجعه اینماد: رزرو نشتی باعث «موجودی کافی ولی خرید ناممکن»). سوابق مالی هم
یتیم می‌شوند. لغو فقط از مسیر سرویس (cancel_order) یا انقضای خودکار.
"""
from django.contrib import admin
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse

from src.modules.catalog.models import Category, Supplier, Product, ProductVariant, Inventory
from src.modules.order.admin import OrderAdmin, OrderItemInline
from src.modules.order.models import Order, OrderItem

User = get_user_model()
HOST = 'rihan360.ir'


class OrderDeleteLockTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('qa_admin', 'qa@x.ir', 'x1234567')
        cls.cat = Category.objects.create(name='cat', slug='cat')
        cls.sup = Supplier.objects.create(title='تامین‌کننده تست', city='تهران')
        from decimal import Decimal
        cls.p = Product.objects.create(
            category=cls.cat, supplier=cls.sup, name='محصول تست',
            slug='test-lock', unit='number',
            base_price=Decimal('10000'), margin_percent=Decimal('10'),
            short_description='تست')
        ProductVariant.objects.create(product=cls.p, title='واریانت', price=Decimal('12000'),
                                      stock_quantity=5)
        inv, _ = Inventory.objects.get_or_create(product=cls.p)
        inv.quantity = 5
        inv.save(update_fields=['quantity'])
        cls.user = User.objects.create_user(username='09990000009')
        cls.order = Order.objects.create(user=cls.user, order_number='RH-QA-LOCK',
                                         status=Order.OrderStatus.PENDING)
        OrderItem.objects.create(order=cls.order, product=cls.p,
                                 product_name_snapshot='محصول تست', quantity=1,
                                 unit_price_at_purchase=10000)

    def setUp(self):
        self.rf = RequestFactory()
        self.req = self.rf.get('/')
        self.req.user = self.superuser
        self.oa = OrderAdmin(Order, admin.site)

    def test_order_delete_permission_denied(self):
        self.assertFalse(self.oa.has_delete_permission(self.req))
        self.assertFalse(self.oa.has_delete_permission(self.req, self.order))

    def test_item_inline_delete_denied(self):
        self.assertFalse(OrderItemInline(OrderItem, admin.site).can_delete)

    def test_admin_delete_url_blocked(self):
        self.client.force_login(self.superuser)
        url = reverse('admin:order_order_delete', args=[self.order.pk])
        r = self.client.get(url, HTTP_HOST=HOST)
        self.assertEqual(r.status_code, 403)

    def test_order_still_exists_after_blocked_delete(self):
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())
