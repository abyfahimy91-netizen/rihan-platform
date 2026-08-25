"""تست بخش اعتماد ادمین‌محور + ردیف ارتباط + حذف کادر خالی محتوا — D-108"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, Inventory
from src.modules.pages.models import SiteSettings

HOST = 'rihan360.ir'


class TrustSectionTest(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        cat = Category.objects.create(name='دسته تست اعتماد', slug='test-cat-trust')
        self.product = Product.objects.create(
            name='محصول تست اعتماد', slug='test-trust-product',
            category=cat, unit='عدد',
            base_price=Decimal('100000'), shipping_cost=Decimal('0'),
            margin_percent=0, short_description='توضیح تست',
            origin_story='داستان تست',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        inv, _ = Inventory.objects.get_or_create(product=self.product)
        inv.quantity = Decimal('5')
        inv.save()

    def _configure(self):
        s = SiteSettings.load()
        s.trust_badges = 'ضمانت تست | زیرعنوان تست'
        s.contact_phone = '09140000000'
        s.whatsapp_number = '09141112233'
        s.telegram_url = 'https://t.me/rihan_test'
        s.save()
        return s

    def test_badges_from_settings_rendered(self):
        self._configure()
        r = self.client.get('/products/test-trust-product/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'ضمانت تست')
        self.assertContains(r, 'زیرعنوان تست')

    def test_contact_channels_live_data(self):
        self._configure()
        r = self.client.get('/products/test-trust-product/')
        self.assertContains(r, 'tel:09140000000')
        self.assertContains(r, 'wa.me/989141112233')
        self.assertContains(r, 'https://t.me/rihan_test')

    def test_fake_phone_and_empty_box_gone(self):
        r = self.client.get('/products/test-trust-product/')
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, '09123456789')
        self.assertNotContains(r, 'هنوز محتوایی')

    def test_chips_hidden_when_unset(self):
        r = self.client.get('/products/test-trust-product/')
        self.assertNotContains(r, '<a class="tc-chip')
        self.assertNotContains(r, '<div class="trust-contact-row"')
