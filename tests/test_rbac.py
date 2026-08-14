from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.accounts.rbac import RBACService, ROLE_SUPERADMIN, ROLE_CATEGORY_MANAGER, ROLE_SUPPLIER, ROLE_CUSTOMER
from apps.catalog.models import Supplier

User = get_user_model()

class RBACTestCase(TestCase):
    def setUp(self):
        # 1. SuperAdmin User (عبدالحسین)
        self.superadmin = User.objects.create_user(username='admin_super', password='SuperPass1405!')
        RBACService.assign_role(self.superadmin, ROLE_SUPERADMIN)

        # 2. CategoryManager User (فاطمه)
        self.cat_manager = User.objects.create_user(username='cat_manager_user', password='CatPass1405!')
        RBACService.assign_role(self.cat_manager, ROLE_CATEGORY_MANAGER)

        # 3. Supplier User (مولا)
        self.supplier_user = User.objects.create_user(username='supplier_user', password='SuppPass1405!')
        RBACService.assign_role(self.supplier_user, ROLE_SUPPLIER)
        self.supplier = Supplier.objects.create(
            user=self.supplier_user, title="خشکبار هوراند", contact_name="مولا", phone="09141112233", city="هوراند"
        )

        # 4. Customer User (مریم)
        self.customer = User.objects.create_user(username='customer_user', password='CustPass1405!')
        RBACService.assign_role(self.customer, ROLE_CUSTOMER)

    def test_role_identification(self):
        self.assertEqual(RBACService.get_user_role(self.superadmin), "مدیر ارشد پلتفرم")
        self.assertEqual(RBACService.get_user_role(self.cat_manager), "مدیر دسته‌بندی و خانواده")
        self.assertEqual(RBACService.get_user_role(self.supplier_user), "همکار تأمین‌کننده")
        self.assertEqual(RBACService.get_user_role(self.customer), "خریدار محترم")

    def test_access_boundaries(self):
        c = Client()
        
        # Customer cannot access supplier dashboard
        c.force_login(self.customer)
        res = c.get(reverse('supplier_dashboard'))
        self.assertEqual(res.status_code, 403) # PermissionDenied

        # Supplier can access supplier dashboard
        c.force_login(self.supplier_user)
        res_supp = c.get(reverse('supplier_dashboard'))
        self.assertEqual(res_supp.status_code, 200)

        # Category Manager can access admin
        self.assertTrue(self.cat_manager.is_staff)
        self.assertFalse(self.cat_manager.is_superuser)
