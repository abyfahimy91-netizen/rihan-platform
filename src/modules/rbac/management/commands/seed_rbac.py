"""
seed_rbac: ایجاد Roles و Permissions پیش‌فرض

بر اساس:
- USER-PERSONAS.md: P4 (عبدالحسین), P5 (فاطمه), P6 (بچه‌ها)
- USER-STORIES.md: US-016 تا US-024 (داستان‌های ادمین)
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from modules.rbac.models import Role, Permission, UserProfile

User = get_user_model()


# تعریف permissions بر اساس US-016 تا US-024
PERMISSIONS = [
    # M1: Catalog
    ('catalog.view', 'مشاهده محصولات', 'catalog'),
    ('catalog.create', 'ایجاد محصول', 'catalog'),
    ('catalog.update', 'ویرایش محصول', 'catalog'),
    ('catalog.delete', 'حذف محصول', 'catalog'),
    ('catalog.manage_categories', 'مدیریت دسته‌بندی‌ها', 'catalog'),
    
    # M2: Orders
    ('orders.view', 'مشاهده سفارش‌ها', 'orders'),
    ('orders.approve', 'تأیید سفارش', 'orders'),
    ('orders.reject', 'رد سفارش', 'orders'),
    ('orders.update_status', 'تغییر وضعیت سفارش', 'orders'),
    ('orders.add_tracking', 'افزودن کد رهگیری', 'orders'),
    
    # M3: Family Panel
    ('panel.view_dashboard', 'مشاهده داشبورد', 'panel'),
    ('panel.view_reports', 'مشاهده گزارش‌ها', 'panel'),
    ('panel.manage_settings', 'مدیریت تنظیمات', 'panel'),
    
    # M6: Finance
    ('finance.view', 'مشاهده گزارش‌های مالی', 'finance'),
    ('finance.export', 'خروجی گزارش‌ها', 'finance'),
    
    # M8: Reviews
    ('reviews.view', 'مشاهده نظرات', 'reviews'),
    ('reviews.approve', 'تأیید نظرات', 'reviews'),
    ('reviews.reject', 'رد نظرات', 'reviews'),
    ('reviews.respond', 'پاسخ به نظرات', 'reviews'),
    
    # M9: Leads
    ('leads.view', 'مشاهده سرنخ‌ها', 'leads'),
    ('leads.follow_up', 'پیگیری سرنخ', 'leads'),
    ('leads.mark_obsolete', 'علامت‌گذاری منسوخ', 'leads'),
    
    # M10: Users
    ('users.view', 'مشاهده کاربران', 'users'),
    ('users.create', 'ایجاد کاربر', 'users'),
    ('users.manage', 'مدیریت کاربران', 'users'),
    
    # M14: Plugins
    ('plugins.view', 'مشاهده ماژول‌ها', 'plugins'),
    ('plugins.toggle', 'فعال/غیرفعال کردن ماژول‌ها', 'plugins'),
    ('flags.manage', 'مدیریت Feature Flags', 'plugins'),
]

# تعریف نقش‌ها بر اساس USER-PERSONAS
ROLES = {
    'super_admin': {
        'display_name': 'مدیر ارشد (P4)',
        'description': 'دسترسی کامل - عبدالحسین',
        'session_hours': 8,
        'max_attempts': 5,
        'lockout_minutes': 15,
        'permissions': 'all',  # همه permissions
    },
    'admin': {
        'display_name': 'مدیر عملیات (P5)',
        'description': 'دسترسی بالا - فاطمه (همسر)',
        'session_hours': 8,
        'max_attempts': 5,
        'lockout_minutes': 15,
        'permissions': [
            'catalog.view', 'catalog.create', 'catalog.update',
            'catalog.manage_categories',
            'orders.view', 'orders.approve', 'orders.update_status',
            'orders.add_tracking',
            'panel.view_dashboard', 'panel.view_reports',
            'finance.view',
            'reviews.view', 'reviews.approve', 'reviews.respond',
            'leads.view', 'leads.follow_up',
        ],
    },
    'staff': {
        'display_name': 'کمکی (P6)',
        'description': 'دسترسی محدود - بچه‌ها در آینده',
        'session_hours': 4,
        'max_attempts': 3,
        'lockout_minutes': 30,
        'permissions': [
            'catalog.view',
            'orders.view',
            'panel.view_dashboard',
            'reviews.view',
            'leads.view',
        ],
    },
}


class Command(BaseCommand):
    help = 'Seed کردن Roles و Permissions از USER-PERSONAS و USER-STORIES'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='ایجاد superuser عبدالحسین',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='حذف همه roles و permissions موجود',
        )
    
    def handle(self, *args, **options):
        # حذف در صورت درخواست
        if options['clear']:
            perm_count = Permission.objects.count()
            role_count = Role.objects.count()
            Permission.objects.all().delete()
            Role.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'⚠️  {perm_count} permission و {role_count} role حذف شد'
            ))
        
        # ایجاد Permissions
        perm_created = 0
        perm_updated = 0
        perm_objects = {}
        
        for code, name, module in PERMISSIONS:
            perm, was_created = Permission.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'module': module,
                }
            )
            perm_objects[code] = perm
            if was_created:
                perm_created += 1
            else:
                perm_updated += 1
        
        self.stdout.write(
            f'✅ Permissions: {perm_created} ایجاد | {perm_updated} به‌روزرسانی'
        )
        
        # ایجاد Roles
        role_created = 0
        role_updated = 0
        role_objects = {}
        
        for role_name, role_data in ROLES.items():
            role, was_created = Role.objects.update_or_create(
                name=role_name,
                defaults={
                    'display_name': role_data['display_name'],
                    'description': role_data['description'],
                    'is_system': True,
                    'session_duration_hours': role_data['session_hours'],
                    'max_login_attempts': role_data['max_attempts'],
                    'lockout_duration_minutes': role_data['lockout_minutes'],
                }
            )
            
            # تنظیم permissions
            role.permissions.clear()
            if role_data['permissions'] == 'all':
                role.permissions.set(Permission.objects.all())
            else:
                for perm_code in role_data['permissions']:
                    if perm_code in perm_objects:
                        role.permissions.add(perm_objects[perm_code])
            
            role_objects[role_name] = role
            
            if was_created:
                role_created += 1
            else:
                role_updated += 1
        
        self.stdout.write(
            f'✅ Roles: {role_created} ایجاد | {role_updated} به‌روزرسانی'
        )
        
        # ایجاد superuser در صورت درخواست
        if options['create_superuser']:
            self._create_superuser(role_objects.get('super_admin'))
        
        # خلاصه
        self.stdout.write('\n' + self.style.SUCCESS('📊 خلاصه:'))
        for role in Role.objects.all():
            perms_count = role.permissions.count()
            self.stdout.write(
                f'  • {role.name}: {perms_count} permission'
            )
    
    def _create_superuser(self, super_admin_role):
        """ایجاد superuser عبدالحسین"""
        username = 'abdolhossein'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'⚠️  کاربر {username} از قبل وجود دارد'
            ))
            user = User.objects.get(username=username)
        else:
            user = User.objects.create_superuser(
                username=username,
                email='admin@rihan360.ir',
                password='Rihan1405!',  # رمز موقت
                first_name='عبدالحسین',
                last_name='فهیمی',
            )
            self.stdout.write(self.style.SUCCESS(
                f'✅ کاربر {username} ایجاد شد (رمز: Rihan1405!)'
            ))
        
        # ایجاد/به‌روزرسانی UserProfile
        profile, _ = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'role': super_admin_role,
                'is_active': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f'✅ UserProfile ایجاد شد با نقش {super_admin_role.name}'
        ))
