"""
URLs ماژول احراز هویت
منطبق بر ADR-006 و ADR-003
"""
from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    # OTP Endpoints (ADR-006 بخش ۲)
    path('otp/request/', views.otp_request, name='otp-request'),
    path('otp/verify/', views.otp_verify, name='otp-verify'),
]
