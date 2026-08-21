from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap

from src.modules.catalog.sitemaps import ProductSitemap, StaticViewSitemap
from src.modules.catalog.seo_views import robots_txt

sitemaps = {
    'products': ProductSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('supplier/', include('src.modules.supplier_panel.urls')),
    # SEO endpoints (D-079)
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    
    # Catalog at root (Homepage)
    path('', include('src.modules.catalog.urls')),
    # Order Pages (HTML) - مسیرهای زیبا برای مشتری
    path('order/', include('src.modules.order.page_urls')),
    
    # Reviews (M8 - US-009)
    path('reviews/', include('src.modules.reviews.urls')),
    
    # Leads (M9 - US-010)
    path('leads/', include('src.modules.leads.urls')),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Finance (M6)
    path('finance/', include('src.modules.finance.urls')),

    # API endpoints
    path('api/v1/catalog/', include('src.modules.catalog.urls_api')),
    path('api/v1/order/', include('src.modules.order.urls')),
    path('api/v1/auth/', include('src.modules.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
