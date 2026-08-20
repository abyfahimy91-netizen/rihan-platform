"""
Tests for M9 - Leads Module (US-010)

Covers:
- Lead model validation and methods
- Phone validation
- Duplicate prevention (one pending per phone+product)
- Auto-notification signal
- Lead conversion tracking
- Views (lead form page, API)
"""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from src.modules.catalog.models import Product, Category, Supplier, Inventory
from src.modules.order.models import Order, OrderItem
from src.modules.leads.models import Lead


User = get_user_model()


class LeadModelTest(TestCase):
    """Test Lead model methods and validation"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-lead')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product-lead',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
    
    def test_create_lead_with_valid_phone(self):
        """Lead should be created with valid phone format"""
        lead = Lead.objects.create(
            phone='09121234567',
            name='Test User',
            product=self.product
        )
        self.assertEqual(lead.status, Lead.LeadStatus.PENDING)
    
    def test_phone_validation_rejects_invalid_format(self):
        """Invalid phone format should be rejected via full_clean()"""
        from django.core.exceptions import ValidationError
        
        lead = Lead(
            phone='12345',  # Invalid - too short
            product=self.product
        )
        
        # Django RegexValidator only runs on full_clean(), not save()
        with self.assertRaises(ValidationError):
            lead.full_clean()
    
    def test_can_create_lead_returns_true_for_new(self):
        """New lead should be allowed"""
        can_create, message = Lead.can_create_lead('09121111111', self.product)
        self.assertTrue(can_create)
    
    def test_can_create_lead_rejects_duplicate(self):
        """Duplicate pending lead should be rejected"""
        Lead.objects.create(
            phone='09122222222',
            product=self.product,
            status=Lead.LeadStatus.PENDING
        )
        can_create, message = Lead.can_create_lead('09122222222', self.product)
        self.assertFalse(can_create)
        self.assertIn('قبلاً', message)
    
    def test_can_create_lead_allows_re_submit_after_notify(self):
        """After notification, user can submit again (new pending)"""
        lead = Lead.objects.create(
            phone='09123333333',
            product=self.product,
            status=Lead.LeadStatus.PENDING
        )
        lead.notify(method='SMS')
        
        # Now should be able to create new pending
        can_create, message = Lead.can_create_lead('09123333333', self.product)
        self.assertTrue(can_create)
    
    def test_notify_method(self):
        """notify() should set status and notified_at"""
        lead = Lead.objects.create(
            phone='09124444444',
            product=self.product
        )
        
        self.assertFalse(lead.notified_at)
        lead.notify(method='SMS')
        
        self.assertEqual(lead.status, Lead.LeadStatus.NOTIFIED)
        self.assertIsNotNone(lead.notified_at)
        self.assertEqual(lead.notification_method, 'SMS')
    
    def test_convert_method(self):
        """convert() should set status and link to order"""
        lead = Lead.objects.create(
            phone='09125555555',
            product=self.product
        )
        order = Order.objects.create(
            status='DELIVERED',
            total_price=Decimal('100000')
        )
        
        lead.convert(order)
        
        self.assertEqual(lead.status, Lead.LeadStatus.CONVERTED)
        self.assertEqual(lead.order, order)
        self.assertIsNotNone(lead.converted_at)
    
    def test_cancel_method(self):
        """cancel() should set status to CANCELLED"""
        lead = Lead.objects.create(
            phone='09126666666',
            product=self.product
        )
        lead.cancel()
        
        self.assertEqual(lead.status, Lead.LeadStatus.CANCELLED)
    
    def test_get_pending_leads_for_product(self):
        """get_pending_leads_for_product should return only pending"""
        Lead.objects.create(
            phone='09127777777',
            product=self.product,
            status=Lead.LeadStatus.PENDING
        )
        Lead.objects.create(
            phone='09128888888',
            product=self.product,
            status=Lead.LeadStatus.NOTIFIED
        )
        
        pending = Lead.get_pending_leads_for_product(self.product)
        self.assertEqual(pending.count(), 1)


class LeadAutoNotificationTest(TestCase):
    """Test auto-notification signal when product becomes available"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-auto')
        self.product = Product.objects.create(
            name='Product For Notify',
            slug='product-for-notify',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
        self.inventory = Inventory.objects.get(product=self.product)
    
    def test_auto_notify_when_stock_added(self):
        """Adding stock should auto-notify all pending leads"""
        # Create 3 pending leads
        for i in range(3):
            Lead.objects.create(
                phone=f'0912000000{i}',
                product=self.product,
                status=Lead.LeadStatus.PENDING
            )
        
        # Add stock
        self.inventory.add_stock(10)
        
        # Check all are notified
        pending_count = Lead.objects.filter(
            product=self.product,
            status=Lead.LeadStatus.PENDING
        ).count()
        notified_count = Lead.objects.filter(
            product=self.product,
            status=Lead.LeadStatus.NOTIFIED
        ).count()
        
        self.assertEqual(pending_count, 0)
        self.assertEqual(notified_count, 3)
    
    def test_no_notify_if_no_leads(self):
        """Adding stock with no leads should not fail"""
        # This should not raise any exception
        self.inventory.add_stock(5)
        self.assertEqual(self.inventory.quantity, 5)
    
    def test_auto_notify_uses_bulk_update(self):
        """Auto-notification should mark method as AUTO"""
        Lead.objects.create(
            phone='09121111111',
            product=self.product,
            status=Lead.LeadStatus.PENDING
        )
        
        self.inventory.add_stock(1)
        
        lead = Lead.objects.get(phone='09121111111')
        self.assertEqual(lead.notification_method, 'AUTO')
    
    def test_only_notifies_pending_leads(self):
        """Auto-notification should not touch non-pending leads"""
        # Create a NOTIFIED lead (already notified before)
        notified_lead = Lead.objects.create(
            phone='09122222222',
            product=self.product,
            status=Lead.LeadStatus.NOTIFIED
        )
        
        # Create a PENDING lead
        pending_lead = Lead.objects.create(
            phone='09123333333',
            product=self.product,
            status=Lead.LeadStatus.PENDING
        )
        
        self.inventory.add_stock(1)
        
        notified_lead.refresh_from_db()
        pending_lead.refresh_from_db()
        
        self.assertEqual(notified_lead.status, Lead.LeadStatus.NOTIFIED)
        self.assertEqual(pending_lead.status, Lead.LeadStatus.NOTIFIED)


class LeadConversionTest(TestCase):
    """Test lead conversion when order is placed"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-conv')
        self.product = Product.objects.create(
            name='Product For Conv',
            slug='product-for-conv',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
        self.user = User.objects.create_user(
            username='09124444444',
            first_name='Test'
        )
    
    def test_lead_converts_on_paid_order(self):
        """Lead should be converted when PAID order is placed"""
        lead = Lead.objects.create(
            phone='09124444444',
            product=self.product,
            status=Lead.LeadStatus.NOTIFIED
        )
        
        order = Order.objects.create(
            user=self.user,
            status='PAID',
            total_price=Decimal('100000')
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
        
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.LeadStatus.CONVERTED)
        self.assertEqual(lead.order, order)
    
    def test_no_conversion_for_unrelated_phone(self):
        """Lead with different phone should not be converted"""
        lead = Lead.objects.create(
            phone='09125555555',  # Different from user
            product=self.product,
            status=Lead.LeadStatus.NOTIFIED
        )
        
        order = Order.objects.create(
            user=self.user,  # username=09124444444
            status='PAID',
            total_price=Decimal('100000')
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
        
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.LeadStatus.NOTIFIED)  # Not converted
    
    def test_no_conversion_for_unrelated_product(self):
        """Lead for different product should not be converted"""
        other_product = Product.objects.create(
            name='Other Product',
            slug='other-product-conv',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('200000'),
            status='active'
        )
        
        lead = Lead.objects.create(
            phone='09124444444',
            product=other_product,  # Different product
            status=Lead.LeadStatus.NOTIFIED
        )
        
        order = Order.objects.create(
            user=self.user,
            status='PAID',
            total_price=Decimal('100000')
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,  # Different from lead
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
        
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.LeadStatus.NOTIFIED)  # Not converted


class LeadFormViewTest(TestCase):
    """Test lead form page view"""
    
    def setUp(self):
        self.client = Client()
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-form')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product-form',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
    
    def test_lead_form_renders_without_product(self):
        """General lead form should render"""
        response = self.client.get('/leads/register/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'اطلاع از موجودی')
    
    def test_lead_form_renders_with_product(self):
        """Product-specific lead form should render with product name"""
        response = self.client.get(f'/leads/register/{self.product.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
    
    def test_submit_lead_form_success(self):
        """Valid submission should create lead and show success"""
        response = self.client.post('/leads/register/', {
            'phone': '09121111111',
            'name': 'Test User'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ثبت شد')
        
        # Verify lead was created
        lead = Lead.objects.filter(phone='09121111111').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.name, 'Test User')
        self.assertEqual(lead.status, Lead.LeadStatus.PENDING)
    
    def test_submit_lead_form_without_name(self):
        """Submission without name should succeed (name is optional)"""
        response = self.client.post('/leads/register/', {
            'phone': '09122222222'
        })
        
        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.filter(phone='09122222222').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.name, '')
    
    def test_submit_lead_form_invalid_phone(self):
        """Invalid phone should show error"""
        response = self.client.post('/leads/register/', {
            'phone': '123',  # Invalid
            'name': 'Test'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'نامعتبر')
    
    def test_submit_lead_form_empty_phone(self):
        """Empty phone should show error"""
        response = self.client.post('/leads/register/', {
            'phone': '',
            'name': 'Test'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'الزامی')
    
    def test_submit_duplicate_lead_shows_error(self):
        """Duplicate pending lead should show error"""
        Lead.objects.create(
            phone='09123333333',
            product=self.product,
            status=Lead.LeadStatus.PENDING
        )
        
        response = self.client.post(f'/leads/register/{self.product.slug}/', {
            'phone': '09123333333'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'قبلاً')


class LeadAPIViewTest(TestCase):
    """Test lead API endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-api-lead')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product-api-lead',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
    
    def test_api_submit_lead_success(self):
        """API should create lead and return success"""
        response = self.client.post('/leads/api/submit/', {
            'phone': '09124444444',
            'name': 'API User'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('lead_id', data)
    
    def test_api_submit_with_product_slug(self):
        """API should accept product_slug"""
        response = self.client.post('/leads/api/submit/', {
            'phone': '09125555555',
            'product_slug': self.product.slug
        })
        
        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.filter(phone='09125555555').first()
        self.assertEqual(lead.product, self.product)
    
    def test_api_invalid_phone_returns_400(self):
        """Invalid phone should return 400"""
        response = self.client.post('/leads/api/submit/', {
            'phone': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_api_nonexistent_product_returns_404(self):
        """Non-existent product slug should return 404"""
        response = self.client.post('/leads/api/submit/', {
            'phone': '09126666666',
            'product_slug': 'nonexistent-slug'
        })
        
        self.assertEqual(response.status_code, 404)
