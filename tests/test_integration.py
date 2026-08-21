"""
Integration Test - Full Purchase Flow
US-059: قیف فروش مرحله به مرحله

Flow:
    ساخت محصول -> ایجاد سفارش -> پرداخت -> تأیید ادمین ->
    تحویل -> ثبت خودکار تراکنش مالی (Signal M6)
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from src.modules.catalog.models import Supplier, Product, Category
from src.modules.order.models import Order, OrderItem, Payment
from src.modules.finance.models import SupplierLedger, SupplierTransaction


class FullFlowIntegrationTest(TestCase):
    """تست جریان کامل خرید: از سفارش تا ثبت مالی"""

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

    def test_full_purchase_flow(self):
        """
        Flow کامل:
        1. ایجاد سفارش DRAFT
        2. ثبت آیتم سفارش
        3. ثبت پرداخت کارت‌به‌کارت
        4. تأیید پرداخت توسط ادمین
        5. تغییر وضعیت به DELIVERED
        6. بررسی ثبت خودکار تراکنش مالی (Signal)
        7. بررسی موجودی تأمین‌کننده
        """
        # Step 1: ایجاد سفارش
        order = Order.objects.create(
            status=Order.OrderStatus.DRAFT,
            guest_name="علی محمدی",
            guest_phone="09121234567",
            guest_address="تهران، خیابان ولیعصر",
            subtotal=Decimal('130000'),
            total_price=Decimal('130000')
        )

        # Step 2: ثبت آیتم
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            unit_price_at_purchase=Decimal('65000'),
            product_name_snapshot="سماق هوراند"
        )

        # Step 3: ثبت پرداخت
        payment = Payment.objects.create(
            order=order,
            amount=Decimal('130000'),
            status=Payment.PaymentStatus.PENDING,
            gateway=Payment.PaymentGateway.MANUAL
        )

        # Step 4: تأیید پرداخت توسط ادمین
        payment.confirm(self.admin, notes="رسید تأیید شد")
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.SUCCESS)

        # Step 5: تغییر وضعیت به PAID
        order.status = Order.OrderStatus.PAID
        order.save()

        # Step 6: تحویل (trigger signal M6)
        order.status = Order.OrderStatus.DELIVERED
        order.save()

        # Step 7: بررسی ثبت تراکنش مالی
        ledger = SupplierLedger.objects.filter(supplier=self.supplier).first()
        self.assertIsNotNone(ledger, "SupplierLedger باید ایجاد شده باشد")

        transaction = SupplierTransaction.objects.filter(
            ledger=ledger,
            order=order
        ).first()
        self.assertIsNotNone(transaction, "SupplierTransaction باید ایجاد شده باشد")
        self.assertEqual(transaction.amount, Decimal('130000'))
        self.assertEqual(
            transaction.transaction_type,
            SupplierTransaction.TransactionType.SALE
        )

        # Step 8: بررسی موجودی
        self.assertEqual(ledger.balance, Decimal('130000'))

    def test_cancelled_order_no_finance(self):
        """سفارش لغو شده نباید تراکنش مالی ایجاد کند"""
        order = Order.objects.create(
            status=Order.OrderStatus.CANCELLED,
            total_price=Decimal('50000')
        )

        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('50000'),
            product_name_snapshot="سماق هوراند"
        )

        # سیگنال نباید برای CANCELLED فعال شود
        count = SupplierTransaction.objects.filter(order=order).count()
        self.assertEqual(count, 0)
