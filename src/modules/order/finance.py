"""
سرویس مالی Rihan (D-113) — بهای تمام‌شده، حاشیه سود و تسویه تامین‌کننده

مدل تصمیم‌گرفته‌شده با کاربر:
- قیمت فروش دستی وارد می‌شود (تحقیق رقابتی + قیمت روانی توسط مالک)
- قیمت خرید هر واریانت در ProductVariant.cost_price
- هزینه پست/سایر در لحظه ارسال، دستی توسط ارسال‌کننده (تامین‌کننده یا ادمین) ثبت می‌شود
- قابل پرداخت به تامین‌کننده = قیمت خرید اقلام + هزینه‌هایی که خودش پیش‌پرداخت کرده
- فروش خود ادمین (مرسوله RIHAN) مشمول تسویه نیست — فقط در گزارش سود

منبع حقیقت: فیلدهای Shipment + snapshot قیمت خرید در OrderItem (بدون دفتر تراکنش موازی)
"""
import logging
from decimal import Decimal

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Order, Shipment

logger = logging.getLogger(__name__)

ZERO = Decimal('0')


# ═══════════════ محاسبات مرسوله ═══════════════

def shipment_financials(shipment):
    """خلاصه مالی یک مرسوله"""
    items_cost = shipment.items_cost
    supplier_extra = shipment.supplier_extra_costs
    rihan_extra = shipment.rihan_extra_costs
    return {
        'items_cost': items_cost,
        'supplier_extra': supplier_extra,
        'rihan_extra': rihan_extra,
        'landed_cost': items_cost + supplier_extra + rihan_extra,
        'revenue': shipment.items_revenue,
        'payable': shipment.supplier_payable,
        'settled': shipment.settlement_status == Shipment.SettlementStatus.SETTLED,
        'settled_amount': shipment.settled_amount or ZERO,
    }


# ═══════════════ محاسبات سفارش ═══════════════

def order_financials(order):
    """بهای تمام‌شده / سود ناخالص / وضعیت تسویه یک سفارش"""
    revenue = ZERO
    items_cost = ZERO
    unknown_cost = False
    for item in order.items.all():
        revenue += Decimal(item.unit_price_at_purchase) * item.quantity
        if item.unit_cost_at_purchase is None:
            unknown_cost = True
        else:
            items_cost += Decimal(item.unit_cost_at_purchase) * item.quantity

    post_supplier = post_rihan = other_supplier = other_rihan = ZERO
    for sh in order.shipments.exclude(status=Shipment.Status.CANCELED):
        post = sh.post_cost or ZERO
        other = sh.other_costs or ZERO
        if sh.post_paid_by == Shipment.CostBearer.SUPPLIER:
            post_supplier += post
        else:
            post_rihan += post
        if sh.other_paid_by == Shipment.CostBearer.SUPPLIER:
            other_supplier += other
        else:
            other_rihan += other

    landed = items_cost + post_supplier + post_rihan + other_supplier + other_rihan
    profit = revenue - landed
    margin = (profit / revenue * 100) if revenue else ZERO
    return {
        'revenue': revenue,
        'items_cost': items_cost,
        'post_supplier': post_supplier,
        'post_rihan': post_rihan,
        'other_supplier': other_supplier,
        'other_rihan': other_rihan,
        'landed_cost': landed,
        'profit': profit,
        'margin_percent': margin.quantize(Decimal('0.1')),
        'unknown_cost': unknown_cost,
    }


# ═══════════════ تسویه ═══════════════

def settle_shipments(shipments, admin_user, note=''):
    """
    تسویه گروهی مرسوله‌های تامین‌کننده — با snapshot مبلغ در لحظه تسویه.
    خروجی: (تعداد تسویه‌شده، تعداد ردشده)
    """
    from django.db import transaction
    settled = skipped = 0
    with transaction.atomic():
        for sh in shipments:
            if not sh.is_settleable:
                skipped += 1
                continue
            if sh.settlement_status == Shipment.SettlementStatus.SETTLED:
                skipped += 1
                continue
            sh.settlement_status = Shipment.SettlementStatus.SETTLED
            sh.settled_amount = sh.supplier_payable
            sh.settled_at = timezone.now()
            sh.settled_by = admin_user
            sh.settlement_note = (note or '')[:250]
            sh.save(update_fields=[
                'settlement_status', 'settled_amount', 'settled_at',
                'settled_by', 'settlement_note', 'updated_at'])
            settled += 1
    return settled, skipped


def reopen_shipments(shipments, admin_user, note=''):
    """بازکردن تسویه (مثلا مرجوعی یا خطای مبلغ) — snapshot پاک می‌شود"""
    from django.db import transaction
    reopened = skipped = 0
    with transaction.atomic():
        for sh in shipments:
            if sh.settlement_status != Shipment.SettlementStatus.SETTLED:
                skipped += 1
                continue
            sh.settlement_status = Shipment.SettlementStatus.UNSETTLED
            sh.settled_amount = None
            sh.settled_at = None
            sh.settled_by = admin_user
            sh.settlement_note = ((note or '') + ' — تسویه بازشد')[:250]
            sh.save(update_fields=[
                'settlement_status', 'settled_amount', 'settled_at',
                'settled_by', 'settlement_note', 'updated_at'])
            reopened += 1
    return reopened, skipped


