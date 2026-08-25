"""
URLهای پنل تأمین‌کننده (D-105 — مرسوله‌محور)
"""
from django.urls import path
from . import views

app_name = 'supplier_panel'

urlpatterns = [
    path('', views.supplier_dashboard, name='dashboard'),
    path('shipments/', views.shipment_list, name='shipment_list'),
    path('shipments/<uuid:pk>/', views.shipment_detail, name='shipment_detail'),
]
