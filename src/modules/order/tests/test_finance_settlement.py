"""
D-113: تست‌های مالی — بهای تمام‌شده، حاشیه سود و تسویه تامین‌کننده

پوشش:
- snapshot قیمت خرید در لحظه چک‌اوت (CheckoutService.create_order)
- محاسبه قابل پرداخت تامین‌کننده (خرید + پیش‌پرداخت‌های او؛ نه هزینه‌های ریهان)
- تسویه گروهی مرسوله‌ها با snapshot مبلغ + وضعیت تجمعی سفارش (NONE/PENDING/PARTIAL/SETTLED)
- بازکردن تسویه
- گزارش مالی تامین‌کننده (فروش / قابل پرداخت / تسویه‌شده / مانده)
- نمای کلی ادمین (فروش، بهای تمام‌شده، سود، حاشیه)
- مرسوله لغوشده از تسویه و گزارش خارج است
"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from src.modules.catalog.models import Category, Supplier, Product, ProductVariant
from src.modules.order import finance
from src.modules.order.models import Order, OrderItem, Shipment
from src.modules.order.fulfillment import build_shipments

User = get_user_model()


class FinanceTestBase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='دسته مالی', slug='fin-cat')
        self.supplier = Supplier.objects.create(
            title='تامین‌کننده مالی', city='تبریز', phone='09143333333')
        self.product = Product.objects.create(
            name='محصول مالی', slug='fin-prod', category=self.category,
            supplier=self.supplier, base_price=Decimal('100000'),
            short_description='x', origin_story='x', status='active')
        self.inhouse = Product.objects.create(
            name='کالای داخلی', slug='fin-inhouse', category=self.category,
            base_price=Decimal('50000'),
            short_description='x', origin_story='x', status='active')

        self.v1 = ProductVariant.objects.create(
            product=self.product, title='بسته ۵۰۰ گرمی',
            price=Decimal('150000'), cost_price=Decimal('100000'), stock_quantity=10)
        self.admin_user = User.objects.create_user(
            username='09140000000', password='x', is_staff=True, is_superuser=True)

        self.order = Order.objects.create(
            status=Order.OrderStatus.PAID,
            guest_name='خریدار مالی', guest_phone='09144444444',
            guest_postal_code='5151411111',
            guest_address='تبریز، خیابان مالی، پلاک ۷',
        )
        # خرید: ۲ عدد از واریانت ۵۰۰گرمی (فروش ۱۵۰هزار × ۲) + ۱ کالای داخلی (۵۰هزار)
        self.item_v = OrderItem.objects.create(
            order=self.order, product=self.product, variant=self.v1,
            variant_title='بسته ۵۰۰ گرمی', quantity=2,
            unit_price_at_purchase=Decimal('150000'),
            unit_cost_at_purchase=Decimal('100000'),
            product_name_snapshot='محصول مالی')
        self.item_in = OrderItem.objects.create(
            order=self.order, product=self.inhouse, quantity=1,
            unit_price_at_purchase=Decimal('50000'),
            product_name_snapshot='کالای داخلی')


class ShipmentPayableTests(FinanceTestBase):
    def _supplier_shipment(self):
        return next(s for s in build_shipments(self.order)
                    if s.fulfiller == Shipment.FulfillerType.SUPPLIER)

    def test_build_shipments_sets_payer_defaults(self):
        sup = self._supplier_shipment()
        rihan = next(s for s in self.order.shipments.all()
                     if s.fulfiller == Shipment.FulfillerType.RIHAN)
        self.assertEqual(sup.post_paid_by, Shipment.CostBearer.SUPPLIER)
        self.assertEqual(rihan.post_paid_by, Shipment.CostBearer.RIHAN)

    def test_payable_is_cost_plus_supplier_advance_only(self):
        sup = self._supplier_shipment()
        # خرید اقلام تامین‌کننده: ۱۰۰هزار × ۲
        self.assertEqual(sup.items_cost, Decimal('200000'))
        # تامین‌کننده پست و بسته‌بندی پرداخت کرده
        sup.post_cost = Decimal('90000')
        sup.other_costs = Decimal('10000')
        sup.save()
        self.assertEqual(sup.supplier_extra_costs, Decimal('100000'))
        self.assertEqual(sup.supplier_payable, Decimal('300000'))

    def test_rihan_paid_costs_not_in_payable(self):
        sup = self._supplier_shipment()
        sup.post_cost = Decimal('90000')
        sup.post_paid_by = Shipment.CostBearer.RIHAN
        sup.other_costs = Decimal('10000')
        sup.other_paid_by = Shipment.CostBearer.RIHAN
        sup.save()
        self.assertEqual(sup.supplier_extra_costs, Decimal('0'))
        self.assertEqual(sup.supplier_payable, Decimal('200000'))
        self.assertEqual(sup.rihan_extra_costs, Decimal('100000'))

    def test_rihan_shipment_not_settleable(self):
        rihan = next(s for s in build_shipments(self.order)
                     if s.fulfiller == Shipment.FulfillerType.RIHAN)
        self.assertFalse(rihan.is_settleable)
        self.assertEqual(rihan.supplier_payable, Decimal('0'))
        settled, skipped = finance.settle_shipments(
            [rihan], self.admin_user)
        self.assertEqual((settled, skipped), (0, 1))


class OrderSettlementStatusTests(FinanceTestBase):
    def test_status_lifecycle(self):
        build_shipments(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.settlement_status, Order.SettlementStatus.PENDING)

        sup = self.order.shipments.get(fulfiller=Shipment.FulfillerType.SUPPLIER)
        sup.post_cost = Decimal('90000')
        sup.save()
        finance.settle_shipments([sup], self.admin_user)

        self.order.refresh_from_db()
        self.assertEqual(self.order.settlement_status, Order.SettlementStatus.SETTLED)

        # snapshot مبلغ: خرید اقلام + پیش‌پرداخت
        sup.refresh_from_db()
        self.assertEqual(sup.settled_amount, Decimal('290000'))
        self.assertEqual(sup.settled_by, self.admin_user)
        self.assertIsNotNone(sup.settled_at)

    def test_partial_settlement_for_multi_supplier(self):
        supplier_b = Supplier.objects.create(
            title='تامین‌کننده ب', city='تهران', phone='09125555555')
        prod_b = Product.objects.create(
            name='محصول ب', slug='fin-prod-b', category=self.category,
            supplier=supplier_b, base_price=Decimal('80000'),
            short_description='x', origin_story='x', status='active')
        OrderItem.objects.create(
            order=self.order, product=prod_b, quantity=1,
            unit_price_at_purchase=Decimal('120000'),
            unit_cost_at_purchase=Decimal('80000'),
            product_name_snapshot='محصول ب')

        build_shipments(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.settlement_status, Order.SettlementStatus.PENDING)

        a = self.order.shipments.get(supplier=self.supplier)
        finance.settle_shipments([a], self.admin_user)
        self.order.refresh_from_db()
        self.assertEqual(self.order.settlement_status, Order.SettlementStatus.PARTIAL)

        b = self.order.shipments.get(supplier=supplier_b)
        finance.settle_shipments([b], self.admin_user)
        self.order.refresh_from_db()
        self.assertEqual(self.order.settlement_status, Order.SettlementStatus.SETTLED)

    def test_rihan_only_order_is_none(self):
        solo = Order.objects.create(
            status=Order.OrderStatus.PAID,
            guest_name='خریدار داخلی', guest_phone='09146666666',
            guest_postal_code='5151411111', guest_address='تبریز، محل داخلی')
        OrderItem.objects.create(
            order=solo, product=self.inhouse, quantity=1,
            unit_price_at_purchase=Decimal('50000'),
            product_name_snapshot='کالای داخلی')
        build_shipments(solo)
        solo.refresh_from_db()
        self.assertEqual(solo.settlement_status, Order.SettlementStatus.NONE)

    def test_canceled_shipment_excluded(self):
        build_shipments(self.order)
        sup = self.order.shipments.get(fulfiller=Shipment.FulfillerType.SUPPLIER)
        sup.status = Shipment.Status.CANCELED
        sup.save()
        self.order.refresh_from_db()
        self.assertEqual(self.order.settlement_status, Order.SettlementStatus.NONE)


class ReopenSettlementTests(FinanceTestBase):
    def test_reopen_clears_snapshot(self):
        build_shipments(self.order)
        sup = self.order.shipments.get(fulfiller=Shipment.FulfillerType.SUPPLIER)
        finance.settle_shipments([sup], self.admin_user, note='واریز اول')
        reopened, skipped = finance.reopen_shipments([sup], self.admin_user, note='مرجوعی شد')
        self.assertEqual((reopened, skipped), (1, 0))
        sup.refresh_from_db()
        self.assertEqual(sup.settlement_status, Shipment.SettlementStatus.UNSETTLED)
        self.assertIsNone(sup.settled_amount)
        self.assertIsNone(sup.settled_at)
        self.order.refresh_from_db()
        self.assertEqual(self.order.settlement_status, Order.SettlementStatus.PENDING)


class FinanceReportsTests(FinanceTestBase):
    def test_order_financials(self):
        build_shipments(self.order)
        sup = self.order.shipments.get(fulfiller=Shipment.FulfillerType.SUPPLIER)
        sup.post_cost = Decimal('90000')  # پرداختی تامین‌کننده
        sup.save()
        rihan_shipment = self.order.shipments.get(fulfiller=Shipment.FulfillerType.RIHAN)
        rihan_shipment.post_cost = Decimal('30000')  # پرداختی ریهان
        rihan_shipment.save()

        f = finance.order_financials(self.order)
        # فروش: ۳۰۰ + ۵۰
        self.assertEqual(f['revenue'], Decimal('350000'))
        # بهای تمام‌شده: ۲۰۰ (خرید) + ۹۰ + ۳۰ (پست) = ۳۲۰
        self.assertEqual(f['landed_cost'], Decimal('320000'))
        self.assertEqual(f['profit'], Decimal('30000'))
        self.assertAlmostEqual(float(f['margin_percent']), 8.6, places=1)

    def test_supplier_financials_report(self):
        build_shipments(self.order)
        sup = self.order.shipments.get(supplier=self.supplier)
        sup.post_cost = Decimal('90000')
        sup.save()
        rep = finance.supplier_financials(self.supplier)
        # فروش اقلام او: ۱۵۰ × ۲
        self.assertEqual(rep['sold_total'], Decimal('300000'))
        self.assertEqual(rep['payable_total'], Decimal('290000'))
        self.assertEqual(rep['unsettled_total'], Decimal('290000'))
        self.assertEqual(rep['balance'], Decimal('290000'))

        finance.settle_shipments([sup], self.admin_user)
        rep = finance.supplier_financials(self.supplier)
        self.assertEqual(rep['settled_total'], Decimal('290000'))
        self.assertEqual(rep['balance'], Decimal('0'))

    def test_admin_overview_totals(self):
        build_shipments(self.order)
        f = finance.admin_overview()
        self.assertEqual(f['revenue'], Decimal('350000'))
        self.assertEqual(f['items_cost'], Decimal('200000'))
        self.assertEqual(f['profit'], Decimal('150000'))
        row = next(r for r in f['supplier_rows'] if r['supplier'] == self.supplier)
        self.assertEqual(row['payable_total'], Decimal('200000'))


class CheckoutCostSnapshotTests(FinanceTestBase):
    def test_create_order_snapshots_cost(self):
        """چک‌اوت باید قیمت خرید واریانت را در سفارش کپی کند"""
        from unittest.mock import patch
        from src.modules.order.checkout_service import CheckoutService

        # سبد با واریانت
        from src.modules.order.models import Cart, CartItem
        cart = Cart.objects.create()
        CartItem.objects.create(
            cart=cart, product=self.product, variant=self.v1,
            quantity=2, unit_price_at_add=Decimal('150000'))

        guest = {
            'name': 'خریدار سبد', 'phone': '09147777777',
            'address': 'تبریز، خیابان سبد، پلاک ۳', 'postal_code': '5151411111',
            'shipping_cost': 0,
        }
        # رزرو موجودی را ماک می‌کنیم تا تست به انبار وابسته نباشد؟ نه — سرویس واقعی را صدا می‌زنیم
        order = CheckoutService.create_order(cart, guest_info=guest)
        item = order.items.first()
        self.assertIsNotNone(item.unit_cost_at_purchase)
        self.assertEqual(item.unit_cost_at_purchase, Decimal('100000'))
