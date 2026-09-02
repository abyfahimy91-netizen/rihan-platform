"""
RBAC-PERM-14050611 — تست چک‌لیست فارسی مجوزها در پنل نقش‌ها
"""
from django.test import TestCase, Client
from src.modules.rbac.models import Role


def _admin_client():
    from django.contrib.auth import get_user_model
    U = get_user_model()
    a = U.objects.create_user(username='09120000009', password='x123456789', email='a@r.local')
    a.is_staff = True
    a.is_superuser = True
    a.save()
    c = Client()
    c.force_login(a)
    return c


class PermissionCatalogTests(TestCase):
    def setUp(self):
        self.c = _admin_client()
        self.role = Role.objects.create(name='نقش تست', code='permtest',
                                        permissions=['product.view', 'order.view'])

    def test_change_page_shows_persian_checklist(self):
        r = self.c.get(f'/admin/rbac/role/{self.role.pk}/change/')
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn('چک‌لیست', body)
        self.assertIn('ایجاد محصول جدید', body)
        self.assertIn('دیدن همه سفارش‌ها', body)
        self.assertIn('دسترسی کامل', body)
        # JSON خام در بخش جمع‌شونده
        self.assertIn('product.view', body)
        # چک‌باکس‌های تیک‌خورده
        self.assertIn('checked', body)

    def test_add_page_has_checklist_not_json(self):
        r = self.c.get('/admin/rbac/role/add/')
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn('name="perms"', body)
        self.assertNotIn('permissions_json_view', body)

    def test_saving_checkboxes_updates_permissions(self):
        r = self.c.post(f'/admin/rbac/role/{self.role.pk}/change/', {
            'name': 'نقش تست', 'code': 'permtest',
            'description': 'تست',
            'perms': ['product.view', 'product.create', 'finance.report'],
        })
        self.assertEqual(r.status_code, 302)
        self.role.refresh_from_db()
        self.assertEqual(set(self.role.permissions), {'product.view', 'product.create', 'finance.report'})
        self.assertEqual(len(self.role.permissions), 3)

    def test_unknown_codes_preserved_and_displayed(self):
        self.role.permissions = ['product.view', 'legacy.custom_code']
        self.role.save()
        r = self.c.get(f'/admin/rbac/role/{self.role.pk}/change/')
        body = r.content.decode()
        self.assertIn('legacy.custom_code', body)  # به‌صورت سایر نمایش داده می‌شود
        r2 = self.c.post(f'/admin/rbac/role/{self.role.pk}/change/', {
            'name': 'نقش تست', 'code': 'permtest',
            'perms': ['product.view', 'legacy.custom_code'],
        })
        self.role.refresh_from_db()
        self.assertIn('legacy.custom_code', self.role.permissions)

    def test_system_roles_unchanged_in_db(self):
        admin = Role.objects.get(code='admin')
        self.assertEqual(admin.permissions, ['*'])
