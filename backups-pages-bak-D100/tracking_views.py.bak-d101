"""
Views برای پیگیری سفارش و صفحه پرداخت

طراحی جدید سفر مشتری (کاهش اصطکاک):
- صفحه پرداخت یکپارچه: کارت‌های مقصد + راهنما + فرم ثبت رسید همه در یک صفحه
- مشتری فقط ۴ رقم آخر کارت خود را وارد می‌کند (زمان واریز خودکار = همین حالا،
  رسید اختیاری) — چیزی برای به خاطر سپردن وجود ندارد
- پس از ثبت → صفحه موفقیت با راهنمای «چه اتفاقی بعد می‌افتد؟»
"""
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Order, Payment
from .payment_gateway import get_payment_gateway
from .checkout_service import CheckoutService
from .expiry import release_expired_orders
from src.core.fa import money

# تبدیل ارقام فارسی/عربی به لاتین (ورودی فرم‌ها همیشه لاتین ذخیره شود)
_EN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def _to_en_digits(value):
    return str(value or '').translate(_EN_DIGITS)


def _check_order_access(request, order):
    """بررسی دسترسی به سفارش: مالک لاگین‌شده، ادمین، یا مهمان با همان سشن"""
    if request.user.is_authenticated:
        return order.user == request.user or request.user.is_staff
    tracking_order_id = request.session.get('tracking_order_id')
    return bool(tracking_order_id and str(tracking_order_id) == str(order.id))


def _sweep_expired():
    """پاکسازی lazy: آزادسازی سفارش‌های منقضی (ارزان و امن برای صدا زدن در هر صفحه)"""
    try:
        release_expired_orders()
    except Exception:
        pass


def _order_flags(order, payment=None):
    """پرچم‌های مشترک قالب‌ها: مهلت رزرو، امکان لغو و پرداخت"""
    payment = payment or order.payments.order_by('-created_at').first()
    evidence_submitted = bool(
        payment and payment.status == Payment.PaymentStatus.PENDING_REVIEW
    )
    remaining = order.remaining_seconds
    return {
        'remaining_seconds': remaining,
        'is_expired': order.is_reservation_expired,
        'can_pay': order.status == Order.OrderStatus.PENDING and remaining > 0,
        'can_cancel': (
            order.status == Order.OrderStatus.PENDING
            and remaining > 0
            and not evidence_submitted
        ),
        'evidence_submitted': evidence_submitted,
    }


def _get_support_phone():
    """شماره تماس پشتیبانی از تنظیمات سایت"""
    try:
        from src.modules.family_panel.models import SiteSettings
        obj = SiteSettings.objects.first()
        return (obj.contact_phone or '') if obj else ''
    except Exception:
        return ''


# ═══════════════════════════════════════════════════════════════
# صفحه پرداخت کارت‌به‌کارت (یکپارچه)
# ═══════════════════════════════════════════════════════════════

def payment_page_view(request, order_number):
    """
    GET  : کارت‌های مقصد (با دکمه کپی) + راهنمای کوتاه + فرم ثبت رسید
    POST : ثبت رسید — فقط ۴ رقم آخر اجباری است
    """
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number,
    )
    if not _check_order_access(request, order):
        return HttpResponseForbidden('دسترسی غیرمجاز')

    # آزادسازی سفارش‌های منقضی قبل از هر چیز (D-099)
    _sweep_expired()
    order.refresh_from_db()

    gateway = get_payment_gateway()
    accounts = gateway.get_destination_accounts()

    # پرداخت در جریان — اگر نیست بساز
    payment = order.payments.filter(
        status__in=[Payment.PaymentStatus.PENDING, Payment.PaymentStatus.PENDING_REVIEW]
    ).order_by('-created_at').first()
    if not payment:
        payment = Payment.objects.create(
            order=order,
            amount=order.total_price,
            gateway=Payment.PaymentGateway.MANUAL,
            status=Payment.PaymentStatus.PENDING,
        )

    already_submitted = payment.status == Payment.PaymentStatus.PENDING_REVIEW
    errors = []
    last4_input = ''

    if request.method == 'POST' and accounts:
        last4_input = (request.POST.get('sender_card_last4') or '').strip()
        last4 = ''.join(ch for ch in _to_en_digits(last4_input) if ch.isdigit())
        last4_input = last4

        receipt = request.FILES.get('receipt_image')
        if receipt:
            if receipt.size > 5 * 1024 * 1024:
                errors.append('حجم عکس رسید بیشتر از ۵ مگابایت است. لطفاً نسخه کوچک‌تری انتخاب کنید.')
            elif not (receipt.content_type or '').startswith('image/'):
                errors.append('لطفاً تصویر رسید را از نوع عکس (JPG یا PNG) انتخاب کنید.')

        # زمان واریز: پیش‌فرض همین حالا؛ اگر مشتری زمان دیگری گفت همان استفاده می‌شود
        transfer_time = timezone.now()
        raw_time = (request.POST.get('transfer_time') or '').strip()
        if raw_time:
            parsed = parse_datetime(raw_time)
            if parsed is not None:
                if timezone.is_naive(parsed):
                    parsed = timezone.make_aware(parsed)
                transfer_time = parsed

        if not last4_input:
            errors.append('لطفاً ۴ رقم آخر کارتی که با آن پرداخت کردید را وارد کنید.')
        elif len(last4_input) != 4:
            errors.append('۴ رقم آخر کارت باید دقیقاً چهار رقم باشد.')

        if not errors:
            try:
                gateway.submit_evidence(payment, {
                    'sender_card_last4': last4,
                    'transfer_time': transfer_time,
                    'amount': payment.amount,
                    'receipt_image': receipt,
                })
                messages.success(request, 'رسید پرداخت شما با موفقیت ثبت شد. 🌿')
                return redirect('order_pages:payment_success',
                                order_number=order.order_number)
            except ValueError as e:
                errors.append(str(e))

    flags = _order_flags(order, payment)
    context = {
        'order': order,
        'payment': payment,
        'accounts': accounts,
        'amount_display': money(order.total_price),
        'items_count': sum(i.quantity for i in order.items.all()),
        'already_submitted': already_submitted,
        'errors': errors,
        'last4_input': last4_input,
        'support_phone': _get_support_phone(),
        'order_cancelled': order.status == Order.OrderStatus.CANCELLED,
        **flags,
    }
    return render(request, 'order/payment_page.html', context)


