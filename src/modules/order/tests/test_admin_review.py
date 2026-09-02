"""
SALES-14050610 — تست بازآرایی پنل ادمین
- سایدبار گروه‌بندی جدید + مخفی‌شدن ماژول‌های قدیمی/فنی
- خروجی CSV سفارش‌ها
- اینلاین استفاده‌های کوپن
"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Product, ProductVariant
from src.modules.order.models import Coupon, Order, OrderItem
from src.modules.pages.models import SiteSettings

HOST = 'rihan360.ir'


def _admin_client():
    from django.contrib.auth import get_user_model
    U = get_user_model()
    admin = U.objects.create_user(username='09120000000', password='x123456789', email='a@r.local')
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    c = Client()
    c.force_login(admin)
    return c


class SidebarReorgTests(TestCase):
    def test_admin_home_renders_with_new_groups(self):
        c = _admin_client()
        r = c.get('/admin/', HTTP_HOST=HOST)
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        for title in ['🛍 محصولات و انبار', '🧾 سفارش‌ها و ارسال', '🎟 کمپین و تخفیف',
                      '📞 مشتریان و سرنخ‌ها', '🧩 محتوای سایت', '💰 امور مالی',
                      '👥 دسترسی و نقش‌ها', '⚙️ فنی و امنیت (پیشرفته)']:
            self.assertIn(title, body)

    def test_legacy_modules_hidden(self):
        c = _admin_client()
        body = c.get('/admin/', HTTP_HOST=HOST).content.decode()
        self.assertIn('/admin/order/coupon/', body)   # لینک کوپن در سایدبار هست
        self.assertNotIn('/admin/leads/lead/', body)  # Lead قدیمی از ادمین حذف شده
        self.assertNotIn('/admin/family_panel/', body)  # ماژول‌های قدیمی family_panel حذف شده

    def test_coupon_link_in_campaign_group(self):
        c = _admin_client()
        body = c.get('/admin/', HTTP_HOST=HOST).content.decode()
        seg = body.split('🎟 کمپین و تخفیف')[1].split('</ul>')[0]
        self.assertIn('/admin/order/coupon/', seg)


class OrderCsvExportTests(TestCase):
    def test_csv_export_action(self):
        from django.utils import timezone
        c = _admin_client()
        cat = Category.objects.create(name='c', slug='c1')
        p = Product.objects.create(name='پ', slug='p1', category=cat, base_price=Decimal('1000'),
                                   short_description='s', origin_story='o', status='active')
        o = Order.objects.create(
            status=Order.OrderStatus.PENDING,
            guest_name='مشتری نمونه', guest_phone='09121112233',
            session_key='csv-test', guest_address='تبریز',
        )
        OrderItem.objects.create(order=o, product=p, product_name_snapshot='سماق نمونه',
                                 quantity=Decimal('2'), unit_price_at_purchase=Decimal('2950000'))
        o.calculate_totals()
        r = c.post('/admin/order/order/', {
            'action': 'export_orders_csv',
            '_selected_action': [str(o.pk)],
        }, HTTP_HOST=HOST)
        self.assertEqual(r.status_code, 200)
        content = r.content.decode('utf-8-sig')
        self.assertIn('شماره سفارش', content)
        self.assertIn(o.order_number, content)
        self.assertIn('سماق نمونه', content)
        self.assertIn('5900000', content)


class CouponInlineTests(TestCase):
    def test_coupon_use_inline_visible(self):
        c = _admin_client()
        cat = Category.objects.create(name='c2', slug='c2')
        p = Product.objects.create(name='پ2', slug='p2', category=cat, base_price=Decimal('1000'),
                                   short_description='s', origin_story='o', status='active')
        coupon = Coupon.objects.create(code='INL1', kind=Coupon.FIXED, value=50000)
        o = Order.objects.create(status=Order.OrderStatus.PENDING, guest_name='گ',
                                 guest_phone='09120001122', session_key='inl-test', guest_address='تبریز')
        from src.modules.order.models import CouponUse
        CouponUse.objects.create(coupon=coupon, order=o, phone='09120001122', amount=Decimal('50000'))
        r = c.get(f'/admin/order/coupon/{coupon.pk}/change/', HTTP_HOST=HOST)
        self.assertEqual(r.status_code, 200)
        self.assertIn('09120001122'.encode(), r.content)
