from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/catalog/', include('src.modules.catalog.urls')),
    path('api/v1/order/', include('src.modules.order.urls')),
    path('api/v1/auth/', include('src.modules.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