# ═══════════════════════════════════════════════════════════════
# صفحه موفقیت پس از ثبت رسید
# ═══════════════════════════════════════════════════════════════

def payment_success_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not _check_order_access(request, order):
        return HttpResponseForbidden('دسترسی غیرمجاز')

    payment = order.payments.order_by('-created_at').first()
    context = {
        'order': order,
        'payment': payment,
        'amount_display': money(order.total_price),
        'card_last4': payment.sender_card_last4 if payment else '',
        'support_phone': _get_support_phone(),
    }
    return render(request, 'order/payment_success.html', context)


# ═══════════════════════════════════════════════════════════════
# لغو سفارش پرداخت‌نشده توسط مشتری (D-099)
# ═══════════════════════════════════════════════════════════════

def _post_cancel_redirect(request, next_url, order_number):
    """بعد از لغو: به مسیر درخواستی (اگر امن بود) وگرنه به صفحه پیگیری برگرد"""
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return redirect(next_url)
    return redirect('order_pages:tracking_page', order_number=order_number)


def cancel_order_view(request, order_number):
    """
    POST : لغو سفارشِ در انتظار پرداخت + آزادسازی رزرو موجودی

    قوانین:
    - فقط مالک سفارش (کاربر لاگین‌شده یا مهمان همان سشن)
    - فقط وقتی سفارش PENDING است و رسیدی ثبت نشده (PENDING_REVIEW نیست)
    - سفارش منقضی‌شده را پاکسازی خودکار لغو می‌کند؛ اینجا فقط انصراف فعال
    """
    if request.method != 'POST':
        return HttpResponseForbidden('درخواست نامعتبر است')

    order = get_object_or_404(Order, order_number=order_number)
    if not _check_order_access(request, order):
        return HttpResponseForbidden('دسترسی غیرمجاز')

    next_url = request.POST.get('next') or ''

    if order.status != Order.OrderStatus.PENDING:
        messages.info(request, 'این سفارش دیگر در وضعیت پرداخت نیست و قابل لغو نیست.')
        return _post_cancel_redirect(request, next_url, order.order_number)

    payment = order.payments.order_by('-created_at').first()
    if payment and payment.status == Payment.PaymentStatus.PENDING_REVIEW:
        messages.warning(
            request,
            'رسید پرداخت شما در حال بررسی است؛ برای لغو سفارش لطفاً با پشتیبانی تماس بگیرید.'
        )
        return redirect('order_pages:tracking_page', order_number=order.order_number)

    if order.is_reservation_expired:
        _sweep_expired()
        order.refresh_from_db()
        messages.info(request, 'مهلت پرداخت این سفارش تمام شده بود و موجودی آن آزاد شد.')
        return _post_cancel_redirect(request, next_url, order.order_number)

    CheckoutService.cancel_order(
        order,
        reason='انصراف مشتری از سفارش',
        user=request.user if request.user.is_authenticated else None,
    )
    messages.success(
        request,
        'سفارش شما لغو شد و موجودی رزرو‌شده آزاد گردید. هر وقت خواستید دوباره ثبت کنید. 🌿'
    )
    return _post_cancel_redirect(request, next_url, order.order_number)