def refresh_order_settlement_status(order):
    """وضعیت تجمعی تسویه سفارش از روی مرسوله‌هایش"""
    supplier_qs = (
        order.shipments
        .exclude(status=Shipment.Status.CANCELED)
        .filter(fulfiller=Shipment.FulfillerType.SUPPLIER)
        .exclude(supplier=None)
    )
    total = supplier_qs.count()
    if total == 0:
        new = Order.SettlementStatus.NONE
    else:
        settled = supplier_qs.filter(
            settlement_status=Shipment.SettlementStatus.SETTLED).count()
        if settled == 0:
            new = Order.SettlementStatus.PENDING
        elif settled < total:
            new = Order.SettlementStatus.PARTIAL
        else:
            new = Order.SettlementStatus.SETTLED
    if order.settlement_status != new:
        order.settlement_status = new
        order.save(update_fields=['settlement_status', 'updated_at'])
    return new


# ═══════════════ گزارش‌ها ═══════════════

def _shipment_rows(qs):
    """ردیف‌های مالی مرسوله‌ها برای جدول گزارش (اقلام prefetch شود)"""
    rows = []
    for sh in qs.prefetch_related('items__order_item').select_related('order', 'supplier'):
        f = shipment_financials(sh)
        rows.append({
            'shipment': sh,
            'order_number': sh.order.order_number,
            'supplier_title': sh.supplier.title if sh.supplier_id else 'ریهان',
            **f,
        })
    return rows


def supplier_financials(supplier):
    """
    گزارش مالی تامین‌کننده:
    - sold_total: ارزش فروش اقلام او (سفارش‌های غیرلغوشده)
    - payable_total: کل قابل دریافت (خرید + پیش‌پرداخت‌هایش)
    - unsettled / settled: تفکیک تسویه
    """
    shipments = list(
        Shipment.objects.filter(supplier=supplier)
        .exclude(status=Shipment.Status.CANCELED)
        .prefetch_related('items__order_item')
        .select_related('order')
    )
    sold = ZERO
    payable = ZERO
    unsettled = ZERO
    settled = ZERO
    unsettled_count = settled_count = 0
    for sh in shipments:
        sold += sh.items_revenue
        p = sh.supplier_payable
        payable += p
        if sh.settlement_status == Shipment.SettlementStatus.SETTLED:
            settled += sh.settled_amount or ZERO
            settled_count += 1
        else:
            unsettled += p
            unsettled_count += 1
    return {
        'sold_total': sold,
        'payable_total': payable,
        'settled_total': settled,
        'unsettled_total': unsettled,
        'unsettled_count': unsettled_count,
        'settled_count': settled_count,
        'shipment_count': len(shipments),
        'balance': unsettled,  # طلب فعلی تامین‌کننده
    }


def admin_overview():
    """
    نمای کلی مالی ادمین: کل فروش / بهای تمام‌شده / سود ناخالص
    + جدول هر تامین‌کننده: فروخته / قابل پرداخت / تسویه‌شده / مانده طلب
    (فقط سفارش‌های غیر DRAFT و غیر CANCELLED)
    """
    orders = Order.objects.exclude(
        status__in=[Order.OrderStatus.DRAFT, Order.OrderStatus.CANCELLED])

    revenue = items_cost = post_r = post_s = other_r = other_s = ZERO
    for o in orders.prefetch_related('items'):
        f = order_financials(o)
        revenue += f['revenue']
        items_cost += f['items_cost']
        post_r += f['post_rihan']
        post_s += f['post_supplier']
        other_r += f['other_rihan']
        other_s += f['other_supplier']

    from src.modules.catalog.models import Supplier
    supplier_rows = []
    for sup in Supplier.objects.filter(is_active=True).order_by('title'):
        d = supplier_financials(sup)
        d['supplier'] = sup
        if d['shipment_count']:
            supplier_rows.append(d)

    profit = revenue - (items_cost + post_r + post_s + other_r + other_s)
    margin = (profit / revenue * 100) if revenue else ZERO
    return {
        'order_count': orders.count(),
        'revenue': revenue,
        'items_cost': items_cost,
        'post_rihan': post_r,
        'post_supplier': post_s,
        'other_rihan': other_r,
        'other_supplier': other_s,
        'landed_cost': items_cost + post_r + post_s + other_r + other_s,
        'profit': profit,
        'margin_percent': margin.quantize(Decimal('0.1')),
        'supplier_rows': supplier_rows,
        'unsettled_total': sum(r['unsettled_total'] for r in supplier_rows),
        'settled_total': sum(r['settled_total'] for r in supplier_rows),
    }


# ═══════════════ سیگنال‌ها ═══════════════

@receiver(post_save, sender=Shipment)
def _shipment_saved_refresh_order(sender, instance, **kwargs):
    try:
        refresh_order_settlement_status(instance.order)
    except Exception:  # noqa: BLE001 — گزارش مالی نباید عملیات ارسال را بشکند
        logger.exception('refresh settlement status failed for order %s', instance.order_id)


@receiver(post_delete, sender=Shipment)
def _shipment_deleted_refresh_order(sender, instance, **kwargs):
    try:
        order_id = instance.order_id
        order = Order.objects.filter(pk=order_id).first()
        if order:
            refresh_order_settlement_status(order)
    except Exception:  # noqa: BLE001
        logger.exception('refresh settlement status failed after delete for order %s',
                         instance.order_id)
