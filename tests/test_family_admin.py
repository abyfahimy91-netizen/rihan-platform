from django.test import TestCase, Client
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
