"""
Auth Page Views - صفحات HTML ورود/ثبت‌نام و پروفایل
منطبق بر D-095: احراز هویت دوکاناله (OTP پیامکی + رمز عبور) + یادآوری دستگاه

جریان ورود:
- کانال ۱ (پیشنهادی): شماره موبایل → کد ۶ رقمی پیامکی → ورود (ثبت‌نام خودکار)
- کانال ۲: شماره موبایل + رمز عبور (برای مواقع قطعی پیامک یا ترجیح کاربر)
- فراموشی رمز: شماره موبایل → کد پیامکی → تنظیم رمز جدید
- یادآوری دستگاه: کوکی امن ۳۰ روزه (HttpOnly) — بدون نیاز به ورود مجدد
- نام کاربری همه نقش‌ها = شماره موبایل
"""
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .services.device_service import DeviceService
from .services.otp_service import OtpService
from .services.password_service import PasswordService

logger = logging.getLogger(__name__)

User = get_user_model()

SESSION_PHONE_KEY = 'otp_pending_phone'
SESSION_RESET_PHONE_KEY = 'reset_pending_phone'
SESSION_RESET_USER_KEY = 'reset_verified_uid'

DEVICE_COOKIE = 'rihan_device_token'
DEVICE_COOKIE_DAYS = 30


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


def _merge_guest_cart(request, user):
    """اتصال سبد مهمان فعلی به کاربر پس از ورود (ادامه سفر خرید بدون گم شدن سبد)"""
    try:
        from src.modules.order.models import Cart
        key = getattr(request.session, 'session_key', None)
        if key:
            Cart.objects.filter(session_key=key, user__isnull=True, is_active=True).update(user=user)
            guest_cart = Cart.objects.filter(session_key=key, user=user, is_active=True).first()
            other = Cart.objects.filter(user=user, is_active=True).exclude(pk=guest_cart.pk if guest_cart else None).order_by('-updated_at').first() if guest_cart else None
            if guest_cart and other:
                for item in guest_cart.items.all():
                    from src.modules.order.services import add_to_cart
                    try:
                        add_to_cart(other, str(item.product.id), item.quantity)
                    except Exception:
                        pass
                guest_cart.is_active = False
                guest_cart.save()
    except Exception:
        logger.exception("cart merge failed")


def _remember_device(response, request, user):
    """ایجاد توکن دستگاه + ست کوکی امن ۳۰ روزه (فقط اگر کاربر تیک یادآوری زده باشد)"""
    if request.POST.get('remember') != '1':
        return
    try:
        token = DeviceService.create_device_token(
            user,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            ip_address=_client_ip(request),
        )
        response.set_cookie(
            DEVICE_COOKIE, token,
            max_age=DEVICE_COOKIE_DAYS * 24 * 3600,
            httponly=True, secure=True, samesite='Lax', path='/',
        )
    except Exception:
        logger.exception("device token creation failed")


# ══════════════════════════ ورود / ثبت‌نام ══════════════════════════

