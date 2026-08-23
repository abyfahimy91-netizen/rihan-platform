"""
Auth Page Views - صفحات HTML ورود/ثبت‌نام و پروفایل
متمایز از API Views (views.py)

Flow (ADR-006 Passwordless):
1. کاربر شماره موبایل وارد می‌کند → OtpService.request_otp
2. کد ۶ رقمی را وارد می‌کند → OtpService.verify_otp → login()
3. کاربر جدید خودکار ساخته می‌شود (= ثبت‌نام بدون فرم اضافه)
"""
import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .services.otp_service import OtpService

logger = logging.getLogger(__name__)

SESSION_PHONE_KEY = 'otp_pending_phone'


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
            # اگر کاربر سبد فعال دیگری هم دارد، آیتم‌های سبد مهمان را به آن منتقل کن
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


def login_page_view(request):
    """صفحه ورود / ثبت‌نام دو مرحله‌ای با کد پیامکی"""
    if request.user.is_authenticated:
        return redirect('auth_pages:profile')

    next_url = request.GET.get('next') or request.POST.get('next') or '/'
    step = 'phone'
    demo_code = None
    phone_display = ''

    if request.method == 'POST':
        action = request.POST.get('action', '')
        ip = _client_ip(request)

        if action == 'request_otp':
            raw_phone = (request.POST.get('phone') or '').strip()
            success, message, otp_code = OtpService.request_otp(raw_phone, ip)
            if success:
                is_valid, normalized = OtpService.validate_phone(raw_phone)
                request.session[SESSION_PHONE_KEY] = normalized
                request.session.set_expiry(600)  # ۱۰ دقیقه برای تکمیل ورود
                step = 'code'
                phone_display = normalized
                demo_code = otp_code  # فقط در حالت توسعه مقدار دارد
                if demo_code:
                    messages.info(request, f'حالت آزمایشی: کد شما {demo_code} است.')
                else:
                    messages.success(request, 'کد تأیید پیامک شد. لطفاً صندوق پیامک را بررسی کنید.')
            else:
                messages.error(request, message)
                step = 'phone'

        elif action == 'verify_otp':
            phone = request.session.get(SESSION_PHONE_KEY)
            code = (request.POST.get('code') or '').strip()
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
                    return redirect(next_url if next_url.startswith('/') else '/')
                else:
                    messages.error(request, message)
                    step = 'code'
                    phone_display = phone

    context = {
        'step': step,
        'phone_display': phone_display,
        'next_url': next_url,
    }
    return render(request, 'accounts/login.html', context)


@login_required
def profile_view(request):
    """پروفایل کاربر + تاریخچه سفارش‌ها"""
    STATUS_FA = {
        'DRAFT': 'پیش‌نویس', 'PENDING': 'در انتظار پرداخت', 'PAID': 'پرداخت شده',
        'PROCESSING': 'در حال آماده‌سازی', 'SHIPPED': 'ارسال شده', 'DELIVERED': 'تحویل شده',
        'CANCELLED': 'لغو شده', 'RETURNED': 'مرجوع شده',
    }

    if request.method == 'POST':
        u = request.user
        u.first_name = (request.POST.get('first_name') or '').strip()
        u.last_name = (request.POST.get('last_name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        if email and '@' not in email:
            messages.error(request, 'ایمیل معتبر نیست.')
        else:
            u.email = email
            u.save(update_fields=['first_name', 'last_name', 'email'])
            messages.success(request, 'اطلاعات حساب ذخیره شد ✅')
        return redirect('auth_pages:profile')

    orders = request.user.orders.prefetch_related('items').order_by('-created_at')[:20]
    order_list = [{
        'order_number': o.order_number,
        'created_at': o.created_at,
        'status': o.status,
        'status_fa': STATUS_FA.get(o.status, o.status),
        'total_price': o.total_price,
        'items_count': sum(i.quantity for i in o.items.all()),
    } for o in orders]

    return render(request, 'accounts/profile.html', {
        'orders': order_list,
    })


def logout_view(request):
    """خروج از حساب"""
    logout(request)
    messages.success(request, 'با موفقیت خارج شدید. به امید دیدار! 🌿')
    return redirect('/')
