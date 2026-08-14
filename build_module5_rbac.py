import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

files = {
    BASE / "src/apps/accounts/rbac.py": """from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from functools import wraps

ROLE_SUPERADMIN = 'SuperAdmin'
ROLE_CATEGORY_MANAGER = 'CategoryManager'
ROLE_SUPPLIER = 'Supplier'
ROLE_CUSTOMER = 'Customer'

class RBACService:
    \"\"\"سرویس مدیریت نقش‌ها و ماتریس دسترسی پلتفرم ریهان (M5 - ADR-002)\"\"\"
    
    @classmethod
    def setup_roles_and_permissions(cls):
        # 1. SuperAdmin Group (مدیر ارشد)
        super_group, _ = Group.objects.get_or_create(name=ROLE_SUPERADMIN)
        # دسترسی کامل دارد
        
        # 2. CategoryManager Group (مدیر دسته‌بندی و خانواده)
        cat_group, _ = Group.objects.get_or_create(name=ROLE_CATEGORY_MANAGER)
        from apps.catalog.models import Product, Category, ContentBlock
        from apps.orders.models import Order
        
        # مجوزهای محصولات و کاتالوگ و مشاهده سفارشات
        catalog_cts = [
            ContentType.objects.get_for_model(Product),
            ContentType.objects.get_for_model(Category),
            ContentType.objects.get_for_model(ContentBlock),
            ContentType.objects.get_for_model(Order),
        ]
        perms = Permission.objects.filter(content_type__in=catalog_cts)
        cat_group.permissions.set(perms)

        # 3. Supplier Group (تأمین‌کننده)
        supp_group, _ = Group.objects.get_or_create(name=ROLE_SUPPLIER)
        # تأمین‌کننده فقط از داشبورد اختصاصی استفاده می‌کند
        
        return {
            ROLE_SUPERADMIN: super_group,
            ROLE_CATEGORY_MANAGER: cat_group,
            ROLE_SUPPLIER: supp_group
        }

    @classmethod
    def assign_role(cls, user, role_name):
        cls.setup_roles_and_permissions()
        user.groups.clear()
        
        if role_name == ROLE_SUPERADMIN:
            user.is_staff = True
            user.is_superuser = True
            group = Group.objects.get(name=ROLE_SUPERADMIN)
            user.groups.add(group)
        elif role_name == ROLE_CATEGORY_MANAGER:
            user.is_staff = True
            user.is_superuser = False
            group = Group.objects.get(name=ROLE_CATEGORY_MANAGER)
            user.groups.add(group)
        elif role_name == ROLE_SUPPLIER:
            user.is_staff = False
            user.is_superuser = False
            group = Group.objects.get(name=ROLE_SUPPLIER)
            user.groups.add(group)
        else: # Customer
            user.is_staff = False
            user.is_superuser = False
            
        user.save()
        return user

    @classmethod
    def get_user_role(cls, user):
        if not user.is_authenticated:
            return "مهمان"
        if user.is_superuser or user.groups.filter(name=ROLE_SUPERADMIN).exists():
            return "مدیر ارشد پلتفرم"
        if user.groups.filter(name=ROLE_CATEGORY_MANAGER).exists():
            return "مدیر دسته‌بندی و خانواده"
        if hasattr(user, 'supplier_profile') or user.groups.filter(name=ROLE_SUPPLIER).exists():
            return "همکار تأمین‌کننده"
        return "خریدار محترم"

# دکوراتورهای امنیتی نقش‌محور
def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_superuser or request.user.groups.filter(name=ROLE_SUPERADMIN).exists()):
            raise PermissionDenied("این بخش فقط در انحصار مدیر ارشد پلتفرم ریهان است.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def category_manager_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.groups.filter(name__in=[ROLE_SUPERADMIN, ROLE_CATEGORY_MANAGER]).exists()):
            raise PermissionDenied("دسترسی به این بخش نیازمند مجوز مدیریت دسته‌بندی است.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
""",

    BASE / "src/apps/accounts/management/__init__.py": "",
    BASE / "src/apps/accounts/management/commands/__init__.py": "",

    BASE / "src/apps/accounts/management/commands/setup_rbac.py": """from django.core.management.base import BaseCommand
from apps.accounts.rbac import RBACService

class Command(BaseCommand):
    help = 'راه‌اندازی و تثبیت گروه‌ها و سطوح دسترسی سازمانی ریهان (M5)'

    def handle(self, *args, **options):
        roles = RBACService.setup_roles_and_permissions()
        self.stdout.write(self.style.SUCCESS(f"✓ ماتریس نقش‌های سازمانی با موفقیت تثبیت شد: {list(roles.keys())}"))
""",

    BASE / "tests/test_rbac.py": """from django.test import TestCase, Client
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
"""
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created: {path.name}")

# Update PluginRegistry in src/apps/core/plugins.py to mark M5 as active
plugins_file = BASE / "src/apps/core/plugins.py"
plugins_text = plugins_file.read_text(encoding="utf-8")
if 'PluginRegistry.register("M5"' not in plugins_text:
    plugins_text += '\nPluginRegistry.register("M5", "سیستم کنترل دسترسی نقش‌محور RBAC", "0.5.8", is_system=True)\n'
    plugins_file.write_text(plugins_text, encoding="utf-8")
    print("✓ Registered M5 in PluginRegistry")

print("All Module M5 RBAC Files Deployed.")
