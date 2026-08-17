"""
Activity Log Views برای ماژول family_panel
منطبق بر US-026: مشاهده لاگ فعالیت‌ها
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import timedelta

from ..decorators import require_family
from ..models import ActivityLog
from ..serializers import ActivityLogSerializer


@require_GET
@require_family
def activity_log_list(request):
    """
    لیست لاگ‌های فعالیت.
    
    منطبق بر US-026:
    - چه کسی + چه کاری + چه زمانی + از کجا
    - فیلتر بر اساس کاربر و بازه زمانی
    
    Query Params:
        - user_id: فیلتر بر اساس کاربر
        - action: فیلتر بر اساس نوع عملیات
        - days: بازه زمانی (روز)
        - limit: تعداد نتایج (پیش‌فرض: ۵۰)
    """
    # فیلترها
    user_id = request.GET.get('user_id')
    action = request.GET.get('action')
    days = request.GET.get('days', '30')
    limit = int(request.GET.get('limit', '50'))
    
    try:
        days = int(days)
    except ValueError:
        days = 30
    
    # Query base
    logs = ActivityLog.objects.all()
    
    # فیلتر بر اساس بازه زمانی
    if days > 0:
        cutoff = timezone.now() - timedelta(days=days)
        logs = logs.filter(created_at__gte=cutoff)
    
    # فیلتر بر اساس کاربر
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    # فیلتر بر اساس نوع عملیات
    if action:
        logs = logs.filter(action=action)
    
    # مرتب‌سازی و محدودسازی
    logs = logs.order_by('-created_at')[:limit]
    
    serializer = ActivityLogSerializer(logs, many=True)
    
    return JsonResponse({
        'success': True,
        'logs': serializer.data,
        'count': len(serializer.data),
        'filters': {
            'user_id': user_id,
            'action': action,
            'days': days,
            'limit': limit,
        },
    }, json_dumps_params={'ensure_ascii': False})


@require_GET
@require_family
def activity_log_stats(request):
    """
    آمار لاگ‌های فعالیت.
    
    Returns:
        - تعداد کل لاگ‌ها
        - تعداد بر اساس نوع عملیات
        - تعداد بر اساس کاربر
    """
    days = int(request.GET.get('days', '30'))
    cutoff = timezone.now() - timedelta(days=days)
    
    logs = ActivityLog.objects.filter(created_at__gte=cutoff)
    
    # آمار بر اساس نوع عملیات
    action_stats = {}
    for action_choice, action_label in ActivityLog.ACTION_CHOICES:
        count = logs.filter(action=action_choice).count()
        if count > 0:
            action_stats[action_choice] = {
                'label': action_label,
                'count': count,
            }
    
    # آمار بر اساس کاربر
    user_stats = {}
    for log in logs:
        user_key = log.user.username
        if user_key not in user_stats:
            user_stats[user_key] = {
                'name': f"{log.user.first_name} {log.user.last_name}" if log.user.first_name else log.user.username,
                'count': 0,
            }
        user_stats[user_key]['count'] += 1
    
    return JsonResponse({
        'success': True,
        'total': logs.count(),
        'period_days': days,
        'by_action': action_stats,
        'by_user': user_stats,
    }, json_dumps_params={'ensure_ascii': False})
