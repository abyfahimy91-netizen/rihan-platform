"""
ویوی سفارشی ورود پنل مدیریت ریحان
- «مرا به خاطر بسپار» ۳۰ روزه (D-095)
- قفل ضد Brute-Force مبتنی بر دیتابیس (فاز ۶): ۵ تلاش ناموفق در ۱۵ دقیقه
  بر اساس نام کاربری «یا» آی‌پی → پاسخ 403 بدون حتی رسیدن به چک رمز.
"""
import logging
from datetime import timedelta

from django.contrib.admin import site as admin_site
from django.http import HttpResponseForbidden
from django.utils import timezone

from .models import AdminLoginAttempt

logger = logging.getLogger(__name__)

REMEMBER_DAYS = 30
LOCK_THRESHOLD = 5          # حداکثر تلاش ناموفق
LOCK_WINDOW_MINUTES = 15    # پنجره شمارش
ATTEMPT_RETENTION_HOURS = 48


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = xff.split(',')[0].strip() if xff else ''
    return ip or request.META.get('REMOTE_ADDR', '') or 'unknown'


def _locked_info(username, ip):
    """اگر قفل فعال باشد، (True, ثانیه‌مانده) برمی‌گرداند."""
    since = timezone.now() - timedelta(minutes=LOCK_WINDOW_MINUTES)
    recent = AdminLoginAttempt.objects.filter(succeeded=False, created_at__gte=since)
    hits = recent.filter(
        models_q_username_or_ip(username, ip)
    )
    count = hits.count()
    if count < LOCK_THRESHOLD:
        return False, 0
    oldest = hits.order_by('created_at').first()
    unlock_at = oldest.created_at + timedelta(minutes=LOCK_WINDOW_MINUTES)
    wait_seconds = max(1, int((unlock_at - timezone.now()).total_seconds()))
    return True, wait_seconds


def models_q_username_or_ip(username, ip):
    from django.db.models import Q
    q = Q(ip=ip)
    if username:
        q |= Q(username__iexact=username)
    return q


def rihan_admin_login(request):
    """ورود ادمین: قفل Brute-Force + گزینه «مرا به خاطر بسپار»."""
    is_post = request.method == 'POST'

    if is_post:
        username = (request.POST.get('username') or '').strip()
        ip = _client_ip(request)
        locked, wait_s = _locked_info(username, ip)
        if locked:
            logger.warning('Admin login LOCKED user=%r ip=%s wait=%ss', username, ip, wait_s)
            minutes = max(1, wait_s // 60 + (1 if wait_s % 60 else 0))
            return HttpResponseForbidden(
                '<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8">'
                '<title>ورود موقتاً قفل است</title>'
                '<body style="font-family:sans-serif;text-align:center;padding-top:12vh;color:#333">'
                '<h2>🔒 ورود موقتاً قفل شده است</h2>'
                '<p>به‌دلیل تلاش‌های ناموفق مکرر، چند دقیقه دسترسی مسدود شد.</p>'
                '<p>لطفاً حدود <strong>%d دقیقه</strong> دیگر دوباره تلاش کنید.</p>'
                '</body></html>' % minutes
            )

    remember = is_post and request.POST.get('remember_me') == 'on'
    response = admin_site.login(request)

    if is_post:
        try:
            AdminLoginAttempt.objects.create(
                username=(request.POST.get('username') or '').strip()[:64],
                ip=_client_ip(request),
                succeeded=bool(request.user.is_authenticated),
            )
            cutoff = timezone.now() - timedelta(hours=ATTEMPT_RETENTION_HOURS)
            AdminLoginAttempt.objects.filter(created_at__lt=cutoff).delete()
        except Exception:
            logger.exception('admin login attempt logging failed')

    if remember and is_post and request.user.is_authenticated:
        try:
            request.session.set_expiry(REMEMBER_DAYS * 24 * 3600)
            request.session.save()
            logger.info(f"Admin session extended {REMEMBER_DAYS}d for {request.user.username}")
        except Exception:
            logger.exception("admin remember-me failed")

    return response
