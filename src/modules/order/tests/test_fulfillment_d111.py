"""
D-111 — تست‌های اعتبارسنجی کد رهگیری، وضعیت «در انتظار تایید»،
جزئیات شرکت حمل «سایر»، لینک رسید ادمین و الزام کد پستی
"""
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from src.modules.catalog.models import Category, Supplier, Product
from src.modules.order.models import (
    Order, OrderItem, Payment, Shipment,
)
from src.modules.order.admin import PaymentAdmin
from src.modules.order.fulfillment import (
    FulfillmentError,
    build_shipments,
    carrier_code_hint,
    mark_shipped,
    validate_tracking_code,
)

User = get_user_model()

TINY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


class D110Base(TestCase):
    """فیکسچر مشترک: سفارش پرداخت‌شده با مرسوله تامین‌کننده"""

    def setUp(self):
        self.category = Category.objects.create(name='دسته D110', slug='d110-cat')
        self.supplier = Supplier.objects.create(
            title='تامین D110', city='تبریز', phone='09141110000')
        self.product = Product.objects.create(
            name='محصول D110', slug='d110-product', category=self.category,
            supplier=self.supplier, base_price=Decimal('100000'),
            short_description='x', origin_story='x', status='active')
        self.order = Order.objects.create(
            status=Order.OrderStatus.PAID,
            guest_name='گیرنده D110', guest_phone='09142220000',
            guest_postal_code='5151411111',
            guest_address='تبریز، خیابان آزمایش، پلاک ۱',
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2,
            unit_price_at_purchase=Decimal('100000'), product_name_snapshot='محصول D110')
        self.shipment = build_shipments(self.order)[0]

        self.admin_user = User.objects.create_superuser(
            username='d110admin', password='d110pass!', email='a@b.local')


class TrackingCodeValidationTests(D110Base):
    def test_post_accepts_20_to_24_digits(self):
        self.assertEqual(validate_tracking_code('POST', '1' * 20), '1' * 20)
        self.assertEqual(validate_tracking_code('POST', '2' * 24), '2' * 24)

    def test_post_rejects_wrong_length(self):
        with self.assertRaises(FulfillmentError):
            validate_tracking_code('POST', '1' * 10)
        with self.assertRaises(FulfillmentError):
            validate_tracking_code('POST', '1' * 30)

    def test_post_rejects_letters_and_empty(self):
        with self.assertRaises(FulfillmentError):
            validate_tracking_code('POST', 'AB123456789012345678')
        with self.assertRaises(FulfillmentError):
            validate_tracking_code('POST', '')

    def test_post_accepts_persian_digits(self):
        code = validate_tracking_code('POST', '۱۲۳۴۵۶۷۸۹۰۱۲۳۴۵۶۷۸۹۰')
        self.assertEqual(code, '12345678901234567890')

    def test_post_accepts_international_s10_format(self):
        """فرمت بین‌المللی S10: دو حرف + ۹ رقم + دو حرف"""
        self.assertEqual(validate_tracking_code('POST', 'RA555555555IR'), 'RA555555555IR')
        self.assertEqual(validate_tracking_code('POST', 'rr123456789ir'), 'RR123456789IR')

    def test_chapar_exactly_14_digits(self):
        self.assertEqual(validate_tracking_code('CHAPAR', '1' * 14), '1' * 14)
        with self.assertRaises(FulfillmentError):
            validate_tracking_code('CHAPAR', '1' * 13)

    def test_tipax_15_to_25_digits(self):
        self.assertEqual(validate_tracking_code('TIPAX', '5' * 15), '5' * 15)
        with self.assertRaises(FulfillmentError):
            validate_tracking_code('TIPAX', '5' * 10)

    def test_other_allows_empty(self):
        self.assertEqual(validate_tracking_code('OTHER', ''), '')

    def test_hints_exist_for_all_carriers(self):
        for value, _label in Shipment.Carrier.choices:
            self.assertTrue(carrier_code_hint(value))


