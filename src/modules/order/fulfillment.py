"""
D-105 — زنجیره ارسال (Fulfillment): تخصیص سفارش به تامین‌کننده یا ریهان

جریان کامل کالا:
۱. پرداخت تایید شد → build_shipments اقلام را بر اساس Product.supplier تفکیک می‌کند:
   - هر تامین‌کننده یک Shipment جداگانه می‌گیرد (فقط اقلام خودش، بدون هیچ قیمتی)
   - محصولِ بدون تامین‌کننده → مرسوله «ریهان» (پردازش و ارسال داخلی خودمان)
۲. پیامک خودکار به تامین‌کننده (شماره از Supplier.phone) + ثبت در NotificationLog
   حتی اگر پیامک نرفت، ادمین در لاگ اطلاع‌رسانی‌ها می‌بیند.
۳. ثبت کد رهگیری (ادمین یا خود تامین‌کننده در پنل) → mark_shipped:
   - وضعیت سفارش همگام می‌شود (وقتی همه مرسوله‌ها رفتند → SHIPPED)
   - پیامک مشتری حاوی کد رهگیری + لینک «یک‌کلیکی» که سامانه پست را با کد پرشده باز می‌کند
۴. mark_delivered → وقتی همه مرسوله‌ها تحویل شدند، سفارش DELIVERED می‌شود.

قانون امنیتی: متن دستور ارسال محوله هرگز قیمت ندارد — فقط مقدار، گیرنده و آدرس.
"""
from __future__ import annotations

import logging
import os

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

SITE_BASE_URL = (os.environ.get('SITE_BASE_URL', '') or 'https://rihan360.ir').rstrip('/')

# لینک مستقیم رهگیری — کلیک مشتری، سامانه باربری را با کدِ پرشده باز می‌کند
CARRIER_TRACKING_URLS = {
    'POST': 'https://tracking.post.ir/search.aspx?id={code}',
    'TIPAX': 'https://newtracking.tipax.ir/Tracking?code={code}',
    'CHAPAR': 'https://chaparshipment.com/tracking?Number={code}',
}

_FA_TO_EN = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


class FulfillmentError(Exception):
    """خطای منطقی زنجیره ارسال — پیام فارسی برای نمایش به کاربر/ادمین"""


def to_en_digits(value) -> str:
    """تبدیل ارقام فارسی/عربی به لاتین + حذف فاصله و خط تیره (برای کد رهگیری)"""
    return str(value or '').translate(_FA_TO_EN).replace(' ', '').replace('-', '').strip()


def normalize_tracking_code(value) -> str:
    """کد رهگیری فقط حروف لاتین و عدد — ورودی فارسی هم می‌پذیرد"""
    code = to_en_digits(value)
    allowed = ''
    for ch in code:
        if ch.isalnum():
            allowed += ch.upper() if ch.isalpha() else ch
    return allowed


def build_tracking_url(carrier: str, code: str) -> str:
    """آدرس رهگیری مستقلی که با باز شدن، جست‌وجو با کد انجام شده است"""
    template = CARRIER_TRACKING_URLS.get(carrier or '')
    if not template or not code:
        return ''
    return template.format(code=code)


# ═══════════════════════════════════════════════════════════════
# D-111 — اعتبارسنجی استاندارد کد رهگیری هر شرکت حمل
# منبع: پست پیشتاز ۲۰ تا ۲۴ رقم؛ تیپاکس ۱۵ تا ۲۵ رقم؛
# چاپار شماره بارنامه دقیقاً ۱۴ رقم؛ «سایر» آزاد (اختیاری با ثبت جزئیات).
# ═══════════════════════════════════════════════════════════════

