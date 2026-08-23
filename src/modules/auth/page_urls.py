"""
URLs صفحات HTML ماژول Auth (ورود/ثبت‌نام/پروفایل)
"""
from django.urls import path
from . import page_views

app_name = 'auth_pages'

urlpatterns = [
    path('login/', page_views.login_page_view, name='login'),
    path('profile/', page_views.profile_view, name='profile'),
    path('logout/', page_views.logout_view, name='logout'),
]
