"""
URLs صفحات HTML ماژول Order (UI سبد خرید)
"""
from django.urls import path
from . import cart_views, tracking_views

app_name = 'order_pages'

urlpatterns = [
    path('cart/', cart_views.cart_page_view, name='cart_page'),
    path('cart/add/', cart_views.add_to_cart_view, name='add_to_cart_page'),
    path('cart/update/', cart_views.update_cart_item_view, name='update_cart_page'),
    path('cart/remove/', cart_views.remove_from_cart_view, name='remove_cart_page'),
    # Tracking & Payment (M7 + M2)
    path('lookup/', tracking_views.tracking_lookup_view, name='tracking_lookup'),
    path('tracking/<str:order_number>/', tracking_views.tracking_page_view, name='tracking_page'),
    path('payment/<str:order_number>/', tracking_views.payment_page_view, name='payment_page'),
]
