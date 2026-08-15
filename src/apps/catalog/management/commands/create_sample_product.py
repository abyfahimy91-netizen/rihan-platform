"""
Management command برای ایجاد محصول نمونه با بلوک‌های مختلف
"""
from django.core.management.base import BaseCommand
from apps.catalog.models import Product, Category, ContentBlock, Supplier


class Command(BaseCommand):
    help = 'ایجاد محصول نمونه "سماق اصیل هوراند" با 4 بلوک'

    def handle(self, *args, **options):
        # ایجاد یا دریافت category
        category, _ = Category.objects.get_or_create(
            name='خشکبار',
            defaults={'slug': 'dried-fruits', 'description': 'خشکبار اصیل ایرانی'}
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Category: {category.name}'))

        # ایجاد یا دریافت supplier
        supplier, _ = Supplier.objects.get_or_create(
            title='تأمین‌کننده هوراند',
            defaults={
                'contact_name': 'علی محمدی',
                'phone': '09123456789',
                'city': 'هوراند',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Supplier: {supplier.title}'))

        # ایجاد محصول نمونه
        product, created = Product.objects.get_or_create(
            title='سماق اصیل هوراند',
            defaults={
                'slug': 'sumac-horand',
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

        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ محصول "{product.title}" ایجاد شد'))
            
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
                    'content': 'این سماق از کوه‌های هوراند جمع‌آوری شده و کاملاً طبیعی است. بدون هیچ‌گونه افزودنی شیمیایی.',
                    'sort_order': 2,
                },
                {
                    'block_type': 'quote',
                    'content': 'سماق هوراند طعمی متفاوت و اصیل دارد که در هیچ جای دیگر پیدا نمی‌کنید.',
                    'quote_author': 'استاد محمدی، کارشناس طب سنتی',
                    'sort_order': 3,
                },
                {
                    'block_type': 'cta',
                    'title': 'همین الان سفارش دهید',
                    'link_text': 'افزودن به سبد خرید',
                    'link_url': '/add-to-cart/sumac-horand',
                    'sort_order': 4,
                },
            ]
            
            for block_data in blocks:
                ContentBlock.objects.create(product=product, **block_data)
                self.stdout.write(f'  ✓ بلوک {block_data["block_type"]} ایجاد شد')
        else:
            self.stdout.write(self.style.WARNING(f'ℹ️  محصول "{product.title}" از قبل وجود داشت'))

        self.stdout.write(self.style.SUCCESS(f'\n📦 تعداد محصولات: {Product.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'🧱 تعداد بلوک‌ها: {ContentBlock.objects.count()}'))
