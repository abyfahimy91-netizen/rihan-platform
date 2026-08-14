from django.test import TestCase, Client
from django.urls import reverse
from apps.catalog.models import Category, Product, ContentBlock

class CatalogTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="ارگانیک", slug="organic")
        self.p = Product.objects.create(
            category=self.cat, title="عسل سبلان", slug="honey-sabalan",
            sku="RIHAN-H1", summary="عسل طبیعی", price=450000, compare_at_price=500000, stock=10
        )
        self.b = ContentBlock.objects.create(product=self.p, block_type="story", title="داستان عسل", content="متن داستان")

    def test_product_model(self):
        self.assertTrue(self.p.has_discount)
        self.assertEqual(self.p.discount_percent, 10)

    def test_views_and_apis(self):
        c = Client()
        self.assertEqual(c.get(reverse('product_list')).status_code, 200)
        self.assertEqual(c.get(reverse('product_detail', kwargs={'slug': self.p.slug})).status_code, 200)
        self.assertEqual(c.get(reverse('api_products')).status_code, 200)
