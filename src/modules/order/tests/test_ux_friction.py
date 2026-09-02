"""
UX-FRICTION-14050611 — تست اصلاحات اصطکاک خرید (به‌روزرسانی با بازخورد کاربر 14050611)
- CTA اصلی نارنجی + دکمهٔ ثانویهٔ «افزودن به سبد خرید» برگشت (درخواست کاربر)
- پیام منافع ثبت‌نام جایگزین «ثبت‌نام لازم نیست»
- نوار چسبان: دکمهٔ «ثبت سفارش»
"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, ProductVariant
from src.modules.order.models import Order

HOST = 'rihan360.ir'


def make_product():
    cat = Category.objects.create(name='ux', slug='ux-cat')
    p = Product.objects.create(
        name='محصول UX', slug='ux-prod', category=cat,
        base_price=Decimal('2950000'), short_description='t', origin_story='x', status='active')
    ProductVariant.objects.create(product=p, title='۱کیلو', price=Decimal('2950000'), stock_quantity=5)
    return p


class ProductPageFrictionTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.c = Client()

    def test_primary_and_secondary_cta(self):
        """دکمهٔ اصلی خرید سریع + دکمهٔ ثانویهٔ افزودن به سبد — هر دو موجود"""
        c = self.c.get('/products/ux-prod/', HTTP_HOST=HOST).content.decode()
        self.assertIn('data-fast-buy', c)
        self.assertRegex(c, r'>\s*افزودن به سبد خرید\s*</button>')

    def test_registration_benefit_message(self):
        """پیام جدید: منافع ثبت‌نام — نه «لازم نیست»"""
        c = self.c.get('/products/ux-prod/', HTTP_HOST=HOST).content.decode()
        self.assertNotIn('ثبت‌نام لازم نیست', c)
        self.assertIn('با ثبت‌نام، آدرس‌ها ذخیره و سوابق سفارش در پروفایل شما می‌ماند', c)

    def test_sticky_bar_button_text(self):
        c = self.c.get('/products/ux-prod/', HTTP_HOST=HOST).content.decode()
        self.assertIn('ثبت سفارش</button>', c)
        self.assertNotIn('>خرید سریع</button>', c)

    def test_orange_cta_css(self):
        c = self.c.get('/products/ux-prod/', HTTP_HOST=HOST).content.decode()
        self.assertIn('#E8590C', c)
        # دکمهٔ ثانویه واقعاً ثانویه است (کوچک‌تر و کم‌رنگ)
        self.assertIn('padding: 13px 28px', c)


class CheckoutFrictionTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.c = Client()

    def _fill_cart(self):
        self.c.get('/order/cart/', HTTP_HOST=HOST)
        self.c.post('/order/cart/add/', {'product_slug': 'ux-prod', 'quantity': '1'})

    def test_postal_help_before_field(self):
        self._fill_cart()
        c = self.c.get('/order/checkout/', HTTP_HOST=HOST).content.decode()
        self.assertIn('چطور پیدا کنم؟', c)
        self.assertLess(c.find('چطور پیدا کنم؟'), c.find('id="id_postal_code"'))

    def test_coupon_collapsed_by_default(self):
        self._fill_cart()
        c = self.c.get('/order/checkout/', HTTP_HOST=HOST).content.decode()
        self.assertIn('<details class="coupon-box"', c)

    def test_registration_benefit_under_submit(self):
        self._fill_cart()
        c = self.c.get('/order/checkout/', HTTP_HOST=HOST).content.decode()
        self.assertIn('با ثبت‌نام، آدرس‌ها ذخیره و سوابق سفارش در پروفایل شما می‌ماند', c)
        self.assertNotIn('ثبت‌نام لازم نیست', c)

    def test_full_flow_fast_buy_to_order(self):
        """سفر کامل: خرید سریع → تسویه → سفارش"""
        r = self.c.post('/order/cart/add/', {'product_slug': 'ux-prod', 'quantity': '1'})
        self.assertEqual(r.status_code, 302)
        self.c.post('/order/checkout/', dict(
            name='خریدار ساده', phone='09121112233',
            address='تبریز، خیابان آزادی، پلاک ۱۰، واحد ۲',
            postal_code='5151411111',
        ), HTTP_HOST=HOST, follow=True)
        self.assertEqual(Order.objects.count(), 1)
        o = Order.objects.first()
        self.assertEqual(o.total_price, Decimal('2950000'))
        self.assertEqual(o.guest_name, 'خریدار ساده')
