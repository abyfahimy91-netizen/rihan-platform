"""تست‌های GEO — D-118: ربات‌های AI در robots.txt، llms.txt غنی،
اسکیمای Product غنی‌شده (priceValidUntil/seller/countryOfOrigin/additionalProperty)،
کادر پاسخ سریع و aggregateRating شرطی."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from src.modules.catalog.indexnow import INDEXNOW_KEY
from src.modules.catalog.models import (
    Category, Supplier, Product, Inventory,
)
from src.modules.order.models import Order, OrderItem
from src.modules.reviews.models import Review

User = get_user_model()
HOST = 'rihan360.ir'


class GeoTestBase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        cat = Category.objects.create(name='دسته GEO', slug='geo-cat')
        sup = Supplier.objects.create(title='تامین GEO', city='تبریز')
        self.product = Product.objects.create(
            name='سماق تست GEO', slug='geo-sumac-test',
            category=cat, supplier=sup, unit='گرم',
            base_price=Decimal('100000'), shipping_cost=Decimal('0'), margin_percent=0,
            short_description='توضیح تست GEO',
            geo_answer='پاسخ سریع تست؛ خاستگاه هوراند.',
            metadata={
                'country_of_origin': 'Iran',
                'facts': [{'name': 'خاستگاه', 'value': 'هوراند'}],
            },
            status='active',
        )
        Inventory.objects.get_or_create(product=self.product)


class RobotsAITest(GeoTestBase):
    def test_ai_crawlers_explicitly_listed(self):
        body = self.client.get('/robots.txt').content.decode()
        for bot in ('GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'PerplexityBot',
                    'ClaudeBot', 'Google-Extended', 'Applebot-Extended', 'Bingbot'):
            self.assertIn('User-agent: %s' % bot, body)
        self.assertIn('Sitemap:', body)

    def test_admin_still_disallowed(self):
        body = self.client.get('/robots.txt').content.decode()
        self.assertIn('Disallow: /admin/', body)


class LlmsTxtTest(GeoTestBase):
    def test_llms_contains_quick_answer_and_facts(self):
        body = self.client.get('/llms.txt').content.decode()
        self.assertIn('پاسخ سریع تست', body)
        self.assertIn('خاستگاه: هوراند', body)
        self.assertIn('/products/geo-sumac-test/', body)
        self.assertIn('ضمانت ۷ روزه', body)


class IndexNowKeyFileTest(GeoTestBase):
    def test_key_file_served_at_root(self):
        r = self.client.get('/%s.txt' % INDEXNOW_KEY)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode().strip(), INDEXNOW_KEY)


class ProductSchemaTest(GeoTestBase):
    def _page(self):
        return self.client.get('/products/geo-sumac-test/').content.decode()

    def test_schema_enriched_fields(self):
        html = self._page()
        for needle in ('"priceValidUntil"', '"itemCondition"', '"seller"',
                       '"countryOfOrigin"', '"additionalProperty"',
                       '"PropertyValue"', '"خاستگاه"'):
            self.assertIn(needle, html)

    def test_quick_answer_box_rendered(self):
        html = self._page()
        self.assertIn('geo-answer-section', html)
        self.assertIn('پاسخ سریع تست', html)

    def test_no_aggregate_rating_without_reviews(self):
        self.assertNotIn('AggregateRating', self._page())

    def test_aggregate_rating_with_approved_review(self):
        user = User.objects.create_user(username='09140000000', password='x')
        order = Order.objects.create(
            user=user, status=Order.OrderStatus.DELIVERED,
            guest_name='تست', guest_phone=user.username,
            guest_address='آدرس تستی طولانی کافی برای سیستم',
        )
        OrderItem.objects.create(
            order=order, product=self.product, quantity=1,
            unit_price_at_purchase=self.product.final_price,
        )
        Review.objects.create(
            product=self.product, order=order, user=user,
            rating=5, text='عالی بود', is_approved=True,
        )
        html = self._page()
        self.assertIn('AggregateRating', html)
        self.assertIn('"ratingValue": "5.0"', html)
        self.assertIn('"reviewCount": 1', html)
