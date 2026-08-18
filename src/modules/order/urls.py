from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'order'

# API Router (برای endpoints برنامه‌ای)
router = DefaultRouter()
router.register(r'cart', views.CartViewSet, basename='cart')
router.register(r'payment', views.PaymentViewSet, basename='payment')
router.register(r'addresses', views.AddressViewSet, basename='addresses')
router.register(r'orders', views.OrderViewSet, basename='orders')

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # API Routes (JSON) - برای ارتباط با فرانت‌اند
    # ═══════════════════════════════════════════════════════════════
    path('', include(router.urls)),
]
