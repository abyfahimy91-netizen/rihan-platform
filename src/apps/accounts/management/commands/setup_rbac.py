from django.core.management.base import BaseCommand
from apps.accounts.rbac import RBACService

class Command(BaseCommand):
    help = 'راه‌اندازی و تثبیت گروه‌ها و سطوح دسترسی سازمانی ریهان (M5)'

    def handle(self, *args, **options):
        roles = RBACService.setup_roles_and_permissions()
        self.stdout.write(self.style.SUCCESS(f"✓ ماتریس نقش‌های سازمانی با موفقیت تثبیت شد: {list(roles.keys())}"))