class OtherCarrierShipmentTests(D110Base):
    def test_mark_shipped_other_without_code_requires_details(self):
        with self.assertRaises(FulfillmentError):
            mark_shipped(self.shipment, carrier='OTHER', tracking_code='')

    def test_mark_shipped_other_with_details_ok(self):
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            shipment, sent = mark_shipped(
                self.shipment, carrier='OTHER', tracking_code='',
                other_carrier_name='پیک موتوری رضایی',
                other_carrier_person='علی رضایی',
                other_carrier_phone='09143330000',
            )
        self.assertEqual(shipment.status, Shipment.Status.SHIPPED)
        self.assertEqual(shipment.tracking_code, '')
        self.assertEqual(shipment.other_carrier_name, 'پیک موتوری رضایی')
        self.assertEqual(shipment.carrier_full_label, 'سایر (پیک موتوری رضایی)')
        self.assertIn('ارسال‌کننده: علی رضایی', shipment.other_details_text)
        self.assertIn('09143330000', shipment.other_details_text)
        self.assertTrue(sent)
        sms_text = mock_sms.call_args[0][1]
        self.assertIn('پیک موتوری رضایی', sms_text)

    def test_mark_shipped_post_still_requires_code(self):
        with self.assertRaises(FulfillmentError):
            mark_shipped(self.shipment, carrier='POST', tracking_code='')

    def test_mark_shipped_post_persian_digits_ok(self):
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            shipment, _ = mark_shipped(
                self.shipment, carrier='POST', tracking_code='۱' * 20)
        self.assertEqual(shipment.tracking_code, '1' * 20)