def login_page_view(request):
    """ورود دوکاناله با راهنمای گام‌به‌گام (سفر مشتری: ۱ شماره ← ۲ تأیید ← ۳ ورود)"""
    if request.user.is_authenticated:
        return redirect('auth_pages:profile')

    next_url = request.GET.get('next') or request.POST.get('next') or '/'
    ip = _client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')[:255]

    # مقادیر پیش‌فرض context
    ctx = {
        'step': 'phone',          # phone | code | password | forgot | reset_code | set_password
        'method': 'otp',          # otp | password (تب فعال)
        'phone_display': '',
        'next_url': next_url,
        'code_error': False,
        'resend_seconds': 120,
    }

    if request.method == 'POST':
        action = request.POST.get('action', '')
        method = request.POST.get('method', 'otp')
        ctx['method'] = method

        # ── مرحله ۱: درخواست کد پیامکی ──
        if action == 'request_otp':
            raw_phone = (request.POST.get('phone') or '').strip()
            success, message, otp_code = OtpService.request_otp(raw_phone, ip)
            if success:
                is_valid, normalized = OtpService.validate_phone(raw_phone)
                request.session[SESSION_PHONE_KEY] = normalized
                request.session.set_expiry(600)
                ctx.update(step='code', phone_display=normalized)
                if otp_code:
                    messages.info(request, f'حالت آزمایشی: کد شما {otp_code} است.')
                else:
                    messages.success(request, 'کد تأیید پیامک شد. لطفاً صندوق پیامک را بررسی کنید. 📩')
            else:
                messages.error(request, message)
                ctx.update(step='phone', phone_display=raw_phone)

        # ── مرحله ۲: تأیید کد و ورود ──
        elif action == 'verify_otp':
            phone = request.session.get(SESSION_PHONE_KEY)
            code = ''.join(ch for ch in (request.POST.get('code') or '') if ch.isdigit())
            if not phone:
                messages.error(request, 'مهلت ورود منقضی شد. لطفاً دوباره شماره را وارد کنید.')
            else:
                success, message, user = OtpService.verify_otp(phone, code, ip)
                if success:
                    login(request, user)
                    request.session.pop(SESSION_PHONE_KEY, None)
                    _merge_guest_cart(request, user)
                    fname = (user.first_name or '').strip()
                    messages.success(request, f'خوش آمدید {fname}! 👋' if fname else 'خوش آمدید! 👋')
                    response = redirect(next_url if next_url.startswith('/') else '/')
                    _remember_device(response, request, user)
                    return response
                else:
                    messages.error(request, message)
                    ctx.update(step='code', phone_display=phone, code_error=True)

        # ── ورود با رمز عبور ──
        elif action == 'password_login':
            phone = (request.POST.get('phone') or '').strip()
            password = request.POST.get('password') or ''
            success, message, user = PasswordService.attempt_login(phone, password, ip, ua)
            if success:
                login(request, user)
                _merge_guest_cart(request, user)
                fname = (user.first_name or '').strip()
                messages.success(request, f'خوش آمدید {fname}! 👋' if fname else 'خوش آمدید! 👋')
                response = redirect(next_url if next_url.startswith('/') else '/')
                _remember_device(response, request, user)
                return response
            else:
                messages.error(request, message)
                ctx.update(step='password', phone_display=phone)

        # ── فراموشی رمز: مرحله ۱ (دریافت شماره و ارسال کد) ──
        elif action == 'forgot_request':
            raw_phone = (request.POST.get('phone') or '').strip()
            is_valid, normalized = OtpService.validate_phone(raw_phone)
            user = User.objects.filter(username=normalized).first() if is_valid else None
            # پیام یکسان برای شماره موجود/ناموجود (ضد Account Enumeration)
            if user and user.has_usable_password():
                success, message, _ = OtpService.request_otp(raw_phone, ip)
                if success:
                    request.session[SESSION_RESET_PHONE_KEY] = normalized
                    request.session.set_expiry(600)
                    ctx.update(step='reset_code', phone_display=normalized)
                    messages.success(request, 'کد تأیید برای بازنشانی رمز عبور پیامک شد. 📩')
                    return render(request, 'accounts/login.html', ctx)
            messages.info(request, 'اگر این شماره در سیستم ثبت شده باشد، کد بازنشانی برایتان پیامک می‌شود.')
            ctx.update(step='forgot', phone_display=raw_phone)

        # ── فراموشی رمز: مرحله ۲ (تأیید کد) ──
        elif action == 'verify_reset_code':
            phone = request.session.get(SESSION_RESET_PHONE_KEY)
            code = ''.join(ch for ch in (request.POST.get('code') or '') if ch.isdigit())
            if not phone:
                messages.error(request, 'مهلت بازنشانی منقضی شد. لطفاً دوباره تلاش کنید.')
                ctx['step'] = 'forgot'
            else:
                success, message, user = OtpService.verify_otp(phone, code, ip)
                if success:
                    request.session[SESSION_RESET_USER_KEY] = user.id
                    request.session[SESSION_RESET_PHONE_KEY] = phone
                    ctx.update(step='set_password', phone_display=phone)
                else:
                    messages.error(request, message)
                    ctx.update(step='reset_code', phone_display=phone, code_error=True)

        # ── فراموشی رمز: مرحله ۳ (رمز جدید) ──
        elif action == 'set_new_password':
            uid = request.session.get(SESSION_RESET_USER_KEY)
            phone = request.session.get(SESSION_RESET_PHONE_KEY)
            p1 = request.POST.get('password1') or ''
            p2 = request.POST.get('password2') or ''
            user = User.objects.filter(id=uid, username=phone).first() if uid and phone else None
            if user is None:
                messages.error(request, 'نشست بازنشانی منقضی شده است. لطفاً دوباره شروع کنید.')
                ctx['step'] = 'forgot'
            else:
                ok, message = PasswordService.set_password(user, p1, p2)
                if ok:
                    request.session.pop(SESSION_RESET_USER_KEY, None)
                    request.session.pop(SESSION_RESET_PHONE_KEY, None)
                    messages.success(request, 'رمز عبور جدید ذخیره شد. حالا وارد شوید. 🔑')
                    ctx.update(step='password', phone_display=phone)
                else:
                    messages.error(request, message)
                    ctx.update(step='set_password', phone_display=phone)

    # حالت‌های GET: تب رمز عبور، فراموشی رمز، و بازگشت به مرحله کد
    if request.method == 'GET':
        gstep = request.GET.get('step')
        if gstep == 'code':
            phone = request.session.get(SESSION_PHONE_KEY)
            if phone:
                ctx.update(step='code', phone_display=phone)
        elif gstep == 'forgot':
            ctx.update(step='forgot', method='password')
        elif gstep == 'reset_code':
            phone = request.session.get(SESSION_RESET_PHONE_KEY)
            if phone:
                ctx.update(step='reset_code', phone_display=phone, method='password')
        if request.GET.get('method') == 'password' and ctx['step'] == 'phone':
            ctx['step'] = 'password'

    return render(request, 'accounts/login.html', ctx)