# ═══════════════════════════════════════════════════════════════
# پیگیری سفارش
# ═══════════════════════════════════════════════════════════════

def tracking_page_view(request, order_number):
    """صفحه پیگیری سفارش با تایم‌لاین مرحله‌به‌مرحله"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'payments'),
        order_number=order_number,
    )
    if not _check_order_access(request, order):
        return HttpResponseForbidden('دسترسی غیرمجاز')

    # آزادسازی سفارش‌های منقضی (D-099) — وضعیت ممکن است همین حالا عوض شود
    if order.status == Order.OrderStatus.PENDING:
        _sweep_expired()
        order.refresh_from_db()

    history = order.status_history.all().order_by('created_at')

    timeline = [
        {'status': 'created', 'title': 'ثبت سفارش', 'icon': '📝', 'active': False},
        {'status': 'paid', 'title': 'تایید پرداخت', 'icon': '💳', 'active': False},
        {'status': 'processing', 'title': 'آماده‌سازی', 'icon': '📦', 'active': False},
        {'status': 'shipped', 'title': 'ارسال شد', 'icon': '🚚', 'active': False},
        {'status': 'delivered', 'title': 'تحویل شد', 'icon': '🏠', 'active': False},
    ]
    status_order = ['DRAFT', 'PENDING', 'PAID', 'PROCESSING', 'SHIPPED', 'DELIVERED']
    current_status = order.status
    # تعداد مراحل تکمیل‌شده: قبل از پرداخت فقط «ثبت سفارش»؛ بعد از آن مطابق جایگاه وضعیت
    if current_status in ('DRAFT', 'PENDING'):
        active_count = 1
    elif current_status in status_order:
        active_count = status_order.index(current_status)
    else:  # CANCELLED و امثال آن
        active_count = 0
    for i in range(min(active_count, 5)):
        timeline[i]['active'] = True

    # حذف توضیحات تکراری «تغییر وضعیت به: ...» چون عنوان همان وضعیت است
    history_items = [
        h for h in history
        if not (h.description or '').startswith('تغییر وضعیت به:')
    ]

    context = {
        'order': order,
        'history': history_items,
        'timeline': timeline,
        'payment': order.payments.order_by('-created_at').first(),
        'items_count': sum(i.quantity for i in order.items.all()),
        'amount_display': money(order.total_price),
        'support_phone': _get_support_phone(),
        **_order_flags(order),
    }
    return render(request, 'order/tracking_page.html', context)


def tracking_lookup_view(request):
    """
    بازیابی سفارش بدون ورود به حساب (پشتیبانِ مسیر اصلی = پروفایل).
    برای مواقعی که مشتری از دستگاه دیگری آمده یا لینک را گم کرده.
    """
    error_message = None
    form_data = {}

    if request.method == 'POST':
        form_data = {
            'order_number': (request.POST.get('order_number') or '').strip(),
            'phone': _to_en_digits((request.POST.get('phone') or '').strip()),
        }
        order_number, phone = form_data['order_number'], form_data['phone']

        if not order_number or not phone:
            error_message = 'لطفاً شماره سفارش و شماره موبایل خود را وارد کنید.'
        else:
            clean = re.sub(r'\s', '', order_number).upper()
            order = Order.objects.filter(order_number__iexact=clean).first()

            # اگر مشتری خط تیره‌ها را ننوشته باشد: RH140500002 ← RH-1405-00002
            if not order:
                m = re.match(r'^(RH)?(\d{4})(\d{5})$', clean)
                if m:
                    order = Order.objects.filter(
                        order_number__iexact='RH-{}-{}'.format(m.group(2), m.group(3))
                    ).first()

            if not order:
                error_message = ('سفارشی با این شماره پیدا نشد. '
                                 'شماره سفارش را از پیامک تایید خرید بررسی کنید.')
            elif not (order.guest_phone == phone or
                      (order.user and order.user.username == phone)):
                error_message = ('شماره موبایل با این سفارش مطابقت ندارد. '
                                 'همان شماره‌ای که هنگام خرید وارد کردید را بنویسید.')
            else:
                if not request.session.session_key:
                    request.session.create()
                request.session['tracking_order_id'] = str(order.id)
                return redirect('order_pages:tracking_page',
                                order_number=order.order_number)

    return render(request, 'order/tracking_lookup.html', {
        'error': error_message,
        'form_data': form_data,
    })