class AwaitingReviewTests(D110Base):
    def _pending_order(self, with_user=False):
        """سفارش در انتظار پرداخت — بدون مرسوله (build_shipments نشده)"""
        user = None
        if with_user:
            user = User.objects.create_user(username='09142220000', password='x1234567')
        order = Order.objects.create(
            status=Order.OrderStatus.PENDING,
            user=user,
            guest_name='گیرنده D110', guest_phone='09142220000',
            guest_postal_code='5151411111',
            guest_address='تبریز، خیابان آزمایش، پلاک ۱',
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        return order

    def _submit_evidence(self, order):
        payment = Payment.objects.create(
            order=order, amount=order.total_price,
            status=Payment.PaymentStatus.PENDING)
        payment.submit_evidence('1234', timezone.now())
        return payment

    def test_awaiting_review_flags(self):
        order = self._pending_order()
        self.assertEqual(order.status_display_label, 'در انتظار پرداخت')
        self.assertEqual(order.status_badge_code, 'PENDING')
        self._submit_evidence(order)
        order.refresh_from_db()
        self.assertTrue(order.awaiting_review)
        self.assertEqual(order.status_display_label, 'در انتظار تایید پرداخت')
        self.assertEqual(order.status_badge_code, 'PENDING_REVIEW')

    def test_not_awaiting_after_confirm(self):
        order = self._pending_order()
        payment = self._submit_evidence(order)
        order.refresh_from_db()
        self.assertTrue(order.awaiting_review)
        payment.status = Payment.PaymentStatus.SUCCESS
        payment.save()
        order.refresh_from_db()
        self.assertFalse(order.awaiting_review)
        self.assertEqual(order.status_display_label, 'در انتظار پرداخت')

    def test_tracking_page_shows_awaiting_review_and_no_pay_button(self):
        order = self._pending_order()
        self._submit_evidence(order)
        client = Client()
        session = client.session
        session['tracking_order_id'] = str(order.id)
        session.save()
        r = client.get(reverse('order_pages:tracking_page',
                               args=[order.order_number]))
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('در انتظار تایید', content)
        self.assertIn('رسید پرداخت شما ثبت شد', content)
        self.assertNotIn('تکمیل پرداخت', content)

    def test_profile_shows_awaiting_review(self):
        order = self._pending_order(with_user=True)
        self._submit_evidence(order)
        u = User.objects.get(username='09142220000')
        client = Client()
        client.force_login(u)
        r = client.get(reverse('auth_pages:profile'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('در انتظار تایید', r.content.decode())


class TrackingLinkInProfileTests(D110Base):
    def test_profile_and_tracking_show_shipment_link(self):
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            mark_shipped(self.shipment, carrier='POST', tracking_code='9' * 20)

        client = Client()
        session = client.session
        session['tracking_order_id'] = str(self.order.id)
        session.save()
        r = client.get(reverse('order_pages:tracking_page',
                               args=[self.order.order_number]))
        content = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn('مرسوله‌ها', content)
        self.assertIn('99999999999999999999', content)
        self.assertIn('tracking.post.ir', content)

    def test_tracking_page_other_carrier_details_visible(self):
        with patch('src.modules.auth.services.sms_service.SmsService.send_sms') as mock_sms:
            mock_sms.return_value = (True, 'mock')
            mark_shipped(
                self.shipment, carrier='OTHER', tracking_code='',
                other_carrier_name='باربری سریع‌بار',
                other_carrier_person='حسین محمدی',
                other_carrier_phone='09144440000')
        client = Client()
        session = client.session
        session['tracking_order_id'] = str(self.order.id)
        session.save()
        content = client.get(reverse(
            'order_pages:tracking_page', args=[self.order.order_number])).content.decode()
        self.assertIn('سایر (باربری سریع‌بار)', content)
        self.assertIn('حسین محمدی', content)
        self.assertIn('09144440000', content)


class AdminReceiptLinkTests(D110Base):
    def _payment_with_receipt(self):
        payment = Payment.objects.create(
            order=self.order, amount=self.order.total_price,
            status=Payment.PaymentStatus.PENDING_REVIEW,
            sender_card_last4='6037',
            receipt_image=SimpleUploadedFile('r.png', TINY_PNG, content_type='image/png'),
        )
        return payment

    def test_evidence_preview_contains_clickable_link(self):
        payment = self._payment_with_receipt()
        pa = PaymentAdmin(Payment, django_admin.site)
        html = pa.evidence_preview(payment)
        self.assertIn('<a href=', html)
        self.assertIn('مشاهده رسید', html)

    def test_order_change_page_has_payment_inline_with_receipt(self):
        self._payment_with_receipt()
        client = Client()
        client.force_login(self.admin_user)
        url = reverse('admin:order_order_change', args=[self.order.pk])
        r = client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn('مشاهده رسید', r.content.decode())

    def test_shipment_admin_rejects_bad_chapar_code(self):
        client = Client()
        client.force_login(self.admin_user)
        url = reverse('admin:order_shipment_change', args=[self.shipment.pk])
        r = client.post(url, {
            'order': self.order.pk,
            'fulfiller': self.shipment.fulfiller,
            'supplier': self.supplier.pk,
            'status': Shipment.Status.NEW,
            'carrier': 'CHAPAR',
            'tracking_code': '1234567890123',
            'notes': '',
            'other_carrier_name': '',
            'other_carrier_person': '',
            'other_carrier_phone': '',
        })
        content = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn('۱۴ رقم', content)
        self.shipment.refresh_from_db()
        self.assertEqual(shipment_status(self.shipment), Shipment.Status.NEW)


def shipment_status(shipment):
    shipment.refresh_from_db()
    return shipment.status


class SupplierTrackingFormValidationTests(D110Base):
    """اعتبارسنجی فرم ثبت کد در پنل تامین‌کننده"""

    def setUp(self):
        super().setUp()
        from src.modules.supplier_panel.forms import TrackingCodeForm
        self.form_cls = TrackingCodeForm

    def test_form_rejects_short_post_code(self):
        form = self.form_cls(data={'carrier': 'POST', 'tracking_code': '12345'})
        self.assertFalse(form.is_valid())
        self.assertIn('۲۰ تا ۲۴ رقم', str(form.errors))

    def test_form_other_requires_details(self):
        form = self.form_cls(data={'carrier': 'OTHER', 'tracking_code': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('الزامی', str(form.errors))

    def test_form_other_with_details_valid(self):
        form = self.form_cls(data={
            'carrier': 'OTHER', 'tracking_code': '',
            'other_carrier_name': 'پیک آزمایشی',
            'other_carrier_person': 'رضا رضایی',
            'other_carrier_phone': '09140000000',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_supplier_detail_template_has_format_hints_and_no_price_label(self):
        # قالب باید راهنمای فرمت داشته باشد و عبارت «بدون قیمت» حذف شده باشد
        from django.template.loader import get_template
        tpl = get_template('supplier_panel/shipment_detail.html')
        src = tpl.template.source
        self.assertIn('فرمت استاندارد', src)
        self.assertNotIn('بدون قیمت', src)
        self.assertIn('other-fields', src)
