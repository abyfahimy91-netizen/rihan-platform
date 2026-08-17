"""
Tests for InventoryService.
Validates all inventory operations per ADR-002 and INVENTORY-FLOW.md.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from src.modules.catalog.models import Category, Supplier, Product, Inventory
from src.modules.catalog.services.inventory_service import InventoryService
from src.modules.catalog.services.exceptions import (
    InsufficientStockError,
    InventoryValidationError,
    ProductNotFoundError,
)

User = get_user_model()


class InventoryServiceTestCase(TestCase):
    """Test suite for InventoryService."""
    
    def setUp(self):
        """Create test data."""
        # Create category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
        )
        
        # Create supplier
        self.supplier = Supplier.objects.create(
            title='Test Supplier',
            city='Tehran',
        )
        
        # Create product (Inventory auto-created by signal)
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            supplier=self.supplier,
            unit='kg',
            base_price=Decimal('100.00'),
            shipping_cost=Decimal('10.00'),
            margin_percent=Decimal('20.00'),
            short_description='Test product',
            origin_story='Test origin',
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
        )
    
    # ========================================================================
    # ADD STOCK TESTS
    # ========================================================================
    
    def test_add_stock_basic(self):
        """Test basic stock addition."""
        txn = InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial stock',
            user=self.user,
        )
        
        inventory = Inventory.objects.get(product=self.product)
        self.assertEqual(inventory.quantity, Decimal('10'))
        self.assertEqual(inventory.reserved_quantity, Decimal('0'))
        self.assertEqual(inventory.available_quantity, Decimal('10'))
        
        self.assertEqual(txn.change_type, 'purchase')
        self.assertEqual(txn.quantity_change, Decimal('10'))
        self.assertEqual(txn.created_by, self.user)
    
    def test_add_stock_negative_quantity_raises(self):
        """Test that negative quantity raises error."""
        with self.assertRaises(InventoryValidationError):
            InventoryService.add_stock(
                product=self.product,
                quantity=Decimal('-5'),
                reason='Invalid',
            )
    
    def test_add_stock_zero_quantity_raises(self):
        """Test that zero quantity raises error."""
        with self.assertRaises(InventoryValidationError):
            InventoryService.add_stock(
                product=self.product,
                quantity=Decimal('0'),
                reason='Invalid',
            )
    
    # ========================================================================
    # RESERVATION TESTS
    # ========================================================================
    
    def test_reserve_for_order_success(self):
        """Test successful reservation."""
        # Add stock first
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial',
        )
        
        # Reserve 3 units
        transactions = InventoryService.reserve_for_order(
            order_items=[
                {'product': self.product, 'quantity': Decimal('3')},
            ],
            user=self.user,
            order_id='test-order-1',
        )
        
        self.assertEqual(len(transactions), 1)
        
        inventory = Inventory.objects.get(product=self.product)
        self.assertEqual(inventory.quantity, Decimal('10'))  # Unchanged
        self.assertEqual(inventory.reserved_quantity, Decimal('3'))
        self.assertEqual(inventory.available_quantity, Decimal('7'))
    
    def test_reserve_insufficient_stock_raises(self):
        """Test that reserving more than available raises error."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('5'),
            reason='Initial',
        )
        
        with self.assertRaises(InsufficientStockError) as cm:
            InventoryService.reserve_for_order(
                order_items=[
                    {'product': self.product, 'quantity': Decimal('10')},
                ],
                order_id='test-order',
            )
        
        self.assertEqual(cm.exception.requested, Decimal('10'))
        self.assertEqual(cm.exception.available, Decimal('5'))
    
    # ========================================================================
    # CONFIRM SALE TESTS
    # ========================================================================
    
    def test_confirm_sale_success(self):
        """Test confirming a sale after payment."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial',
        )
        
        InventoryService.reserve_for_order(
            order_items=[
                {'product': self.product, 'quantity': Decimal('3')},
            ],
            order_id='order-1',
        )
        
        # Confirm sale
        transactions = InventoryService.confirm_sale(
            order_items=[
                {'product': self.product, 'quantity': Decimal('3')},
            ],
            user=self.user,
            order_id='order-1',
        )
        
        inventory = Inventory.objects.get(product=self.product)
        self.assertEqual(inventory.quantity, Decimal('7'))  # Reduced
        self.assertEqual(inventory.reserved_quantity, Decimal('0'))  # Released
        self.assertEqual(inventory.available_quantity, Decimal('7'))
        
        self.assertEqual(transactions[0].change_type, 'sale')
    
    # ========================================================================
    # RELEASE RESERVATION TESTS
    # ========================================================================
    
    def test_release_reservation_success(self):
        """Test releasing reservation (cancelled order)."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial',
        )
        
        InventoryService.reserve_for_order(
            order_items=[
                {'product': self.product, 'quantity': Decimal('3')},
            ],
            order_id='order-cancel',
        )
        
        # Release reservation
        transactions = InventoryService.release_reservation(
            order_items=[
                {'product': self.product, 'quantity': Decimal('3')},
            ],
            order_id='order-cancel',
            reason='Customer cancelled',
        )
        
        inventory = Inventory.objects.get(product=self.product)
        self.assertEqual(inventory.quantity, Decimal('10'))  # Unchanged
        self.assertEqual(inventory.reserved_quantity, Decimal('0'))  # Released
        self.assertEqual(inventory.available_quantity, Decimal('10'))
    
    # ========================================================================
    # RETURN STOCK TESTS
    # ========================================================================
    
    def test_return_stock_success(self):
        """Test returning stock after customer return."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial',
        )
        
        # Simulate sale
        InventoryService.reserve_for_order(
            order_items=[
                {'product': self.product, 'quantity': Decimal('3')},
            ],
            order_id='order-return',
        )
        InventoryService.confirm_sale(
            order_items=[
                {'product': self.product, 'quantity': Decimal('3')},
            ],
            order_id='order-return',
        )
        
        # Return stock
        transactions = InventoryService.return_stock(
            order_items=[
                {'product': self.product, 'quantity': Decimal('1')},
            ],
            order_id='order-return',
            reason='Customer return',
        )
        
        inventory = Inventory.objects.get(product=self.product)
        self.assertEqual(inventory.quantity, Decimal('8'))  # 10 - 3 + 1
    
    # ========================================================================
    # ADJUSTMENT TESTS
    # ========================================================================
    
    def test_adjust_stock_success(self):
        """Test stock adjustment for reconciliation."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial',
        )
        
        # Adjust to actual physical count
        txn = InventoryService.adjust_stock(
            product=self.product,
            new_quantity=Decimal('8'),
            reason='Physical count adjustment',
            user=self.user,
        )
        
        inventory = Inventory.objects.get(product=self.product)
        self.assertEqual(inventory.quantity, Decimal('8'))
        self.assertEqual(txn.change_type, 'adjustment')
        self.assertEqual(txn.quantity_change, Decimal('-2'))
    
    # ========================================================================
    # QUERY METHOD TESTS
    # ========================================================================
    
    def test_check_availability_true(self):
        """Test availability check with sufficient stock."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial',
        )
        
        self.assertTrue(
            InventoryService.check_availability(self.product, Decimal('5'))
        )
    
    def test_check_availability_false(self):
        """Test availability check with insufficient stock."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('5'),
            reason='Initial',
        )
        
        self.assertFalse(
            InventoryService.check_availability(self.product, Decimal('10'))
        )
    
    def test_get_low_stock_products(self):
        """Test low stock product query."""
        # Add only 1 unit (low stock threshold is 2 by default)
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('1'),
            reason='Initial',
        )
        
        low_stock = InventoryService.get_low_stock_products()
        product_ids = [inv.product.id for inv in low_stock]
        self.assertIn(self.product.id, product_ids)
    
    def test_get_product_history(self):
        """Test transaction history retrieval."""
        InventoryService.add_stock(
            product=self.product,
            quantity=Decimal('10'),
            reason='Initial',
        )
        
        history = InventoryService.get_product_history(self.product)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].change_type, 'purchase')
