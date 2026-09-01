# -*- coding: utf-8 -*-
"""D-126/D-127: اتصال هویت به سرنخ‌ها بدون اصطکاک + سخت‌سازی امنیتی.

لایه ۱: دکمهٔ شناور «پاسخ سریع در واتساپ» — مشتری خودش پیام می‌دهد؛ پیام
شامل یک کد یکتاست که سرنخِ همان IP را پیدا می‌کند. وقتی ادمین پیام را در
واتساپ دید، در پنل شماره/نام را با همان کد ثبت می‌کند → هویت وصل می‌شود.
لایه ۲: link_registered_users — اعضای سایت که DeviceToken از یک IP دارند
به‌طور خودکار با سرنخ همان IP وصل می‌شوند (فقط پرکردن جاهای خالی).

سخت‌سازی (D-127):
- IP واقعی از X-Real-IP (nginx، جعل‌ناپذیر) — کلاینت با XFF جعلی نمی‌تواند
  سرنخ‌های تقلبی بسازد یا کد سرنخ دیگران را بگیرد.
- throttle دو لایه: هر IP حداکثر 30 درخواست/ساعت + سراسری 600/ساعت.
- سقف کل سرنخ‌ها برای جلوگیری از پرشدن دیتابیس.
- کلید خاموش‌کننده: SiteSettings.wa_fab_enabled (پنل ادمین).
"""
import secrets
import urllib.parse

from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect

from .models import VisitorLead

_CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # بدون 0/O و 1/I
RL_PER_IP = 30        # درخواست کد در ساعت برای هر IP واقعی
RL_GLOBAL = 600       # درخواست کد در ساعت کل
MAX_LEADS = 5000      # سقف کل سرنخ‌ها (ضد سیل دیتابیس)


def generate_code():
    return ''.join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


def get_client_ip(request):
    """IP واقعی: X-Real-IP (جعل‌ناپذیر، ست‌شده توسط nginx خودمان) →
    آخرین عنصر XFF (افزودهٔ nginx خودمان) → REMOTE_ADDR.
    ⚠️ هرگز اولین عنصر XFF را باور نکن — توسط کلاینت جعل‌پذیر است."""
    ip = request.META.get('HTTP_X_REAL_IP')
    if ip:
        return ip.strip()
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


def _throttle(request):
    """دو شمارندهٔ ساعتی؛ False یعنی درخواست رد شود."""
    ip = get_client_ip(request)
    k_ip = f'wa_code_rl:{ip}'
    k_all = 'wa_code_rl:__global__'
    n_ip = cache.get(k_ip) or 0
    n_all = cache.get(k_all) or 0
    if n_ip >= RL_PER_IP or n_all >= RL_GLOBAL:
        return False
    cache.set(k_ip, n_ip + 1, 3600)
    cache.set(k_all, n_all + 1, 3600)
    return True


def support_code_view(request):
    """GET ajax از دکمهٔ شناور: کد اتصال + لینک واتساپ آماده می‌دهد."""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'bad-request'}, status=400)
    from src.modules.pages.models import SiteSettings
    s = SiteSettings.load()
    if not getattr(s, 'wa_fab_enabled', False):
        # مثل «پیکربندی نشده» جواب بده — وجود قابلیت لو نرود
        return JsonResponse({'ok': False, 'error': 'not-configured'}, status=404)
    intl = (getattr(s, 'whatsapp_number', '') or '').strip()
    if not intl:
        return JsonResponse({'ok': False, 'error': 'not-configured'}, status=404)
    if not _throttle(request):
        return JsonResponse({'ok': False, 'error': 'too-many-requests'}, status=429)
    ip = get_client_ip(request)
    if not ip or ip == 'testserver':
        return JsonResponse({'ok': False, 'error': 'no-ip'}, status=400)
    lead = VisitorLead.objects.filter(ip=ip).first()
    created = False
    if lead is None:
        # ضد سیل: سقف کل ردیف‌ها
        if VisitorLead.objects.count() >= MAX_LEADS:
            return JsonResponse({'ok': False, 'error': 'limit-reached'}, status=429)
        lead = VisitorLead.objects.create(ip=ip, stage=VisitorLead.Stage.PRODUCT,
                                          stage_rank=2, is_hot=False,
                                          city='واتساپ', isp='—')
        created = True
    if not lead.link_code:
        lead.link_code = generate_code()
        lead.save(update_fields=['link_code'])
    msg = f'سلام 👋 (کد {lead.link_code})'
    return JsonResponse({'ok': True, 'created': created, 'code': lead.link_code,
                         'wa_url': f'https://wa.me/{intl}?text={urllib.parse.quote(msg)}'})


