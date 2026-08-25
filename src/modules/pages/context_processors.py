"""کانتکست پروسسور تنظیمات سایت — متغیر site_settings در همه قالب‌ها در دسترس است.

D-108: علاوه بر site_settings، نشان‌های اعتماد پارس‌شده (trust_badges) و
شماره واتساپ نرمال‌شده بین‌المللی (support_whatsapp) هم ارائه می‌شود.
"""
import re

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