CARRIER_CODE_RULES = {
    'POST': {
        'min_len': 20, 'max_len': 24, 'digits_only': True,
        'hint': '۲۰ تا ۲۴ رقم (پیشتاز/ویژه) یا فرمت RA123456789IR (بین‌المللی)',
        'error': 'کد رهگیری پست باید ۲۰ تا ۲۴ رقم باشد (یا فرمت بین‌المللی مثل RA123456789IR). لطفاً کد روی رسید پست را دقیقاً و کامل وارد کنید.',
    },
    'TIPAX': {
        'min_len': 15, 'max_len': 25, 'digits_only': True,
        'hint': '۱۵ تا ۲۵ رقم — کد رهگیری روی رسید تیپاکس',
        'error': 'کد رهگیری تیپاکس باید ۱۵ تا ۲۵ رقم باشد. کد روی رسید تیپاکس را کامل وارد کنید.',
    },
    'CHAPAR': {
        'min_len': 14, 'max_len': 14, 'digits_only': True,
        'hint': 'دقیقاً ۱۴ رقم — شماره بارنامه چاپار',
        'error': 'کد رهگیری چاپار باید دقیقاً ۱۴ رقم باشد (شماره بارنامه روی رسید).',
    },
    'OTHER': {
        'min_len': 3, 'max_len': 40, 'digits_only': False,
        'hint': 'اختیاری — اگر شناسه/کد پیگیری دارید وارد کنید',
        'error': 'کد پیگیری واردشده کوتاه است؛ اگر شناسه‌ای وجود ندارد آن را خالی بگذارید و جزئیات ارسال‌کننده را کامل کنید.',
    },
}


def carrier_code_hint(carrier: str) -> str:
    """راهنمای فرمت کد رهگیری برای نمایش زیر فیلد (ادمین/پنل تامین‌کننده)"""
    rule = CARRIER_CODE_RULES.get(carrier or '')
    return rule['hint'] if rule else ''


def validate_tracking_code(carrier: str, code: str) -> str:
    """
    کد نرمال‌شده را با استاندارد شرکت حمل می‌سنجد.
    خروجی: کد (خالی مجاز فقط برای OTHER) — نامعتبر: FulfillmentError با پیام فارسی.
    """
    import re
    from .models import Shipment

    rule = CARRIER_CODE_RULES.get(carrier or '')
    if rule is None:
        raise FulfillmentError('شرکت حمل انتخاب‌شده معتبر نیست.')

    code = normalize_tracking_code(code)

    if carrier == Shipment.Carrier.OTHER:
        if code and len(code) < rule['min_len']:
            raise FulfillmentError(rule['error'])
        return code  # برای «سایر» خالی هم مجاز است

    if not code:
        raise FulfillmentError('لطفاً کد رهگیری مرسوله را وارد کنید.')

    # پست: فرمت بین‌المللی S10 مثل RA123456789IR / RR123456789IR هم معتبر است
    if carrier == Shipment.Carrier.POST and re.match(r'^[A-Z]{2}\d{9}[A-Z]{2}$', code):
        return code

    if rule['digits_only'] and not code.isdigit():
        raise FulfillmentError(
            f'کد رهگیری این شرکت حمل فقط باید رقم باشد. {rule["error"]}')
    if not (rule['min_len'] <= len(code) <= rule['max_len']):
        raise FulfillmentError(rule['error'])
    return code


def short_tracking_link(code: str) ->str:
    """لینک کوتاه دامنه خودمان → ریدایرکت به سامانه باربری (/order/t/<code>/)"""
    return f'{SITE_BASE_URL}/order/t/{code}'


# ────────────────────────────────────────────────
# تنظیمات اطلاع‌رسانی (ادمین‌محور)
# ────────────────────────────────────────────────

def _site_settings():
    try:
        from src.modules.pages.models import SiteSettings
        return SiteSettings.objects.first()
    except Exception:
        return None


def notify_suppliers_enabled() -> bool:
    s = _site_settings()
    return bool(getattr(s, 'sms_notify_suppliers', True))


def notify_customers_enabled() -> bool:
    s = _site_settings()
    return bool(getattr(s, 'sms_notify_customers', True))


def _log_notification(kind, recipient, ok, detail='', order=None, shipment=None):
    from .models import NotificationLog
    try:
        NotificationLog.objects.create(
            kind=kind, recipient=(recipient or '')[:20], success=bool(ok),
            detail=(detail or '')[:250], order=order, shipment=shipment,
        )
    except Exception:
        logger.exception('NotificationLog write failed')


