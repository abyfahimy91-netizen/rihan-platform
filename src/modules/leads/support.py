# -*- coding: utf-8 -*-
"""D-126: اتصال هویت به سرنخ‌ها بدون اصطکاک.

لایه ۱: دکمهٔ شناور «پاسخ سریع در واتساپ» — مشتری خودش پیام می‌دهد؛ پیام
شامل یک کد یکتاست که سرنخِ همان IP را پیدا می‌کند. وقتی ادمین پیام را در
واتساپ دید، در پنل شماره/نام را با همان کد ثبت می‌کند → هویت وصل می‌شود.
لایه ۲: link_registered_users — اعضای سایت که DeviceToken از یک IP دارند
به‌طور خودکار با سرنخ همان IP وصل می‌شوند (فقط پرکردن جاهای خالی).
"""
import secrets

from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages

from .models import VisitorLead

_CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # بدون 0/O و 1/I


def generate_code():
    return ''.join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


def get_client_ip(request):
    """همان منطق core.middleware._get_client_ip: X-Forwarded-For اول."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def support_code_view(request):
    """GET ajax از دکمهٔ شناور: کد اتصال + لینک واتساپ آماده می‌دهد."""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'error': 'bad-request'}, status=400)
    from src.modules.pages.models import SiteSettings
    s = SiteSettings.objects.first()
    intl = (s and getattr(s, 'whatsapp_number', '') or '').strip()
    if not intl:
        return JsonResponse({'ok': False, 'error': 'whatsapp-not-configured'}, status=404)
    ip = get_client_ip(request)
    if not ip or ip == 'testserver':
        return JsonResponse({'ok': False, 'error': 'no-ip'}, status=400)
    lead = VisitorLead.objects.filter(ip=ip).first()
    created = False
    if lead is None:
        lead = VisitorLead.objects.create(ip=ip, stage=VisitorLead.Stage.CART,
                                          stage_rank=3, is_hot=True,
                                          city='واتساپ', isp='—')
        created = True
    if not lead.link_code:
        lead.link_code = generate_code()
        lead.save(update_fields=['link_code'])
    import urllib.parse
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
