"""داشبوردهای مالی Rihan (D-113) — ادمین و تامین‌کننده"""
import csv
from functools import wraps

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from src.modules.order import finance as order_finance


def _require_staff(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, 'دسترسی غیرمجاز. فقط ادمین‌ها مجاز هستند.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _require_supplier(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'لطفاً وارد حساب کاربری شوید.')
            return redirect('/')
        if not hasattr(request.user, 'supplier_profile'):
            messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست.')
            return redirect('/')
        return view_func(request, supplier=request.user.supplier_profile, *args, **kwargs)
    return wrapper


@_require_staff
def finance_dashboard_admin(request):
    """داشبورد مالی ادمین: فروش/بهای تمام‌شده/سود + جدول تسویه هر تامین‌کننده"""
    overview = order_finance.admin_overview()
    context = {
        'overview': overview,
        'title': 'داشبورد مالی',
    }
    return render(request, 'finance/admin_dashboard.html', context)


@_require_supplier
def finance_dashboard_supplier(request, supplier=None):
    """حساب من (تامین‌کننده): چقدر فروختم / چقدر طلب دارم / تاریخچه تسویه"""
    from src.modules.order.models import Shipment
    fin = order_finance.supplier_financials(supplier)

    shipments = (
        Shipment.objects.filter(supplier=supplier)
        .exclude(status=Shipment.Status.CANCELED)
        .prefetch_related('items__order_item')
        .select_related('order')
        .order_by('-created_at')
    )
    rows = order_finance._shipment_rows(shipments)

    context = {
        'supplier': supplier,
        'fin': fin,
        'rows': rows,
        'title': 'مالی و تسویه',
    }
    return render(request, 'finance/supplier_dashboard.html', context)


@_require_staff
def finance_export_csv(request):
    """خروجی CSV جدول تامین‌کننده‌ها (فروش/قابل پرداخت/تسویه/مانده)"""
    overview = order_finance.admin_overview()
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="rihan-finance.csv"'
    response.write('\ufeff')  # BOM برای اکسل فارسی
    writer = csv.writer(response)
    writer.writerow([
        'تامین‌کننده', 'تعداد مرسوله', 'فروش (تومان)', 'قابل پرداخت کل',
        'تسویه‌شده', 'مانده طلب', 'تسویه‌نشده (تعداد)',
    ])
    for row in overview['supplier_rows']:
        writer.writerow([
            row['supplier'].title,
            row['shipment_count'],
            row['sold_total'],
            row['payable_total'],
            row['settled_total'],
            row['balance'],
            row['unsettled_count'],
        ])
    writer.writerow([])
    writer.writerow([
        'جمع کل', '', overview['revenue'], '', overview['settled_total'],
        overview['unsettled_total'], '',
    ])
    return response
