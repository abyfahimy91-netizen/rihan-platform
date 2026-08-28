"""تست آدرس‌های کاربر — D-102 (ذخیره آدرس، انتخاب در تسویه‌حساب، مدیریت در پروفایل)
از مدل موجود order.Address استفاده می‌شود (schema آماده بود، UI نداشت).
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from src.modules.catalog.models import Category, Supplier, Product, Inventory
from src.modules.order import address_service
from src.modules.order.models import Address, Order

User = get_user_model()

HOST = 'rihan360.ir'


class AddressModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='09121110000', password='test123456', email='t@rihan.local'
        )

    def _addr(self, **kw):
        base = dict(
            user=self.user, full_name='کاربر تست', phone='09121110000',
            detailed_address='تبریز، خیابان آزادی، پلاک ۱۰',
        )
        base.update(kw)
        return Address.objects.create(**base)

    def test_first_address_becomes_default(self):
        a = self._addr()
        self.assertTrue(a.is_default)

    def test_only_one_default(self):
        a1 = self._addr(is_default=True)
        a2 = self._addr(detailed_address='تهران، ولیعصر، پلاک ۲', is_default=True)
        a1.refresh_from_db()
        self.assertFalse(a1.is_default)
        self.assertTrue(a2.is_default)

    def test_set_default_switches(self):
        a1 = self._addr()
        a2 = self._addr(detailed_address='تهران، ولیعصر، پلاک ۲')
        self.assertTrue(address_service.set_default(self.user, a2.pk))
        a1.refresh_from_db()
        self.assertFalse(a1.is_default)

    def test_delete_default_promotes_next(self):
        a1 = self._addr()
        a2 = self._addr(detailed_address='تهران، ولیعصر، پلاک ۲')
        address_service.delete_address(self.user, a2.pk)
        a1.refresh_from_db()
        self.assertTrue(a1.is_default)

    def test_cannot_access_others_address(self):
        other = User.objects.create_user(username='09121110001', password='x1234567', email='o@rihan.local')
        a = Address.objects.create(
            user=other, full_name='غریبه', phone='09121110001',
            detailed_address='آدرس غریبه طولانی کافی',
        )
        self.assertIsNone(address_service.get_for_user(self.user, a.pk))


class AddressValidationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='09121110002', password='x1234567', email='v@rihan.local')

    def _data(self, **kw):
        base = {
            'full_name': 'کاربر تست', 'phone': '09121110002',
            'address': 'تبریز، خیابان آزادی، پلاک ۱۰',
            'postal_code': '5154911111', 'title': 'خانه',  # D-111: کد پستی الزامی
        }
        base.update(kw)
        return base

    def test_valid_data_creates(self):
        a = address_service.create_for_user(self.user, self._data())
        self.assertEqual(a.full_name, 'کاربر تست')
        self.assertEqual(a.detailed_address, 'تبریز، خیابان آزادی، پلاک ۱۰')

    def test_invalid_phone_rejected(self):
        with self.assertRaises(ValueError):
            address_service.create_for_user(self.user, self._data(phone='12345'))

    def test_short_address_rejected(self):
        with self.assertRaises(ValueError):
            address_service.create_for_user(self.user, self._data(address='تهران'))

    def test_missing_postal_rejected(self):
        """D-111: کد پستی ۱۰ رقمی الزامی است"""
        with self.assertRaises(ValueError):
            address_service.create_for_user(self.user, self._data(postal_code=''))
        with self.assertRaises(ValueError):
            address_service.create_for_user(self.user, self._data(postal_code='123'))


class CheckoutAddressTest(TestCase):
    """انتخاب آدرس ذخیره‌شده در تسویه‌حساب + ذخیره خودکار آدرس جدید"""

    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        self.user = User.objects.create_user(
            username='09121110003', password='test123456', email='c@rihan.local',
            first_name='مریم', last_name='احمدی',
        )
        cat = Category.objects.create(name='تست دسته', slug='test-cat-addr')
        sup = Supplier.objects.create(title='تست تامین', city='تبریز')
        self.product = Product.objects.create(
            name='محصول تست آدرس', slug='test-addr-product',
            category=cat, supplier=sup, unit='عدد',
            base_price=Decimal('100000'), shipping_cost=Decimal('0'),
            margin_percent=0, short_description='تست', origin_story='تست',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        inv, _ = Inventory.objects.get_or_create(product=self.product)
        inv.quantity = Decimal('10')
        inv.save()

        self.client.force_login(self.user)
        self.client.post('/order/cart/add/', {'product_slug': self.product.slug, 'quantity': 1})

    def test_checkout_shows_saved_addresses(self):
        Address.objects.create(
            user=self.user, full_name='مریم احمدی', phone='09121110003',
            detailed_address='تبریز، آزادی، پلاک ۱۰', is_default=True, title='خانه',
        )
        r = self.client.get('/order/checkout/')
        content = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn('تبریز، آزادی، پلاک ۱۰', content)
        self.assertIn('افزودن آدرس جدید', content)
        self.assertIn('پیش‌فرض', content)

    def test_order_with_saved_address(self):
        a = Address.objects.create(
            user=self.user, full_name='مریم احمدی', phone='09121110003',
            detailed_address='تبریز، آزادی، پلاک ۱۰', postal_code='5154911111',
        )
        r = self.client.post('/order/checkout/', {'address_choice': f'id:{a.pk}'})
        self.assertEqual(r.status_code, 302)
        order = Order.objects.latest('id')
        self.assertEqual(order.guest_name, 'مریم احمدی')
        self.assertIn('آزادی', order.guest_address or '')

    def test_new_address_auto_saved_when_checked(self):
        r = self.client.post('/order/checkout/', {
            'address_choice': 'new',
            'title': 'محل کار',
            'name': 'مریم احمدی',
            'phone': '09121110003',
            'address': 'تهران، ولیعصر، پلاک ۲۲',
            'postal_code': '1234567890',
            'save_address': 'on',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.user.addresses.count(), 1)
        a = self.user.addresses.first()
        self.assertEqual(a.title, 'محل کار')
        self.assertTrue(a.is_default)  # اولین آدرس

    def test_new_address_not_saved_when_unchecked(self):
        r = self.client.post('/order/checkout/', {
            'address_choice': 'new',
            'name': 'مریم احمدی',
            'phone': '09121110003',
            'address': 'تهران، ولیعصر، پلاک ۲۲',
            'postal_code': '1234567890',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.user.addresses.count(), 0)

    def test_cannot_use_others_address(self):
        other = User.objects.create_user(username='09121110004', password='x1234567', email='x@rihan.local')
        a = Address.objects.create(
            user=other, full_name='غریبه', phone='09121110004',
            detailed_address='آدرس غریبه طولانی کافی',
        )
        r = self.client.post('/order/checkout/', {'address_choice': f'id:{a.pk}'})
        self.assertEqual(r.status_code, 200)  # برنمی‌گردد به پرداخت
        self.assertIn('پیدا نشد', r.content.decode())


class ProfileAddressTest(TestCase):
    """مدیریت آدرس‌ها در پروفایل"""

    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        self.user = User.objects.create_user(
            username='09121110005', password='test123456', email='p@rihan.local',
            first_name='مریم', last_name='احمدی',
        )
        self.client.force_login(self.user)

    def _add(self, **kw):
        data = {
            'action': 'address_save',
            'title': 'خانه',
            'full_name': 'مریم احمدی',
            'phone': '09121110005',
            'address': 'تبریز، آزادی، پلاک ۱۰',
            'postal_code': '5154911111',  # D-111: کد پستی الزامی شد
        }
        data.update(kw)
        return self.client.post('/accounts/profile/', data)

    def test_add_address_rejects_missing_postal(self):
        """D-111: کد پستی ۱۰ رقمی الزامی است"""
        r = self._add(postal_code='')
        self.user.refresh_from_db()
        self.assertEqual(self.user.addresses.count(), 0)

    def test_add_address_error_same_page_no_data_loss(self):
        """D-113c: خطای کدپستی → بدون ریدایرکت؛ همان صفحه باز می‌شود و داده‌های تایپ‌شده حفظ است"""
        r = self._add(postal_code='')
        self.assertEqual(r.status_code, 200)  # نه 302 — کاربر «پرت» نمی‌شود
        content = r.content.decode()
        self.assertIn('adr-errors', content)              # خطا داخل خود فرم
        self.assertIn('اداره پست', content)                # توضیح قانع‌کننده الزام
        self.assertIn('مریم احمدی', content)               # نام تایپ‌شده حفظ شده
        self.assertIn('تبریز، آزادی، پلاک ۱۰', content)    # آدرس تایپ‌شده حفظ شده
        self.assertIn('adr-form-box" open', content)       # فرم خودکار باز است
        self.assertEqual(self.user.addresses.count(), 0)

    def test_edit_address_error_same_page_no_data_loss(self):
        """D-113c: خطا هنگام ویرایش → بازرندر با داده‌های تایپ‌شده؛ آدرس اصلی دست‌نخورده"""
        self._add()
        a = self.user.addresses.first()
        r = self._add(address_id=a.pk, postal_code='123')
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('adr-errors', content)
        self.assertIn(f'value="{a.pk}"', content)          # hidden address_id حفظ شده
        a.refresh_from_db()
        self.assertIn('آزادی', a.detailed_address)         # آدرس اصلی تغییر نکرده

    def test_add_address(self):
        r = self._add()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.user.addresses.count(), 1)

    def test_edit_address(self):
        self._add()
        a = self.user.addresses.first()
        self._add(address_id=a.pk, address='تهران، ولیعصر، پلاک ۲۲', title='محل کار')
        a.refresh_from_db()
        self.assertIn('ولیعصر', a.detailed_address)
        self.assertEqual(a.title, 'محل کار')

    def test_set_default_action(self):
        self._add()
        self._add(title='محل کار', address='تهران، ولیعصر، پلاک ۲۲ طولانی')
        first = self.user.addresses.first()
        r = self.client.post('/accounts/profile/', {
            'action': 'address_default', 'address_id': first.pk,
        })
        self.assertEqual(r.status_code, 302)
        first.refresh_from_db()
        self.assertTrue(first.is_default)

    def test_delete_action(self):
        self._add()
        a = self.user.addresses.first()
        self.client.post('/accounts/profile/', {
            'action': 'address_delete', 'address_id': a.pk,
        })
        self.assertEqual(self.user.addresses.count(), 0)

    def test_addresses_tab_in_profile(self):
        self._add()
        r = self.client.get('/accounts/profile/')
        content = r.content.decode()
        self.assertIn('آدرس‌های من', content)
        self.assertIn('افزودن آدرس جدید', content)
        self.assertIn('تبریز، آزادی، پلاک ۱۰', content)

    def test_edit_prefill_via_query(self):
        self._add()
        a = self.user.addresses.first()
        r = self.client.get('/accounts/profile/', {'edit': a.pk})
        self.assertEqual(r.status_code, 200)
