"""
FEEDBACK-14050611 — تست‌های بازخورد کاربر
1) افزودن به سبد برگشت + استایل ثانویه
2) پیام جدید منافع ثبت‌نام (نه «لازم نیست» به تنهایی)
3) دکمهٔ ادامه به تسویه نارنجی یکدست در سبد
4) رزرو موجودی: مهلت ۶۰ دقیقه + آزادسازی خودکار (تحقیق وضعیت)
"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, ProductVariant
from src.modules.order.models import Order

HOST = 'rihan360.ir'


def make_product():
    cat = Category.objects.create(name='fb', slug='fb-cat')
    p = Product.objects.create(
        name='محصول فیدبک', slug='fb-prod', category=cat,
        base_price=Decimal('100000'), short_description='t', origin_story='x', status='active')
    ProductVariant.objects.create(product=p, title='۱کیلو', price=Decimal('100000'), stock_quantity=5)
    return p


class RestoredSecondaryCTATests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.c = Client()

    def test_both_buttons_present_variant_buybox(self):
        c = self.c.get('/products/fb-prod/', HTTP_HOST=HOST).content.decode()
        self.assertIn('data-fast-buy', c)
        self.assertRegex(c, r'>\s*افزودن به سبد خرید\s*</button>')

    def test_secondary_button_is_visually_secondary(self):
        c = self.c.get('/products/fb-prod/', HTTP_HOST=HOST).content.decode()
        # استایل جدید: padding کوچک‌تر 13px و حاشیه باریک 1.5px
        self.assertIn('padding: 13px 28px', c)
        self.assertIn('border: 1.5px solid var(--color-border)', c)


class RegistrationMessageTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.c = Client()

    def test_old_message_replaced_everywhere(self):
        self.c.get('/order/cart/', HTTP_HOST=HOST)
        self.c.post('/order/cart/add/', {'product_slug': 'fb-prod', 'quantity': '1'})
        prod = self.c.get('/products/fb-prod/', HTTP_HOST=HOST).content.decode()
        checkout = self.c.get('/order/checkout/', HTTP_HOST=HOST).content.decode()
        for body in (prod, checkout):
            self.assertNotIn('ثبت‌نام لازم نیست', body)
            self.assertIn('با ثبت‌نام، آدرس‌ها ذخیره و سوابق سفارش در پروفایل شما می‌ماند', body)


class CartCheckoutOrangeTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.c = Client()

    def test_cart_checkout_button_orange(self):
        self.c.get('/order/cart/', HTTP_HOST=HOST)
        self.c.post('/order/cart/add/', {'product_slug': 'fb-prod', 'quantity': '1'})
        c = self.c.get('/order/cart/', HTTP_HOST=HOST).content.decode()
        self.assertIn('#E8590C', c)
        self.assertIn('ادامه به تسویه‌حساب', c)


class ReservationSystemTests(TestCase):
    """تحقیق و قفل رفتار رزرو: سفارش PENDING مهلت دارد؛ پس از انقضا خودکار آزاد می‌شود"""

    def setUp(self):
        self.product = make_product()
        self.c = Client()

    def _create_pending_order(self):
        from src.modules.catalog.models import Inventory
        Inventory.objects.get_or_create(
            product=self.product,
            defaults={'quantity': Decimal('5'), 'reserved_quantity': Decimal('0'), 'unit': 'کیلوگرم'})
        self.c.post('/order/cart/add/', {'product_slug': 'fb-prod', 'quantity': '2'})
        r = self.c.post('/order/checkout/', dict(
            name='تست رزرو', phone='09121110000',
            address='تبریز، تست، پلاک ۱', postal_code='5151411111'), HTTP_HOST=HOST)
        return Order.objects.first()

    def test_pending_order_gets_60min_expiry(self):
        from django.utils import timezone
        from datetime import timedelta
        o = self._create_pending_order()
        self.assertEqual(o.status, Order.OrderStatus.PENDING)
        self.assertIsNotNone(o.expires_at)
        diff = o.expires_at - timezone.now()
        self.assertLessEqual(abs(diff - timedelta(minutes=60)), timedelta(seconds=5))

    def test_stock_reserved_while_pending(self):
        v = self.product.variants.first()
        self._create_pending_order()
        from src.modules.catalog.models import Inventory
        inv = Inventory.objects.get(product=self.product)
        self.assertGreater(inv.reserved_quantity, 0)

    def test_expired_reservation_released_back_to_stock(self):
        from django.utils import timezone
        from datetime import timedelta
        from src.modules.catalog.models import Inventory
        from src.modules.order.expiry import release_expired_orders
        o = self._create_pending_order()
        inv = Inventory.objects.get(product=self.product)
        self.assertGreater(inv.reserved_quantity, 0)
        # انقضا را به گذشته ببر و release را اجرا کن
        Order.objects.filter(pk=o.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        release_expired_orders()
        o.refresh_from_db()
        self.assertEqual(o.status, Order.OrderStatus.CANCELLED)
        inv.refresh_from_db()
        self.assertEqual(inv.reserved_quantity, 0)
