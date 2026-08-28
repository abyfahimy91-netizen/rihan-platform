"""
D-113: تست‌های داشبوردهای مالی (ادمین و تامین‌کننده) + خروجی CSV
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from src.modules.catalog.models import Category, Supplier, Product, ProductVariant
from src.modules.order import finance
from src.modules.order.models import Order, OrderItem, Shipment
from src.modules.order.fulfillment import build_shipments

User = get_user_model()


class FinanceDashboardTestBase(TestCase):
    @classmethod
    def _server(cls):
        return 'rihan360.ir'

    def setUp(self):
        self.category = Category.objects.create(name='دسته داشبورد', slug='dash-cat')
        self.supplier = Supplier.objects.create(
            title='تامین‌کننده داشبورد', city='تبریز', phone='09148888888')
        self.supplier_user = User.objects.create_user(
            username='09148888888', password='testpass123')
        # D-085: اتصال OneToOne کاربر به تامین‌کننده
        self.supplier.user = self.supplier_user
        self.supplier.save()

        self.product = Product.objects.create(
            name='محصول داشبورد', slug='dash-prod', category=self.category,
            supplier=self.supplier, base_price=Decimal('100000'),
            short_description='x', origin_story='x', status='active')
        self.v1 = ProductVariant.objects.create(
            product=self.product, title='بسته ۵۰۰ گرمی',
            price=Decimal('150000'), cost_price=Decimal('100000'), stock_quantity=10)

        self.staff = User.objects.create_user(
            username='09149999999', password='x', is_staff=True, is_superuser=True)

        self.order = Order.objects.create(
            status=Order.OrderStatus.PAID,
            guest_name='خریدار داشبورد', guest_phone='09141234567',
            guest_postal_code='5151411111', guest_address='تبریز، خیابان تست ۹')
        OrderItem.objects.create(
            order=self.order, product=self.product, variant=self.v1,
            variant_title='بسته ۵۰۰ گرمی', quantity=2,
            unit_price_at_purchase=Decimal('150000'),
            unit_cost_at_purchase=Decimal('100000'),
            product_name_snapshot='محصول داشبورد')
        build_shipments(self.order)

        self.client = Client(SERVER_NAME=self._server())


class AdminDashboardTests(FinanceDashboardTestBase):
    def test_requires_staff(self):
        self.client.force_login(self.supplier_user)
        r = self.client.get('/finance/admin/')
        self.assertEqual(r.status_code, 302)

    def test_shows_totals_and_supplier_row(self):
        self.client.force_login(self.staff)
        r = self.client.get('/finance/admin/')
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('تامین‌کننده داشبورد', content)
        self.assertIn('300000', content)  # فروش اقلام تامین‌کننده

    def test_csv_export(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('finance:export_csv'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
        body = r.content.decode('utf-8-sig')
        self.assertIn('تامین‌کننده داشبورد', body)
        self.assertIn('200000', body)  # بدون هزینه پیش‌پرداخت: ۲۰۰هزار


class SupplierDashboardTests(FinanceDashboardTestBase):
    def test_requires_supplier_link(self):
        stranger = User.objects.create_user(username='09141110000', password='x')
        self.client.force_login(stranger)
        r = self.client.get('/finance/supplier/')
        self.assertEqual(r.status_code, 302)

    def test_supplier_sees_own_balance_only(self):
        self.client.force_login(self.supplier_user)
        r = self.client.get('/finance/supplier/')
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        # قابل دریافت: ۱۰۰هزار × ۲
        self.assertIn('200000', content)
        self.assertIn('در انتظار تسویه', content)

    def test_settled_view_after_settlement(self):
        sup = self.order.shipments.get(supplier=self.supplier)
        finance.settle_shipments([sup], self.staff, note='واریز تستی')
        self.client.force_login(self.supplier_user)
        r = self.client.get('/finance/supplier/')
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('تسویه شد', content)


class SupplierPanelFinanceIntegrationTests(FinanceDashboardTestBase):
    """هزینه‌های ثبت‌شده در فرم ارسال تامین‌کننده باید در قابل پرداخت بیاید"""

    def setUp(self):
        super().setUp()
        from src.modules.rbac.services.role_service import RoleService
        RoleService.create_system_roles()
        RoleService.assign_role(self.supplier_user, 'supplier')

    def test_tracking_form_saves_costs(self):
        from src.modules.supplier_panel.forms import TrackingCodeForm
        sup = self.order.shipments.get(supplier=self.supplier)
        form = TrackingCodeForm(data={
            'carrier': 'POST',
            'tracking_code': '12345678901234567890',
            'post_cost': '95000',
            'other_costs': '15000',
            'other_costs_note': 'کارتن و برچسب',
        })
        self.assertTrue(form.is_valid(), form.errors)
        sup.post_cost = form.cleaned_data['post_cost']
        sup.other_costs = form.cleaned_data['other_costs']
        sup.other_costs_note = form.cleaned_data['other_costs_note']
        sup.post_paid_by = Shipment.CostBearer.SUPPLIER
        sup.other_paid_by = Shipment.CostBearer.SUPPLIER
        sup.save()
        sup.refresh_from_db()
        self.assertEqual(sup.supplier_payable, Decimal('310000'))

    def test_shipment_list_shows_settlement_column(self):
        self.client.force_login(self.supplier_user)
        r = self.client.get('/supplier/shipments/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('تسویه', r.content.decode())
