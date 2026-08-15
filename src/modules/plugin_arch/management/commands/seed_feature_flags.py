"""
seed_feature_flags: ایجاد Feature Flags از مستندات

بر اساس:
- D-079 (برند مستقل، بلوک‌محور، سئو، قیف فروش)
- MVP-SCOPE.md (ویژگی‌های ۱۴ ماژول)
- feature_flags.py قبلی apps.core
"""
from django.core.management.base import BaseCommand
from modules.plugin_arch.models import FeatureFlag


FLAGS = [
    # M1: کاتالوگ و بلوک‌محور (D-079)
    ('FEATURE_PRODUCT_CONTENT_BLOCKS', 'بلوک‌محور محصولات', True, 'catalog'),
    ('FEATURE_PRODUCT_BLOCK_JUNCTION', 'اتصال محصولات به بلوک‌ها', True, 'catalog'),
    
    # M2: سبد خرید (D-080)
    ('FEATURE_CART_TRANSPARENT_PRICING', 'قیمت‌گذاری شفاف D-080', True, 'cart'),
    ('FEATURE_CART_GUEST_CHECKOUT', 'خرید مهمان', True, 'cart'),
    
    # M3: پنل خانواده
    ('FEATURE_FAMILY_PANEL_ACTIVITY_LOG', 'لاگ فعالیت ادمین‌ها', True, 'admin'),
    ('FEATURE_FAMILY_PANEL_NOTIFICATIONS', 'اعلان‌ها در پنل خانواده', False, 'admin'),
    
    # M4: پنل تأمین‌کننده (D-079)
    ('FEATURE_SUPPLIER_PANEL', 'پنل تأمین‌کننده', False, 'supplier'),
    
    # M5: RBAC
    ('FEATURE_RBAC_ENFORCEMENT', 'اجرای RBAC', True, 'auth'),
    
    # M6: مالی
    ('FEATURE_FINANCE_REPORTS', 'گزارش‌های مالی', True, 'finance'),
    
    # M8: نظرات معتمد (D-044)
    ('FEATURE_CUSTOMER_REVIEWS', 'نظرات مشتریان معتمد', False, 'reviews'),
    ('FEATURE_REVIEWS_ADMIN_APPROVAL', 'نیاز به تأیید ادمین', True, 'reviews'),
    
    # M9: سرنخ‌ها
    ('FEATURE_LEAD_CAPTURE', 'فرم سرنخ کالا ناموجود C3', True, 'leads'),
    
    # M10: احراز هویت (ADR-006)
    ('FEATURE_SMS_OTP_LOGIN', 'ورود با پیامک OTP', True, 'auth'),
    ('FEATURE_BACKUP_PASSWORD_LOGIN', 'ورود با رمز پشتیبان', True, 'auth'),
    
    # M11: پرداخت (ADR-005)
    ('FEATURE_CARD_TO_CARD_PAYMENT', 'پرداخت کارت‌به‌کارت', True, 'payment'),
    ('FEATURE_ONLINE_PAYMENT_GATEWAY', 'درگاه پرداخت آنلاین', False, 'payment'),
    
    # M7: پیگیری
    ('FEATURE_ORDER_TRACKING_PUBLIC', 'پیگیری سفارش بدون لاگین', True, 'tracking'),
    
    # M13: هویت بصری (D-079)
    ('FEATURE_VISUAL_IDENTITY_BRAND', 'برند مستقل', True, 'ui'),
    
    # M14: معماری
    ('FEATURE_PLUGIN_HOOKS', 'سیستم Hook ها', True, 'core'),
    
    # سئو (D-079)
    ('FEATURE_SEO_SCHEMAS', 'Schema.org برای محصولات', True, 'seo'),
    ('FEATURE_SEO_SITEMAP', 'Sitemap.xml خودکار', True, 'seo'),
    
    # قیف فروش (D-079)
    ('FEATURE_SALES_FUNNEL', 'قیف فروش', True, 'marketing'),
]


class Command(BaseCommand):
    help = 'Seed کردن Feature Flags از مستندات فاز ۳ و ۴'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='حذف همه flags موجود قبل از seed',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            count = FeatureFlag.objects.count()
            FeatureFlag.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'⚠️  {count} flag حذف شد'))
        
        created = 0
        updated = 0
        
        for name, description, enabled, category in FLAGS:
            flag, was_created = FeatureFlag.objects.update_or_create(
                name=name,
                defaults={
                    'description': description,
                    'enabled': enabled,
                    'category': category,
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {created} flag ایجاد شد | {updated} flag به‌روزرسانی شد'
        ))
        self.stdout.write(f'📊 مجموع: {FeatureFlag.objects.count()} flag')
