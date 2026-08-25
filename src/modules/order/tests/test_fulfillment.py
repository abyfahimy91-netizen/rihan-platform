"""
D-105: تست‌های زنجیره ارسال (Fulfillment)

پوشش:
- تفکیک خودکار اقلام بین تامین‌کننده‌ها و ریهان (سفارش چندتامین‌کننده‌ای)
- متن دستور ارسال بدون قیمت
- ثبت کد رهگیری: همگام‌سازی وضعیت سفارش + پیامک مشتری با لینک یک‌کلیکی
- ریدایرکت /order/t/<code>/ به سامانه پست
- نرمال‌سازی ارقام فارسی و ساخت لینک رهگیری
- خاموش/روشن بودن اطلاع‌رسانی از تنظیمات سایت
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from src.modules.catalog.models import Category, Supplier, Product
from src.modules.order.models import Order, OrderItem, Shipment, NotificationLog
from src.modules.order.fulfillment import (
    build_shipments,
    mark_shipped,
    mark_delivered,
    dispatch_instruction_text,
    normalize_tracking_code,
    build_tracking_url,
    customer_shipped_text,
)

User = get_user_model()


class FulfillmentTestBase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='دسته ارسال', slug='fulfill-cat')
        self.supplier_a = Supplier.objects.create(
            title='تامین‌کننده الف', city='تبریز', phone='09141111111')
        self.product_a = Product.objects.create(
            name='محصول الف', slug='prod-a', category=self.category,
            supplier=self.supplier_a, base_price=Decimal('100000'),
            short_description='x', origin_story='x', status='active')
        self.no_sup_product = Product.objects.create(
            name='محصول داخلی ریحان', slug='inhouse-b', category=self.category,
            base_price=Decimal('50000'),
            short_description='x', origin_story='x', status='active')

        self.order = Order.objects.create(
            status=Order.OrderStatus.PAID,
            guest_name='میرعلی تستی', guest_phone='09142222222',
            guest_postal_code='5151411111',
            guest_address='تبریز، خیابان آزادی، پلاک ۱۲',
        )
        self.item_a = OrderItem.objects.create(
            order=self.order, product=self.product_a, quantity=3,
            unit_price_at_purchase=Decimal('100000'), product_name_snapshot='محصول الف')
        self.item_b = OrderItem.objects.create(
            order=self.order, product=self.no_sup_product, quantity=1,
            unit_price_at_purchase=Decimal('50000'), product_name_snapshot='محصول داخلی ریحان')


class BuildShipmentsTests(FulfillmentTestBase):
    def test_splits_by_supplier_and_rihan(self):
        created = build_shipments(self.order)
        self.assertEqual(len(created), 2)
        kinds = {s.fulfiller for s in created}
        self.assertEqual(kinds, {Shipment.FulfillerType.SUPPLIER, Shipment.FulfillerType.RIHAN})

        sup_shipment = next(s for s in created if s.fulfiller == Shipment.FulfillerType.SUPPLIER)
        self.assertEqual(sup_shipment.supplier, self.supplier_a)
        self.assertEqual(
            {si.order_item_id for si in sup_shipment.items.all()}, {self.item_a.id})

        rihan = next(s for s in created if s.fulfiller == Shipment.FulfillerType.RIHAN)
        self.assertIsNone(rihan.supplier)
        self.assertEqual({si.order_item_id for si in rihan.items.all()}, {self.item_b.id})

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.OrderStatus.PROCESSING)
        self.assertTrue(self.order.status_history.filter(status='PROCESSING').exists())

    def test_build_is_idempotent(self):
        first = build_shipments(self.order)
        second = build_shipments(self.order)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 2)
        self.assertEqual(Shipment.objects.filter(order=self.order).count(), 2)

    def test_dispatch_text_has_no_price(self):
        shipment = build_shipments(self.order)[0]
        text = dispatch_instruction_text(shipment)
        self.assertIn('محصول الف × 3', text)
        self.assertIn('09142222222', text)
        self.assertIn('5151411111', text)
        self.assertNotIn('100000', text)
        self.assertNotIn('تومان', text)

    def test_inactive_supplier_falls_back_to_rihan(self):
        self.supplier_a.is_active = False
        self.supplier_a.save()
        created = build_shipments(self.order)
        self.assertTrue(all(s.fulfiller == Shipment.FulfillerType.RIHAN for s in created))

    def test_supplier_sms_sent_on_assignment(self):
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            build_shipments(self.order)
        # فقط مرسوله تامین‌کننده پیامک می‌گیرد (نه ریهان)
        self.assertEqual(mock_sms.call_count, 1)
        phone_arg = mock_sms.call_args[0][0]
        message_arg = mock_sms.call_args[0][1]
        self.assertEqual(phone_arg, '09141111111')
        self.assertIn('/supplier/', message_arg)
        self.assertTrue(NotificationLog.objects.filter(kind='SUPPLIER_ASSIGN', success=True).exists())


class MarkShippedTests(FulfillmentTestBase):
    def _ship_all_but_one(self):
        created = build_shipments(self.order)
        return created

    def test_order_shipped_only_when_all_shipments_shipped(self):
        a, b = self._ship_all_but_one()

        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            mark_shipped(a, carrier='POST', tracking_code='RA123456789IR')

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.OrderStatus.PROCESSING)  # هنوز یکی مانده

        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            mark_shipped(b, carrier='POST', tracking_code='RA987654321IR')

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.OrderStatus.SHIPPED)
        self.assertTrue(self.order.status_history.filter(status='SHIPPED').exists())

    def test_customer_sms_contains_one_click_link(self):
        shipment = build_shipments(self.order)[0]
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            mark_shipped(shipment, carrier='POST', tracking_code='RA555555555IR')
        phone_arg, message_arg = mock_sms.call_args[0]
        self.assertEqual(phone_arg, '09142222222')
        self.assertIn('RA555555555IR', message_arg)
        self.assertIn('/order/t/RA555555555IR', message_arg)
        self.assertTrue(NotificationLog.objects.filter(kind='CUSTOMER_SHIPPED', success=True).exists())

    def test_notify_disabled_via_site_settings(self):
        from src.modules.pages.models import SiteSettings
        SiteSettings.objects.create(sms_notify_customers=False, sms_notify_suppliers=True)
        shipment = build_shipments(self.order)[0]  # پیامک تامین‌کننده فعال است ولی اینجا مهم نیست
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            mark_shipped(shipment, carrier='POST', tracking_code='RA111111111IR')
        # هیچ تماسی برای مشتری زده نشد چون اعلان خاموش است
        self.assertFalse(mock_sms.called)

    def test_delivered_syncs_order_status(self):
        a, b = self._ship_all_but_one()
        mark_shipped(a, carrier='POST', tracking_code='RA000000001IR', send_customer_sms=False)
        mark_shipped(b, carrier='POST', tracking_code='RA000000002IR', send_customer_sms=False)
        mark_delivered(a)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.OrderStatus.SHIPPED)
        mark_delivered(b)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.OrderStatus.DELIVERED)


class TrackingUtilitiesTests(TestCase):
    def test_normalize_persian_digits(self):
        self.assertEqual(normalize_tracking_code(' ۱۲۳۴۵۶۷۸۹۰ '), '1234567890')
        self.assertEqual(normalize_tracking_code('ra-123'), 'RA123')

    def test_build_tracking_url_post(self):
        url = build_tracking_url('POST', 'RA123456789IR')
        self.assertEqual(url, 'https://tracking.post.ir/search.aspx?id=RA123456789IR')
        self.assertEqual(build_tracking_url('OTHER', 'X1'), '')

    def test_redirect_view_opens_post_site_with_code(self):
        order = Order.objects.create(status=Order.OrderStatus.PAID, guest_phone='09120000000')
        Shipment.objects.create(
            order=order, fulfiller=Shipment.FulfillerType.RIHAN,
            status=Shipment.Status.SHIPPED, carrier='POST',
            tracking_code='RA123456789IR')
        client = Client()
        response = client.get('/order/t/RA123456789IR/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('tracking.post.ir', response['Location'])

    def test_redirect_persian_digits_code(self):
        order = Order.objects.create(status=Order.OrderStatus.PAID, guest_phone='09120000000')
        Shipment.objects.create(
            order=order, fulfiller=Shipment.FulfillerType.RIHAN,
            status=Shipment.Status.SHIPPED, carrier='POST',
            tracking_code='RA555555555IR')
        client = Client()
        # مشتری از پیامک با ارقام/حروف متفاوت می‌آید
        response = client.get('/order/t/ra555555555ir/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('RA555555555IR', response['Location'])

    def test_redirect_unknown_code_goes_to_lookup(self):
        client = Client()
        response = client.get('/order/t/UNKNOWN999/')
        self.assertEqual(response.status_code, 302)

    def test_customer_shipped_text_is_short_and_complete(self):
        order = Order.objects.create(
            status=Order.OrderStatus.PAID,
            guest_name='م', guest_phone='09120000000')
        shipment = Shipment.objects.create(order=order, fulfiller=Shipment.FulfillerType.RIHAN)
        shipment.tracking_code = 'RA123456789IR'
        text = customer_shipped_text(shipment)
        self.assertIn(order.order_number, text)
        self.assertIn('RA123456789IR', text)
        self.assertLess(len(text), 300)
