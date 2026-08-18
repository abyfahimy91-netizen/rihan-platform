"""
Order Page URLs - مسیرهای HTML برای مشتری
جدا از API URLs برای تمایز بین endpoints برنامه‌ای و صفحات کاربری

Namespace: order_pages (برای جلوگیری از تداخل با API router)
"""
from django.urls import path
from . import page_views

app_name = 'order_pages'  # Namespace جداگانه

urlpatterns = [
    path(
        'payment/<str:order_number>/',
        page_views.payment_submit_page,
        name='payment_submit'
    ),
    path(
        'tracking/<str:order_number>/',
        page_views.order_tracking_page,
        name='order_tracking'
    ),
    path(
        'success/<str:order_number>/',
        page_views.payment_success_page,
        name='payment_success'
    ),
]
