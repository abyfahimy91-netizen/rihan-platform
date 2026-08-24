"""
ویوی سفارشی ورود پنل مدیریت ریحان — افزودن «مرا به خاطر بسپار» به ورود ادمین
منطبق بر D-095: با تیک زدن، نشست ادمین به‌جای بسته‌شدن مرورگر، ۳۰ روز دوام می‌آورد.
"""
import logging

from django.contrib.admin import site as admin_site

logger = logging.getLogger(__name__)

REMEMBER_DAYS = 30


def rihan_admin_login(request):
    """ورود ادمین با گزینه «مرا به خاطر بسپار» — بقیه رفتار همان ورود پیش‌فرض جنگو است."""
    remember = request.method == 'POST' and request.POST.get('remember_me') == 'on'
    response = admin_site.login(request)

    if remember and request.method == 'POST' and request.user.is_authenticated:
        try:
            request.session.set_expiry(REMEMBER_DAYS * 24 * 3600)
            request.session.save()
            logger.info(f"Admin session extended {REMEMBER_DAYS}d for {request.user.username}")
        except Exception:
            logger.exception("admin remember-me failed")

    return response
