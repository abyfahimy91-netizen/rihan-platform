from django.test import TestCase, Client
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
