"""
D-124: متن پیامک دستی مشتری در صفحه مرسولهٔ ادمین.

تا فعال‌شدن پنل پیامکی، ادمین متن را کپی و با گوشی خودش می‌فرستد:
تشکر بابت خرید + اقلام + کد رهگیری + لینک یک‌کلیکی (سامانه باربری با کدِ پرشده باز می‌شود).
قانون امنیتی: متن هرگز قیمت ندارد.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from src.modules.catalog.models import Category, Product, Supplier
from src.modules.order.models import Order, OrderItem, Shipment
from src.modules.order.fulfillment import (
    build_shipments,
    manual_customer_sms_text,
    sms_auto_send_available,
)

User = get_user_model()


class ManualSmsTestBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='09128888001', password='Xtest12345',
            is_staff=True, is_superuser=True)
        self.supplier = Supplier.objects.create(
            title='تامین‌کننده پیامک', city='تبریز', phone='09128888002')
        cat = Category.objects.create(name='cat-sms', slug='cat-sms')
        self.product = Product.objects.create(
            name='سماق پیامکی', slug='sms-prod', category=cat, supplier=self.supplier,
            base_price=Decimal('1500000'), final_price=Decimal('1500000'),
            short_description='x', origin_story='x', status='active')
        self.order = Order.objects.create(
            user=self.admin, status=Order.OrderStatus.PROCESSING,
            guest_name='مشتری پیامک', guest_phone='09128888003',
            guest_postal_code='5151411111',
            guest_address='تبریز، خیابان پیامک، پلاک ۵')
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=2,
            unit_price_at_purchase=Decimal('1500000'),
            unit_cost_at_purchase=Decimal('950000'),
            product_name_snapshot='سماق پیامکی')
        build_shipments(self.order)
        self.shipment = Shipment.objects.get(order=self.order)

    def _ship(self, code='12345678901234567890'):
        self.shipment.tracking_code = code
        self.shipment.status = Shipment.Status.SHIPPED
        self.shipment.save(update_fields=['tracking_code', 'status'])
        return self.shipment


class ManualSmsTextTests(ManualSmsTestBase):
    def test_contains_thanks_items_code_and_link(self):
        self._ship()
        text = manual_customer_sms_text(self.shipment)
        self.assertIn('سپاس از خرید', text)
        self.assertIn(self.order.order_number, text)
        self.assertIn('سماق پیامکی × 2', text)
        self.assertIn('12345678901234567890', text)
        self.assertIn(f'/order/t/12345678901234567890', text)
        self.assertIn('پیگیری', text)

    def test_no_price_in_sms(self):
        self._ship()
        text = manual_customer_sms_text(self.shipment)
        self.assertNotIn('۱٬۵۰۰٬۰۰۰', text)
        self.assertNotIn('۹۵۰٬۰۰۰', text)
        self.assertNotIn('1,500,000', text)

    def test_other_carrier_sms_without_code(self):
        self.shipment.carrier = Shipment.Carrier.OTHER
        self.shipment.other_carrier_name = 'پیک رضایی'
        self.shipment.other_carrier_person = 'آقای رضایی'
        self.shipment.other_carrier_phone = '09128888004'
        self.shipment.save()
        text = manual_customer_sms_text(self.shipment)
        self.assertIn('پیک رضایی', text)
        self.assertIn(self.order.order_number, text)

    def test_new_shipment_without_code_has_no_sms_text(self):
        text = manual_customer_sms_text(self.shipment)
        # بدون کد و بدون سایر → متن کامل ساخته نمی‌شود (هیچ لینکی نیست)
        self.assertNotIn('/order/t/', text)

    def test_auto_send_available_false_without_provider(self):
        self.assertFalse(sms_auto_send_available())


class ManualSmsAdminUITests(ManualSmsTestBase):
    def _admin(self):
        c = Client(SERVER_NAME='rihan360.ir')
        c.force_login(self.admin)
        return c

    def test_change_page_shows_sms_box_with_copy_button(self):
        self._ship()
        body = self._admin().get(
            f'/admin/order/shipment/{self.shipment.pk}/change/').content.decode()
        self.assertIn('متن پیامک مشتری', body)
        self.assertIn('rihan-sms-text', body)
        self.assertIn('rihan-copy-sms', body)
        self.assertIn('12345678901234567890', body)

    def test_change_page_without_code_shows_placeholder(self):
        body = self._admin().get(
            f'/admin/order/shipment/{self.shipment.pk}/change/').content.decode()
        self.assertIn('هنوز کد رهگیری ثبت نشده', body)
        self.assertNotIn('rihan-sms-text', body)

    def test_box_mentions_manual_send_when_sms_off(self):
        self._ship()
        body = self._admin().get(
            f'/admin/order/shipment/{self.shipment.pk}/change/').content.decode()
        self.assertIn('با گوشی خودتان', body)

    def test_char_count_and_test_link_present(self):
        self._ship()
        body = self._admin().get(
            f'/admin/order/shipment/{self.shipment.pk}/change/').content.decode()
        self.assertIn('کاراکتر', body)
        self.assertIn('/order/t/12345678901234567890', body)
