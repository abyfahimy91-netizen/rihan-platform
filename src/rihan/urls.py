from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from apps.catalog.sitemaps import ProductSitemap, CategorySitemap

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('apps.core.urls')),
    path('', include('apps.catalog.urls')),
    path('', include('apps.orders.urls')),
]
