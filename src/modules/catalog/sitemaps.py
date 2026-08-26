"""
Sitemaps for Rihan Platform (D-079 - SEO from Day One)
Generates dynamic sitemap.xml for all active products
"""
from django.contrib.sitemaps import Sitemap
from .models import Product


class ProductSitemap(Sitemap):
    """Sitemap for active products"""
    changefreq = 'weekly'
    priority = 0.8
    protocol = 'https'
    
    def items(self):
        return Product.objects.filter(
            status='active',
            deleted_at__isnull=True
        ).order_by('-updated_at')
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return f'/products/{obj.slug}/'


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.5
    changefreq = 'monthly'
    protocol = 'https'
    
    def items(self):
        return ['home', 'about', 'contact', 'faq', 'return-policy']

    def location(self, item):
        urls = {
            'home': '/',
            'about': '/about/',
            'contact': '/contact/',
            'faq': '/faq/',
            'return-policy': '/return-policy/',
        }
        return urls.get(item, '/')
