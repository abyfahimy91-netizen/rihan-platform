"""اطلاع‌رسانی صفحات به IndexNow (D-118 GEO) — استفاده:

    python manage.py indexnow_submit --all          # همهٔ صفحات فعال
    python manage.py indexnow_submit URL1 URL2 ...  # URLهای مشخص

cron هفتگی برای تازه‌سازی کامل در /etc/cron.d/rihan-indexnow تنظیم شده است.
"""
from django.core.management.base import BaseCommand

from src.modules.catalog.indexnow import HOST, collect_all_urls, submit_urls


class Command(BaseCommand):
    help = 'ارسال URLها به IndexNow (Bing/Yandex/Seznam/Naver/Yep)'

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='*', type=str, help='URLهای مشخص برای ارسال')
        parser.add_argument('--all', action='store_true',
                            help='همهٔ صفحات فعال (محصولات + صفحات ثابت)')

    def handle(self, *args, **opts):
        urls = collect_all_urls() if opts['all'] else opts['urls']
        if not urls:
            self.stderr.write('هیچ URLی داده نشد — یا URL بده یا --all بزن.')
            return
        try:
            status = submit_urls(urls)
            self.stdout.write(self.style.SUCCESS(
                'IndexNow: %d URL به %s ارسال شد (HTTP %s)' % (len(urls), HOST, status)))
        except Exception as exc:
            self.stderr.write('IndexNow submit failed: %s' % exc)
            raise SystemExit(1)
