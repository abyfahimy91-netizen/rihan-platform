from django.test import TestCase, Client
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
