"""
SALES-14050610 — تست موتور کد تخفیف
"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, ProductVariant
from src.modules.order.models import Coupon, Order

HOST = 'rihan360.ir'

FormData = dict(
    name='مشتری تستی',
    phone='09121112233',
    address='تبریز، خیابان تست، پلاک ۱۲، واحد ۳',
    postal_code='5151411111',
)


def make_product():
    cat = Category.objects.create(name='دستهٔ کمپین', slug='camp-cat')
    p = Product.objects.create(
        name='سماق کمپین', slug='camp-prod', category=cat,
        base_price=Decimal('2950000'), short_description='توضیح', origin_story='x',
        status='active',
    )
    ProductVariant.objects.create(product=p, title='بسته ۱ کیلوگرمی', price=Decimal('2950000'), stock_quantity=5)
    return p


class CouponModelTests(TestCase):
    def test_percent_discount(self):
        c = Coupon.objects.create(code='P50', kind=Coupon.PERCENT, value=50)
        self.assertEqual(c.discount_for(Decimal('100000')), Decimal('50000'))

    def test_fixed_discount_never_exceeds_subtotal(self):
        c = Coupon.objects.create(code='BIG', kind=Coupon.FIXED, value=9999999)
        self.assertEqual(c.discount_for(Decimal('100000')), Decimal('100000'))

    def test_expired_code_is_invalid(self):
        from django.utils import timezone
        from datetime import timedelta
        c = Coupon.objects.create(code='OLD', kind=Coupon.FIXED, value=50000,
                                  expires_at=timezone.now() - timedelta(days=1))
        ok, err = c.is_valid_window()
        self.assertFalse(ok)
        self.assertIn('منقضی', err)

    def test_total_cap(self):
        c = Coupon.objects.create(code='CAP1', kind=Coupon.FIXED, value=10000, max_uses_total=1, used_count=1)
        ok, err = c.is_valid_window()
        self.assertFalse(ok)
        self.assertIn('ظرفیت', err)


class CheckoutWithCouponTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.coupon = Coupon.objects.create(
            code='KHOSHAMAD', kind=Coupon.FIXED, value=200000,
            note='کمپین خوش‌آمد — تست',
        )
        self.client = Client()

    def _add_to_cart(self):
        r = self.client.post('/order/cart/add/', {'product_slug': 'camp-prod', 'quantity': '1'})
        self.assertEqual(r.status_code, 302)
        return r

    def _checkout(self, extra=None):
        data = dict(FormData)
        data.update(extra or {})
        return self.client.post('/order/checkout/', data, HTTP_HOST=HOST)

    def test_order_gets_discount_with_coupon(self):
        self._add_to_cart()
        r = self._checkout({'coupon_code': ' khoshamad '})
        self.assertEqual(Order.objects.count(), 1)
        o = Order.objects.first()
        self.assertEqual(o.coupon.code, 'KHOSHAMAD')
        self.assertEqual(o.discount_amount, Decimal('200000'))
        self.assertEqual(o.total_price, Decimal('2750000'))
        self.assertEqual(o.coupon_uses.count(), 1)
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.used_count, 1)

    def test_order_without_coupon_untouched(self):
        self._add_to_cart()
        self._checkout()
        o = Order.objects.first()
        self.assertIsNone(o.coupon)
        self.assertEqual(o.discount_amount, Decimal('0'))
        self.assertEqual(o.total_price, o.subtotal)

    def test_invalid_code_blocks_order_with_error(self):
        self._add_to_cart()
        r = self._checkout({'coupon_code': 'NOPE'})
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn('کد تخفیف معتبر نیست'.encode(), r.content)

    def test_min_cart_blocks_small_cart(self):
        Coupon.objects.filter(pk=self.coupon.pk).update(min_cart=Decimal('5000000'))
        self._add_to_cart()
        r = self._checkout({'coupon_code': 'KHOSHAMAD'})
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn('سبدهای بالای'.encode(), r.content)

    def test_per_user_cap_blocks_second_use(self):
        self._add_to_cart()
        self._checkout({'coupon_code': 'KHOSHAMAD'})
        self.assertEqual(Order.objects.count(), 1)
        # سبد جدید (سبد قبلی پس از سفارش غیرفعال شد)
        self.client.get('/order/cart/', HTTP_HOST=HOST)
        self._add_to_cart()
        r = self._checkout({'coupon_code': 'KHOSHAMAD'})
        self.assertEqual(Order.objects.count(), 1)
        self.assertIn('قبلاً از این کد استفاده کرده‌اید'.encode(), r.content)

    def test_checkout_page_shows_coupon_field(self):
        self._add_to_cart()
        r = self.client.get('/order/checkout/', HTTP_HOST=HOST)
        self.assertIn('coupon_code'.encode(), r.content)
        self.assertIn('کد تخفیف دارید؟'.encode(), r.content)
