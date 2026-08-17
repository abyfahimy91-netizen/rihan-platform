"""
URLs ماژول RBAC (M5)
منطبق بر ADR-003
"""
from django.urls import path
from . import views

app_name = 'rbac'

urlpatterns = [
    path('roles/', views.list_roles, name='list-roles'),
    path('roles/<str:code>/', views.role_detail, name='role-detail'),
    path('my-role/', views.my_role, name='my-role'),
    path('assign/', views.assign_role, name='assign-role'),
    path('revoke/', views.revoke_role, name='revoke-role'),
]
