"""
Tests for SEO features (sitemap.xml, robots.txt)
"""
from django.test import TestCase
from django.urls import reverse
from src.modules.catalog.models import Product, Category, Supplier


class SitemapTest(TestCase):
    """Test sitemap.xml functionality"""
    
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
    
    def test_sitemap_contains_active_products(self):
        """Sitemap should contain active products"""
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertIn('test-product', response.content.decode())
    
    def test_sitemap_excludes_inactive_products(self):
        """Sitemap should not contain inactive products"""
        self.product.status = 'inactive'
        self.product.save()
        response = self.client.get('/sitemap.xml')
        self.assertNotIn('test-product', response.content.decode())
    
    def test_robots_txt(self):
        """robots.txt should be accessible"""
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sitemap:', response.content.decode())

    def test_sitemap_includes_faq_and_policy(self):
        """Sitemap should include faq and return-policy pages"""
        response = self.client.get('/sitemap.xml')
        content = response.content.decode()
        self.assertIn('/faq/', content)
        self.assertIn('/return-policy/', content)

    def test_llms_txt(self):
        """llms.txt should be accessible and list active products"""
        response = self.client.get('/llms.txt')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('rihan360.ir', content)
        self.assertIn('test-product', content)
