"""
D-099: لغو خودکار سفارش‌های پرداخت‌نشده‌ای که مهلت رزرو‌شان تمام شده است.

Usage:
    python manage.py release_expired_orders
"""
from django.core.management.base import BaseCommand

from src.modules.order.expiry import release_expired_orders


class Command(BaseCommand):
    help = 'لغو سفارش‌های در انتظار پرداخت که مهلت رزرو موجودی‌شان تمام شده است'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet', action='store_true',
            help='فقط تعداد را چاپ کن (برای cron)',
        )

    def handle(self, *args, **options):
        cancelled = release_expired_orders()
        if options['quiet']:
            self.stdout.write(str(len(cancelled)))
        elif cancelled:
            self.stdout.write(self.style.SUCCESS(
                f'{len(cancelled)} سفارش منقضی لغو و موجودی آزاد شد: {", ".join(cancelled)}'
            ))
        else:
            self.stdout.write('سفارش منقضی‌ای وجود نداشت.')
