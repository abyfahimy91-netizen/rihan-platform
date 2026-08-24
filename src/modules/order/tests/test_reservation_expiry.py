"""
D-099: تست‌های مهلت رزرو سفارش پرداخت‌نشده و لغو توسط مشتری

پوشش:
- ست‌شدن expires_at هنگام ثبت سفارش
- آزادسازی خودکار سفارش منقضی (release_expired_orders)
- دست‌نخوردن سفارش فعال
- ویوی لغو: مالک، غیرمالک، سفارش پرداخت‌شده، سفارش با رسید ثبت‌شده
"""
from decimal import Decimal
from datetime import timedelta
from unittest.mock import Mock

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from src.modules.catalog.models import Category, Supplier, Product, Inventory
from src.modules.order.models import Cart, Order, Payment, OrderStatusHistory
from src.modules.order.services import get_or_create_cart, add_to_cart
from src.modules.order.checkout_service import CheckoutService
from src.modules.order.expiry import release_expired_orders

User = get_user_model()


class ReservationExpiryTest(TestCase):
    """مهلت رزرو موجودی و آزادسازی خودکار (D-099)"""

    def setUp(self):
        self.customer = User.objects.create_user(
            username='09120000001',
            password='test123456',
        )
        self.other = User.objects.create_user(
            username='09120000002',
            password='test123456',
        )
        self.category = Category.objects.create(name='تست دسته', slug='test-cat-exp')
        self.supplier = Supplier.objects.create(title='تست تامین', city='تست')
        self.product = Product.objects.create(
            name='محصول تست رزرو',
            slug='test-reserve-product',
            category=self.category,
            supplier=self.supplier,
            unit='عدد',
            base_price=Decimal('100000'),
            shipping_cost=Decimal('0'),
            margin_percent=10,
            short_description='تست',
            origin_story='تست',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        self.inventory, _ = Inventory.objects.get_or_create(
            product=self.product,
            defaults={'quantity': Decimal('10'), 'reserved_quantity': Decimal('0'), 'unit': 'عدد'},
        )
        self.inventory.quantity = Decimal('10')
        self.inventory.reserved_quantity = Decimal('0')
        self.inventory.save()

    def _create_order(self, user=None, quantity=2):
        request = Mock()
        request.user = user
        request.session = Mock()
        request.session.session_key = f'test-{timezone.now().timestamp()}'
        cart = get_or_create_cart(request)
        add_to_cart(cart, str(self.product.id), quantity=quantity)
        return CheckoutService.create_order(
            cart=cart,
            guest_info={
                'name': 'مشتری تست',
                'phone': '09121234567',
                'address': 'تهران، خیابان تست، پلاک ۱۰',
                'postal_code': '1234567890',
            },
            user=user,
        )

    # ── ایجاد سفارش ──

    def test_create_order_sets_expiry(self):
        """ثبت سفارش باید مهلت رزرو (~۶۰ دقیقه) ست کند"""
        order = self._create_order(user=self.customer)
        self.assertIsNotNone(order.expires_at)
        remaining = order.remaining_seconds
        self.assertGreater(remaining, 55 * 60)
        self.assertLessEqual(remaining, 60 * 60)
        self.assertTrue(order.is_payable)
        self.assertFalse(order.is_reservation_expired)

    # ── آزادسازی خودکار ──

    def test_expired_order_auto_released(self):
        """سفارش منقضی: لغو خودکار + آزاد شدن رزرو + ثبت تاریخچه"""
        order = self._create_order(user=self.customer)
        Order.objects.filter(pk=order.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        order.refresh_from_db()

        cancelled = release_expired_orders()

        self.assertIn(order.order_number, cancelled)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.CANCELLED)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, Decimal('0'))

        self.assertTrue(order.status_history.filter(
            status=OrderStatusHistory.HistoryStatus.CANCELLED
        ).exists())

    def test_active_order_not_released(self):
        """سفارش داخل مهلت نباید لغو شود"""
        order = self._create_order(user=self.customer)
        cancelled = release_expired_orders()
        self.assertNotIn(order.order_number, cancelled)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.PENDING)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, Decimal('2'))

    def test_paid_order_not_released(self):
        """سفارش پرداخت‌شده حتی با expires_at گذشته نباید لغو شود"""
        order = self._create_order(user=self.customer)
        Order.objects.filter(pk=order.pk).update(
            status=Order.OrderStatus.PAID,
            expires_at=timezone.now() - timedelta(minutes=30),
        )
        cancelled = release_expired_orders()
        self.assertNotIn(order.order_number, cancelled)


