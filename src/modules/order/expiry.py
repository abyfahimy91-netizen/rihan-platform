"""
OrderReservationExpiry - آزادسازی خودکار موجودی سفارش‌های پرداخت‌نشده (D-099)

قانون کسب‌وکار:
- هر سفارش هنگام ثبت، موجودی‌اش برای مدت محدودی (پیش‌فرض ۶۰ دقیقه) رزرو می‌شود
- اگر مشتری تا پایان مهلت پرداخت نکند، رزرو آزاد و سفارش به‌صورت خودکار لغو می‌شود
- مهلت از طریق settings.ORDER_PAYMENT_TTL_MINUTES قابل تغییر است

نحوه اجرا:
- Lazy: هنگام بازدید صفحات پرداخت/پیگیری/پروفایل (release_expired_orders)
- Cron: دستور مدیریت `python manage.py release_expired_orders` هر ۵ دقیقه
"""
import logging

from django.db import transaction
from django.utils import timezone

from .models import Order, OrderStatusHistory, Payment
from .checkout_service import CheckoutService

logger = logging.getLogger(__name__)

AUTO_CANCEL_DESCRIPTION = (
    'مهلت پرداخت تمام شد؛ رزرو موجودی به‌صورت خودکار آزاد شد. '
    'در صورت تمایل می‌توانید دوباره خرید را ادامه دهید.'
)


def release_expired_orders(now=None):
    """
    لغو خودکار سفارش‌های در انتظار پرداخت که مهلت‌شان تمام شده است.

    Returns:
        list[str]: شماره سفارش‌هایی که در این اجرا لغو شدند
    """
    now = now or timezone.now()

    expired_orders = list(
        Order.objects.filter(
            status=Order.OrderStatus.PENDING,
            expires_at__isnull=False,
            expires_at__lt=now,
        ).prefetch_related('items')
    )

    cancelled_numbers = []
    for order in expired_orders:
        # محافظ: سفارشی که رسید پرداخت ثبت کرده (در انتظار بررسی ادمین است)
        # هرگز به‌صورت خودکار لغو نمی‌شود — پول مشتری ممکن است واریز شده باشد
        latest_payment = order.payments.order_by('-created_at').first()
        if latest_payment and latest_payment.status == Payment.PaymentStatus.PENDING_REVIEW:
            logger.info(
                f"Order {order.order_number}: expiry skipped — evidence under review"
            )
            continue
        try:
            with transaction.atomic():
                # جلوگیری از ثبت تاریخچه تکراری توسط سیگنال؛ توضیح اختصاصی می‌نویسیم
                order._skip_history_signal = True
                CheckoutService.cancel_order(
                    order,
                    reason='انقضای مهلت پرداخت (آزادسازی خودکار موجودی)',
                    user=None,
                )
                OrderStatusHistory.objects.create(
                    order=order,
                    status=OrderStatusHistory.HistoryStatus.CANCELLED,
                    description=AUTO_CANCEL_DESCRIPTION,
                )
            cancelled_numbers.append(order.order_number)
            logger.info(f"Order {order.order_number}: reservation expired and released")
        except Exception:
            logger.exception(f"Failed to release expired order {order.order_number}")

    if cancelled_numbers:
        logger.info(f"Released {len(cancelled_numbers)} expired order(s): {cancelled_numbers}")

    return cancelled_numbers
