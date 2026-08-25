"""D-107: لینک کوتاه، متن اشتراک‌گذاری ادمین‌محور، قالب پیامک و متاتگ OG"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from src.modules.catalog.models import Category, Product, ShortLink
from src.modules.pages.models import SiteSettings
from src.modules.order.fulfillment import render_sms_template


class ShareShortLinkTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='دسته D107', slug='d107-cat')
        self.product = Product.objects.create(
            name='محصول D107', slug='prod-d107', category=self.category,
            base_price=10000, short_description='x', origin_story='x', status='active')

    def test_share_returns_short_url_and_admin_text(self):
        SiteSettings.objects.create(
            share_message_text='پیشنهاد ویژه امروز!',
            share_hashtags='#Rihan #تست')
        resp = self.client.post(reverse('catalog:product_share', args=[self.product.slug]),
                                {'channel': 'telegram'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('/p/', data['url'])
        self.assertEqual(len(data['url'].rsplit('/', 2)[-2]), 8)
        self.assertIn('پیشنهاد ویژه امروز!', data['text'])
        self.assertIn('محصول D107', data['text'])
        self.assertIn('#تست', data['text'])

    def test_short_link_redirects_to_product(self):
        code = ShortLink.get_for_product(self.product).code
        resp = self.client.get(f'/p/{code}/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/products/prod-d107', resp['Location'])
        # همان محصول دوباره → همان کد (idempotent)
        self.assertEqual(ShortLink.get_for_product(self.product).code, code)

    def test_unknown_code_404(self):
        resp = self.client.get('/p/zzzzzzzz/')
        self.assertEqual(resp.status_code, 404)

    def test_product_page_has_absolute_og_image(self):
        self.client.get(f'/products/{self.product.slug}/')
        html = self.client.get(f'/products/{self.product.slug}/').content.decode()
        self.assertIn('property="og:image"', html)
        self.assertIn('summary_large_image', html)


class SmsTemplateTests(TestCase):
    def test_custom_template_renders_placeholders(self):
        out = render_sms_template(
            '{brand} | سفارش {order_number} — {tracking_code}',
            'DEFAULT {order_number}',
            {'brand': 'Rihan', 'order_number': 'RH-1', 'tracking_code': 'RA9'})
        self.assertEqual(out, 'Rihan | سفارش RH-1 — RA9')

    def test_broken_template_falls_back_to_default(self):
        out = render_sms_template(
            'خراب {unknown_var} {',
            'پیش‌فرض امن',
            {'brand': 'x'})
        self.assertEqual(out, 'پیش‌فرض امن')

    def test_empty_template_uses_default(self):
        out = render_sms_template('', 'سلام {brand}', {'brand': 'Rihan'})
        self.assertEqual(out, 'سلام Rihan')
