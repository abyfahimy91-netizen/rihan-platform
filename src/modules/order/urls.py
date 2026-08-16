from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet, PaymentViewSet

app_name = 'order'

router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'payment', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
]
