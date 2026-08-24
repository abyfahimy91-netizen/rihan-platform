"""
D-099: فیلد مهلت پرداخت (رزرو موقت موجودی) برای سفارش

- expires_at روی Order
- Backfill: سفارش‌های PENDING قدیمی = created_at + ORDER_PAYMENT_TTL_MINUTES (پیش‌فرض ۶۰ دقیقه)
"""
from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


DEFAULT_TTL_MINUTES = 60


def backfill_pending_orders(apps, schema_editor):
    Order = apps.get_model('order', 'Order')
    ttl = timedelta(minutes=DEFAULT_TTL_MINUTES)
    Order.objects.filter(
        status='PENDING',
        expires_at__isnull=True,
    ).update(expires_at=models.F('created_at') + ttl)


def unbackfill(apps, schema_editor):
    Order = apps.get_model('order', 'Order')
    Order.objects.filter(status='PENDING').update(expires_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0009_alter_payment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='expires_at',
            field=models.DateTimeField(
                blank=True,
                help_text='سفارش‌های در انتظار پرداخت بعد از این زمان به‌صورت خودکار لغو و موجودی آزاد می‌شود',
                null=True,
                verbose_name='مهلت پرداخت (رزرو موجودی)',
            ),
        ),
        migrations.RunPython(backfill_pending_orders, unbackfill),
    ]
