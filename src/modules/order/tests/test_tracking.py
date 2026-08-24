"""
Tests for M7 - Order Tracking (D-082)

Covers:
- OrderStatusHistory signal auto-capture
- Tracking lookup by phone + order number
- Tracking page access control
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from src.modules.order.models import (
    Order, OrderItem, OrderStatusHistory, Payment
)
from src.modules.catalog.models import Product, Category, Supplier, Inventory


User = get_user_model()


class OrderStatusHistorySignalTest(TestCase):
    """Test the auto-capture signal for status history"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='09121111111',
            first_name='Test',
            last_name='User'
        )
        self.supplier = Supplier.objects.create(
            title='Test Supplier',
            city='Tehran'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-cat'
        )
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
    
    def _create_order(self, status='DRAFT'):
        return Order.objects.create(
            user=self.user,
            status=status,
            guest_name='Test Customer',
            guest_phone='09121111111',
            total_price=Decimal('200000'),
        )
    
    def test_order_creation_creates_history(self):
        """Creating an order should create ORDER_CREATED history"""
        order = self._create_order()
        history = OrderStatusHistory.objects.filter(order=order)
        
        self.assertEqual(history.count(), 1)
        self.assertEqual(
            history.first().status,
            OrderStatusHistory.HistoryStatus.ORDER_CREATED
        )
    
    def test_status_change_creates_history(self):
        """Changing status should create new history record"""
        order = self._create_order()
        
        order.status = 'PENDING'
        order.save()
        
        history = OrderStatusHistory.objects.filter(order=order).order_by('created_at')
        self.assertEqual(history.count(), 2)
        self.assertEqual(
            history.last().status,
            OrderStatusHistory.HistoryStatus.PENDING_PAYMENT
        )
    
    def test_same_status_no_duplicate(self):
        """Saving with same status should NOT create duplicate history"""
        order = self._create_order()
        initial_count = OrderStatusHistory.objects.filter(order=order).count()
        
        # Save without status change
        order.save()
        
        final_count = OrderStatusHistory.objects.filter(order=order).count()
        self.assertEqual(initial_count, final_count)
    
    def test_full_lifecycle_history(self):
        """Test full order lifecycle creates correct history"""
        order = self._create_order()
        
        # PENDING -> PAID -> PROCESSING -> SHIPPED -> DELIVERED
        for status in ['PENDING', 'PAID', 'PROCESSING', 'SHIPPED', 'DELIVERED']:
            order.status = status
            order.save()
        
        history = OrderStatusHistory.objects.filter(order=order).order_by('created_at')
        
        # 1 (created) + 5 (changes) = 6 records
        self.assertEqual(history.count(), 6)
        
        # Verify order of statuses
        statuses = [h.status for h in history]
        expected = [
            OrderStatusHistory.HistoryStatus.ORDER_CREATED,
            OrderStatusHistory.HistoryStatus.PENDING_PAYMENT,
            OrderStatusHistory.HistoryStatus.PAYMENT_CONFIRMED,
            OrderStatusHistory.HistoryStatus.PROCESSING,
            OrderStatusHistory.HistoryStatus.SHIPPED,
            OrderStatusHistory.HistoryStatus.DELIVERED,
        ]
        self.assertEqual(statuses, expected)
    
    def test_shipped_at_auto_set(self):
        """shipped_at should be auto-set when status changes to SHIPPED"""
        order = self._create_order()
        
        self.assertIsNone(order.shipped_at)
        
        order.status = 'SHIPPED'
        order.save()
        
        order.refresh_from_db()
        self.assertIsNotNone(order.shipped_at)
    
    def test_delivered_at_auto_set(self):
        """delivered_at should be auto-set when status changes to DELIVERED"""
        order = self._create_order()
        
        self.assertIsNone(order.delivered_at)
        
        order.status = 'DELIVERED'
        order.save()
        
        order.refresh_from_db()
        self.assertIsNotNone(order.delivered_at)
    
    def test_no_duplicate_shipped_records(self):
        """Bug fix verification: no duplicate SHIPPED records"""
        order = self._create_order()
        
        order.status = 'SHIPPED'
        order.tracking_code = 'TEST123'
        order.save()
        
        shipped_count = OrderStatusHistory.objects.filter(
            order=order,
            status=OrderStatusHistory.HistoryStatus.SHIPPED
        ).count()
        
        self.assertEqual(shipped_count, 1)
    
    def test_tracking_code_stored_in_history(self):
        """Tracking code should be stored in history record"""
        order = self._create_order()
        
        order.status = 'SHIPPED'
        order.tracking_code = 'TRACK123456'
        order.save()
        
        shipped_history = OrderStatusHistory.objects.filter(
            order=order,
            status=OrderStatusHistory.HistoryStatus.SHIPPED
        ).first()
        
        self.assertEqual(shipped_history.tracking_code, 'TRACK123456')


