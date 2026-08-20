"""
Signals for Order Module (M2 + M7)

Auto-captures status changes in OrderStatusHistory for a REAL timeline.
Based on D-082: M7 - Order Tracking

Design notes:
- Uses QuerySet.update() (not instance.save()) when setting shipped_at /
  delivered_at, so post_save is not triggered recursively.
- On creation, an ORDER_CREATED entry is ALWAYS recorded. If the order is
  created with a non-DRAFT status, an extra entry for that status is added.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_status_mapping():
    """Map Order.status -> OrderStatusHistory.HistoryStatus."""
    from .models import OrderStatusHistory
    return {
        'DRAFT': OrderStatusHistory.HistoryStatus.ORDER_CREATED,
        'PENDING': OrderStatusHistory.HistoryStatus.PENDING_PAYMENT,
        'PAID': OrderStatusHistory.HistoryStatus.PAYMENT_CONFIRMED,
        'PROCESSING': OrderStatusHistory.HistoryStatus.PROCESSING,
        'SHIPPED': OrderStatusHistory.HistoryStatus.SHIPPED,
        'DELIVERED': OrderStatusHistory.HistoryStatus.DELIVERED,
        'CANCELLED': OrderStatusHistory.HistoryStatus.CANCELLED,
    }


def _apply_special_dates(instance, history_status):
    """
    Set shipped_at / delivered_at when entering those statuses.
    Uses QuerySet.update() to avoid re-triggering post_save.
    Returns an extra Persian description suffix.
    """
    from .models import Order, OrderStatusHistory

    if history_status == OrderStatusHistory.HistoryStatus.SHIPPED and not instance.shipped_at:
        now = timezone.now()
        Order.objects.filter(pk=instance.pk).update(shipped_at=now)
        instance.shipped_at = now
        return ' (هم‌اکنون ارسال شد)'

    if history_status == OrderStatusHistory.HistoryStatus.DELIVERED and not instance.delivered_at:
        now = timezone.now()
        Order.objects.filter(pk=instance.pk).update(delivered_at=now)
        instance.delivered_at = now
        return ' (هم‌اکنون تحویل شد)'

    return ''


@receiver(post_save, sender='order.Order')
def capture_order_status_change(sender, instance, created, **kwargs):
    """Capture every order status change in OrderStatusHistory."""
    from .models import OrderStatusHistory

    if getattr(instance, '_skip_history_signal', False):
        return

    try:
        status_mapping = _get_status_mapping()

        if created:
            # ALWAYS record the creation event.
            OrderStatusHistory.objects.create(
                order=instance,
                status=OrderStatusHistory.HistoryStatus.ORDER_CREATED,
                description='سفارش ثبت شد',
            )
            logger.info(f"Order {instance.order_number}: created (history recorded)")

            # If created with a non-DRAFT status, also record that status.
            if instance.status != 'DRAFT':
                current_status = status_mapping.get(instance.status)
                if current_status and current_status != OrderStatusHistory.HistoryStatus.ORDER_CREATED:
                    extra = _apply_special_dates(instance, current_status)
                    OrderStatusHistory.objects.create(
                        order=instance,
                        status=current_status,
                        description='وضعیت: ' + instance.get_status_display() + extra,
                        tracking_code=instance.tracking_code or '',
                    )
            return

        # Update case: only record when the status actually changed.
        history_status = status_mapping.get(instance.status)
        if not history_status:
            logger.warning(f"Unknown order status: {instance.status}")
            return

        last_history = (
            OrderStatusHistory.objects.filter(order=instance)
            .order_by('-created_at')
            .first()
        )

        if last_history and last_history.status == history_status:
            return  # No change, nothing to record.

        extra = _apply_special_dates(instance, history_status)

        if last_history:
            description = 'تغییر وضعیت به: ' + instance.get_status_display() + extra
        else:
            description = 'وضعیت: ' + instance.get_status_display() + extra

        OrderStatusHistory.objects.create(
            order=instance,
            status=history_status,
            description=description,
            tracking_code=instance.tracking_code or '',
        )
        logger.info(
            f"Order {instance.order_number}: status history recorded - {history_status}"
        )

    except Exception as e:
        logger.error(
            f"Failed to capture status change for order {instance.order_number}: {e}"
        )


@receiver(post_save, sender='order.Payment')
def capture_payment_status_change(sender, instance, created, **kwargs):
    """Capture payment status changes as order history entries."""
    from .models import OrderStatusHistory

    try:
        order = instance.order

        if instance.status == 'PENDING_REVIEW' and not created:
            exists = OrderStatusHistory.objects.filter(
                order=order,
                status=OrderStatusHistory.HistoryStatus.PAYMENT_SUBMITTED,
            ).exists()
            if not exists:
                OrderStatusHistory.objects.create(
                    order=order,
                    status=OrderStatusHistory.HistoryStatus.PAYMENT_SUBMITTED,
                    description='مشتری مدارک پرداخت را ارسال کرد',
                )
                logger.info(f"Order {order.order_number}: payment evidence submitted")

        elif instance.status == 'FAILED':
            OrderStatusHistory.objects.create(
                order=order,
                status=OrderStatusHistory.HistoryStatus.PAYMENT_REJECTED,
                description='پرداخت رد شد: ' + (instance.admin_notes or 'بدون دلیل'),
            )
            logger.info(f"Order {order.order_number}: payment rejected")

    except Exception as e:
        logger.error(f"Failed to capture payment status: {e}")
