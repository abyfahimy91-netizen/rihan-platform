"""
URLs صفحات HTML ماژول Auth (ورود/ثبت‌نام/پروفایل)
"""
from django.urls import path
from . import page_views

app_name = 'auth_pages'

urlpatterns = [
    path('login/', page_views.login_page_view, name='login'),
    # D-106: ثبت‌نام با رمز عبور (مسیر موازی بدون پیامک)
    path('register/', page_views.register_page_view, name='register'),
    path('profile/', page_views.profile_view, name='profile'),
    path('logout/', page_views.logout_view, name='logout'),
]
