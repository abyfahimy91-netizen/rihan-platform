from django.contrib import admin
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
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Apps (ترتیب مهم است - core اول برای home page)
    path('', include('apps.core.urls')),
    path('', include('apps.catalog.urls')),
    path('', include('apps.orders.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.payments.urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin customization
admin.site.site_header = "سامانه مدیریت و پنل خانواده ریهان"
admin.site.site_title = "پنل خانواده ریهان"
admin.site.index_title = "داشبورد مدیریت سفارش‌ها و کاتالوگ"