class CancelOrderViewTest(TestCase):
    """لغو سفارش پرداخت‌نشده توسط مشتری (D-099)"""

    def setUp(self):
        self.customer = User.objects.create_user(username='09120000003', password='test123456')
        self.other = User.objects.create_user(username='09120000004', password='test123456')
        self.category = Category.objects.create(name='تست دسته ۲', slug='test-cat-cancel')
        self.supplier = Supplier.objects.create(title='تست تامین ۲', city='تست')
        self.product = Product.objects.create(
            name='محصول تست لغو',
            slug='test-cancel-product',
            category=self.category,
            supplier=self.supplier,
            unit='عدد',
            base_price=Decimal('50000'),
            shipping_cost=Decimal('0'),
            margin_percent=10,
            short_description='تست',
            origin_story='تست',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        self.inventory, _ = Inventory.objects.get_or_create(
            product=self.product,
            defaults={'quantity': Decimal('10'), 'reserved_quantity': Decimal('0'), 'unit': 'عدد'},
        )
        self.inventory.quantity = Decimal('10')
        self.inventory.reserved_quantity = Decimal('0')
        self.inventory.save()
        self.client = Client()

    def _login_and_create(self):
        self.client.force_login(self.customer)
        request = Mock()
        request.user = self.customer
        request.session = Mock()
        request.session.session_key = f'test-{timezone.now().timestamp()}'
        cart = get_or_create_cart(request)
        add_to_cart(cart, str(self.product.id), quantity=1)
        return CheckoutService.create_order(
            cart=cart,
            guest_info={'name': 'مشتری', 'phone': '09121234567',
                        'address': 'تهران، خیابان تست، پلاک ۲', 'postal_code': '1234567890'},
            user=self.customer,
        )

    def test_owner_can_cancel_pending_order(self):
        """مالک سفارش PENDING می‌تواند لغو کند؛ موجودی آزاد می‌شود"""
        order = self._login_and_create()
        response = self.client.post(
            f'/order/payment/{order.order_number}/cancel/',
            {'next': '/accounts/profile/'},
        )
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.CANCELLED)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, Decimal('0'))

    def test_non_owner_cannot_cancel(self):
        """کاربر دیگر اجازه لغو سفارش دیگری را ندارد"""
        order = self._login_and_create()
        self.client.force_login(self.other)
        response = self.client.post(f'/order/payment/{order.order_number}/cancel/')
        self.assertEqual(response.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.PENDING)

    def test_cannot_cancel_paid_order(self):
        """سفارش پرداخت‌شده قابل لغو توسط مشتری نیست"""
        order = self._login_and_create()
        Order.objects.filter(pk=order.pk).update(status=Order.OrderStatus.PAID)
        response = self.client.post(f'/order/payment/{order.order_number}/cancel/')
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.PAID)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, Decimal('1'))

    def test_cannot_cancel_after_evidence_submitted(self):
        """بعد از ثبت رسید (PENDING_REVIEW) لغو مستقیم مسدود است"""
        order = self._login_and_create()
        Payment.objects.create(
            order=order,
            amount=order.total_price,
            gateway=Payment.PaymentGateway.MANUAL,
            status=Payment.PaymentStatus.PENDING_REVIEW,
            sender_card_last4='1234',
        )
        response = self.client.post(f'/order/payment/{order.order_number}/cancel/')
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.PENDING)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, Decimal('1'))

    def test_get_not_allowed(self):
        """لغو فقط با POST"""
        order = self._login_and_create()
        response = self.client.get(f'/order/payment/{order.order_number}/cancel/')
        self.assertEqual(response.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.OrderStatus.PENDING)
