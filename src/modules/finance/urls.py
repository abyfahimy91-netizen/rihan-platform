"""
URLهای ماژول مالی (D-113)
"""
from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # داشبورد مالی ادمین
    path('admin/', views.finance_dashboard_admin, name='admin_dashboard'),

    # حساب من (تامین‌کننده)
    path('supplier/', views.finance_dashboard_supplier, name='supplier_dashboard'),

    # خروجی CSV (ادمین)
    path('export/csv/', views.finance_export_csv, name='export_csv'),
]
