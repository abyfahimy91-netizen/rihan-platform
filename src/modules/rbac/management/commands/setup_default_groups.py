# -*- coding: utf-8 -*-
"""
RBAC-GROUPS-14050611: گروه‌های دسترسی آمادهٔ جنگو برای جدول‌های ادمین
- فروش: سفارش/پرداخت/مرسوله (دید) + سرنخ‌ها (مدیریت CRM) + کاربران و کوپن (دید)
- انبار: محصول/دسته/تامین‌کننده (دید+ویرایش) + موجودی (کامل) + مرسوله‌ها (وضعیت) + سفارش (دید)
- حسابدار: سفارش/پرداخت (تایید) + مرسوله (تسویه) + حساب‌های بانکی
+ گیت پنل‌های خاص: /leads/panel/ = مجوز view_visitorlead، /finance/admin/ = مجوز view_bankaccount
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

GROUP_SPECS = {
    'فروش': [
        ('order', ['view_order', 'change_order', 'view_payment', 'view_shipment', 'view_coupon']),
        ('leads', ['view_visitorlead', 'change_visitorlead']),
        ('auth', ['view_user']),
        ('catalog', ['view_product']),
    ],
    'انبار': [
        ('catalog', ['view_product', 'change_product', 'view_category', 'view_supplier',
                     'view_inventory', 'add_inventory', 'change_inventory',
                     'view_inventorytransaction']),
        ('order', ['view_shipment', 'change_shipment', 'view_order']),
    ],
    'حسابدار': [
        ('order', ['view_order', 'view_payment', 'change_payment', 'view_shipment',
                   'view_bankaccount', 'view_coupon']),
    ],
}


class Command(BaseCommand):
    help = 'ساخت/به‌روزرسانی گروه‌های دسترسی استاندارد (فروش، انبار، حسابدار)'

    def handle(self, *args, **options):
        for group_name, specs in GROUP_SPECS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            perms = []
            missing = []
            for app_label, codenames in specs:
                for codename in codenames:
                    try:
                        perms.append(Permission.objects.get(
                            content_type__app_label=app_label, codename=codename))
                    except Permission.DoesNotExist:
                        missing.append(f'{app_label}.{codename}')
            group.permissions.set(perms)
            status = 'ساخته شد' if created else 'به‌روزرسانی شد'
            self.stdout.write(f'✅ گروه «{group_name}»: {status} — {len(perms)} مجوز'
                              + (f' | یافت‌نشده: {missing}' if missing else ''))