def _send_sms(kind, phone, message, order=None, shipment=None) -> bool:
    """ارسال پیامک از طریق سرویس متمرکز + ثبت نتیجه در لاگ اطلاع‌رسانی"""
    phone = (phone or '').strip()
    if not phone:
        _log_notification(kind, '', False, 'شماره موبایل موجود نیست', order, shipment)
        return False
    from src.modules.auth.services.sms_service import SmsService
    try:
        ok, provider = SmsService.send_sms(phone, message)
    except Exception as e:  # قطعی شبکه نباید جریان سفارش را بترکاند
        logger.warning('SMS (%s) failed: %s', kind, e)
        ok, provider = False, f'error:{e}'
    _log_notification(kind, phone, ok, provider or '', order, shipment)
    return ok


# ────────────────────────────────────────────────
# ساخت مرسوله‌ها (تفکیک بر اساس تامین‌کننده)
# ────────────────────────────────────────────────

def unassigned_items(order):
    """اقلام سفارش که هنوز در هیچ مرسوله فعالی قرار نگرفته‌اند"""
    from .models import Shipment, ShipmentItem
    assigned_ids = set(
        ShipmentItem.objects.filter(
            shipment__order=order,
        ).exclude(shipment__status=Shipment.Status.CANCELED).values_list('order_item_id', flat=True)
    )
    return [i for i in order.items.select_related('product') if i.id not in assigned_ids]


def build_shipments(order, user=None, notify=True):
    """
    تفکیک اقلام پرداخت‌شده بین تامین‌کننده‌ها + سهم ریهان.
    خروجی: لیست مرسوله‌های ساخته‌شده (اگر قبلاً ساخته شده باشد همان‌ها برمی‌گردد).
    """
    from .models import Shipment, ShipmentItem
    from src.modules.catalog.models import Supplier

    if order.status not in (
        order.OrderStatus.PAID, order.OrderStatus.PROCESSING,
        order.OrderStatus.SHIPPED, order.OrderStatus.DELIVERED,
    ):
        raise FulfillmentError('ساخت مرسوله فقط برای سفارش پرداخت‌شده ممکن است.')

    active = [s for s in order.shipments.all() if s.status != Shipment.Status.CANCELED]
    if active:
        return active

    groups: dict = {}
    for item in unassigned_items(order):
        groups.setdefault(item.product.supplier_id, []).append(item)

    created = []
    with transaction.atomic():
        for sup_id, items in groups.items():
            supplier = None
            if sup_id:
                # تامین‌کننده غیرفعال = ریهان خودش ارسال می‌کند
                supplier = Supplier.objects.filter(pk=sup_id, is_active=True).first()
            fulfiller = (
                Shipment.FulfillerType.SUPPLIER if supplier
                else Shipment.FulfillerType.RIHAN
            )
            # D-113: پیش‌فرض «پرداخت‌کننده هزینه‌ها» همان ارسال‌کننده است
            payer = (Shipment.CostBearer.SUPPLIER if supplier
                     else Shipment.CostBearer.RIHAN)
            shipment = Shipment.objects.create(
                order=order,
                fulfiller=fulfiller,
                supplier=supplier,
                post_paid_by=payer,
                other_paid_by=payer,
            )
            ShipmentItem.objects.bulk_create([
                ShipmentItem(shipment=shipment, order_item=item, quantity=item.quantity)
                for item in items
            ])
            created.append(shipment)

        if created and order.status == order.OrderStatus.PAID:
            order.status = order.OrderStatus.PROCESSING
            order.save(update_fields=['status', 'updated_at'])
            order.status_history.create(
                status='PROCESSING',
                description='تخصیص برای ارسال (تفکیک بر اساس تامین‌کننده)',
                changed_by=user,
            )

    # پیامک بعد از commit تا اگر شبکه کند بود، تراکنش دیتابیس قفل نشود
    if notify:
        for shipment in created:
            if shipment.fulfiller == Shipment.FulfillerType.SUPPLIER:
                send_supplier_assignment_sms(shipment)
    return created


# ────────────────────────────────────────────────
# D-107: قالب پیامک‌ها از پنل ادمین + برند لاتین
# ────────────────────────────────────────────────

