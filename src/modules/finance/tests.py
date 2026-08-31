"""D-123: UX داشبورد مالی — اعداد فارسی، بدون اعشار خام، جدول داخل کادر."""
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from src.modules.catalog.models import Category, Product, Supplier
from src.modules.order.models import Order, OrderItem, Shipment
from src.modules.order.fulfillment import build_shipments

User = get_user_model()


class FinanceDashboardTestBase(TestCase):
    """سفارش تحویل‌شده با مرسوله تامین‌کننده: خرید ۹۵۰٬۰۰۰×۲ + پست ۴۵٬۰۰۰"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='09127777001', password='Xtest12345', is_staff=True)
        self.supplier = Supplier.objects.create(
            title='تامین‌کننده مالی تست', city='تبریز', phone='09127777002')
        cat = Category.objects.create(name='cat-fin', slug='cat-fin')
        self.product = Product.objects.create(
            name='محصول مالی', slug='fin-prod', category=cat, supplier=self.supplier,
            base_price=Decimal('1500000'), final_price=Decimal('1500000'),
            short_description='x', origin_story='x', status='active')
        self.order = Order.objects.create(
            user=self.admin, status=Order.OrderStatus.DELIVERED,
            guest_name='خریدار مالی', guest_phone='09127777003',
            guest_postal_code='5151411111',
            guest_address='تبریز، خیابان تست، پلاک ۱')
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2,
            unit_price_at_purchase=Decimal('1500000'),
            unit_cost_at_purchase=Decimal('950000'),
            product_name_snapshot='محصول مالی')
        build_shipments(self.order)
        self.shipment = Shipment.objects.get(order=self.order)
        self.shipment.post_cost = Decimal('45000')
        self.shipment.post_paid_by = Shipment.CostBearer.SUPPLIER
        self.shipment.save()
        self.shipment.status = Shipment.Status.DELIVERED
        self.shipment.save(update_fields=['status'])
        self.client = Client(SERVER_NAME='rihan360.ir')

    def _admin(self):
        c = Client(SERVER_NAME='rihan360.ir')
        c.force_login(self.admin)
        return c


class AdminDashboardRenderTests(FinanceDashboardTestBase):
    def setUp(self):
        super().setUp()
        self.body = self._admin().get('/finance/admin/').content.decode()

    def test_money_in_persian_digits_with_thousands(self):
        # قابل پرداخت = ۹۵۰٬۰۰۰×۲ + ۴۵٬۰۰۰ پست تامین‌کننده
        self.assertIn('۱٬۹۴۵٬۰۰۰', self.body)

    def test_no_raw_english_decimal_amounts(self):
        # هیچ مبلغ خام Decimal (مثل 1945000.00) نباید رندر شود
        self.assertNotIn('.00', self.body)
        self.assertNotIn('1945000', self.body)
        self.assertNotIn('2945000', self.body)

    def test_margin_percent_no_decimal_dump(self):
        # ۱۹۴۵۰۰۰ / ۳۰۰۰۰۰۰ = ۶۴.۸٪ → int → ۶۵٪ نه «64.8»
        self.assertNotIn('64.8', self.body)
        self.assertIn('٪', self.body)

    def test_unsettled_badge_in_fa(self):
        self.assertIn('۱ تسویه‌نشده', self.body)

    def test_table_inside_wrap_and_responsive(self):
        self.assertIn('table-wrap', self.body)
        self.assertIn('rwd-table', self.body)
        self.assertIn('data-label=', self.body)

    def test_debt_note_and_settle_link(self):
        self.assertIn('مانده بدهی', self.body)
        self.assertIn('/admin/order/shipment/', self.body)

    def test_settled_row_shows_full_and_green(self):
        from src.modules.order.finance import settle_shipments
        settle_shipments([self.shipment], self.admin)
        body = self._admin().get('/finance/admin/').content.decode()
        self.assertIn('تسویه کامل', body)


class SupplierDashboardRenderTests(FinanceDashboardTestBase):
    def setUp(self):
        super().setUp()
        self.sup_user = User.objects.create_user(
            username='09127777002', password='Xtest12345')
        self.supplier.user = self.sup_user
        self.supplier.save()
        c = Client(SERVER_NAME='rihan360.ir')
        c.force_login(self.sup_user)
        self.body = c.get('/finance/supplier/').content.decode()

    def test_payable_in_fa_money(self):
        self.assertIn('۱٬۹۴۵٬۰۰۰', self.body)
        self.assertNotIn('.00', self.body)

    def test_order_number_ltr(self):
        self.assertIn('dir="ltr"', self.body)
        self.assertIn(self.order.order_number, self.body)


class FinanceAccessTests(FinanceDashboardTestBase):
    def test_anonymous_redirects_home(self):
        r = Client(SERVER_NAME='rihan360.ir').get('/finance/admin/')
        self.assertEqual(r.status_code, 302)

    def test_non_staff_redirects_home(self):
        u = User.objects.create_user(username='09127777004', password='Xtest12345')
        c = Client(SERVER_NAME='rihan360.ir')
        c.force_login(u)
        r = c.get('/finance/admin/')
        self.assertEqual(r.status_code, 302)

    def test_staff_gets_200(self):
        self.assertEqual(self._admin().get('/finance/admin/').status_code, 200)
