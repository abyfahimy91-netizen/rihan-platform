"""
Viewهای ماژول مالی (M6)

پوشش User Stories:
- US-021: گزارش مالی (داشبورد ادمین)
- US-030: حساب ماهانه تأمین‌کننده (داشبورد تأمین‌کننده)
"""
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from functools import wraps

from src.modules.catalog.models import Supplier
from .services import FinanceService
from .exports import FinanceExporter
from .models import SupplierLedger


def require_staff(view_func):
    """Decorator: فقط کاربران staff (ادمین)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'لطفاً وارد حساب کاربری شوید.')
            return redirect('/')
        if not request.user.is_staff:
            messages.error(request, 'دسترسی غیرمجاز. فقط ادمین‌ها مجاز هستند.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_supplier(view_func):
    """Decorator: فقط تأمین‌کنندگان"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'لطفاً وارد حساب کاربری شوید.')
            return redirect('/')
        
        # بررسی اینکه آیا کاربر به Supplier متصل است (D-085)
        # استفاده از hasattr برای جلوگیری از RelatedObjectDoesNotExist
        if not hasattr(request.user, 'supplier_profile'):
            messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست.')
            return redirect('/')
        
        supplier = request.user.supplier_profile
        return view_func(request, supplier=supplier, *args, **kwargs)
    return wrapper


def finance_dashboard_admin(request):
    """
    داشبورد مالی ادمین
    US-021: گزارش مالی (درآمد، تعداد سفارش، حساب تأمین‌کنندگان)
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, 'دسترسی غیرمجاز.')
        return redirect('/')
    
    stats = FinanceService.get_dashboard_stats(days=30)
    
    # لیست دفاتر حساب تأمین‌کنندگان با موجودی
    ledgers = SupplierLedger.objects.select_related('supplier').all()
    
    context = {
        'stats': stats,
        'ledgers': ledgers,
    }
    
    return render(request, 'finance/admin_dashboard.html', context)


def finance_dashboard_supplier(request):
    """
    داشبورد مالی تأمین‌کننده
    US-030: حساب ماهانه تأمین‌کننده
    """
    if not request.user.is_authenticated:
        messages.error(request, 'لطفاً وارد حساب کاربری شوید.')
        return redirect('/')
    
    if not hasattr(request.user, 'supplier_profile'):
        messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست.')
        return redirect('/')
    
    supplier = request.user.supplier_profile
    
    # دریافت سال و ماه از پارامترهای URL (اختیاری)
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    
    report = FinanceService.get_supplier_monthly_report(
        supplier,
        year=year,
        month=month
    )
    
    # موجودی کل
    ledger = FinanceService.get_or_create_ledger(supplier)
    
    context = {
        'supplier': supplier,
        'report': report,
        'ledger': ledger,
        'year': report['year'],
        'month': report['month'],
    }
    
    return render(request, 'finance/supplier_dashboard.html', context)



def finance_export_excel(request):
    """
    Export گزارش مالی به اکسل
    US-031: خروجی اکسل گزارش مالی
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, 'دسترسی غیرمجاز.')
        return redirect('/')
    
    import jdatetime
    today = jdatetime.date.today()
    filename = f'finance-report-{today.strftime("%Y-%m-%d")}.xlsx'
    
    output = FinanceExporter.export_all_transactions()
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
