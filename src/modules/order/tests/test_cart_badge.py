"""
D-115: نشان قرمز تعداد سبد روی آیکون هدر — سرور-رندر روی همه صفحات
- قبلاً بج هدر همیشه «۰» هاردکد بود و فقط بعد از تغییر تعداد در صفحه سبد با AJAX به‌روز می‌شد
- حالا: سبد خالی → بج مخفی | بعد از افزودن → «۱» قرمز | تغییر تعداد → JSON و رندر سرور هر دو درست
- پروسسور فقط-خواندنی است: برای بازدیدکننده ناشناس هرگز رکورد Cart نمی‌سازد
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, ProductVariant
from src.modules.order.models import Cart


class CartBadgeTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='دسته بج', slug='badge-cat')
        self.product = Product.objects.create(
            name='محصول بج', slug='badge-prod', category=self.category,
            base_price=Decimal('100000'), short_description='x', origin_story='x',
            status='active')
        self.variant = ProductVariant.objects.create(
            product=self.product, title='بسته ۵۰۰ گرمی',
            price=Decimal('1470000'), stock_quantity=5)

    def _client(self):
        # دام شناخته‌شده: ALLOWED_HOSTS شامل testserver نیست
        return Client(SERVER_NAME='rihan360.ir')

    def _add(self, client, quantity=1):
        return client.post('/order/cart/add/', {
            'product_slug': 'badge-prod', 'quantity': str(quantity)})

    # ── ۱) پروسسور نباید برای ناشناس سبد بسازد ──
    def test_processor_never_creates_cart_for_anonymous(self):
        c = self._client()
        r = c.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Cart.objects.count(), 0)

    # ── ۲) سبد خالی → بج مخفی (نه ۰ گمراه‌کننده) ──
    def test_badge_hidden_when_cart_empty(self):
        c = self._client()
        r = c.get('/order/cart/')
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn('id="cart-count" hidden>', body)

    # ── ۳) اولین افزودن → بلافاصله «۱» روی خود صفحه سبد ──
    def test_badge_shows_one_on_cart_page_right_after_add(self):
        c = self._client()
        r = self._add(c, 1)
        self.assertEqual(r.status_code, 302)  # ریدایرکت به صفحه سبد
        body = c.get('/order/cart/').content.decode()
        self.assertIn('id="cart-count" >۱<', body)
        self.assertNotIn('id="cart-count" hidden', body)

    # ── ۴) همان لحظه روی صفحه اصلی هم عدد هست (نه فقط صفحه سبد) ──
    def test_badge_visible_on_home_after_add(self):
        c = self._client()
        self._add(c, 1)
        body = c.get('/').content.decode()
        self.assertIn('id="cart-count" >۱<', body)

    # ── ۵) افزودن مجدد همان محصول → جمع تعداد «۲» ──
    def test_badge_sums_quantities(self):
        c = self._client()
        self._add(c, 1)
        self._add(c, 1)
        body = c.get('/order/cart/').content.decode()
        self.assertIn('id="cart-count" >۲<', body)

    # ── ۶) تغییر تعداد با AJAX → هم JSON درست، هم رندر بعدی سرور ──
    def test_badge_after_ajax_quantity_change(self):
        c = self._client()
        self._add(c, 1)
        item = Cart.objects.first().items.first()
        r = c.post('/order/cart/update/', {
            'item_id': str(item.pk), 'quantity': '3',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('item_count'), 3)
        self.assertEqual(data.get('count_fa'), '۳')
        body = c.get('/order/cart/').content.decode()
        self.assertIn('id="cart-count" >۳<', body)

    # ── ۷) کاربر واردشده → بج از سبدِ خودش می‌آید ──
    def test_authenticated_user_badge_from_user_cart(self):
        User = get_user_model()
        u = User.objects.create_user(username='09120000000', password='RihanTest123')
        c = self._client()
        c.force_login(u)
        self._add(c, 2)
        body = c.get('/').content.decode()
        self.assertIn('id="cart-count" >۲<', body)
