"""
RIHAN Platform - Main URL Configuration

URL ها بر اساس:
- M13: هویت بصری
- M5: RBAC Authentication
- M14: Plugin Architecture
- Apps: catalog, orders, accounts, payments
"""
from modules.rbac.admin_site import rihan_admin
from django.contrib import admin
admin.autodiscover()

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from apps.catalog.sitemaps import ProductSitemap, CategorySitemap

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    # Custom Admin با Dashboard (M5)
    path('admin/', rihan_admin.urls),
    
    # M5: RBAC Authentication
    path('panel/', include('modules.rbac.urls'))
    
    # Sitemap (M1 - SEO)
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Apps
    path('', include('apps.core.urls')),
    path('', include('apps.catalog.urls')),
    path('', include('apps.orders.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.payments.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