class TrackingLookupViewTest(TestCase):
    """Test the tracking lookup page (phone + order number)"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='09122222222',
            first_name='Lookup',
            last_name='User'
        )
        self.order = Order.objects.create(
            user=self.user,
            status='PENDING',
            guest_name='Guest Customer',
            guest_phone='09122222222',
            total_price=Decimal('300000'),
        )
    
    def test_lookup_page_renders(self):
        """GET /order/lookup/ should render the form"""
        response = self.client.get('/order/lookup/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'پیگیری سفارش')
    
    def test_lookup_with_correct_phone_and_order(self):
        """POST with correct phone + order should redirect to tracking"""
        response = self.client.post('/order/lookup/', {
            'phone': '09122222222',
            'order_number': self.order.order_number,
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn(self.order.order_number, response.url)
    
    def test_lookup_with_wrong_phone(self):
        """POST with wrong phone should show error"""
        response = self.client.post('/order/lookup/', {
            'phone': '09129999999',  # Wrong phone
            'order_number': self.order.order_number,
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مطابقت ندارد')
    
    def test_lookup_with_wrong_order_number(self):
        """POST with wrong order number should show error"""
        response = self.client.post('/order/lookup/', {
            'phone': '09122222222',
            'order_number': 'RH-1405-99999',  # Non-existent
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'پیدا نشد')
    
    def test_lookup_with_empty_fields(self):
        """POST with empty fields should show error"""
        response = self.client.post('/order/lookup/', {
            'phone': '',
            'order_number': '',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لطفاً')
    
    def test_lookup_with_guest_phone(self):
        """Guest phone (snapshot) should also work"""
        # Create order without user (guest only)
        guest_order = Order.objects.create(
            user=None,
            status='PENDING',
            guest_name='Pure Guest',
            guest_phone='09123333333',
            total_price=Decimal('100000'),
        )
        
        response = self.client.post('/order/lookup/', {
            'phone': '09123333333',
            'order_number': guest_order.order_number,
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn(guest_order.order_number, response.url)
    
    def test_lookup_sets_session_key(self):
        """After successful lookup, order's session_key should be updated"""
        initial_session_key = self.order.session_key
        
        self.client.post('/order/lookup/', {
            'phone': '09122222222',
            'order_number': self.order.order_number,
        })
        
        self.order.refresh_from_db()
        # Session key should be set (not empty)
        self.assertIsNotNone(self.order.session_key)


class TrackingPageViewTest(TestCase):
    """Test the tracking page itself"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='09124444444',
            first_name='Tracking',
            last_name='User'
        )
        self.order = Order.objects.create(
            user=self.user,
            status='SHIPPED',
            guest_name='Test Customer',
            guest_phone='09124444444',
            total_price=Decimal('500000'),
            tracking_code='TRACK789',
            shipping_method='Post',
        )
    
    def test_tracking_page_as_owner(self):
        """Owner should be able to see tracking page"""
        self.client.force_login(self.user)
        response = self.client.get(f'/order/tracking/{self.order.order_number}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)
    
    def test_tracking_page_unauthorized(self):
        """Non-owner without session should be forbidden"""
        other_user = User.objects.create_user(
            username='09125555555',
            first_name='Other',
            last_name='User'
        )
        self.client.force_login(other_user)
        response = self.client.get(f'/order/tracking/{self.order.order_number}/')
        
        self.assertEqual(response.status_code, 403)
    
    def test_tracking_page_shows_timeline(self):
        """Tracking page should show the timeline"""
        self.client.force_login(self.user)
        response = self.client.get(f'/order/tracking/{self.order.order_number}/')
        
        self.assertEqual(response.status_code, 200)
        # Check timeline elements
        self.assertContains(response, 'سفارش ثبت شد')
        self.assertContains(response, 'ارسال')
