"""
Integration tests for Order-Inventory integration.
Tests the complete flow: cart -> order -> payment -> return
Per D-045, D-080, INVENTORY-FLOW.md

Uses Django's test client for real session support.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from src.modules.catalog.models import Category, Supplier, Product, Inventory
from src.modules.catalog.services.inventory_service import InventoryService
from src.modules.catalog.services.exceptions import InsufficientStockError
from src.modules.order.models import Cart, Order
from src.modules.order.services import (
    get_or_create_cart,
    add_to_cart,
    create_order_from_cart,
    confirm_payment,
    cancel_order,
)
from src.modules.order.checkout_service import CheckoutService

User = get_user_model()


class OrderInventoryIntegrationTestCase(TestCase):
    """Integration tests for Order-Inventory flow per D-045."""
    
    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name='Integration Test',
            slug='integration-test',
        )
        
        self.supplier = Supplier.objects.create(
            title='Test Supplier',
            city='Tehran',
        )
        
        self.product_a = Product.objects.create(
            name='Product A',
            slug='product-a',
            category=self.category,
            supplier=self.supplier,
            unit='kg',
            base_price=Decimal('100.00'),
            shipping_cost=Decimal('10.00'),
            margin_percent=Decimal('20.00'),
            short_description='Test A',
            origin_story='Origin A',
        )
        
        self.product_b = Product.objects.create(
            name='Product B',
            slug='product-b',
            category=self.category,
            supplier=self.supplier,
            unit='number',
            base_price=Decimal('50.00'),
            shipping_cost=Decimal('5.00'),
            margin_percent=Decimal('15.00'),
            short_description='Test B',
            origin_story='Origin B',
        )
        
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
        )
        
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass',
        )
    
    def _get_cart_for_user(self, user):
        """Helper to get or create cart for a user."""
        # Use a mock request with proper session
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        
        factory = RequestFactory()
        request = factory.get('/')
        
        # Add session middleware to request
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        
        request.user = user
        return get_or_create_cart(request)
    
    def _get_cart_for_guest(self):
        """Helper to get or create cart for guest."""
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        
        factory = RequestFactory()
        request = factory.get('/')
        
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        
        # Anonymous user
        request.user = type('AnonymousUser', (), {'is_authenticated': False})()
        return get_or_create_cart(request)
    
    # ========================================================================
    # CART TESTS (No reservation at cart add - D-045)
    # ========================================================================
    
    def test_add_to_cart_checks_availability_not_reserves(self):
        """Adding to cart checks availability but does NOT reserve."""
        InventoryService.add_stock(self.product_a, Decimal('10'))
        
        cart = self._get_cart_for_user(self.user)
        item = add_to_cart(cart, self.product_a.id, quantity=5)
        
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(item.quantity, 5)
        
        inventory = Inventory.objects.get(product=self.product_a)
        self.assertEqual(inventory.quantity, Decimal('10'))
        self.assertEqual(inventory.reserved_quantity, Decimal('0'))
        self.assertEqual(inventory.available_quantity, Decimal('10'))
    
    def test_add_to_cart_fails_when_insufficient_stock(self):
        """Adding to cart fails if stock is insufficient."""
        InventoryService.add_stock(self.product_a, Decimal('3'))
        
        cart = self._get_cart_for_user(self.user)
        
        with self.assertRaises(ValidationError):
            add_to_cart(cart, self.product_a.id, quantity=5)
    
    # ========================================================================
    # ORDER CREATION TESTS (Reservation at order create - D-045)
    # ========================================================================
    
    def test_create_order_reserves_stock(self):
        """Creating order reserves stock per D-045."""
        InventoryService.add_stock(self.product_a, Decimal('10'))
        
        cart = self._get_cart_for_user(self.user)
        add_to_cart(cart, self.product_a.id, quantity=3)
        
        order = create_order_from_cart(cart, user=self.user)
        
        self.assertEqual(order.status, Order.OrderStatus.PENDING)
        
        inventory = Inventory.objects.get(product=self.product_a)
        self.assertEqual(inventory.quantity, Decimal('10'))
        self.assertEqual(inventory.reserved_quantity, Decimal('3'))
        self.assertEqual(inventory.available_quantity, Decimal('7'))
    
    def test_create_order_fails_with_insufficient_stock(self):
        """Order creation fails if stock insufficient at reserve time."""
        InventoryService.add_stock(self.product_a, Decimal('2'))
        
        cart = self._get_cart_for_user(self.user)
        add_to_cart(cart, self.product_a.id, quantity=2)
        
        # Reduce stock after adding to cart
        inventory = Inventory.objects.get(product=self.product_a)
        inventory.quantity = Decimal('1')
        inventory.save()
        
        with self.assertRaises(InsufficientStockError):
            create_order_from_cart(cart, user=self.user)
    
    # ========================================================================
    # PAYMENT CONFIRMATION TESTS
    # ========================================================================
    
    def test_confirm_payment_converts_reservation_to_sale(self):
        """Confirming payment converts reservation to sale."""
        InventoryService.add_stock(self.product_a, Decimal('10'))
        
        cart = self._get_cart_for_user(self.user)
        add_to_cart(cart, self.product_a.id, quantity=3)
        
        order = create_order_from_cart(cart, user=self.user)
        order = confirm_payment(order, admin_user=self.admin)
        
        # D-105: پس از تایید، مرسوله‌ها خودکار ساخته و سفارش «در حال آماده‌سازی» می‌شود
        self.assertEqual(order.status, Order.OrderStatus.PROCESSING)
        self.assertTrue(order.shipments.count() >= 1)
        
        inventory = Inventory.objects.get(product=self.product_a)
        self.assertEqual(inventory.quantity, Decimal('7'))
        self.assertEqual(inventory.reserved_quantity, Decimal('0'))
        self.assertEqual(inventory.available_quantity, Decimal('7'))
    
    # ========================================================================
    # ORDER CANCELLATION TESTS
    # ========================================================================
    
    def test_cancel_order_releases_reservation(self):
        """Cancelling order releases reservation."""
        InventoryService.add_stock(self.product_a, Decimal('10'))
        
        cart = self._get_cart_for_user(self.user)
        add_to_cart(cart, self.product_a.id, quantity=3)
        
        order = create_order_from_cart(cart, user=self.user)
        order = cancel_order(order, reason='Test cancellation')
        
        self.assertEqual(order.status, Order.OrderStatus.CANCELLED)
        
        inventory = Inventory.objects.get(product=self.product_a)
        self.assertEqual(inventory.quantity, Decimal('10'))
        self.assertEqual(inventory.reserved_quantity, Decimal('0'))
        self.assertEqual(inventory.available_quantity, Decimal('10'))
    
    # ========================================================================
    # RETURN TESTS
    # ========================================================================
    
    def test_return_stock_after_payment(self):
        """Returning stock after payment adds back to inventory."""
        InventoryService.add_stock(self.product_a, Decimal('10'))
        
        cart = self._get_cart_for_user(self.user)
        add_to_cart(cart, self.product_a.id, quantity=3)
        
        order = create_order_from_cart(cart, user=self.user)
        order = confirm_payment(order, admin_user=self.admin)
        
        order = CheckoutService.process_return(
            order=order,
            items_to_return=[
                {'product': self.product_a, 'quantity': 1},
            ],
            reason='Customer changed mind',
            admin_user=self.admin,
        )
        
        inventory = Inventory.objects.get(product=self.product_a)
        self.assertEqual(inventory.quantity, Decimal('8'))
    
    # ========================================================================
    # MULTI-PRODUCT TESTS
    # ========================================================================
    
    def test_multi_product_order(self):
        """Test order with multiple products."""
        InventoryService.add_stock(self.product_a, Decimal('10'))
        InventoryService.add_stock(self.product_b, Decimal('5'))
        
        cart = self._get_cart_for_user(self.user)
        add_to_cart(cart, self.product_a.id, quantity=3)
        add_to_cart(cart, self.product_b.id, quantity=2)
        
        order = create_order_from_cart(cart, user=self.user)
        order = confirm_payment(order, admin_user=self.admin)
        
        inv_a = Inventory.objects.get(product=self.product_a)
        inv_b = Inventory.objects.get(product=self.product_b)
        
        self.assertEqual(inv_a.quantity, Decimal('7'))
        self.assertEqual(inv_b.quantity, Decimal('3'))
    
    # ========================================================================
    # GUEST CHECKOUT TESTS
    # ========================================================================
    
    def test_guest_checkout(self):
        """Test guest checkout flow."""
        InventoryService.add_stock(self.product_a, Decimal('10'))
        
        cart = self._get_cart_for_guest()
        add_to_cart(cart, self.product_a.id, quantity=2)
        
        guest_info = {
            'name': 'Guest User',
            'phone': '09121234567',
            'address': 'Tehran, Test Street',
            'postal_code': '1234567890',
        }
        
        order = create_order_from_cart(cart, guest_info=guest_info)
        
        self.assertEqual(order.guest_name, 'Guest User')
        self.assertEqual(order.guest_phone, '09121234567')
        self.assertIsNone(order.user)
        self.assertEqual(order.status, Order.OrderStatus.PENDING)
