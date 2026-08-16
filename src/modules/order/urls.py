from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet, PaymentViewSet, AddressViewSet, OrderViewSet

app_name = 'order'

router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'payment', PaymentViewSet, basename='payment')
router.register(r'addresses', AddressViewSet, basename='addresses')
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),
]
