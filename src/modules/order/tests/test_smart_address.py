"""D-120 — UX هوشمند ورود آدرس: نرمال‌سازی بخشنده سرور، autocomplete استاندارد،
بازبینی زنده «تحویل به» در چک‌اوت، کارت آدرس + لینک نقشه در صفحه پرداخت.

اصطکاک صفر: کاربر هر چه تایپ کند (ارقام فارسی، خط تیره، +98، بدون صفر) سرور تمیز می‌کند.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from src.modules.catalog.models import Category, Supplier, Product, Inventory
from src.modules.order import address_service
from src.modules.order.models import Order

User = get_user_model()
HOST = 'rihan360.ir'


class NormalizeTest(TestCase):
    """نرمال‌سازی موبایل و کد پستی — هر ورودی معقول باید تمیز شود"""

    def test_normalize_phone_variants(self):
        self.assertEqual(address_service.normalize_phone('0912 345 6789'), '09123456789')
        self.assertEqual(address_service.normalize_phone('+989123456789'), '09123456789')
        self.assertEqual(address_service.normalize_phone('+98 912 345 6789'), '09123456789')
        self.assertEqual(address_service.normalize_phone('00989123456789'), '09123456789')
        self.assertEqual(address_service.normalize_phone('9123456789'), '09123456789')
        self.assertEqual(address_service.normalize_phone('۰۹۱۲۳۴۵۶۷۸۹'), '09123456789')

    def test_normalize_phone_keeps_valid_as_is(self):
        self.assertEqual(address_service.normalize_phone('09123456789'), '09123456789')

    def test_normalize_postal_variants(self):
        self.assertEqual(address_service.normalize_postal_code('۵۱۵۱۴-۱۱۱۱۱'), '5151411111')
        self.assertEqual(address_service.normalize_postal_code('51514 11111'), '5151411111')
        self.assertEqual(address_service.normalize_postal_code('۵۱۵۱۴۱۱۱۱۱'), '5151411111')
        self.assertEqual(address_service.normalize_postal_code('1234567890'), '1234567890')

    def test_validation_accepts_normalized_input(self):
        """سرویس آدرس با ورودی «کثیف» خطا نمی‌دهد — بعد از نرمال‌سازی"""
        user = User.objects.create_user(username='09121110700', password='x1234567', email='n@rihan.local')
        clean, errors = address_service.validate_address_data({
            'full_name': 'کاربر تست',
            'phone': '0912 345 6789',
            'address': 'تبریز، خیابان آزادی، پلاک ۱۰',
            'postal_code': '۵۱۵۱۴-۱۱۱۱۱',
        })
        self.assertEqual(errors, [])
        self.assertEqual(clean['phone'], '09123456789')
        self.assertEqual(clean['postal_code'], '5151411111')
        a = address_service.create_for_user(user, {
            'full_name': 'کاربر تست', 'phone': '9123456789',
            'address': 'تبریز، خیابان آزادی، پلاک ۱۰', 'postal_code': '51514 11111',
        })
        self.assertEqual(a.phone, '09123456789')
        self.assertEqual(a.postal_code, '5151411111')


class SmartAddressTest(TestCase):
    """چک‌اوت و پروفایل: autocomplete + بازبینی زنده + صفحه پرداخت"""

    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        self.user = User.objects.create_user(
            username='09121110500', password='test123456', email='sa@rihan.local',
        )
        cat = Category.objects.create(name='دسته هوشمند', slug='test-cat-smart')
        sup = Supplier.objects.create(title='تامین هوشمند', city='هوراند')
        self.product = Product.objects.create(
            name='محصول هوشمند', slug='test-smart-product',
            category=cat, supplier=sup, unit='عدد',
            base_price=Decimal('100000'), shipping_cost=Decimal('0'),
            margin_percent=0, short_description='تست', origin_story='تست',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        inv, _ = Inventory.objects.get_or_create(product=self.product)
        inv.quantity = Decimal('50')
        inv.save()
        self.client.force_login(self.user)

    def _fill_cart(self):
        self.client.post('/order/cart/add/', {'product_slug': self.product.slug, 'quantity': 1})

    def _post_checkout(self, **kw):
        self._fill_cart()
        data = {
            'address_choice': 'new',
            'title': 'خانه',
            'name': 'مریم احمدی',
            'phone': '09121110500',
            'address': 'تبریز، خیابان آزادی، پلاک ۱۰',
            'postal_code': '1234567890',
        }
        data.update(kw)
        return self.client.post('/order/checkout/', data)

    # ── نرمال‌سازی در جریان واقعی چک‌اوت ──
    def test_checkout_postal_persian_digits_with_dash(self):
        r = self._post_checkout(postal_code='۵۱۵۱۴-۱۱۱۱۱')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.latest('id').guest_postal_code, '5151411111')

    def test_checkout_postal_with_space(self):
        r = self._post_checkout(postal_code='51514 11111')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.latest('id').guest_postal_code, '5151411111')

    def test_checkout_phone_without_leading_zero(self):
        r = self._post_checkout(phone='9123456789')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Order.objects.latest('id').guest_phone, '09123456789')

    def test_checkout_garbage_postal_still_rejected(self):
        r = self._post_checkout(postal_code='abc')
        self.assertEqual(r.status_code, 200)
        self.assertIn('کد پستی', r.content.decode())

    # ── markup: autocomplete + بازبینی زنده ──
    def test_checkout_has_autocomplete_and_live_preview(self):
        self._fill_cart()
        r = self.client.get('/order/checkout/')
        c = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn('autocomplete="postal-code"', c)
        self.assertIn('autocomplete="street-address"', c)
        self.assertIn('autocomplete="name"', c)
        self.assertIn('autocomplete="tel"', c)
        self.assertIn('id="deliveryPreview"', c)
        self.assertIn('id="pcLive"', c)
        self.assertIn('id="dpBody"', c)

    def test_profile_address_form_has_autocomplete_and_meter(self):
        r = self.client.get('/accounts/profile/')
        c = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn('autocomplete="street-address"', c)
        self.assertIn('autocomplete="postal-code"', c)
        self.assertIn('autocomplete="given-name"', c)
        self.assertIn('autocomplete="family-name"', c)
        self.assertIn('id="pfPcLive"', c)

    # ── صفحه پرداخت: کارت «تحویل به» (بدون لینک نقشه — D-120b: جستجوی متنی آدرس اعتمادشکن است) ──
    def test_payment_page_shows_address_card(self):
        r = self._post_checkout()
        self.assertEqual(r.status_code, 302)
        order = Order.objects.latest('id')
        r = self.client.get(f'/order/payment/{order.order_number}/')
        self.assertEqual(r.status_code, 200)
        c = r.content.decode()
        self.assertIn('تحویل به:', c)
        self.assertIn('آزادی', c)
        self.assertIn('مریم احمدی', c)
        self.assertNotIn('balad.ir', c)

    def test_payment_page_hides_address_card_when_cancelled(self):
        self._post_checkout()
        order = Order.objects.latest('id')
        order.status = Order.OrderStatus.CANCELLED
        order.save()
        r = self.client.get(f'/order/payment/{order.order_number}/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('تحویل به:', r.content.decode())
