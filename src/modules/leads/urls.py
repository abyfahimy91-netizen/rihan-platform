"""
URLs for Leads Module (M9)
"""
from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    # General lead form (no product)
    path(
        'register/',
        views.lead_form_page,
        name='lead_form'
    ),
    
    # Lead form for specific product
    path(
        'register/<str:product_slug>/',
        views.lead_form_page,
        name='lead_form_product'
    ),
    
    # API endpoint (AJAX)
    path(
        'api/submit/',
        views.submit_lead_api,
        name='submit_lead_api'
    ),
]

# D-125: پنل ردیابی سرنخ‌های بازدید (staff-only)
urlpatterns += [
    path('panel/', views.lead_panel, name='panel'),
    path('panel/refresh/', views.lead_panel_refresh, name='panel_refresh'),
    path('panel/status/<uuid:pk>/', views.lead_panel_status, name='panel_status'),
    path('panel/export/csv/', views.lead_panel_csv, name='panel_csv'),
]

# ── D-126: کد اتصال واتساپ + اتصال سریع در پنل ──
from . import support

urlpatterns += [
    path('support-code/', support.support_code_view, name='support_code'),
    path('panel/link/<uuid:pk>/', support.panel_link_lead, name='panel_link'),
]
