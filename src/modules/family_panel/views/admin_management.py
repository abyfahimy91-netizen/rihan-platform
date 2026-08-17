"""
Admin Management Views برای ماژول family_panel
منطبق بر US-025: مدیریت کاربران خانواده

نکته مهم (ADR-006):
- بدون رمز عبور (OTP فقط)
- کاربران با شماره موبایل اضافه می‌شوند
- ورود با OTP انجام می‌شود
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth import get_user_model

from ..decorators import require_family, require_main_admin
from ..services import FamilyService
from ..serializers import FamilyMemberSerializer, AddFamilyMemberSerializer

User = get_user_model()


@require_GET
@require_family
def list_family_members(request):
    """
    لیست اعضای خانواده.
    
    منطبق بر US-025:
    - نمایش همه اعضای خانواده
    - با نقش و وضعیت
    """
    members = FamilyService.get_family_members()
    serializer = FamilyMemberSerializer(members, many=True)
    
    return JsonResponse({
        'success': True,
        'members': serializer.data,
        'count': len(members),
    }, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_main_admin
def add_family_member(request):
    """
    افزودن عضو خانواده.
    
    منطبق بر US-025:
    - فقط ادمین اصلی بتواند کاربر بسازد
    - نام + نقش + موبایل (بدون رمز - OTP)
    
    Body:
        {
            "phone": "09121234567",
            "first_name": "نام",
            "last_name": "نام خانوادگی",
            "role_code": "family_admin"
        }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON نامعتبر است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    serializer = AddFamilyMemberSerializer(data=data)
    if not serializer.is_valid():
        return JsonResponse({
            'success': False,
            'errors': serializer.errors,
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    phone = serializer.validated_data['phone']
    first_name = serializer.validated_data['first_name']
    last_name = serializer.validated_data['last_name']
    role_code = serializer.validated_data['role_code']
    
    # بررسی تکراری نبودن
    if User.objects.filter(username=phone).exists():
        return JsonResponse({
            'success': False,
            'error': f'کاربر با شماره {phone} قبلاً ثبت شده است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    try:
        user = FamilyService.add_family_member(
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            role_code=role_code,
            granted_by=request.user,
        )
        
        # ثبت لاگ
        FamilyService.log_activity(
            user=request.user,
            action='admin_create',
            description=f"افزودن عضو خانواده: {first_name} {last_name}",
            entity_type='user',
            entity_id=str(user.pk),
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        return JsonResponse({
            'success': True,
            'message': f'عضو خانواده {first_name} {last_name} اضافه شد',
            'member': FamilyMemberSerializer(user).data,
        }, json_dumps_params={'ensure_ascii': False})
    
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=400, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_main_admin
def deactivate_family_member(request):
    """
    غیرفعال‌سازی عضو خانواده (حذف نرم).
    
    منطبق بر US-025:
    - غیرفعال‌سازی بدون حذف
    
    Body:
        {
            "user_id": 123
        }
    """
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({
            'success': False,
            'error': 'JSON نامعتبر است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    if not user_id:
        return JsonResponse({
            'success': False,
            'error': 'user_id الزامی است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'کاربر یافت نشد',
        }, status=404, json_dumps_params={'ensure_ascii': False})
    
    # جلوگیری از غیرفعال‌سازی خود
    if user.pk == request.user.pk:
        return JsonResponse({
            'success': False,
            'error': 'نمی‌توانید خودتان را غیرفعال کنید',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    FamilyService.deactivate_family_member(user, deactivated_by=request.user)
    
    return JsonResponse({
        'success': True,
        'message': f'کاربر {user.username} غیرفعال شد',
    }, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_main_admin
def reactivate_family_member(request):
    """
    فعال‌سازی مجدد عضو خانواده.
    
    Body:
        {
            "user_id": 123
        }
    """
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({
            'success': False,
            'error': 'JSON نامعتبر است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'کاربر یافت نشد',
        }, status=404, json_dumps_params={'ensure_ascii': False})
    
    user.is_active = True
    user.save(update_fields=['is_active'])
    
    # ثبت لاگ
    FamilyService.log_activity(
        user=request.user,
        action='admin_update',
        description=f"فعال‌سازی مجدد: {user.username}",
        entity_type='user',
        entity_id=str(user.pk),
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    
    return JsonResponse({
        'success': True,
        'message': f'کاربر {user.username} فعال شد',
    }, json_dumps_params={'ensure_ascii': False})
