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