# ══════════════════════════ پروفایل ══════════════════════════

ORDER_STATUS_FA = {
    'DRAFT': 'پیش‌نویس', 'PENDING': 'در انتظار پرداخت', 'PAID': 'پرداخت شده',
    'PROCESSING': 'در حال آماده‌سازی', 'SHIPPED': 'ارسال شده', 'DELIVERED': 'تحویل شده',
    'CANCELLED': 'لغو شده', 'RETURNED': 'مرجوع شده',
}


@login_required
def profile_view(request):
    """پروفایل کاربر: اطلاعات + امنیت (رمز) + دستگاه‌های من + تاریخچه سفارش‌ها"""
    u = request.user

    if request.method == 'POST':
        action = request.POST.get('action', 'save_info')

        if action == 'save_info':
            u.first_name = (request.POST.get('first_name') or '').strip()
            u.last_name = (request.POST.get('last_name') or '').strip()
            email = (request.POST.get('email') or '').strip()
            if email and '@' not in email:
                messages.error(request, 'ایمیل معتبر نیست.')
            else:
                u.email = email
                u.save(update_fields=['first_name', 'last_name', 'email'])
                messages.success(request, 'اطلاعات حساب ذخیره شد ✅')

        elif action == 'set_password':
            p1 = request.POST.get('password1') or ''
            p2 = request.POST.get('password2') or ''
            ok, message = PasswordService.set_password(u, p1, p2)
            (messages.success if ok else messages.error)(request, message)

        elif action == 'change_password':
            current = request.POST.get('current_password') or ''
            p1 = request.POST.get('password1') or ''
            p2 = request.POST.get('password2') or ''
            ok, message = PasswordService.change_password(u, current, p1, p2)
            (messages.success if ok else messages.error)(request, message)

        elif action == 'revoke_device':
            DeviceService.revoke_device_by_id(u, request.POST.get('device_id') or '')
            messages.success(request, 'دستگاه انتخاب‌شده از حساب شما خارج شد. ✅')

        elif action == 'revoke_all_devices':
            DeviceService.revoke_all_devices(u)
            messages.success(request, 'همه دستگاه‌ها خارج شدند. دفعات بعد باید دوباره وارد شوید. ✅')

        return redirect('auth_pages:profile')

    # آزادسازی سفارش‌های منقضی تا وضعیت‌ها همیشه تازه باشد (D-099)
    try:
        from src.modules.order.expiry import release_expired_orders
        release_expired_orders()
    except Exception:
        pass

    orders = u.orders.prefetch_related('items', 'payments').order_by('-created_at')[:20]

    order_list = []
    for o in orders:
        payment = o.payments.order_by('-created_at').first() if hasattr(o, 'payments') else None
        evidence_submitted = bool(
            payment and payment.status == 'PENDING_REVIEW'
        )
        remaining = o.remaining_seconds
        can_cancel = o.status == 'PENDING' and remaining > 0 and not evidence_submitted
        order_list.append({
            'order_number': o.order_number,
            'created_at': o.created_at,
            'status': o.status,
            'status_fa': ORDER_STATUS_FA.get(o.status, o.status),
            'total_price': o.total_price,
            'items_count': sum(i.quantity for i in o.items.all()),
            # D-099: مهلت رزرو + امکانات لغو/پرداخت
            'remaining_seconds': remaining,
            'is_expired': o.is_reservation_expired,
            'can_pay': o.status == 'PENDING' and remaining > 0,
            'can_cancel': can_cancel,
        })

    # آمار سریع هدر پروفایل
    active_statuses = {'PENDING', 'PAID', 'PROCESSING', 'SHIPPED'}
    profile_stats = {
        'total_orders': len(order_list),
        'active_orders': sum(1 for o in order_list if o['status'] in active_statuses),
        'total_spent': sum(o['total_price'] for o in order_list
                           if o['status'] not in ('CANCELLED', 'DRAFT')),
    }

    devices = []
    for d in DeviceService.get_user_devices(u):
        ua = d.get('user_agent') or ''
        if 'iPhone' in ua or 'iPad' in ua:
            device_type = '📱 آیفون / آیپد'
        elif 'Android' in ua:
            device_type = '🤖 اندروید'
        elif 'Macintosh' in ua:
            device_type = '💻 مک'
        elif 'Windows' in ua:
            device_type = '💻 ویندوز'
        else:
            device_type = '🌐 مرورگر'
        devices.append({**d, 'device_type': device_type})

    return render(request, 'accounts/profile.html', {
        'orders': order_list,
        'stats': profile_stats,
        'devices': devices,
        'has_password': PasswordService.has_password(u),
    })


# ══════════════════════════ خروج ══════════════════════════

def logout_view(request):
    """خروج از حساب (کوکی دستگاه حفظ می‌شود تا ورود بعدی خودکار باشد؛
    کاربر می‌تواند از «دستگاه‌های من» در پروفایل آن را باطل کند)"""
    logout(request)
    messages.success(request, 'با موفقیت خارج شدید. به امید دیدار! 🌿')
    return redirect('/')
