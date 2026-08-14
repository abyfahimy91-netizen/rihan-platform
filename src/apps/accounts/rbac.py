from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from functools import wraps

ROLE_SUPERADMIN = 'SuperAdmin'
ROLE_CATEGORY_MANAGER = 'CategoryManager'
ROLE_SUPPLIER = 'Supplier'
ROLE_CUSTOMER = 'Customer'

class RBACService:
    """سرویس مدیریت نقش‌ها و ماتریس دسترسی پلتفرم ریهان (M5 - ADR-002)"""
    
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
