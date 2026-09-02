"""
RBAC-GROUPS-14050611 — تست گروه‌های آماده و گیت پنل‌های خاص
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from src.modules.order.models import Order
from src.modules.rbac.management.commands.setup_default_groups import GROUP_SPECS


def ensure_groups():
    """ساخت گروه‌ها در دیتابیس تست (از همان SPEC دستور مدیریت)"""
    from django.contrib.auth.models import Permission
    for group_name, specs in GROUP_SPECS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        perms = [Permission.objects.get(content_type__app_label=a, codename=c)
                 for a, codes in specs for c in codes]
        group.permissions.set(perms)


U = get_user_model()
HOST = 'rihan360.ir'


class DefaultGroupsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_groups()
    def test_groups_exist_with_expected_perm_counts(self):
        self.assertTrue(Group.objects.filter(name='فروش').exists())
        self.assertTrue(Group.objects.filter(name='انبار').exists())
        self.assertTrue(Group.objects.filter(name='حسابدار').exists())
        self.assertEqual(Group.objects.get(name='فروش').permissions.count(), 9)
        self.assertEqual(Group.objects.get(name='انبار').permissions.count(), 11)
        self.assertEqual(Group.objects.get(name='حسابدار').permissions.count(), 6)

    def test_sales_group_has_lead_perms(self):
        g = Group.objects.get(name='فروش')
        codes = set(g.permissions.values_list('codename', flat=True))
        self.assertIn('view_visitorlead', codes)
        self.assertIn('change_visitorlead', codes)
        self.assertIn('change_order', codes)
        self.assertNotIn('change_payment', codes)  # تایید پرداخت کار حسابدار است

    def test_accountant_has_change_payment(self):
        g = Group.objects.get(name='حسابدار')
        codes = set(g.permissions.values_list('codename', flat=True))
        self.assertIn('change_payment', codes)
        self.assertIn('view_bankaccount', codes)


class PanelGatesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_groups()

    def _user(self, groups=(), superuser=False):
        u = U.objects.create_user(username=f'0912{abs(hash(groups)) % 10**8:08d}',
                                  password='x123456789', email='t@r.local')
        u.is_staff = True
        u.is_superuser = superuser
        u.save()
        for g in groups:
            u.groups.add(Group.objects.get(name=g))
        return u

    def test_sales_user_can_open_leads_panel_but_not_finance(self):
        c = Client()
        c.force_login(self._user(groups=('فروش',)))
        r = c.get('/leads/panel/', HTTP_HOST=HOST)
        self.assertEqual(r.status_code, 200)
        r2 = c.get('/finance/admin/', HTTP_HOST=HOST)
        self.assertIn(r2.status_code, (302, 403))

    def test_accountant_can_open_finance(self):
        c = Client()
        c.force_login(self._user(groups=('حسابدار',)))
        r = c.get('/finance/admin/', HTTP_HOST=HOST)
        self.assertEqual(r.status_code, 200)

    def test_warehouse_cannot_open_leads_panel(self):
        c = Client()
        c.force_login(self._user(groups=('انبار',)))
        r = c.get('/leads/panel/', HTTP_HOST=HOST, follow=True)
        self.assertEqual(r.request['PATH_INFO'], '/')

    def test_superuser_still_everywhere(self):
        c = Client()
        c.force_login(self._user(superuser=True))
        self.assertEqual(c.get('/leads/panel/', HTTP_HOST=HOST).status_code, 200)
        self.assertEqual(c.get('/finance/admin/', HTTP_HOST=HOST).status_code, 200)

    def test_sales_sees_only_own_group_models_in_admin(self):
        c = Client()
        c.force_login(self._user(groups=('فروش',)))
        body = c.get('/admin/', HTTP_HOST=HOST).content.decode()
        self.assertIn('/admin/order/order/', body)
        self.assertIn('/admin/leads/visitorlead/', body)
        # محصولات فقط دید
        r = c.get('/admin/catalog/product/', HTTP_HOST=HOST)
        self.assertEqual(r.status_code, 200)
        # ولی نقش‌های RBAC و موجودی ممنوع
        self.assertEqual(c.get('/admin/rbac/role/', HTTP_HOST=HOST).status_code, 403)
        self.assertEqual(c.get('/admin/catalog/inventory/', HTTP_HOST=HOST).status_code, 403)
