"""
D-119: صف کار ادمین (داشبورد راهنمامحور) + بج‌های قرمز سایدبار

- گام‌ها به ترتیب: تایید پرداخت → ارسال ریهان → پیگیری تامین‌کننده → در راه → نظرات
- دیرکرد تامین‌کننده بر اساس supplier_deadline_hours تنظیمات سایت محاسبه می‌شود
- /admin/ باید صف کار و بج قرمز را نشان دهد
"""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from src.modules.catalog.models import Category, Supplier, Product
from src.modules.order.models import Order, OrderItem, Payment, Shipment
from src.modules.catalog.templatetags.admin_dashboard import rihan_work_queue
from src.modules.pages.models import SiteSettings

User = get_user_model()


class WorkQueueTestBase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='دسته صف', slug='wq-cat')
        self.supplier = Supplier.objects.create(
            title='تامین‌کننده صف', city='تبریز', phone='09143333333')
        self.product = Product.objects.create(
            name='محصول صف', slug='wq-prod', category=self.category,
            supplier=self.supplier, base_price=Decimal('100000'),
            short_description='x', origin_story='x', status='active')
        self.admin_user = User.objects.create_user(
            username='09124444444', password='RihanAdmin123', is_staff=True, is_superuser=True)

    def _order(self, status, with_user=True):
        user = User.objects.get(username='09124444444') if with_user else None
        o = Order.objects.create(
            user=user, status=status,
            guest_name='خریدار صف', guest_phone='09120000003',
            guest_postal_code='5151411111', guest_address='تبریز')
        OrderItem.objects.create(
            order=o, product=self.product, quantity=1,
            unit_price_at_purchase=Decimal('100000'), product_name_snapshot='محصول صف')
        return o


class WorkQueueCountsTests(WorkQueueTestBase):
    def test_empty_store_has_zero_urgent(self):
        q = rihan_work_queue()
        self.assertEqual(q['urgent_total'], 0)
        self.assertEqual(q['pending_payments'], 0)

    def test_pending_payment_counted_as_urgent(self):
        o = self._order(Order.OrderStatus.PENDING)
        Payment.objects.create(order=o, amount=o.total_price,
                               status=Payment.PaymentStatus.PENDING_REVIEW)
        q = rihan_work_queue()
        self.assertEqual(q['pending_payments'], 1)
        self.assertEqual(q['urgent_total'], 1)

    def test_rihan_new_shipment_counted(self):
        o = self._order(Order.OrderStatus.PROCESSING)
        Shipment.objects.create(order=o, fulfiller=Shipment.FulfillerType.RIHAN)
        q = rihan_work_queue()
        self.assertEqual(q['rihan_new'], 1)
        self.assertEqual(q['urgent_total'], 1)

    def test_paid_without_shipment_counted(self):
        self._order(Order.OrderStatus.PAID)
        q = rihan_work_queue()
        self.assertEqual(q['paid_without_shipment'], 1)

    def test_supplier_overdue_detected_by_deadline(self):
        o = self._order(Order.OrderStatus.PROCESSING)
        s = Shipment.objects.create(
            order=o, fulfiller=Shipment.FulfillerType.SUPPLIER, supplier=self.supplier)
        # تازه ساخته شده → دیرکرد نیست
        self.assertFalse(s.is_overdue)
        q = rihan_work_queue()
        self.assertEqual(q['supplier_overdue'], 0)

        # از مهلت پیش‌فرض ۴۸ ساعت بگذرد
        Shipment.objects.filter(pk=s.pk).update(
            created_at=timezone.now() - timedelta(hours=49))
        s.refresh_from_db()
        self.assertTrue(s.is_overdue)
        q = rihan_work_queue()
        self.assertEqual(q['supplier_overdue'], 1)
        self.assertEqual(q['urgent_total'], 1)

    def test_deadline_hours_from_settings(self):
        s = SiteSettings.load()
        s.supplier_deadline_hours = 24
        s.save()
        from src.modules.order.fulfillment import supplier_deadline_hours
        self.assertEqual(supplier_deadline_hours(), 24)
        # صفر یا مقادیر نامعتبر → پیش‌فرض ۴۸
        s.supplier_deadline_hours = 0
        s.save()
        self.assertEqual(supplier_deadline_hours(), 48)

    def test_overdue_respects_custom_deadline(self):
        s = SiteSettings.load()
        s.supplier_deadline_hours = 24
        s.save()
        o = self._order(Order.OrderStatus.PROCESSING)
        ship = Shipment.objects.create(
            order=o, fulfiller=Shipment.FulfillerType.SUPPLIER, supplier=self.supplier)
        Shipment.objects.filter(pk=ship.pk).update(
            created_at=timezone.now() - timedelta(hours=30))
        ship.refresh_from_db()
        self.assertTrue(ship.is_overdue)


