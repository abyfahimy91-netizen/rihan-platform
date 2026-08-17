"""
Dashboard Views برای ماژول family_panel
منطبق بر US-017: مشاهده داشبورد
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..decorators import require_family
from ..services import DashboardService, FamilyService


@require_GET
@require_family
def dashboard_view(request):
    """
    داشبورد اصلی پنل خانواده.
    
    منطبق بر US-017:
    - خلاصه روزانه (سفارش‌ها، درآمد، موجودی)
    - نمودار فروش ۳۰ روزه
    - هشدار موجودی کم
    - سفارش‌های در انتظار تأیید
    """
    data = DashboardService.get_dashboard_data()
    alerts = DashboardService.get_alerts()
    
    # ثبت لاگ فعالیت
    FamilyService.log_activity(
        user=request.user,
        action='login',
        description='مشاهده داشبورد',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    
    # در MVP، JSON برمی‌گردانیم
    # در آینده، template HTML با HTMX اضافه می‌شود
    return JsonResponse({
        'success': True,
        'data': data,
        'alerts': alerts,
    }, json_dumps_params={"ensure_ascii": False})


@require_GET
@require_family
def dashboard_summary_view(request):
    """
    خلاصه سریع داشبورد (برای ویجت‌ها).
    """
    stats = DashboardService.get_summary_stats()
    
    return JsonResponse({
        'success': True,
        'data': stats,
    }, json_dumps_params={"ensure_ascii": False})


@require_GET
@require_family
def dashboard_alerts_view(request):
    """
    هشدارهای داشبورد.
    """
    alerts = DashboardService.get_alerts()
    
    return JsonResponse({
        'success': True,
        'alerts': alerts,
    }, json_dumps_params={"ensure_ascii": False})
