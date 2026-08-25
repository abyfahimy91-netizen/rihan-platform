"""D-105 — یادآوری پیامکی تامین‌کننده‌های بی‌تحرک (برای cron ساعتی)"""
from django.core.management.base import BaseCommand

from src.modules.order.fulfillment import remind_pending_suppliers


class Command(BaseCommand):
    help = 'به تامین‌کننده‌هایی که ظرف SLA کد رهگیری ثبت نکرده‌اند دوباره پیامک می‌دهد'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24,
                            help='چند ساعت بعد از تخصیص یادآوری شود (پیش‌فرض ۲۴)')
        parser.add_argument('--max-reminders', type=int, default=3,
                            help='حداکثر تعداد یادآوری برای هر مرسوله')
        parser.add_argument('--quiet', action='store_true')

    def handle(self, *args, **opts):
        count = remind_pending_suppliers(
            sla_hours=opts['hours'], max_reminders=opts['max_reminders'])
        if not opts['quiet']:
            self.stdout.write(self.style.SUCCESS(f'{count} reminder(s) sent'))
