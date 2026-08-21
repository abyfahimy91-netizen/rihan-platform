"""
ویوهای پنل تأمین‌کننده (M4)
منطبق بر US-028 و US-029
امنیت: RBAC + User-Supplier Link (D-085)
"""
import logging

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from src.modules.order.models import Order
from src.modules.catalog.models import Supplier
from src.modules.rbac.decorators import require_supplier

from .forms import TrackingCodeForm

logger = logging.getLogger(__name__)


def get_supplier_for_user(user):
    """
    دریافت Supplier مرتبط با کاربر.
    D-085: User-Supplier Link via OneToOneField
    """
    try:
        return user.supplier_profile
    except Supplier.DoesNotExist:
        return None


@require_supplier
def supplier_dashboard(request):
    """
    داشبورد تأمین‌کننده
    US-028: ورود تأمین‌کننده
    """
    supplier = get_supplier_for_user(request.user)
    
    if not supplier:
        messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست. لطفاً با ادمین تماس بگیرید.')
        return redirect('home')
    
    pending_orders = Order.objects.filter(
        items__product__supplier=supplier,
        status__in=['PAID', 'PROCESSING'],
    ).distinct().count()
    
    shipped_orders = Order.objects.filter(
        items__product__supplier=supplier,
        status='SHIPPED',
    ).distinct().count()
    
    context = {
        'supplier': supplier,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
    }
    
    return render(request, 'supplier_panel/dashboard.html', context)


@require_supplier
def supplier_order_list(request):
    """
    لیست سفارشات تأمین‌کننده
    US-029: فقط سفارشات مرتبط با محصولات تأمین‌کننده
    """
    supplier = get_supplier_for_user(request.user)
    
    if not supplier:
        messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست.')
        return redirect('home')
    
    orders = Order.objects.filter(
        items__product__supplier=supplier,
    ).select_related('user').prefetch_related('items__product').distinct().order_by('-created_at')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'supplier': supplier,
        'orders': orders,
        'status_filter': status_filter,
    }
    
    return render(request, 'supplier_panel/order_list.html', context)


@require_supplier
def submit_tracking_code(request, order_id):
    """
    ثبت کد رهگیری برای سفارش
    US-029: تأمین‌کننده کد رهگیری مرسوله را ثبت می‌کند
    امنیت: فقط سفارشات مرتبط با محصولات تأمین‌کننده
    """
    supplier = get_supplier_for_user(request.user)
    
    if not supplier:
        messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست.')
        return redirect('home')
    
    order = get_object_or_404(
        Order,
        id=order_id,
        items__product__supplier=supplier,
    )
    
    if request.method == 'POST':
        form = TrackingCodeForm(request.POST)
        if form.is_valid():
            tracking_code = form.cleaned_data['tracking_code']
            shipping_method = form.cleaned_data['shipping_method']
            
            order.tracking_code = tracking_code
            order.status = 'SHIPPED'
            order.shipped_at = timezone.now()
            order.save()
            
            logger.info(
                f"Supplier {supplier.title} submitted tracking code "
                f"{tracking_code} for order {order.order_number}"
            )
            
            messages.success(request, 'کد رهگیری با موفقیت ثبت شد. مشتری می‌تواند سفارش را پیگیری کند.')
            return redirect('supplier_panel:order_list')
    else:
        form = TrackingCodeForm()
    
    context = {
        'supplier': supplier,
        'order': order,
        'form': form,
    }
    
    return render(request, 'supplier_panel/submit_tracking.html', context)
