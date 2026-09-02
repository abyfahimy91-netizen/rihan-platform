"""
UX-FRICTION-14050611 — تست اصلاحات اصطکاک خرید
- قالب: حذف دکمهٔ دوم، hint بدون ثبت‌نام، راهنمای کدپستی، کوپن جمع‌شونده
- جریان کامل: محصول → خرید سریع → تسویه → سفارش (بدون اصطکاک)
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

    def test_no_dual_cta_single_buy_button(self):
        r = self.c.get('/products/ux-prod/', HTTP_HOST=HOST)
        c = r.content.decode()
        self.assertNotIn('class="btn-view-cart"', c)  # دکمهٔ دوم حذف شد
        self.assertIn('data-fast-buy', c)             # فقط خرید سریع
        self.assertNotIn('>افزودن به سبد</button>', c)

    def test_cta_hint_reassurance(self):
        c = self.c.get('/products/ux-prod/', HTTP_HOST=HOST).content.decode()
        self.assertIn('ثبت‌نام لازم نیست', c)
        self.assertIn('پشتیبانی واتساپ', c)

    def test_sticky_bar_button_text(self):
        c = self.c.get('/products/ux-prod/', HTTP_HOST=HOST).content.decode()
        self.assertIn('ثبت سفارش</button>', c)
        self.assertNotIn('>خرید سریع</button>', c)

    def test_orange_cta_css(self):
        c = self.c.get('/products/ux-prod/', HTTP_HOST=HOST).content.decode()
        self.assertIn('#E8590C', c)  # رنگ CTA یکتا


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
        # راهنما باید قبل از input کدپستی بیاید
        self.assertLess(c.find('چطور پیدا کنم؟'), c.find('id="id_postal_code"'))

    def test_coupon_collapsed_by_default(self):
        self._fill_cart()
        c = self.c.get('/order/checkout/', HTTP_HOST=HOST).content.decode()
        self.assertIn('<details class="coupon-box"', c)

    def test_reassurance_under_submit(self):
        self._fill_cart()
        c = self.c.get('/order/checkout/', HTTP_HOST=HOST).content.decode()
        self.assertIn('اطلاعات شما فقط برای ارسال سفارش است', c)

    def test_full_flow_fast_buy_to_order(self):
        """سفر کامل بدون اصطکاک: کلیک خرید → تسویه → ثبت سفارش"""
        r = self.c.post('/order/cart/add/', {'product_slug': 'ux-prod', 'quantity': '1'})
        self.assertEqual(r.status_code, 302)
        r2 = self.c.post('/order/checkout/', dict(
            name='خریدار ساده', phone='09121112233',
            address='تبریز، خیابان آزادی، پلاک ۱۰، واحد ۲',
            postal_code='5151411111',
        ), HTTP_HOST=HOST, follow=True)
        self.assertEqual(Order.objects.count(), 1)
        o = Order.objects.first()
        self.assertEqual(o.total_price, Decimal('2950000'))
        self.assertEqual(o.guest_name, 'خریدار ساده')
