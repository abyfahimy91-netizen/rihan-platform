"""
ویوهای پنل تأمین‌کننده — نسخه D-105 (مرسوله‌محور)

تغییر مهم نسبت به قبل: تامین‌کننده دیگر «کل سفارش» را نمی‌بیند؛
فقط مرسوله‌های خودش را می‌بیند که شامل:
- اقلام او (نام محصول + واریانت + تعداد — بدون هیچ قیمتی)
- نام/موبایل/کدپستی/آدرس گیرنده
و پس از ارسال، کد رهگیری را در همین صفحه ثبت می‌کند؛
ثبت کد = پیامک خودکار رهگیری برای مشتری.

امنیت: RBAC + User-Supplier Link (D-085)
"""
import logging

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from src.modules.catalog.models import Supplier
from src.modules.order.models import Shipment
from src.modules.order.fulfillment import (
    FulfillmentError,
    dispatch_instruction_text,
    mark_shipped,
)
from src.modules.rbac.decorators import require_supplier

from .forms import TrackingCodeForm

logger = logging.getLogger(__name__)


def get_supplier_for_user(user):
    """دریافت Supplier مرتبط با کاربر (D-085: OneToOne link)"""
    try:
        return user.supplier_profile
    except Supplier.DoesNotExist:
        return None


def _own_shipments(supplier):
    return (
        Shipment.objects.filter(supplier=supplier)
        .exclude(status=Shipment.Status.CANCELED)
        .select_related('order')
        .prefetch_related('items__order_item')
        .order_by('-created_at')
    )


@require_supplier
def supplier_dashboard(request):
    """داشبورد: چند مرسوله منتظر اقدام شماست؟"""
    supplier = get_supplier_for_user(request.user)

    if not supplier:
        messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست. لطفاً با ادمین تماس بگیرید.')
        return redirect('home')

    qs = _own_shipments(supplier)
    context = {
        'supplier': supplier,
        'new_count': qs.filter(status=Shipment.Status.NEW).count(),
        'shipped_count': qs.filter(status=Shipment.Status.SHIPPED).count(),
        'delivered_count': qs.filter(status=Shipment.Status.DELIVERED).count(),
        'recent_new': list(qs.filter(status=Shipment.Status.NEW)[:5]),
    }
    return render(request, 'supplier_panel/dashboard.html', context)


@require_supplier
def shipment_list(request):
    """لیست مرسوله‌های تامین‌کننده با فیلتر وضعیت"""
    supplier = get_supplier_for_user(request.user)

    if not supplier:
        messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست.')
        return redirect('home')

    shipments = _own_shipments(supplier)
    status_filter = request.GET.get('status', '')
    valid_statuses = {c for c, _ in Shipment.Status.choices if c != Shipment.Status.CANCELED}
    if status_filter in valid_statuses:
        shipments = shipments.filter(status=status_filter)

    context = {
        'supplier': supplier,
        'shipments': shipments,
        'status_filter': status_filter,
        'statuses': [
            {'value': value, 'label': label}
            for value, label in Shipment.Status.choices
            if value != Shipment.Status.CANCELED
        ],
    }
    return render(request, 'supplier_panel/shipment_list.html', context)


@require_supplier
def shipment_detail(request, pk):
    """
    جزئیات مرسوله: اقلام (بدون قیمت) + گیرنده + ثبت کد رهگیری.
    POST فرم → mark_shipped → پیامک خودکار رهگیری برای مشتری.
    """
    supplier = get_supplier_for_user(request.user)

    if not supplier:
        messages.error(request, 'حساب کاربری شما به تأمین‌کننده‌ای متصل نیست.')
        return redirect('home')

    # امنیت: فقط مرسوله‌های متعلق به همین تامین‌کننده
    shipment = get_object_or_404(
        Shipment.objects.select_related('order').prefetch_related('items__order_item'),
        pk=pk,
        supplier=supplier,
    )
    order = shipment.order

    if request.method == 'POST':
        form = TrackingCodeForm(request.POST)
        if form.is_valid():
            try:
                mark_shipped(
                    shipment,
                    carrier=form.cleaned_data['carrier'],
                    tracking_code=form.cleaned_data['tracking_code'],
                    user=request.user,
                    via='supplier',
                )
                messages.success(
                    request,
                    'کد رهگیری ثبت شد ✅ پیامک رهگیری برای مشتری ارسال شد.'
                )
                return redirect('supplier_panel:shipment_detail', pk=shipment.pk)
            except FulfillmentError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'لطفاً خطاهای فرم را برطرف کنید.')
    else:
        initial = {}
        if not shipment.carrier:
            initial['carrier'] = Shipment.Carrier.POST
        form = TrackingCodeForm(initial=initial)

    items = []
    for si in shipment.items.all():
        title = si.order_item.product_name_snapshot
        variant = (si.order_item.variant_title or '').strip()
        if variant:
            title += f' — {variant}'
        items.append({'title': title, 'quantity': si.quantity})

    context = {
        'supplier': supplier,
        'shipment': shipment,
        'order': order,
        'form': form,
        'items': items,
        'receiver_name': order.guest_name or (order.user.get_full_name() if order.user else ''),
        'receiver_phone': order.guest_phone or (order.user.get_username() if order.user else ''),
        'address_text': (
            f"نام: {order.guest_name}\n"
            f"موبایل: {order.guest_phone}\n"
            f"کد پستی: {order.guest_postal_code}\n"
            f"آدرس: {order.guest_address}"
        ),
        'dispatch_text': dispatch_instruction_text(shipment),
    }
    return render(request, 'supplier_panel/shipment_detail.html', context)


# ── سازگاری با لینک‌های قدیمی ──

@require_supplier
def legacy_order_redirect(request, **kwargs):
    return redirect('supplier_panel:shipment_list')
