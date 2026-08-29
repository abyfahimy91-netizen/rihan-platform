"""
D-119: اعلان‌های درون‌سایتی کاربر (زنگولهٔ هدر + صفحه اعلان‌ها)

- تغییر وضعیت سفارش (تایید پرداخت / آماده‌سازی / ارسال / تحویل / لغو) → اعلان برای خریدار عضو
- مهمان‌ها هیچ اعلان درون‌سایتی نمی‌گیرند (فقط پیامک)
- امنیت: هر کاربر فقط اعلان‌های خودش را می‌بیند و می‌خواند
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from src.modules.catalog.models import Category, Product
from src.modules.order.models import (
    Order, OrderItem, UserNotification, Shipment,
)
from src.modules.order.fulfillment import mark_shipped, mark_delivered

User = get_user_model()


class NotificationTestBase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='09120000001', password='RihanTest123')
        self.stranger = User.objects.create_user(username='09120000002', password='RihanTest123')
        self.category = Category.objects.create(name='دسته اعلان', slug='ntf-cat')
        self.product = Product.objects.create(
            name='محصول اعلان', slug='ntf-prod', category=self.category,
            base_price=Decimal('100000'), short_description='x', origin_story='x',
            status='active')
        self.order = Order.objects.create(
            user=self.owner, status=Order.OrderStatus.PENDING,
            guest_name='مشتری عضو', guest_phone='09120000001',
            guest_postal_code='5151411111', guest_address='تبریز، آزادی، ۱۲')
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=1,
            unit_price_at_purchase=Decimal('100000'), product_name_snapshot='محصول اعلان')

    def _client(self):
        return Client(SERVER_NAME='rihan360.ir')


class SignalNotificationTests(NotificationTestBase):
    def test_payment_confirmed_creates_notification(self):
        self.order.status = Order.OrderStatus.PAID
        self.order.save()
        n = UserNotification.objects.filter(
            recipient=self.owner, kind=UserNotification.Kind.PAYMENT_CONFIRMED).first()
        self.assertIsNotNone(n)
        self.assertIn(self.order.order_number, n.title)
        self.assertEqual(n.url, f'/order/tracking/{self.order.order_number}/')

    def test_shipped_notification_has_tracking_code(self):
        from unittest.mock import patch
        shipment = Shipment.objects.create(order=self.order, fulfiller=Shipment.FulfillerType.RIHAN)
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (False, 'test')
            mark_shipped(shipment, 'POST', '12345678901234567890', via='admin')
        n = UserNotification.objects.filter(
            recipient=self.owner, kind=UserNotification.Kind.SHIPPED).first()
        self.assertIsNotNone(n)
        self.assertIn('12345678901234567890', n.body)
        # همگام‌سازی سفارش هم خودش اعلان می‌سازد (post_save روی Order)
        self.assertTrue(UserNotification.objects.filter(recipient=self.owner).exists())

    def test_delivered_notification_encourages_review(self):
        self.order.status = Order.OrderStatus.SHIPPED
        self.order.save()
        UserNotification.objects.all().delete()
        self.order.status = Order.OrderStatus.DELIVERED
        self.order.save()
        n = UserNotification.objects.filter(
            recipient=self.owner, kind=UserNotification.Kind.DELIVERED).first()
        self.assertIsNotNone(n)
        self.assertIn('نظر', n.body)

    def test_cancelled_notification(self):
        self.order.status = Order.OrderStatus.CANCELLED
        self.order.save()
        self.assertTrue(UserNotification.objects.filter(
            recipient=self.owner, kind=UserNotification.Kind.CANCELLED).exists())

    def test_guest_order_gets_no_notification(self):
        guest_order = Order.objects.create(
            status=Order.OrderStatus.PENDING,
            guest_name='مهمان', guest_phone='09120000009',
            guest_postal_code='5151411111', guest_address='تبریز')
        guest_order.status = Order.OrderStatus.PAID
        guest_order.save()
        self.assertEqual(UserNotification.objects.count(), 0)

    def test_no_duplicate_on_same_status_save(self):
        self.order.status = Order.OrderStatus.PAID
        self.order.save()
        count = UserNotification.objects.filter(
            recipient=self.owner, kind=UserNotification.Kind.PAYMENT_CONFIRMED).count()
        self.order.refresh_from_db()
        self.order.save()  # همان وضعیت — نباید اعلان جدید بیاید
        self.assertEqual(UserNotification.objects.filter(
            recipient=self.owner, kind=UserNotification.Kind.PAYMENT_CONFIRMED).count(), count)


class NotificationEndpointsTests(NotificationTestBase):
    def setUp(self):
        super().setUp()
        UserNotification.notify(
            self.owner, UserNotification.Kind.PAYMENT_CONFIRMED,
            f'پرداخت سفارش {self.order.order_number} تایید شد ✅',
            body='متن تستی', url=f'/order/tracking/{self.order.order_number}/',
            order=self.order)
        self.notif = UserNotification.objects.first()

    def test_recent_requires_login(self):
        r = self._client().get('/order/notifications/recent/')
        self.assertEqual(r.status_code, 302)

    def test_recent_json_scoped_to_owner(self):
        c = self._client()
        c.force_login(self.owner)
        r = c.get('/order/notifications/recent/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['unread'], 1)
        self.assertEqual(len(data['items']), 1)
        self.assertIn(self.order.order_number, data['items'][0]['title'])

    def test_read_one_marks_read(self):
        c = self._client()
        c.force_login(self.owner)
        r = c.post(f'/order/notifications/{self.notif.pk}/read/',
                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['unread'], 0)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_read_one_forbidden_for_other_user(self):
        c = self._client()
        c.force_login(self.stranger)
        r = c.post(f'/order/notifications/{self.notif.pk}/read/')
        self.assertEqual(r.status_code, 404)

    def test_read_all(self):
        UserNotification.notify(
            self.owner, UserNotification.Kind.SHIPPED, 'دومی', body='', url='')
        c = self._client()
        c.force_login(self.owner)
        r = c.post('/order/notifications/read-all/',
                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.json()['unread'], 0)
        self.assertFalse(UserNotification.objects.filter(recipient=self.owner, is_read=False).exists())

    def test_page_renders_and_marks_one_read(self):
        c = self._client()
        c.force_login(self.owner)
        body = c.get('/order/notifications/').content.decode()
        self.assertIn(self.notif.title, body)
        self.assertIn('nt-item unread', body)
        r = c.post('/order/notifications/', {'id': str(self.notif.pk)})
        self.assertEqual(r.status_code, 302)
        body = c.get('/order/notifications/').content.decode()
        self.assertNotIn('nt-item unread', body)


class HeaderBellTests(NotificationTestBase):
    def test_anonymous_has_no_bell(self):
        body = self._client().get('/').content.decode()
        # دام شناخته‌شده: CSS کلاس .notif-bell همیشه در <style> هست — id را چک کن
        self.assertNotIn('id="notif-bell"', body)
        self.assertNotIn('id="notif-count"', body)

    # ── D-119b: زنگوله هرگز جای لینک ورود/حساب من را نگیرد ──
    def test_anonymous_still_sees_login_button(self):
        body = self._client().get('/').content.decode()
        self.assertIn('ورود / ثبت‌نام', body)
        self.assertIn('/accounts/login/', body)
        # ترتیب درست: ورود و ثبت‌نام قبل از زنگوله (سمت راست آن در RTL)
        self.assertLess(body.find('/accounts/login/'), body.find('id="notif-bell"') if 'id="notif-bell"' in body else 10**9)

    def test_authenticated_sees_profile_and_bell_before_cart(self):
        c = self._client()
        c.force_login(self.owner)
        body = c.get('/').content.decode()
        self.assertIn('حساب من', body)
        self.assertIn('id="notif-bell"', body)
        self.assertLess(body.find('حساب من'), body.find('id="notif-bell"'))
        self.assertLess(body.find('id="notif-bell"'), body.find('id="cart-count"'))

    def test_badge_hidden_when_zero_unread(self):
        c = self._client()
        c.force_login(self.owner)
        body = c.get('/').content.decode()
        self.assertIn('id="notif-bell"', body)
        self.assertIn('id="notif-count" hidden>', body)

    def test_badge_shows_one(self):
        UserNotification.notify(
            self.owner, UserNotification.Kind.PAYMENT_CONFIRMED, 'تست', body='', url='')
        c = self._client()
        c.force_login(self.owner)
        body = c.get('/').content.decode()
        self.assertIn('id="notif-count" >۱<', body)
