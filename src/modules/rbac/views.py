"""
Views ماژول RBAC (M5)
منطبق بر ADR-003 (API Strategy) و D-017

Endpoints:
- GET  /api/v1/rbac/roles/           - لیست نقش‌ها
- GET  /api/v1/rbac/roles/<code>/    - جزئیات یک نقش
- GET  /api/v1/rbac/my-role/         - نقش اصلی کاربر فعلی
- POST /api/v1/rbac/assign/          - اعطای نقش (فقط admin)
- POST /api/v1/rbac/revoke/          - لغو نقش (فقط admin)
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Role, UserRole
from .services import RoleService
from .decorators import require_admin


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_roles(request):
    """لیست تمام نقش‌ها (برای کاربران احراز هویت شده)"""
    roles = Role.objects.all().order_by('name')
    data = [
        {
            'code': role.code,
            'name': role.name,
            'description': role.description,
            'permissions_count': len(role.permissions),
            'is_system': role.is_system,
        }
        for role in roles
    ]
    return Response({'roles': data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_detail(request, code):
    """جزئیات یک نقش"""
    role = RoleService.get_role_by_code(code)
    if not role:
        return Response(
            {'error': f'نقش {code} یافت نشد'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    data = {
        'code': role.code,
        'name': role.name,
        'description': role.description,
        'permissions': role.permissions,
        'is_system': role.is_system,
        'users_count': role.user_roles.count(),
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_role(request):
    """نقش اصلی کاربر فعلی"""
    primary_role = RoleService.get_user_primary_role(request.user)
    
    if not primary_role:
        return Response(
            {'role': None, 'message': 'هیچ نقشی به شما اعطا نشده است'},
            status=status.HTTP_200_OK
        )
    
    data = {
        'role': {
            'code': primary_role.code,
            'name': primary_role.name,
            'description': primary_role.description,
            'permissions': primary_role.permissions,
        }
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def assign_role(request):
    """
    اعطای نقش به کاربر (فقط admin).
    
    Body:
        {
            "username": "09121234567",
            "role_code": "family_admin",
            "is_primary": true
        }
    """
    username = request.data.get('username')
    role_code = request.data.get('role_code')
    is_primary = request.data.get('is_primary', True)
    
    if not username or not role_code:
        return Response(
            {'error': 'username و role_code الزامی است'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'error': f'کاربر {username} یافت نشد'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        user_role = RoleService.assign_role(
            user=user,
            role_code=role_code,
            granted_by=request.user,
            is_primary=is_primary
        )
        return Response({
            'message': f'نقش {role_code} به {username} اعطا شد',
            'is_primary': user_role.is_primary,
        }, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def revoke_role(request):
    """
    لغو نقش کاربر (فقط admin).
    
    Body:
        {
            "username": "09121234567",
            "role_code": "family_admin"
        }
    """
    username = request.data.get('username')
    role_code = request.data.get('role_code')
    
    if not username or not role_code:
        return Response(
            {'error': 'username و role_code الزامی است'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'error': f'کاربر {username} یافت نشد'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    success = RoleService.revoke_role(user, role_code)
    
    if success:
        return Response({
            'message': f'نقش {role_code} از {username} لغو شد',
        }, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': f'نقش {role_code} برای {username} یافت نشد'},
            status=status.HTTP_404_NOT_FOUND
        )
