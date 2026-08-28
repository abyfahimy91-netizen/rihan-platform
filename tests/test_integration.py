"""
Integration Test — جریان کامل خرید (بازنویسی D-113)
US-059: قیف فروش مرحله به مرحله

Flow:
    ساخت محصول → ایجاد سفارش → ثبت پرداخت کارت‌به‌کارت → تأیید ادمین
    (CheckoutService.confirm_payment) → PAID→PROCESSING خودکار →
    ساخت مرسوله با تخصیص تامین‌کننده → وضعیت تسویه

نسخه قبلی این فایل به SupplierLedger/SupplierTransaction وابسته بود که در
بازنویسی مالی D-113 حذف شدند؛ منبع حقیقت تسویه الان فیلدهای Shipment است
(دفتر تراکنش موازی دیگر وجود ندارد — مستندات D-113).
"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User

from src.modules.catalog.models import Supplier, Product, Category
from src.modules.order.models import Order, OrderItem, Payment, Shipment
from src.modules.order.checkout_service import CheckoutService


class FullFlowIntegrationTest(TestCase):
    """تست جریان کامل خرید: از سفارش تا مرسوله و وضعیت تسویه تامین‌کننده"""

    def setUp(self):
        # ادمین
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@rihan.ir'
        )

        # دسته‌بندی
        self.category = Category.objects.create(
            name="خشکبار",
            slug="dried-fruits"
        )

        # تأمین‌کننده
        self.supplier = Supplier.objects.create(
            title="تأمین‌کننده هوراند",
            city="هوراند"
        )

        # محصول
        self.product = Product.objects.create(
            name="سماق هوراند",
            slug="somagh-horand",
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('50000'),
            final_price=Decimal('65000'),
            short_description="سماق اعلا",
            origin_story="از کوه‌های هوراند",
            status='active'
        )

    def _make_pending_order(self, status=Order.OrderStatus.PENDING, quantity=2):
        order = Order.objects.create(
            status=status,
            guest_name="علی محمدی",
            guest_phone="09121234567",
            guest_address="تهران، خیابان ولیعصر",
            subtotal=Decimal('130000'),
            total_price=Decimal('130000')
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=quantity,
            unit_price_at_purchase=Decimal('65000'),
            unit_cost_at_purchase=Decimal('50000'),
            product_name_snapshot="سماق هوراند"
        )
        payment = Payment.objects.create(
            order=order,
            amount=Decimal('130000'),
            status=Payment.PaymentStatus.PENDING,
            gateway=Payment.PaymentGateway.MANUAL
        )
        return order, payment

    def test_full_purchase_flow(self):
        """
        Flow کامل:
        1. سفارش PENDING + آیتم + پرداخت کارت‌به‌کارت
        2. تأیید ادمین با CheckoutService.confirm_payment
        3. پرداخت SUCCESS + سفارش PROCESSING خودکار
        4. مرسوله خودکار برای تامین‌کننده محصول ساخته می‌شود (NEW)
        5. وضعیت تسویه سفارش/مرسوله = PENDING (بدهی به تامین‌کننده)
        """
        order, payment = self._make_pending_order()

        order = CheckoutService.confirm_payment(
            order, payment=payment, admin_user=self.admin
        )

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.SUCCESS)
        self.assertEqual(order.status, Order.OrderStatus.PROCESSING)

        # مرسوله خودکار تخصیص تامین‌کننده (D-105)
        shipments = order.shipments.all()
        self.assertEqual(shipments.count(), 1)
        shipment = shipments.first()
        self.assertEqual(shipment.status, Shipment.Status.NEW)
        self.assertEqual(shipment.supplier, self.supplier)

        # تسویه (D-113): بدهی تامین‌کننده = هزینه اقلام (پست پیش‌پرداخت تامین‌کننده اضافه می‌شود)
        self.assertEqual(
            shipment.settlement_status, Shipment.SettlementStatus.UNSETTLED
        )
        self.assertEqual(shipment.items_cost, Decimal('100000'))
        self.assertEqual(shipment.supplier_payable, Decimal('100000'))
        self.assertEqual(
            order.settlement_status, Order.SettlementStatus.PENDING
        )

    def test_cancelled_order_no_shipment(self):
        """سفارش لغوشده هیچ مرسوله/تسویه‌ای نباید داشته باشد"""
        order, _payment = self._make_pending_order(status=Order.OrderStatus.CANCELLED)

        self.assertEqual(order.shipments.count(), 0)
        self.assertEqual(
            order.settlement_status, Order.SettlementStatus.NONE
        )
