"""
Tests for catalog views and block rendering (D-079)
"""
from django.test import TestCase
from src.modules.catalog.models import Product, Category, ContentBlock


class CatalogViewsTest(TestCase):
    """Test catalog views"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            short_description='Test description',
            origin_story='Test origin story',
            status='active'
        )
    
    def test_product_list_view(self):
        """Product list page should be accessible"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test Product', response.content.decode())
    
    def test_product_detail_view(self):
        """Product detail page should be accessible"""
        response = self.client.get(f'/products/{self.product.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test Product', response.content.decode())
    
    def test_product_detail_seo_meta(self):
        """Product detail page should have SEO meta tags"""
        response = self.client.get(f'/products/{self.product.slug}/')
        content = response.content.decode()
        self.assertIn('og:title', content)
        self.assertIn('og:description', content)
    
    def test_block_rendering_text(self):
        """Text blocks should be rendered"""
        ContentBlock.objects.create(
            product=self.product,
            block_type='text',
            content={'text': 'This is a test block content'},
            sort_order=1,
            is_active=True
        )
        response = self.client.get(f'/products/{self.product.slug}/')
        self.assertIn('This is a test block content', response.content.decode())
    
    def test_block_rendering_heading(self):
        """Heading blocks should be rendered"""
        ContentBlock.objects.create(
            product=self.product,
            block_type='heading',
            content={'text': 'Test Heading', 'level': 2},
            sort_order=1,
            is_active=True
        )
        response = self.client.get(f'/products/{self.product.slug}/')
        self.assertIn('Test Heading', response.content.decode())
    
    def test_inactive_blocks_not_rendered(self):
        """Inactive blocks should not be rendered"""
        ContentBlock.objects.create(
            product=self.product,
            block_type='text',
            content={'text': 'This should not appear'},
            sort_order=1,
            is_active=False
        )
        response = self.client.get(f'/products/{self.product.slug}/')
        self.assertNotIn('This should not appear', response.content.decode())
