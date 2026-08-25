"""D-106: ثبت‌نام با رمز عبور (مسیر موازی بدون پیامک) + کلیدهای پیامک سفارشات"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch

from src.modules.auth.models import AuthSettings
from src.modules.catalog.models import Category, Supplier, Product
from src.modules.order.models import Order, OrderItem, Shipment

User = get_user_model()


class PasswordRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.settings_row = AuthSettings.load()

    def test_register_success_creates_user_and_logs_in(self):
        response = self.client.post(reverse('auth_pages:register'), {
            'full_name': 'میرعلی تستی',
            'phone': '۰۹۱۲۳۴۵۶۷۸۹',  # ارقام فارسی هم قبول است
            'password1': 'rihan1234',
            'password2': 'rihan1234',
            'next': '/',
        })
        self.assertRedirects(response, '/', fetch_redirect_response=False)
        user = User.objects.filter(username='09123456789').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'میرعلی')
        self.assertTrue(user.has_usable_password())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_register_duplicate_phone_rejected(self):
        User.objects.create_user(username='09120000000', password='x12345678')
        response = self.client.post(reverse('auth_pages:register'), {
            'full_name': 'تکراری', 'phone': '09120000000',
            'password1': 'rihan1234', 'password2': 'rihan1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='09120000000').count(), 1)

    def test_register_weak_password_rejected(self):
        response = self.client.post(reverse('auth_pages:register'), {
            'full_name': 'ضعیف', 'phone': '09121112222',
            'password1': '12345678',  # بدون حرف
            'password2': '12345678',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='09121112222').exists())

    def test_register_password_mismatch(self):
        response = self.client.post(reverse('auth_pages:register'), {
            'full_name': 'ناهماهنگ', 'phone': '09123334444',
            'password1': 'rihan1234', 'password2': 'rihan9999',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='09123334444').exists())

    def test_register_hidden_when_password_disabled(self):
        s = AuthSettings.load()
        s.password_enabled = False
        s.save()
        response = self.client.get(reverse('auth_pages:register'))
        self.assertRedirects(response, reverse('auth_pages:login'), fetch_redirect_response=False)

    def test_login_page_shows_register_link_when_enabled(self):
        html = self.client.get(reverse('auth_pages:login') + '?method=password').content.decode()
        self.assertIn('/accounts/register/', html)
        self.assertIn('ثبت‌نام با رمز عبور', html)


class OrderSmsToggleTests(TestCase):
    """کلید خاموش/روشن پیامک سفارشات — سیستم موازی"""

    def setUp(self):
        self.category = Category.objects.create(name='دسته D106', slug='d106-cat')
        self.supplier = Supplier.objects.create(
            title='تامین D106', city='تبریز', phone='09140001111')
        self.product = Product.objects.create(
            name='محصول D106', slug='prod-d106', category=self.category,
            supplier=self.supplier, base_price=10000,
            short_description='x', origin_story='x', status='active')
        self.order = Order.objects.create(
            status=Order.OrderStatus.PAID,
            guest_name='مشتری', guest_phone='09141234567')
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=1,
            unit_price_at_purchase=10000, product_name_snapshot='محصول D106')

    def test_supplier_sms_skipped_when_flag_off(self):
        from src.modules.pages.models import SiteSettings
        SiteSettings.objects.create(sms_notify_suppliers=False)
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            shipments = __import__(
                'src.modules.order.fulfillment', fromlist=['build_shipments']
            ).build_shipments(self.order)
        self.assertEqual(len(shipments), 1)  # مرسوله ساخته شد
        self.assertFalse(mock_sms.called)     # ولی پیامکی نرفت

    def test_reminder_respects_flag_off(self):
        from datetime import timedelta
        from django.utils import timezone
        from src.modules.pages.models import SiteSettings
        from src.modules.order.fulfillment import remind_pending_suppliers

        SiteSettings.objects.create(sms_notify_suppliers=False)
        shipment = Shipment.objects.create(
            order=self.order, fulfiller=Shipment.FulfillerType.SUPPLIER,
            supplier=self.supplier, created_at=timezone.now() - timedelta(hours=30))
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            count = remind_pending_suppliers(sla_hours=24)
        self.assertEqual(count, 0)
        self.assertFalse(mock_sms.called)
