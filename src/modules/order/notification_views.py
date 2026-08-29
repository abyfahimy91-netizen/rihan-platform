"""
D-119 — اعلان‌های درون‌سایتی کاربر:
- صفحه کامل اعلان‌ها + خواندن تکی/همه
- JSON «اعلان‌های اخیر» برای بازشوی زنگولهٔ هدر
همه ویوها فقط برای کاربر واردشده؛ هر اعلان فقط از آنِ خودِ کاربر است.
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from src.core.fa import fa_digits
from .models import UserNotification

logger = logging.getLogger(__name__)

RECENT_LIMIT = 10


def _fa_ago(dt):
    """«۳ دقیقه پیش» فارسی — سبک و بدون وابستگی"""
    if not dt:
        return ''
    seconds = max(0, (timezone.now() - dt).total_seconds())
    if seconds < 60:
        return 'همین حالا'
    minutes = int(seconds // 60)
    if minutes < 60:
        return f'{fa_digits(minutes)} دقیقه پیش'
    hours = int(minutes // 60)
    if hours < 24:
        return f'{fa_digits(hours)} ساعت پیش'
    days = int(hours // 24)
    if days < 30:
        return f'{fa_digits(days)} روز پیش'
    from src.core.fa import jalali_date
    return jalali_date(dt)


def _serialize(n):
    return {
        'id': str(n.pk),
        'kind': n.kind,
        'title': n.title,
        'body': n.body,
        'url': n.url,
        'is_read': n.is_read,
        'ago': _fa_ago(n.created_at),
    }


def _unread_count(user):
    return UserNotification.objects.filter(recipient=user, is_read=False).count()


@login_required
def notifications_page(request):
    """صفحه کامل اعلان‌ها + خواندن تکی (POST)"""
    if request.method == 'POST':
        nid = request.POST.get('id', '')
        if nid:
            UserNotification.objects.filter(
                recipient=request.user, pk=nid, is_read=False
            ).update(is_read=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'unread': _unread_count(request.user)})
            messages.success(request, 'اعلان خوانده شد.')
        return redirect('order_pages:notifications_page')

    items = UserNotification.objects.filter(recipient=request.user)[:100]
    return render(request, 'order/notifications.html', {
        'notifications': items,
        'unread': _unread_count(request.user),
    })


@login_required
def notifications_recent(request):
    """JSON آخرین اعلان‌ها برای بازشوی زنگوله (هر کاربر فقط مال خودش)"""
    items = UserNotification.objects.filter(recipient=request.user)[:RECENT_LIMIT]
    return JsonResponse({
        'ok': True,
        'unread': _unread_count(request.user),
        'unread_fa': fa_digits(_unread_count(request.user)),
        'items': [_serialize(n) for n in items],
    })


@login_required
@require_POST
def notifications_read_all(request):
    """علامت‌گذاری همه اعلان‌ها به‌عنوان خوانده‌شده"""
    UserNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
            request.content_type == 'application/json':
        return JsonResponse({'ok': True, 'unread': 0})
    messages.success(request, 'همه اعلان‌ها خوانده شد.')
    return redirect('order_pages:notifications_page')


@login_required
@require_POST
def notifications_read_one(request, pk):
    """خواندن یک اعلان با POST و ریدایرکت به لینک آن (یا JSON)"""
    n = get_object_or_404(UserNotification, pk=pk, recipient=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'unread': _unread_count(request.user)})
    return redirect(n.url or 'order_pages:notifications_page')
