"""
URLهای ماژول مالی (M6)
"""
from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # داشبورد ادمین (US-021)
    path('admin/', views.finance_dashboard_admin, name='admin_dashboard'),
    
    # داشبورد تأمین‌کننده (US-030)
    path('supplier/', views.finance_dashboard_supplier, name='supplier_dashboard'),
    
    # Export (US-031)
    path('export/excel/', views.finance_export_excel, name='export_excel'),
]
