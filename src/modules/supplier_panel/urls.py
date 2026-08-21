"""
URLهای پنل تأمین‌کننده (M4)
"""
from django.urls import path
from . import views

app_name = 'supplier_panel'

urlpatterns = [
    path('', views.supplier_dashboard, name='dashboard'),
    path('orders/', views.supplier_order_list, name='order_list'),
    path('orders/<uuid:order_id>/track/', views.submit_tracking_code, name='submit_tracking'),
]
