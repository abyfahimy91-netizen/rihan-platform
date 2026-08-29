"""کانتکست پروسسور تنظیمات سایت — متغیر site_settings در همه قالب‌ها در دسترس است.

D-108: علاوه بر site_settings، نشان‌های اعتماد پارس‌شده (trust_badges) و
شماره واتساپ نرمال‌شده بین‌المللی (support_whatsapp) هم ارائه می‌شود.
"""
import re

from django.db.models import Sum

from src.core.fa import fa_digits

from .models import SiteSettings

_FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')


def _intl_digits(number):
    """شماره داخلی (۰۹...) یا هر فرمتی را به فرمت بین‌المللی بدون + (98...) می‌برد."""
    d = re.sub(r'\D', '', str(number or '').translate(_FA_DIGITS))
    if d.startswith('00'):
        d = d[2:]
    elif d.startswith('0'):
        d = '98' + d[1:]
    return d


def _parse_trust(raw):
    """خط‌های «عنوان | زیرنویس» را به لیست دیکشنری با آیکون چرخشی تبدیل می‌کند."""
    badges = []
    for i, line in enumerate(str(raw or '').splitlines()):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split('|')]
        badges.append({
            'icon': i % 4,
            'title': parts[0],
            'sub': parts[1] if len(parts) > 1 else '',
        })
    return badges


def site_settings(request):
    s = SiteSettings.load()
    return {
        "site_settings": s,
        "trust_badges": _parse_trust(s.trust_badges),
        "support_whatsapp": _intl_digits(s.whatsapp_number),
    }


def cart_badge(request):
    """🛒 تعداد اقلام سبد برای نشانِ قرمزِ آیکون سبد در هدر (D-115).

    فقط-خواندنی است و هرگز سبد نمی‌سازد (برخلاف get_or_create_cart) تا برای

    فقط-خواندنی است و هرگز سبد نمی‌سازد (برخلاف get_or_create_cart) تا برای
    هر بازدیدکننده ناشناس رکورد DB ساخته نشود. تا قبل از نخستین افزودن به سبد،
    بج مخفی است؛ بعد از آن تعداد واقعی روی همه صفحات سرور-رندر می‌شود،
    پس بلافاصله بعد از «افزودن به سبد» عدد درست دیده می‌شود.
    """
    from src.modules.order.models import Cart

    cart = None
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_active=True).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(
                session_key=session_key, user=None, is_active=True
            ).first()

    count = 0
    if cart:
        count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0

    return {
        'cart_item_count': count,
        'cart_item_count_fa': fa_digits(count),
    }


def notifications_badge(request):
    """🔔 تعداد اعلان‌های نخوانده کاربر برای زنگولهٔ هدر (D-119).

    فقط-خواندنی و فقط برای کاربرِ واردشده — صفر کوئری برای بازدیدکننده ناشناس.
    """
    count = 0
    if request.user.is_authenticated:
        try:
            from src.modules.order.models import UserNotification
            count = UserNotification.objects.filter(
                recipient=request.user, is_read=False).count()
        except Exception:
            count = 0
    return {
        'notif_unread': count,
        'notif_unread_fa': fa_digits(count) if count else '۰',
    }
