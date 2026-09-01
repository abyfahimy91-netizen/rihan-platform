"""
D-128: پیام کنار قیمت (توجیه قیمت) + نمایش تخفیف در کارت صفحه اصلی
- SiteSettings.price_note_enabled / price_note_text از پنل ادمین کنترل می‌شود
- متنِ تنظیم‌شده باید روی کارت صفحه اصلی و زیر قیمت صفحه محصول بیاید
- کلید خاموش یا متن خالی = هیچ رندری، در هیچ صفحه‌ای
"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, ProductVariant
from src.modules.pages.models import SiteSettings

NOTE_TEXT = 'برداشت دستی از کوه‌های هوراند؛ ۱۰۰٪ دانهٔ خالص بدون نمک.'


class PriceNoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='دستهٔ نمایش', slug='pn-cat')
        cls.product = Product.objects.create(
            name='سماق نمایشی', slug='pn-prod', category=cls.category,
            base_price=Decimal('100000'),
            short_description='سماق وحشی هوراند', origin_story='x',
            status='active',
            compare_at_price=Decimal('350000'),
        )
        ProductVariant.objects.create(
            product=cls.product, title='بسته ۱۰۰ گرمی',
            price=Decimal('295000'), stock_quantity=5)
        SiteSettings.objects.create(
            pk=1, price_note_enabled=True, price_note_text=NOTE_TEXT)

    def setUp(self):
        self.c = Client(SERVER_NAME='rihan360.ir')

    # ── صفحه اصلی: پیام کنار قیمت روی کارت ──
    def test_homepage_card_shows_note(self):
        r = self.c.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'price-note')
        self.assertContains(r, 'برداشت دستی از کوه‌های هوراند')

    def test_homepage_card_shows_discount(self):
        """کارت صفحه اصلی باید درصد تخفیف + قیمت خط‌خورده را نشان دهد."""
        r = self.c.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'price-off')
        self.assertContains(r, '٪ تخفیف')
        self.assertContains(r, '۳۵۰٬۰۰۰')

    def test_disabled_note_hidden_on_homepage(self):
        s = SiteSettings.objects.get(pk=1)
        s.price_note_enabled = False
        s.save()
        body = self.c.get('/').content.decode()
        self.assertNotIn('برداشت دستی از کوه‌های هوراند', body)

    def test_blank_text_hidden_on_homepage(self):
        s = SiteSettings.objects.get(pk=1)
        s.price_note_text = ''
        s.save()
        body = self.c.get('/').content.decode()
        self.assertNotIn('برداشت دستی از کوه‌های هوراند', body)

    # ── صفحه محصول: پیام داخل جعبهٔ قیمت ──
    def test_detail_page_shows_note(self):
        r = self.c.get('/products/pn-prod/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'price-note-inline')
        self.assertContains(r, 'برداشت دستی از کوه‌های هوراند')

    def test_disabled_note_hidden_on_detail(self):
        s = SiteSettings.objects.get(pk=1)
        s.price_note_enabled = False
        s.save()
        body = self.c.get('/products/pn-prod/').content.decode()
        self.assertNotIn('برداشت دستی از کوه‌های هوراند', body)

    def test_default_settings_on(self):
        s = SiteSettings.load()
        self.assertTrue(s.price_note_enabled)
