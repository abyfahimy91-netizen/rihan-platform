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
    """ورود دوکاناله با راهنمای گام‌به‌گام (سفر مشتری: ۱ شماره ← ۲ تأیید ← ۳ ورود)
    D-103: روش‌های فعال و روش پیش‌فرض از تنظیمات ادمین (AuthSettings) کنترل می‌شود."""
    if request.user.is_authenticated:
        # D-111: کاربر احرازشده (مثلاً با کوکی دستگاه) اگر ?next امنِ محلی دارد
        # مستقیم به همان مقصد برود؛ قبلاً همیشه به پروفایل پرت می‌شد و
        # کاربرِ پنل تامین‌کننده سرگردان می‌شد.
        _nx = request.GET.get('next') or request.POST.get('next') or ''
        if _nx.startswith('/') and not _nx.startswith('//'):
            return redirect(_nx)
        return redirect('auth_pages:profile')

    next_url = request.GET.get('next') or request.POST.get('next') or '/'
    ip = _client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')[:255]

    # ── تنظیمات ورود از پنل ادمین (D-103) ──
    from .models import AuthSettings
    try:
        _s = AuthSettings.load()
    except Exception:
        _s = None
    otp_enabled = _s.otp_enabled if _s else True
    password_enabled = _s.password_enabled if _s else True

    # روش پیش‌فرض — با محافظ: روشی انتخاب شود که واقعاً فعال است
    default_method = (_s.default_method if _s else 'otp') or 'otp'
    if default_method == 'password' and not password_enabled:
        default_method = 'otp'
    if default_method == 'otp' and not otp_enabled:
        default_method = 'password'
    auth_disabled = not otp_enabled and not password_enabled

    # مقادیر پیش‌فرض context
    ctx = {
        'step': 'disabled' if auth_disabled else ('password' if default_method == 'password' else 'phone'),
        'method': default_method if not auth_disabled else 'otp',
        'phone_display': '',
        'next_url': next_url,
        'code_error': False,
        'resend_seconds': 120,
        # D-103: کنترل روش‌های ورود از ادمین
        'otp_enabled': otp_enabled,
        'password_enabled': password_enabled,
        'default_method': default_method,
        'auth_disabled': auth_disabled,
    }

    if request.method == 'POST':
        action = request.POST.get('action', '')
        method = request.POST.get('method', 'otp')
        ctx['method'] = method

        # ── محافظ D-103: روش غیرفعال را رد کن ──
        if action == 'request_otp' and not otp_enabled:
            messages.error(request, 'ورود با کد پیامکی موقتاً غیرفعال است. لطفاً از رمز عبور استفاده کنید.')
            ctx.update(step='password' if password_enabled else 'disabled')
        elif action in ('password_login', 'forgot_request', 'reset_password', 'set_password') and not password_enabled:
            messages.error(request, 'ورود با رمز عبور موقتاً غیرفعال است. لطفاً از کد پیامکی استفاده کنید.')
            ctx.update(step=('phone' if otp_enabled else 'disabled'), method='otp')

        # ── مرحله ۱: درخواست کد پیامکی ──
        elif action == 'request_otp':
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
                    # D-111 ریشه باگ «هر ۱۰ دقیقه از پنل پرت می‌شوم»:
                    # در Django ≥5، set_expiry(600) مرحله‌ی OTP داخل دیتای سشن
                    # ذخیره می‌شود و از cycle_key در login() جان سالم به در می‌برد
                    # → نشست واقعی هم فقط ۱۰ دقیقه بود! بازنشانی به سیاست سراسری (۱۴ روز).
                    request.session.set_expiry(None)
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
                # D-111: اگر سشن قبلاً در جریان OTP با set_expiry(600) بسته شده بود،
                # همان ۱۰ دقیقه به ورودِ با رمز هم چسبیده بود — بازنشانی به ۱۴ روز.
                request.session.set_expiry(None)
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
        if request.GET.get('method') == 'password' and ctx['step'] == 'phone' and password_enabled:
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

        # D-102: اکشن‌های مدیریت آدرس‌ها (ذخیره/پیش‌فرض/حذف)
        # D-113c: خطای اعتبارسنجی = dict برمی‌گردد → همان صفحه با همان داده‌های
        # تایپ‌شده کاربر رندر می‌شود (بدون پرت‌شدن و بدون پاک‌شدن فرم)
        addr_result = _handle_address_actions(request, u)
        if isinstance(addr_result, dict):
            return _render_profile(request, u, extra_context=addr_result)
        if addr_result:
            return redirect('auth_pages:profile')

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

    return _render_profile(request, u)


