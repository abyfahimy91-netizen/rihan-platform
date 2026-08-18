"""
Order Page Views - رندر صفحات HTML برای مشتری
متمایز از API Views (که در views.py هستند)

Endpoints:
- /order/payment/<order_number>/     : فرم ارسال evidence
- /order/tracking/<order_number>/    : تایم‌لاین پیگیری سفارش
- /order/success/<order_number>/     : صفحه موفقیت پرداخت
"""
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from .models import Order, Payment
from .payment_gateway import get_payment_gateway


def payment_submit_page(request, order_number):
    """
    صفحه فرم ارسال evidence کارت‌به‌کارت
    
    منطق:
    - فقط مالک سفارش یا مهمان با session_key یکسان دسترسی دارد
    - اطلاعات کارت مقصد از Gateway خوانده می‌شود
    - Payment record با وضعیت PENDING یا PENDING_REVIEW باید وجود داشته باشد
    """
    order = get_object_or_404(Order, order_number=order_number)
    
    # چک مالکیت
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("دسترسی غیرمجاز")
    else:
        if order.session_key != request.session.session_key:
            return HttpResponseForbidden("دسترسی غیرمجاز. ابتدا سفارش را از سبد خرید ثبت کنید.")
    
    # سفارش باید در وضعیت قابل پرداخت باشد
    if order.status not in [Order.OrderStatus.DRAFT, Order.OrderStatus.PENDING]:
        return render(request, 'order/payment_submit.html', {
            'error': 'این سفارش قابل پرداخت نیست',
            'order_number': order_number,
        })
    
    # پیدا کردن یا ساختن Payment record
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
    
    # دریافت اطلاعات کارت مقصد
    gateway = get_payment_gateway()
    payment_info = gateway.create_payment(order)
    
    context = {
        'order_number': order.order_number,
        'payment_id': str(payment.id),
        'destination': payment_info['destination'],
        'amount': float(order.total_price),
        'amount_display': f"{order.total_price:,.0f} تومان",
    }
    
    return render(request, 'order/payment_submit.html', context)


def order_tracking_page(request, order_number):
    """
    صفحه پیگیری سفارش با تایم‌لاین ۵ مرحله‌ای
    
    منطق:
    - دسترسی عمومی برای مهمان (با چک session_key)
    - دسترسی فقط مالک برای کاربر لاگین‌کرده
    - نمایش تاریخچه کامل سفارش
    """
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'payments'),
        order_number=order_number
    )
    
    # چک مالکیت
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("دسترسی غیرمجاز")
    else:
        if order.session_key != request.session.session_key:
            return HttpResponseForbidden("دسترسی غیرمجاز. لینک پیگیری فقط برای خریدار در دسترس است.")
    
    context = {
        'order': order,
    }
    
    return render(request, 'order/order_tracking.html', context)


def payment_success_page(request, order_number):
    """
    صفحه موفقیت پس از ثبت evidence
    
    منطق:
    - نمایش خلاصه اطلاعات پرداخت ثبت‌شده
    - لینک به صفحه پیگیری
    """
    order = get_object_or_404(Order, order_number=order_number)
    
    # چک مالکیت
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("دسترسی غیرمجاز")
    else:
        if order.session_key != request.session.session_key:
            return HttpResponseForbidden("دسترسی غیرمجاز")
    
    # آخرین پرداخت
    payment = order.payments.order_by('-created_at').first()
    
    context = {
        'order_number': order.order_number,
        'amount_display': f"{order.total_price:,.0f} تومان",
        'card_last4': payment.sender_card_last4 if payment else '----',
        'payment_status': payment.get_status_display() if payment else '-',
    }
    
    return render(request, 'order/payment_success.html', context)