def _normalize_phone(raw):
    """نرمال‌سازی شماره با address_service (D-120) با فال‌بک دستی."""
    try:
        from src.modules.order.address_service import normalize_phone
        return normalize_phone(raw)
    except Exception:
        import re as _re
        d = _re.sub(r'[^0-9]', '', str(raw or '').translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')))
        if d.startswith('0098'):
            d = '0' + d[4:]
        elif d.startswith('98') and len(d) == 12:
            d = '0' + d[2:]
        elif d.startswith('9') and len(d) == 10:
            d = '0' + d
        return d if d.startswith('09') and len(d) == 11 else ''


def panel_link_lead(request, pk):
    """ادمین کد داخل پیام واتساپ را جستجو می‌کند و شماره/نام را وصل می‌کند.

    GET ?code=XXXX → یافتن و نمایش فرم؛ POST → ثبت شماره/نام.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, 'دسترسی غیرمجاز.')
        return redirect('/')
    lead = VisitorLead.objects.filter(pk=pk).first()
    if not lead:
        messages.error(request, 'سرنخ پیدا نشد.')
        return redirect('leads:panel')
    if request.method == 'POST':
        phone = _normalize_phone(request.POST.get('phone') or '')
        name = (request.POST.get('name') or '').strip()[:100]
        if not phone:
            messages.error(request, 'شماره موبایل معتبر نیست (باید 09xxxxxxxxx باشد).')
        else:
            lead.phone = phone
            if name:
                lead.name = name
            if lead.status == VisitorLead.LeadStatus.NEW:
                lead.status = VisitorLead.LeadStatus.CONTACTED
            lead.save(update_fields=['phone', 'name', 'status', 'updated_at'])
            messages.success(request, f'🔗 {lead.ip} به {phone} وصل شد — حالا می‌توانی تماس بگیری.')
    return redirect('/leads/panel/' + ('?code=' + lead.link_code if lead.link_code else ''))


def link_registered_users():
    """لایهٔ خودکار: اعضایی که DeviceToken از IP یک سرنخ دارند → وصل کن.

    فقط جاهای خالی پر می‌شود؛ هرگز شمارهٔ موجود را بازنویسی نمی‌کند.
    Returns: تعداد اتصال‌های جدید
    """
    from django.apps import apps
    DeviceToken = apps.get_model('rihan_auth', 'DeviceToken')
    linked = 0
    for t in (DeviceToken.objects.exclude(ip_address__isnull=True)
              .select_related('user')):
        # ⚠️ GenericIPAddressField: هرگز با '' مقایسه نشود — فقط isnull
        user = t.user
        phone = _normalize_phone(user.get_username())
        if not phone:
            continue
        name = (getattr(user, 'first_name', '') + ' ' + getattr(user, 'last_name', '')).strip()
        for lead in VisitorLead.objects.filter(ip=t.ip_address).exclude(phone=phone):
            if lead.phone and lead.phone != phone:
                continue  # به نفر دیگری وصل است؛ دست نمی‌زنیم
            lead.phone = phone
            if name:
                lead.name = name
            linked += 1
            lead.save(update_fields=['phone', 'name', 'updated_at'])
    return linked