DEFAULT_CUSTOMER_SHIPPED_SMS = (
    'سفارش {order_number} ارسال شد ({carrier}).'
    '\nکد رهگیری: {tracking_code}'
    '\nپیگیری فوری:\n{link}'
    '\n{brand}'
)

# D-111: ارسال بدون کد رهگیری (شرکت حمل «سایر») — جزئیات ارسال‌کننده به‌جای کد
DEFAULT_CUSTOMER_SHIPPED_SMS_OTHER = (
    'سفارش {order_number} ارسال شد ({carrier}).'
    '\n{other_details}'
    '\n{brand}'
)

DEFAULT_SUPPLIER_ASSIGN_SMS = (
    '{brand} | سفارش جدید {order_number}\n'
    '{items}\n'
    'مشاهده آدرس و ثبت کد رهگیری:\n{link}'
)


def _sms_brand() -> str:
    s = _site_settings()
    brand = getattr(s, 'brand_name_latin', '') if s else ''
    return (brand or 'Rihan').strip()


def render_sms_template(custom: str, default: str, ctx: dict) -> str:
    """قالب ادمین را با متغیرها پر می‌کند؛ قالب خراب/خالی → پیش‌فرض امن"""
    template = (custom or '').strip()
    if not template:
        return default.format(**ctx)
    try:
        out = template.format(**ctx)
        if '{' in out and '}' in out:  # متغیر ناشناخته جا مانده
            raise ValueError('unresolved placeholder')
        return out
    except Exception:
        logger.warning('Custom SMS template invalid; using default. ctx=%s', list(ctx))
        return default.format(**ctx)


def item_line(order_item) -> str:
    title = order_item.product_name_snapshot
    variant = (order_item.variant_title or '').strip()
    if variant:
        title += f' ({variant})'
    return f'- {title} × {order_item.quantity}'


def dispatch_instruction_text(shipment) -> str:
    """متن آماده‌ی «دستور ارسال محوله» — قابل کپی برای ارسال دستی به تامین‌کننده"""
    from src.core.fa import jalali_human

    order = shipment.order
    receiver = customer_name(order)
    phone = customer_phone(order)
    address = (order.guest_address or '').strip()
    postal = (order.guest_postal_code or '').strip()

    lines = [
        f'📦 دستور ارسال محوله — {_sms_brand()}',
        f'مرسوله: #{str(shipment.id)[:8].upper()}',
        f'سفارش: {order.order_number}',
        f'تاریخ: {jalali_human(order.created_at)}',
        '',
        'اقلام ارسالی:',
    ]
    lines += [item_line(si.order_item) for si in shipment.items.select_related('order_item')]
    lines += [
        '',
        'گیرنده:',
        f'نام: {receiver}',
        f'موبایل: {phone}',
        f'کد پستی: {postal}',
        f'آدرس: {address}',
    ]
    if (shipment.notes or '').strip():
        lines.append(f'یادداشت: {shipment.notes.strip()}')
    lines += [
        '',
        '⚠️ پس از بسته‌بندی، کد رهگیری مرسوله را در پنل ثبت کنید:',
        f'{SITE_BASE_URL}/supplier/',
        'ثبت کد رهگیری = ارسال خودکار پیامک رهگیری به مشتری',
    ]
    return '\n'.join(lines)


# ────────────────────────────────────────────────
# تغییر وضعیت مرسوله + همگام‌سازی سفارش + پیامک‌ها
# ────────────────────────────────────────────────

def customer_name(order) -> str:
    if (order.guest_name or '').strip():
        return order.guest_name.strip()
    if order.user:
        return order.user.get_full_name() or order.user.get_username()
    return 'مشتری ریّان'


def customer_phone(order) -> str:
    """شماره موبایل مشتری: مهمان → فیلد مهمان؛ کاربر عضو → نام کاربری (= موبایل)"""
    phone = (order.guest_phone or '').strip()
    if phone:
        return phone
    if order.user and order.user.get_username().startswith('09'):
        return order.user.get_username()
    return ''


