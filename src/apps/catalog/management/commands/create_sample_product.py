"""
Management command برای ایجاد محصول نمونه با بلوک‌های مختلف
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.catalog.models import Product, Category, ContentBlock, Supplier

User = get_user_model()


class Command(BaseCommand):
    help = 'ایجاد محصول نمونه "سماق اصیل هوراند" با 4 بلوک'

    def handle(self, *args, **options):
        # 1) ایجاد User برای تأمین‌کننده
        supplier_user, user_created = User.objects.get_or_create(
            username='supplier_horand',
            defaults={
                'email': 'supplier@rihan360.ir',
                'first_name': 'علی',
                'last_name': 'محمدی',
                'is_active': True,
            }
        )
        if user_created:
            supplier_user.set_password('Supplier1405!')
            supplier_user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ User تأمین‌کننده ایجاد شد: {supplier_user.username}'))
        else:
            self.stdout.write(f'ℹ️  User تأمین‌کننده از قبل وجود داشت')

        # 2) ایجاد Category
        category, _ = Category.objects.get_or_create(
            name='خشکبار',
            defaults={'slug': 'dried-fruits', 'description': 'خشکبار اصیل ایرانی'}
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Category: {category.name}'))

        # 3) ایجاد Supplier با user
        supplier, supplier_created = Supplier.objects.get_or_create(
            user=supplier_user,
            defaults={
                'title': 'تأمین‌کننده هوراند',
                'contact_name': 'علی محمدی',
                'phone': '09123456789',
                'city': 'هوراند',
                'is_active': True,
            }
        )
        if supplier_created:
            self.stdout.write(self.style.SUCCESS(f'✅ Supplier: {supplier.title}'))
        else:
            self.stdout.write(f'ℹ️  Supplier از قبل وجود داشت')

        # 4) ایجاد محصول نمونه
        product, product_created = Product.objects.get_or_create(
            slug='sumac-horand',
            defaults={
                'title': 'سماق اصیل هوراند',
                'sku': 'SUM-001',
                'category': category,
                'supplier': supplier,
                'summary': 'سماق طبیعی و ارگانیک از کوه‌های هوراند',
                'price': 150000,
                'stock': 50,
                'is_available': True,
                'meta_title': 'سماق اصیل هوراند | ریهان',
                'meta_description': 'سماق طبیعی و ارگانیک از کوه‌های هوراند',
            }
        )

        if product_created:
            self.stdout.write(self.style.SUCCESS(f'\n✅ محصول "{product.title}" ایجاد شد'))
            
            # ایجاد بلوک‌های مختلف
            blocks = [
                {
                    'block_type': 'heading',
                    'title': 'داستان سماق هوراند',
                    'sort_order': 1,
                },
                {
                    'block_type': 'text',
                    'title': 'اصالت و کیفیت',
                    'content': 'این سماق از کوه‌های هوراند جمع‌آوری شده و کاملاً طبیعی است. بدون هیچ‌گونه افزودنی شیمیایی. طعمی اصیل و بی‌نظیر که یادآور سفره‌های سنتی ایرانی است.',
                    'sort_order': 2,
                },
                {
                    'block_type': 'quote',
                    'content': 'سماق هوراند طعمی متفاوت و اصیل دارد که در هیچ جای دیگر پیدا نمی‌کنید. این سماق از قلب کوه‌های آذربایجان می‌آید.',
                    'quote_author': 'استاد محمدی، کارشناس طب سنتی',
                    'sort_order': 3,
                },
                {
                    'block_type': 'trust_badges',
                    'title': 'چرا سماق ما؟',
                    'sort_order': 4,
                    'extra_data': {
                        'badges': [
                            {'icon': '✓', 'title': 'کاملاً طبیعی', 'description': 'بدون افزودنی شیمیایی'},
                            {'icon': '↺', 'title': 'گارانتی مرجوعی', 'description': 'در صورت عدم رضایت'},
                            {'icon': '📦', 'title': 'ارسال سریع', 'description': 'به سراسر کشور'},
                        ]
                    }
                },
                {
                    'block_type': 'cta',
                    'title': 'همین الان سفارش دهید',
                    'subtitle': 'ارسال رایگان برای خریدهای بالای ۵۰۰ هزار تومان',
                    'link_text': 'افزودن به سبد خرید',
                    'link_url': '/cart/add/sumac-horand',
                    'sort_order': 5,
                },
            ]
            
            for block_data in blocks:
                ContentBlock.objects.create(product=product, **block_data)
                self.stdout.write(f'  ✓ بلوک {block_data["block_type"]} ایجاد شد')
        else:
            self.stdout.write(self.style.WARNING(f'\nℹ️  محصول "{product.title}" از قبل وجود داشت'))
            self.stdout.write(f'  📦 تعداد بلوک‌های این محصول: {product.content_blocks.count()}')

        # خلاصه
        self.stdout.write(self.style.SUCCESS(f'\n{"="*50}'))
        self.stdout.write(self.style.SUCCESS(f'📦 مجموع محصولات: {Product.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'🧱 مجموع بلوک‌ها: {ContentBlock.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'👤 مجموع تأمین‌کنندگان: {Supplier.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'🗂️ مجموع دسته‌بندی‌ها: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*50}'))