class AdminDashboardRenderTests(WorkQueueTestBase):
    def _admin_client(self):
        c = Client(SERVER_NAME='rihan360.ir')
        c.force_login(self.admin_user)
        return c

    def test_admin_index_shows_work_queue(self):
        body = self._admin_client().get('/admin/').content.decode()
        self.assertIn('کارهای امروز', body)
        self.assertIn('تایید پرداخت', body)
        self.assertIn('پیگیری تامین‌کننده', body)
        self.assertNotIn('rihanGuide', body)  # راهنمای استاتیک قدیمی حذف شده

    def test_admin_index_urgent_bar_on_pending_payment(self):
        o = self._order(Order.OrderStatus.PENDING)
        Payment.objects.create(order=o, amount=o.total_price,
                               status=Payment.PaymentStatus.PENDING_REVIEW)
        body = self._admin_client().get('/admin/').content.decode()
        self.assertIn('<div class="rd-urgent"', body)
        self.assertIn('کار فوری', body)

    def test_admin_index_no_urgent_bar_when_clean(self):
        body = self._admin_client().get('/admin/').content.decode()
        # دام: 'rd-urgent' در CSS داخل همان صفحه هم هست — مارکاپ div را چک کن
        self.assertNotIn('<div class="rd-urgent"', body)

    def test_sidebar_badge_on_pending_payment(self):
        o = self._order(Order.OrderStatus.PENDING)
        Payment.objects.create(order=o, amount=o.total_price,
                               status=Payment.PaymentStatus.PENDING_REVIEW)
        body = self._admin_client().get('/admin/').content.decode()
        self.assertIn('<span class="rsb-badge">', body)

    def test_sidebar_links_include_shipments(self):
        body = self._admin_client().get('/admin/').content.decode()
        self.assertIn('مرسوله‌ها', body)
        self.assertIn('لاگ اطلاع‌رسانی', body)

    # ── D-120: تسویه تامین‌کننده — گام ۶ صف کار + منوی مالی ──
    def test_settlement_step_rendered_with_link(self):
        body = self._admin_client().get('/admin/').content.decode()
        self.assertIn('تسویه تامین‌کننده‌ها', body)
        self.assertIn('href="/finance/admin/"', body)

    def test_settlement_step_hot_on_delivered_unsettled(self):
        o = self._order(Order.OrderStatus.PROCESSING)
        sh = Shipment.objects.create(
            order=o, fulfiller=Shipment.FulfillerType.SUPPLIER, supplier=self.supplier)
        sh.status = Shipment.Status.DELIVERED
        sh.save(update_fields=['status'])
        body = self._admin_client().get('/admin/').content.decode()
        self.assertIn('<div class="rd-urgent"', body)  # جزو فوری‌ها
        self.assertIn('معوق', body)

    def test_settlement_not_hot_when_settled(self):
        o = self._order(Order.OrderStatus.PROCESSING)
        sh = Shipment.objects.create(
            order=o, fulfiller=Shipment.FulfillerType.SUPPLIER, supplier=self.supplier)
        sh.status = Shipment.Status.DELIVERED
        sh.settlement_status = Shipment.SettlementStatus.SETTLED
        sh.save(update_fields=['status', 'settlement_status'])
        q = rihan_work_queue()
        self.assertEqual(q['unsettled_due'], 0)
        self.assertEqual(q['unsettled_due_amount'], 0)

    def test_sidebar_has_finance_group_with_badge(self):
        o = self._order(Order.OrderStatus.PROCESSING)
        sh = Shipment.objects.create(
            order=o, fulfiller=Shipment.FulfillerType.SUPPLIER, supplier=self.supplier)
        sh.status = Shipment.Status.DELIVERED
        sh.save(update_fields=['status'])
        body = self._admin_client().get('/admin/').content.decode()
        self.assertIn('💰 امور مالی', body)
        self.assertIn('داشبورد مالی و تسویه', body)

    def test_admin_finance_dashboard_live(self):
        r = self._admin_client().get('/finance/admin/')
        self.assertEqual(r.status_code, 200)
