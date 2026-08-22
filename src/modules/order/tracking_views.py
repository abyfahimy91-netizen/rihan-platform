"""
Views برای پیگیری سفارش و صفحه پرداخت (M7 + M2)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone

from .models import Order, Payment


def tracking_lookup_view(request):
    """صفحه جستجوی سفارش با شماره سفارش و شماره تلفن"""
    if request.method == 'POST':
        order_number = request.POST.get('order_number', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not order_number or not phone:
            messages.error(request, 'لطفاً شماره سفارش و شماره تلفن را وارد کنید.')
            return render(request, 'order/tracking_lookup.html', {})
        
        # جستجوی سفارش با شماره سفارش و شماره تلفن
        order = Order.objects.filter(
            order_number=order_number,
            guest_phone=phone
        ).first()
        
        if not order:
            messages.error(request, 'شماره تلفن با سفارش مطابقت ندارد. سفارشی با این مشخصات یافت نشد.')
            return render(request, 'order/tracking_lookup.html', {})
        
        # ذخیره در سشن برای دسترسی بعدی
        request.session['tracking_order_id'] = str(order.id)
        return redirect('order_pages:tracking_page', order_number=order.order_number)
    
    return render(request, 'order/tracking_lookup.html', {})


def tracking_page_view(request, order_number):
    """صفحه پیگیری سفارش با تایم‌لاین ۵ مرحله‌ای"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # بررسی دسترسی
    has_access = False
    
    # کاربر وارد شده و مالک سفارش است؟
    if request.user.is_authenticated:
        if hasattr(order, 'user') and order.user == request.user:
            has_access = True
    
    # دسترسی از طریق سشن (از صفحه جستجو)
    if not has_access:
        tracking_order_id = request.session.get('tracking_order_id')
        if tracking_order_id == str(order.id):
            has_access = True
    
    # دسترسی مهمان با شماره تلفن
    if not has_access:
        # بررسی شماره تلفن از پارامترهای درخواست
        phone = request.GET.get('phone') or request.POST.get('phone')
        if phone and order.guest_phone == phone:
            has_access = True
            request.session['tracking_order_id'] = str(order.id)
    
    if not has_access:
        return HttpResponseForbidden('دسترسی غیرمجاز')
    
    # دریافت تاریخچه وضعیت‌ها برای تایم‌لاین
    history = order.status_history.all().order_by('created_at')
    
    # ساخت تایم‌لاین ۵ مرحله‌ای
    timeline = [
        {'status': 'created', 'title': 'ثبت سفارش', 'active': False},
        {'status': 'paid', 'title': 'پرداخت', 'active': False},
        {'status': 'processing', 'title': 'آماده‌سازی', 'active': False},
        {'status': 'shipped', 'title': 'ارسال', 'active': False},
        {'status': 'delivered', 'title': 'تحویل', 'active': False},
    ]
    
    # فعال‌سازی مراحل بر اساس وضعیت فعلی
    status_order = ['DRAFT', 'PENDING', 'PAID', 'PROCESSING', 'SHIPPED', 'DELIVERED']
    current_status = order.status
    
    if current_status in status_order:
        current_idx = status_order.index(current_status)
        for i in range(min(current_idx + 1, 5)):
            timeline[i]['active'] = True
    
    context = {
        'order': order,
        'history': history,
        'timeline': timeline,
    }
    return render(request, 'order/tracking_page.html', context)


def payment_page_view(request, order_number):
    """صفحه پرداخت کارت‌به‌کارت"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # بررسی دسترسی
    has_access = False
    
    if request.user.is_authenticated:
        if hasattr(order, 'user') and order.user == request.user:
            has_access = True
    
    if not has_access:
        tracking_order_id = request.session.get('tracking_order_id')
        if tracking_order_id == str(order.id):
            has_access = True
    
    if not has_access:
        return HttpResponseForbidden('دسترسی غیرمجاز')
    
    # دریافت اطلاعات پرداخت
    payment = Payment.objects.filter(order=order).first()
    
    # اطلاعات کارت مقصد
    from django.conf import settings
    card_config = getattr(settings, 'CARD_TO_CARD_CONFIG', {
        'card_number': '6037-9975-XXXX-XXXX',
        'card_holder': 'نام صاحب کارت',
        'bank_name': 'بانک ملی',
        'iban': 'IR00-0000-0000-0000-0000-000000',
    })
    
    context = {
        'order': order,
        'payment': payment,
        'card_config': card_config,
    }
    return render(request, 'order/payment_page.html', context)
