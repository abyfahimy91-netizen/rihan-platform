"""
سیگنال‌های ماژول مالی

ثبت خودکار تراکنش فروش هنگام تحویل سفارش
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction as db_transaction

from src.modules.order.models import Order
from .services import FinanceService


@receiver(post_save, sender=Order)
def create_sale_transactions_on_delivery(sender, instance, created, **kwargs):
    """
    هنگامی که سفارش به وضعیت DELIVERED تغییر می‌کند،
    تراکنش فروش برای تأمین‌کنندگان ثبت می‌شود.
    """
    # فقط اگر سفارش تازه به DELIVERED رسیده باشد
    if instance.status == Order.OrderStatus.DELIVERED and not created:
        with db_transaction.atomic():
            for item in instance.items.all():
                FinanceService.create_sale_transaction(item, instance)