def _sync_order_after_shipment_status(shipment, user=None):
    """وضعیت سفارش را با وضعیت همه مرسوله‌ها هماهنگ می‌کند"""
    order = shipment.order
    active = [s for s in order.shipments.all() if s.status != shipment.Status.CANCELED]
    if not active:
        return
    statuses = {s.status for s in active}
    all_shipped = statuses <= {shipment.Status.SHIPPED, shipment.Status.DELIVERED}
    all_delivered = statuses == {shipment.Status.DELIVERED}

    if all_delivered and order.status != order.OrderStatus.DELIVERED:
        order.status = order.OrderStatus.DELIVERED
        order.delivered_at = shipment.delivered_at
        order.save(update_fields=['status', 'delivered_at', 'updated_at'])
        order.status_history.create(status='DELIVERED', description='تحویل همه مرسوله‌ها', changed_by=user)
    elif all_shipped and order.status not in (order.OrderStatus.SHIPPED, order.OrderStatus.DELIVERED):
        order.status = order.OrderStatus.SHIPPED
        order.save(update_fields=['status', 'updated_at'])
        order.status_history.create(
            status='SHIPPED',
            description=f'ارسال مرسوله‌ها — کد رهگیری: {shipment.tracking_code}',
            tracking_code=shipment.tracking_code,
            changed_by=user,
        )


def mark_shipped(shipment, carrier: str, tracking_code: str, user=None, via='admin', send_customer_sms=True,
                 other_carrier_name='', other_carrier_person='', other_carrier_phone=''):
    """
    ثبت کد رهگیری مرسوله.
    via: 'admin' یا 'supplier' — هر دو مسیر از اینجا عبور می‌کنند.
    D-111: اعتبارسنجی استاندارد کد برای هر شرکت حمل + جزئیات اجباری حالت «سایر».
    خروجی: (shipment, sms_sent: bool | None)
    """
    from .models import Shipment

    if carrier not in Shipment.Carrier.values:
        carrier = Shipment.Carrier.POST

    # اعتبارسنجی استاندارد کد (برای «سایر» خالی مجاز است)
    code = validate_tracking_code(carrier, tracking_code)

    if carrier == Shipment.Carrier.OTHER:
        missing = [
            label for label, value in (
                ('نام شرکت حمل', other_carrier_name),
                ('نام ارسال‌کننده/راننده', other_carrier_person),
                ('شماره تماس حمل‌کننده', other_carrier_phone),
            ) if not (value or '').strip()
        ]
        if missing:
            raise FulfillmentError(
                'برای گزینه «سایر» باید این موارد کامل شود: ' + '، '.join(missing) + '.')
    else:
        # جزئیات «سایر» برای سایر شرکت‌ها معنا ندارد — پاکسازی ورودی
        other_carrier_name = other_carrier_person = other_carrier_phone = ''

    shipment.carrier = carrier
    shipment.tracking_code = code
    shipment.other_carrier_name = (other_carrier_name or '').strip()
    shipment.other_carrier_person = (other_carrier_person or '').strip()
    shipment.other_carrier_phone = (other_carrier_phone or '').strip()
    shipment.status = Shipment.Status.SHIPPED
    shipment.shipped_at = timezone.now()
    shipment.save(update_fields=[
        'carrier', 'tracking_code', 'other_carrier_name', 'other_carrier_person',
        'other_carrier_phone', 'status', 'shipped_at', 'updated_at'])

    order = shipment.order
    # سازگاری با فیلدهای قدیمی سطح سفارش
    if not order.tracking_code:
        order.tracking_code = code
        order.shipping_method = shipment.carrier_full_label
    order.shipped_at = shipment.shipped_at
    order.save(update_fields=['tracking_code', 'shipping_method', 'shipped_at', 'updated_at'])
    _sync_order_after_shipment_status(shipment, user=user)

    sms_sent = None
    if send_customer_sms and notify_customers_enabled():
        phone = customer_phone(order)
        message = customer_shipped_text(shipment)
        sms_sent = _send_sms('CUSTOMER_SHIPPED', phone, message, order=order, shipment=shipment)
    return shipment, sms_sent


