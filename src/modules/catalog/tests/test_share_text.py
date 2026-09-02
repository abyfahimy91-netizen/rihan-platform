"""
SHARE-CTA-14050611 — تست متن اختصاصی اشتراک‌گذاری + {min_price}
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from src.modules.catalog.models import Category, Product, ProductVariant
from src.modules.pages.models import SiteSettings

HOST = 'rihan360.ir'


def make_product():
    cat = Category.objects.create(name='ct', slug='ct1')
    p = Product.objects.create(
        name='سماق تست', slug='share-prod', category=cat,
        base_price=Decimal('790000'), short_description='t', origin_story='x', status='active')
    ProductVariant.objects.create(product=p, title='۲۵۰گرم', price=Decimal('790000'), stock_quantity=5)
    ProductVariant.objects.create(product=p, title='۱کیلو', price=Decimal('2950000'), stock_quantity=5)
    return p


class ShareTextTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.client = Client()

    def _share(self):
        return self.client.post(
            reverse('catalog:product_share', args=[self.product.slug]),
            {'channel': 'whatsapp'}, HTTP_HOST=HOST)

    def test_endpoint_returns_custom_product_text_with_price(self):
        self.product.share_text = 'همین حالا بگیر! از {min_price} تومان 👆'
        self.product.save()
        r = self._share()
        d = r.json()
        self.assertIn('همین حالا بگیر!', d['text'])
        self.assertIn('۷۹۰٬۰۰۰', d['text'])  # ارزان‌ترین واریانت (فارسی)

    def test_fallback_to_settings_text(self):
        s = SiteSettings.objects.first() or SiteSettings.objects.create()
        s.share_message_text = 'متن عمومی سایت'
        s.save()
        r = self._share()
        self.assertIn('متن عمومی سایت', r.json()['text'])

    def test_product_text_beats_settings_text(self):
        s = SiteSettings.objects.first() or SiteSettings.objects.create()
        s.share_message_text = 'متن عمومی سایت'
        s.save()
        self.product.share_text = 'متن اختصاصی محصول'
        self.product.save()
        self.assertIn('متن اختصاصی محصول', self._share().json()['text'])

    def test_caption_contains_short_link_exactly_once(self):
        self.product.share_text = 'بگیرش از {min_price} 👆'
        self.product.save()
        text = self._share().json()['text']
        self.assertEqual(text.count('rihan360.ir/p/'), 1)

    def test_unknown_placeholder_removed_safely(self):
        self.product.share_text = 'قیمت: {min_price} — کد: {unknown_var}'
        self.product.save()
        text = self._share().json()['text']
        self.assertNotIn('{min_price}', text)
        self.assertIn('{unknown_var}', text)  # ناشناس‌ها دست‌نخورده
