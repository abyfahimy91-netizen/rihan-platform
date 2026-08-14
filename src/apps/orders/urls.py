from django.urls import path
from . import views

urlpatterns = [
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove_view, name='cart_remove'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/success/<str:order_number>/', views.order_success_view, name='order_success'),
    path('admin/orders/<int:order_id>/invoice/', views.admin_order_invoice_view, name='admin_order_invoice'),
    path('api/orders/create/', views.OrderCreateAPI.as_view(), name='api_order_create'),
]
