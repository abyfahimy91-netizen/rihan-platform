"""
تست‌های پنل تامین‌کننده — نسخه D-105 (مرسوله‌محور)
تامین‌کننده فقط مرسوله‌های خودش را می‌بیند؛ بدون هیچ قیمتی.
D-119: هشدار قرمز دیرکرد روی داشبورد تامین‌کننده.
"""
from datetime import timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from src.modules.catalog.models import Supplier, Product, Category
from src.modules.order.models import Order, OrderItem, Shipment
from src.modules.order.fulfillment import build_shipments, mark_shipped
from src.modules.rbac.services.role_service import RoleService

User = get_user_model()


class SupplierPanelTestCase(TestCase):
    """تست‌های پایه پنل تأمین‌کننده (D-105)"""

    def setUp(self):
        self.client = Client()
        RoleService.create_system_roles()

        self.supplier_user = User.objects.create_user(username='supplier1', password='testpass123')
        self.supplier = Supplier.objects.create(
            title='تأمین‌کننده خشکبار', city='تبریز',
            phone='09121234567', user=self.supplier_user,
        )
        RoleService.assign_role(self.supplier_user, 'supplier')

        self.regular_user = User.objects.create_user(username='customer1', password='testpass123')

        self.category = Category.objects.create(name='خشکبار', slug='dried-fruits')
        self.product = Product.objects.create(
            name='سماق ممتاز', slug='sumac-premium',
            category=self.category, supplier=self.supplier,
            base_price=50000, final_price=65000,
            short_description='سماق درجه یک', origin_story='تست',
            status='active',
        )

        self.order = Order.objects.create(
            user=self.regular_user, status='PAID',
            subtotal=65000, total_price=65000,
            guest_name='مشتری تستی', guest_phone='09129876543',
            guest_postal_code='5151411111',
            guest_address='تبریز، خیابان تست، پلاک ۱',
        )
        self.order_item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2,
            unit_price_at_purchase=65000, product_name_snapshot='سماق ممتاز',
        )
        # D-105: ساخت مرسوله برای سفارش پرداخت‌شده
        self.shipment = build_shipments(self.order)[0]

    def test_supplier_dashboard_access(self):
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'پنل تامین‌کننده')

    def test_regular_user_cannot_access_supplier_panel(self):
        self.client.login(username='customer1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_supplier_sees_only_own_shipments(self):
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:shipment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_shipment_detail_has_no_prices(self):
        """امنیت تجاری (به‌روز D-113): تامین‌کننده هرگز قیمت «فروش» را نمی‌بیند —
        ولی فرم ورود هزینه‌های خودش (پست/بسته‌بندی به تومان) روی همان صفحه مجاز است"""
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:shipment_detail', args=[self.shipment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'سماق ممتاز')
        self.assertContains(response, '09129876543')
        # قیمت فروش / مبلغ سفارش هرگز نباید دیده شود:
        self.assertNotContains(response, '65000')
        self.assertNotContains(response, 'مبلغ نهایی')
        self.assertNotContains(response, 'جمع کل کالاها')
        self.assertNotContains(response, 'قیمت فروش')

    def test_submit_tracking_code_sends_customer_sms(self):
        self.client.login(username='supplier1', password='testpass123')
        url = reverse('supplier_panel:shipment_detail', args=[self.shipment.pk])

        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            response = self.client.post(url, {
                'carrier': 'POST',
                'tracking_code': '12345678901234567890',
            })

        self.assertEqual(response.status_code, 302)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, Shipment.Status.SHIPPED)
        self.assertEqual(self.shipment.tracking_code, '12345678901234567890')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'SHIPPED')
        # پیامک مشتری دقیقاً یک‌بار ارسال شده
        self.assertEqual(mock_sms.call_count, 1)
        message = mock_sms.call_args[0][1]
        self.assertIn('/order/t/', message)

    def test_persian_digits_accepted(self):
        self.client.login(username='supplier1', password='testpass123')
        url = reverse('supplier_panel:shipment_detail', args=[self.shipment.pk])
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            response = self.client.post(url, {
                'carrier': 'POST',
                'tracking_code': '۱۲۳۴۵۶۷۸۹۰۱۲۳۴۵۶۷۸۹۰',
            })
        self.assertEqual(response.status_code, 302)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.tracking_code, '12345678901234567890')

    def test_supplier_cannot_access_other_suppliers_shipment(self):
        other_supplier = Supplier.objects.create(title='دیگری', city='تهران', phone='09350000000')
        other_order = Order.objects.create(
            user=self.regular_user, status='PAID',
            subtotal=100000, total_price=100000,
            guest_name='مشتری دیگر', guest_phone='09121111111',
        )
        # محصول بدون تامین‌کننده → مرسوله ریهان (نه این تامین‌کننده)
        no_sup_product = Product.objects.create(
            name='محصول داخلی', slug='inhouse-product',
            category=self.category, base_price=10000, final_price=12000,
            short_description='x', origin_story='x', status='active',
        )
        item = OrderItem.objects.create(
            order=other_order, product=no_sup_product, quantity=1,
            unit_price_at_purchase=10000, product_name_snapshot='محصول داخلی',
        )
        riha_shipment = build_shipments(other_order)[0]
        self.assertEqual(riha_shipment.fulfiller, Shipment.FulfillerType.RIHAN)

        self.client.login(username='supplier1', password='testpass123')
        url = reverse('supplier_panel:shipment_detail', args=[riha_shipment.pk])
        response = self.client.get(url)
        # مرسوله ریهان متعلق به هیچ تامین‌کننده‌ای نیست → ۴۰۴
        self.assertEqual(response.status_code, 404)

    # ── D-116b: تامین‌کننده فقط تسویه خودش را می‌بیند؛ نه قیمت فروش ──
    def test_supplier_dashboard_has_no_sale_prices(self):
        """داشبورد تامین‌کننده هرگز قیمت فروش را نشان نمی‌دهد"""
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'فروش اقلام من')

    def test_shipment_detail_branding_warning(self):
        """هشدار بسته‌بندی: بدون فاکتور/بروشور/برچسب برند خودِ تامین‌کننده — بسته با برند Rihan"""
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:shipment_detail', args=[self.shipment.pk]))
        self.assertContains(response, 'بروشور')
        self.assertContains(response, 'Rihan')
        self.assertContains(response, 'فاکتور')

    # ── D-119: هشدار قرمز دیرکرد روی داشبورد تامین‌کننده ──
    def test_dashboard_no_overdue_warning_when_fresh(self):
        """مرسوله تازه → بدون هشدار دیرکرد"""
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'از مهلت')

    def test_dashboard_shows_red_overdue_warning(self):
        """مرسولهٔ گذشته از مهلت ۴۸ ساعته → جعبه قرمز با لینک مرسوله"""
        Shipment.objects.filter(pk=self.shipment.pk).update(
            created_at=timezone.now() - timedelta(hours=50))
        self.shipment.refresh_from_db()
        self.assertTrue(self.shipment.is_overdue)

        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'از مهلت')
        self.assertContains(response, self.order.order_number)

    def test_overdue_warning_hidden_after_shipped(self):
        """بعد از ثبت کد رهگیری، هشدار دیرکرد می‌رود"""
        Shipment.objects.filter(pk=self.shipment.pk).update(
            created_at=timezone.now() - timedelta(hours=50))
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (False, 'test')
            mark_shipped(self.shipment, carrier='POST',
                         tracking_code='12345678901234567890', send_customer_sms=False)
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertNotContains(response, 'از مهلت')
