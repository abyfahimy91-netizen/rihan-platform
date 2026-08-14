from django.urls import path
from . import views

urlpatterns = [
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/profile/', views.profile_view, name='user_profile'),
    path('api/auth/otp/request/', views.RequestOTPAPI.as_view(), name='api_otp_request'),
    path('api/auth/otp/verify/', views.VerifyOTPAPI.as_view(), name='api_otp_verify'),
]
