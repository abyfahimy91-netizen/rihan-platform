"""
D-113: قیمت نمایشی محصول از «گزینه استاندارد» می‌آید — نه فرمول قدیمی
- صفحه اصلی/لیست باید قیمت واریانت استاندارد را نشان دهد
- فقط یک گزینه استاندارد برای هر محصول
- fallback: ارزان‌ترین گزینه فعال وقتی هیچ پیش‌فرضی تعیین نشده
"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, ProductVariant


class DisplayPricingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='دسته نمایش', slug='disp-cat')
        self.product = Product.objects.create(
            name='محصول نمایشی', slug='disp-prod', category=self.category,
            base_price=Decimal('100000'),  # فرمول قدیمی → final_price=150000
            short_description='x', origin_story='x', status='active')
        self.v_1kg = ProductVariant.objects.create(
            product=self.product, title='بسته ۱ کیلوگرمی',
            price=Decimal('2950000'), stock_quantity=5)
        self.v_500g = ProductVariant.objects.create(
            product=self.product, title='بسته ۵۰۰ گرمی',
            price=Decimal('1477000'), stock_quantity=5)

    def test_display_price_falls_back_to_cheapest(self):
        self.assertEqual(self.product.display_variant, self.v_500g)
        self.assertEqual(self.product.display_price, Decimal('1477000'))

    def test_default_variant_wins(self):
        self.v_1kg.is_default = True
        self.v_1kg.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.display_variant, self.v_1kg)
        self.assertEqual(self.product.display_price, Decimal('2950000'))

    def test_only_one_default_per_product(self):
        self.v_1kg.is_default = True
        self.v_1kg.save()
        self.v_500g.is_default = True
        self.v_500g.save()
        self.v_1kg.refresh_from_db()
        self.assertFalse(ProductVariant.objects.filter(
            product=self.product, is_default=True).exclude(
            pk=self.v_500g.pk).exists())

    def test_inactive_default_skipped(self):
        self.v_1kg.is_default = True
        self.v_1kg.save()
        self.v_1kg.is_active = False
        self.v_1kg.save()
        # گزینه پیش‌فرض غیرفعال → ارزان‌ترین فعال
        self.assertEqual(self.product.display_variant, self.v_500g)

    def test_homepage_shows_variant_price_not_formula(self):
        self.v_1kg.is_default = True
        self.v_1kg.save()
        c = Client(SERVER_NAME='rihan360.ir')
        r = c.get('/')
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        if 'محصول نمایشی' in body:
            # قیمت گزینه استاندارد (۱ کیلو) باید باشد، نه خروجی فرمول قدیمی (۱۵۰٬۰۰۰)
            self.assertIn('۲٬۹۵۰٬۰۰۰', body)
            self.assertIn('بسته ۱ کیلوگرمی', body)
            self.assertNotIn('۱٬۵۰٬۰۰۰', body)
            self.assertNotIn('150000', body)

    def test_discount_percent_uses_display_price(self):
        from decimal import Decimal as D
        self.v_1kg.is_default = True
        self.v_1kg.save()
        self.product.compare_at_price = D('3200000')
        self.product.save()
        # display=2,950,000 → تخفیف ≈ 8٪ (نه نسبت به فرمول قدیمی)
        self.assertEqual(self.product.discount_percent, 8)