def mark_delivered(shipment, user=None):
    from .models import Shipment
    shipment.status = Shipment.Status.DELIVERED
    shipment.delivered_at = timezone.now()
    shipment.save(update_fields=['status', 'delivered_at', 'updated_at'])
    _sync_order_after_shipment_status(shipment, user=user)
    return shipment


# ────────────────────────────────────────────────
# متن پیامک‌ها
# ────────────────────────────────────────────────

def customer_shipped_text(shipment) -> str:
    """کوتاه و کم‌اصطکاک: کد رهگیری + لینک یک‌کلیکی (قالب از ادمین)"""
    order = shipment.order
    code = shipment.tracking_code
    settings = _site_settings()

    if not code:
        # D-111: شرکت حمل «سایر» بدون کد — جزئیات ارسال‌کننده
        ctx = {
            'brand': _sms_brand(),
            'order_number': order.order_number,
            'carrier': shipment.carrier_full_label,
            'other_details': shipment.other_details_text or 'به‌زودی اطلاعات کامل ارسال در پروفایل شما قابل مشاهده است.',
        }
        return render_sms_template(
            getattr(settings, 'sms_text_customer_shipped', ''),
            DEFAULT_CUSTOMER_SHIPPED_SMS_OTHER, ctx)

    ctx = {
        'brand': _sms_brand(),
        'order_number': order.order_number,
        'carrier': shipment.carrier_full_label,
        'tracking_code': code,
        'link': short_tracking_link(code),
    }
    return render_sms_template(
        getattr(settings, 'sms_text_customer_shipped', ''),
        DEFAULT_CUSTOMER_SHIPPED_SMS, ctx)


def send_supplier_assignment_sms(shipment) -> bool:
    """اطلاع به تامین‌کننده: سفارش جدید بدون قیمت + لینک پنل"""
    from .models import Shipment

    if shipment.fulfiller != Shipment.FulfillerType.SUPPLIER or not shipment.supplier:
        return False
    # D-106: کلید ادمین — پیامک تامین‌کننده می‌تواند کلاً خاموش باشد (سیستم موازی)
    if not notify_suppliers_enabled():
        logger.info('Supplier SMS skipped (disabled in SiteSettings) for shipment %s', shipment.id)
        return False
    phone = (shipment.supplier.phone or '').strip()
    brief = '، '.join(
        item_line(si.order_item).lstrip('- ')
        for si in shipment.items.select_related('order_item')[:4]
    )
    more = '' if shipment.items.count() <= 4 else ' …'
    ctx = {
        'brand': _sms_brand(),
        'order_number': shipment.order.order_number,
        'items': brief + more,
        'link': f'{SITE_BASE_URL}/supplier/',
    }
    message = render_sms_template(
        getattr(_site_settings(), 'sms_text_supplier_assign', ''),
        DEFAULT_SUPPLIER_ASSIGN_SMS, ctx)
    ok = _send_sms('SUPPLIER_ASSIGN', phone, message, order=shipment.order, shipment=shipment)
    now = timezone.now()
    shipment.sent_to_supplier_at = shipment.sent_to_supplier_at or now
    shipment.last_notified_at = now
    shipment.supplier_notified_count += 1
    shipment.save(update_fields=['sent_to_supplier_at', 'last_notified_at', 'supplier_notified_count', 'updated_at'])
    return ok


def remind_pending_suppliers(sla_hours: int = 24, max_reminders: int = 3) -> int:
    """یادآوری تامین‌کننده‌های بی‌تحریک: اگر ظرف SLA اقدام نکرد، دوباره پیامک برو"""
    from datetime import timedelta
    from .models import Shipment

    threshold = timezone.now() - timedelta(hours=sla_hours)
    stale = Shipment.objects.filter(
        status=Shipment.Status.NEW,
        fulfiller=Shipment.FulfillerType.SUPPLIER,
        supplier__isnull=False,
        created_at__lt=threshold,
        supplier_notified_count__lt=max_reminders,
    ).select_related('supplier', 'order')
    count = 0
    for shipment in stale:
        if send_supplier_assignment_sms(shipment):
            count += 1
            logger.info('Reminder #%d sent for shipment %s', shipment.supplier_notified_count, shipment.id)
    return count
