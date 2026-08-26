from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap

from src.modules.catalog.sitemaps import ProductSitemap, StaticViewSitemap
from src.modules.catalog.seo_views import robots_txt, llms_txt

import src.modules.auth.admin_login  # noqa: E402 - ورود ادمین با یادآوری دستگاه

sitemaps = {
    'products': ProductSitemap,
    'static': StaticViewSitemap,
}


# 🌿 برندینگ پنل مدیریت ریحان
admin.site.site_header = "🌿 پنل مدیریت ریحان"
admin.site.site_title = "مدیریت ریحان"
admin.site.index_title = "کنترل کامل فروشگاه — همه‌چیز از اینجا قابل مدیریت است"

urlpatterns = [
    path('supplier/', include('src.modules.supplier_panel.urls')),
    # SEO endpoints (D-079)
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('llms.txt', llms_txt, name='llms_txt'),
    
    # Catalog at root (Homepage)
    path('', include('src.modules.catalog.urls')),
    # Order Pages (HTML) - مسیرهای زیبا برای مشتری
    path('order/', include('src.modules.order.page_urls')),
    
    # Reviews (M8 - US-009)
    path('reviews/', include('src.modules.reviews.urls')),
    
    # Leads (M9 - US-010)
    path('leads/', include('src.modules.leads.urls')),
    
    # Pages (M12) - About, Contact, Return Policy
    path('', include('src.modules.pages.urls')),
    
    # Admin
    path('admin/login/', src.modules.auth.admin_login.rihan_admin_login),  # ورود ادمین + «مرا به خاطر بسپار» (D-095)
    path('admin/', admin.site.urls),
    
    # Finance (M6)
    path('finance/', include('src.modules.finance.urls')),

    # API endpoints
    path('api/v1/catalog/', include('src.modules.catalog.urls_api')),
    path('api/v1/order/', include('src.modules.order.urls')),
    path('api/v1/auth/', include('src.modules.auth.urls')),
    # HTML pages for login/register/profile
    path('accounts/', include('src.modules.auth.page_urls')),
]

# --- media served always (nginx proxies /media/ directly; this is the fallback) ---
from django.urls import re_path
from django.views.static import serve as _media_serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', _media_serve, {'document_root': settings.MEDIA_ROOT}),
]