def _render_profile(request, u, extra_context=None):
    """رندر صفحه پروفایل — هم GET هم بازرندر خطای فرم آدرس (D-113c)؛
    خطای اعتبارسنجی بدون ریدایرکت در همین صفحه با داده‌های کاربر نشان داده می‌شود"""
    # آزادسازی سفارش‌های منقضی تا وضعیت‌ها همیشه تازه باشد (D-099)
    try:
        from src.modules.order.expiry import release_expired_orders
        release_expired_orders()
    except Exception:
        pass

    orders = u.orders.prefetch_related('items', 'payments', 'shipments').order_by('-created_at')[:20]

    order_list = []
    for o in orders:
        payment = o.payments.order_by('-created_at').first() if hasattr(o, 'payments') else None
        evidence_submitted = bool(
            payment and payment.status == 'PENDING_REVIEW'
        )
        remaining = o.remaining_seconds
        can_cancel = o.status == 'PENDING' and remaining > 0 and not evidence_submitted
        # D-111: برچسب وضعیت با توجه به رسید ثبت‌شده + مرسوله‌ها با لینک رهگیری
        status_fa = 'در انتظار تایید' if o.awaiting_review else ORDER_STATUS_FA.get(o.status, o.status)
        badge_code = 'PENDING_REVIEW' if o.awaiting_review else o.status
        shipments = [
            {
                'carrier_label': s.carrier_full_label,
                'tracking_code': s.tracking_code,
                'tracking_url': s.tracking_url,
                'status': s.status,
                'status_label': s.get_status_display(),
                'other_details': s.other_details_text,
            }
            for s in o.shipments.exclude(status='CANCELED').order_by('created_at')
        ]
        order_list.append({
            'order_number': o.order_number,
            'created_at': o.created_at,
            'status': o.status,
            'status_fa': status_fa,
            'badge_code': badge_code,
            'shipments': shipments,
            'total_price': o.total_price,
            'items_count': sum(i.quantity for i in o.items.all()),
            # D-099: مهلت رزرو + امکانات لغو/پرداخت
            'remaining_seconds': remaining,
            'is_expired': o.is_reservation_expired,
            'can_pay': o.status == 'PENDING' and remaining > 0 and not evidence_submitted,
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

    ctx = {
        'orders': order_list,
        'stats': profile_stats,
        'devices': devices,
        'has_password': PasswordService.has_password(u),
        # D-102: مدیریت آدرس‌ها در پروفایل
        'addresses': u.addresses.all(),
        'edit_address': _get_edit_address(u, request),
    }
    if extra_context:
        ctx.update(extra_context)
    return render(request, 'accounts/profile.html', ctx)


# ══════════════════════════ آدرس‌ها (D-102) ══════════════════════════

def _get_edit_address(user, request):
    """آدرس در حال ویرایش (از ?edit=<id>) — فقط اگر متعلق به کاربر باشد"""
    from src.modules.order import address_service
    edit_id = request.GET.get('edit') or ''
    if edit_id:
        return address_service.get_for_user(user, edit_id)
    return None


def _address_error_context(request, data, errors, addr=None):
    """D-113c: زمینه بازرندر فرم آدرس در همان صفحه — داده‌های تایپ‌شده حفظ می‌شوند.
    مقادیر خالیِ تایپ‌نشده با مقدار قبلی آدرس (در ویرایش) پر می‌شوند تا قالب
    هرگز لازم نباشد روی edit_address زنجیره default ببندد (edit_address ممکن است None باشد)"""
    d = dict(data)
    d['is_default'] = request.POST.get('is_default') == 'on'
    if addr:
        d['title'] = d.get('title') or addr.title
        d['full_name'] = d.get('full_name') or addr.full_name
        d['phone'] = d.get('phone') or addr.phone
        d['address'] = d.get('address') or addr.detailed_address
        d['postal_code'] = d.get('postal_code') or addr.postal_code
    return {
        'address_form_errors': errors,
        'address_form_data': d,
        'edit_address': addr,
    }


def _handle_address_actions(request, u):
    """اکشن‌های POST مربوط به آدرس‌ها در پروفایل — خروجی: True اگر هندل شد؛
    dict اگر خطای اعتبارسنجی بود (بازرندر همان صفحه با داده‌های کاربر، D-113c)"""
    from src.modules.order import address_service

    action = request.POST.get('action', '')

    if action == 'address_save':
        addr_id = request.POST.get('address_id') or ''
        data = {
            'title': request.POST.get('title'),
            'full_name': request.POST.get('full_name'),
            'phone': request.POST.get('phone'),
            'address': request.POST.get('address'),
            'postal_code': request.POST.get('postal_code'),
        }
        if addr_id:
            addr = address_service.get_for_user(u, addr_id)
            if not addr:
                messages.error(request, 'آدرس موردنظر پیدا نشد.')
                return True
            clean, errors = address_service.validate_address_data(data)
            if errors:
                # D-113c: بدون ریدایرکت — همان صفحه با داده‌های تایپ‌شده بازرندر می‌شود
                return _address_error_context(request, data, errors, addr)
            make_default = request.POST.get('is_default') == 'on'
            addr.title = clean['title']
            addr.full_name = clean['full_name']
            addr.phone = clean['phone']
            addr.detailed_address = clean['detailed_address']
            addr.postal_code = clean['postal_code']
            if make_default:
                addr.is_default = True
            addr.save()
            messages.success(request, 'آدرس به‌روزرسانی شد ✅')
        else:
            try:
                address_service.create_for_user(u, data)
                messages.success(request, 'آدرس جدید ذخیره شد ✅ حالا در تسویه‌حساب با یک کلیک در دسترس است.')
            except ValueError as e:
                return _address_error_context(request, data, str(e).split(' | '), None)
        return True

    if action == 'address_default':
        if address_service.set_default(u, request.POST.get('address_id') or ''):
            messages.success(request, 'آدرس پیش‌فرض شما تغییر کرد ✅')
        else:
            messages.error(request, 'آدرس موردنظر پیدا نشد.')
        return True

    if action == 'address_delete':
        if address_service.delete_address(u, request.POST.get('address_id') or ''):
            messages.success(request, 'آدرس حذف شد.')
        else:
            messages.error(request, 'آدرس موردنظر پیدا نشد.')
        return True

    return False


# ══════════════════════════ خروج ══════════════════════════

def logout_view(request):
    """خروج از حساب (کوکی دستگاه حفظ می‌شود تا ورود بعدی خودکار باشد؛
    کاربر می‌تواند از «دستگاه‌های من» در پروفایل آن را باطل کند)"""
    logout(request)
    messages.success(request, 'با موفقیت خارج شدید. به امید دیدار! 🌿')
    # D-111: پشتیبانی از ?next امنِ محلی — دکمه «خروج و ورود با حساب دیگر»
    # در صفحه ۴۰۳ به‌صورت یک‌ضربه‌ای به مقصد (مثلاً /supplier/) می‌رساند.
    nxt = request.GET.get('next') or ''
    if nxt.startswith('/') and not nxt.startswith('//'):
        return redirect(nxt)
    return redirect('/')


# ══════════════════════════════════════════════════════════
# D-106: ثبت‌نام با رمز عبور — مسیر موازی بدون نیاز به پیامک
# وقتی ادمین OTP را خاموش کند (یا پیامک در دسترس نباشد)، مشتری
# می‌تواند مستقیم با شماره + رمز عبور حساب بسازد.
# کلید دسترسی: AuthSettings.password_enabled (پنل ادمین)
# ══════════════════════════════════════════════════════════

_FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def _normalize_phone(value) -> str:
    return str(value or '').translate(_FA_DIGITS).strip()


def register_page_view(request):
    """ثبت‌نام با نام، شماره موبایل و رمز عبور — بدون پیامک"""
    if request.user.is_authenticated:
        return redirect('auth_pages:profile')

    from .models import AuthSettings
    try:
        _s = AuthSettings.load()
    except Exception:
        _s = None
    password_enabled = bool(_s.password_enabled) if _s else True
    next_url = request.GET.get('next') or request.POST.get('next') or '/'

    if not password_enabled:
        messages.info(request, 'ثبت‌نام فعلاً فقط از راه کد پیامکی انجام می‌شود.')
        return redirect('auth_pages:login')

    ctx = {'next_url': next_url, 'form_values': {}}

    if request.method == 'POST':
        name = (request.POST.get('full_name') or '').strip()
        raw_phone = _normalize_phone(request.POST.get('phone'))
        p1 = request.POST.get('password1') or ''
        p2 = request.POST.get('password2') or ''
        ctx['form_values'] = {'full_name': name[:100]}

        is_valid_phone, phone = OtpService.validate_phone(raw_phone)
        if not is_valid_phone:
            messages.error(request, 'شماره موبایل معتبر نیست. مثال: 09123456789')
        elif User.objects.filter(username=phone).exists():
            messages.error(
                request,
                'این شماره قبلاً ثبت شده است. وارد شوید یا «رمزم را فراموش کرده‌ام» را بزنید.')
        elif p1 != p2:
            messages.error(request, 'رمز عبور و تکرار آن یکسان نیستند.')
        else:
            ok, err = PasswordService.validate_strength(p1)
            if not ok:
                messages.error(request, err)
            else:
                parts = name.split(' ', 1)
                user = User.objects.create_user(
                    username=phone,
                    password=p1,
                    first_name=(parts[0] or '')[:30],
                    last_name=(parts[1][:60] if len(parts) > 1 else ''),
                )
                login(request, user)
                _merge_guest_cart(request, user)
                fname = (parts[0] or '').strip()
                messages.success(
                    request,
                    f'حساب شما ساخته شد؛ خوش آمدید {fname}! 🎉'
                    if fname else 'حساب شما ساخته شد؛ خوش آمدید! 🎉')
                response = redirect(next_url if next_url.startswith('/') else '/')
                _remember_device(response, request, user)
                return response

    return render(request, 'accounts/register.html', ctx)
