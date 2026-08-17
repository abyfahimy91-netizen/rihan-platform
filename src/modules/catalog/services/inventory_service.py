"""
Inventory Service - Central API for all inventory operations.
Based on:
- ADR-002 (Database architecture)
- D-045 (Inventory flow)
- INVENTORY-FLOW.md (Business rules)

This service:
1. Handles all stock changes with full transaction logging
2. Prevents oversell through reservation system
3. Emits hooks for other modules to react
4. Provides clean API for other modules (Order, Admin, Supplier)

Key rules (from INVENTORY-FLOW.md):
- Humans add stock, system controls it
- Reservation happens ONLY at order creation (not at cart add)
- 24-hour reservation timeout
- Full audit log via InventoryTransaction
"""
import logging
from decimal import Decimal
from typing import List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from ..models import Product, Inventory, InventoryTransaction
from .exceptions import (
    InventoryError,
    InsufficientStockError,
    InventoryValidationError,
    ReservationError,
    ProductNotFoundError,
)

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Central service for all inventory operations.
    
    All operations are atomic (wrapped in transactions) and fully logged
    via InventoryTransaction records.
    
    Usage:
        service = InventoryService()
        service.add_stock(product, Decimal('10'), 'Initial stock', user=admin_user)
    """
    
    # ========================================================================
    # STOCK ADDITION (Manual - per D-045)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def add_stock(
        cls,
        product: Product,
        quantity: Decimal,
        reason: str = 'Manual addition',
        user=None,
        reference_type: str = '',
        reference_id=None,
    ) -> InventoryTransaction:
        """
        Add stock to a product (manual operation).
        
        Per D-045: Humans add stock, system only controls it.
        
        Args:
            product: Product to add stock to
            quantity: Amount to add (must be positive)
            reason: Human-readable reason for the addition
            user: User performing the operation (for audit log)
            reference_type: Optional reference (e.g., 'purchase_order')
            reference_id: Optional reference ID
            
        Returns:
            Created InventoryTransaction
            
        Raises:
            InventoryValidationError: If quantity is invalid
            ProductNotFoundError: If product has no inventory
        """
        if quantity <= 0:
            raise InventoryValidationError(
                f"Quantity must be positive, got {quantity}"
            )
        
        try:
            inventory = Inventory.objects.select_for_update().get(product=product)
        except Inventory.DoesNotExist:
            raise ProductNotFoundError(str(product))
        
        # Record before state
        stock_before = inventory.quantity
        
        # Perform the addition
        inventory.add_stock(quantity)
        
        # Create audit log
        txn = InventoryTransaction.create_transaction(
            inventory=inventory,
            change_type='purchase',
            quantity_change=quantity,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            user=user,
        )
        
        # Update transaction with accurate before/after
        txn.stock_before = stock_before
        txn.stock_after = inventory.quantity
        txn.save()
        
        logger.info(
            f"Stock added: {product.name} +{quantity} by {user or 'system'}"
        )
        
        # Emit hook for other modules
        cls._emit_hook('INVENTORY_ADDED', {
            'product': product,
            'inventory': inventory,
            'transaction': txn,
        })
        
        # Check low stock warning
        cls._check_low_stock(inventory)
        
        return txn
    
    # ========================================================================
    # RESERVATION (Per D-045: Only at order creation, 24h timeout)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def reserve_for_order(
        cls,
        order_items: List[dict],
        user=None,
        order_id=None,
    ) -> List[InventoryTransaction]:
        """
        Reserve stock for an order (called when order is created).
        
        Per D-045:
        - Reservation happens ONLY at order creation (not at cart add)
        - 24-hour reservation timeout
        - Prevents oversell
        
        Args:
            order_items: List of dicts with keys:
                - 'product': Product instance
                - 'quantity': Decimal quantity
            user: User creating the order
            order_id: Order ID (for reference)
            
        Returns:
            List of created InventoryTransactions
            
        Raises:
            InsufficientStockError: If any product lacks sufficient stock
        """
        if not order_items:
            return []
        
        transactions = []
        
        # First pass: validate all items have sufficient stock
        for item in order_items:
            product = item['product']
            quantity = item['quantity']
            
            try:
                inventory = Inventory.objects.select_for_update().get(product=product)
            except Inventory.DoesNotExist:
                raise ProductNotFoundError(str(product))
            
            if not inventory.can_reserve(quantity):
                raise InsufficientStockError(
                    product_name=str(product),
                    requested=quantity,
                    available=inventory.available_quantity,
                )
        
        # Second pass: perform reservations
        for item in order_items:
            product = item['product']
            quantity = item['quantity']
            
            inventory = Inventory.objects.select_for_update().get(product=product)
            stock_before = inventory.quantity
            
            inventory.reserve(quantity)
            
            txn = InventoryTransaction.create_transaction(
                inventory=inventory,
                change_type='reservation',
                quantity_change=quantity,
                reason=f'Reserved for order {order_id}',
                reference_type='order',
                reference_id=order_id,
                user=user,
            )
            
            txn.stock_before = stock_before
            txn.stock_after = inventory.quantity
            txn.save()
            
            transactions.append(txn)
            
            logger.info(
                f"Stock reserved: {product.name} {quantity} for order {order_id}"
            )
        
        # Emit hook
        cls._emit_hook('INVENTORY_RESERVED', {
            'order_id': order_id,
            'transactions': transactions,
        })
        
        return transactions
    
    # ========================================================================
    # CONFIRM SALE (After payment verified)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def confirm_sale(
        cls,
        order_items: List[dict],
        user=None,
        order_id=None,
    ) -> List[InventoryTransaction]:
        """
        Confirm sale - convert reservation to actual sale.
        
        Called after admin verifies payment (D-045 flow).
        
        Args:
            order_items: List of dicts with 'product' and 'quantity'
            user: User confirming the sale (usually admin)
            order_id: Order ID for reference
            
        Returns:
            List of InventoryTransactions
        """
        transactions = []
        
        for item in order_items:
            product = item['product']
            quantity = item['quantity']
            
            try:
                inventory = Inventory.objects.select_for_update().get(product=product)
            except Inventory.DoesNotExist:
                raise ProductNotFoundError(str(product))
            
            stock_before = inventory.quantity
            
            # Confirm sale: reduce both quantity and reserved_quantity
            inventory.confirm_sale(quantity)
            
            txn = InventoryTransaction.create_transaction(
                inventory=inventory,
                change_type='sale',
                quantity_change=-quantity,
                reason=f'Sale confirmed for order {order_id}',
                reference_type='order',
                reference_id=order_id,
                user=user,
            )
            
            txn.stock_before = stock_before
            txn.stock_after = inventory.quantity
            txn.save()
            
            transactions.append(txn)
            
            logger.info(
                f"Sale confirmed: {product.name} -{quantity} for order {order_id}"
            )
            
            cls._check_low_stock(inventory)
        
        cls._emit_hook('INVENTORY_SOLD', {
            'order_id': order_id,
            'transactions': transactions,
        })
        
        return transactions
    
    # ========================================================================
    # RELEASE RESERVATION (Cancel order or timeout)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def release_reservation(
        cls,
        order_items: List[dict],
        user=None,
        order_id=None,
        reason: str = 'Order cancelled',
    ) -> List[InventoryTransaction]:
        """
        Release reserved stock (order cancelled or 24h timeout).
        
        Args:
            order_items: List of dicts with 'product' and 'quantity'
            user: User releasing (admin or system)
            order_id: Order ID
            reason: Reason for release
            
        Returns:
            List of InventoryTransactions
        """
        transactions = []
        
        for item in order_items:
            product = item['product']
            quantity = item['quantity']
            
            try:
                inventory = Inventory.objects.select_for_update().get(product=product)
            except Inventory.DoesNotExist:
                raise ProductNotFoundError(str(product))
            
            stock_before = inventory.quantity
            
            inventory.release_reservation(quantity)
            
            txn = InventoryTransaction.create_transaction(
                inventory=inventory,
                change_type='release',
                quantity_change=Decimal('0'),  # Physical stock unchanged
                reason=f'{reason} (order {order_id})',
                reference_type='order',
                reference_id=order_id,
                user=user,
            )
            
            txn.stock_before = stock_before
            txn.stock_after = inventory.quantity
            txn.save()
            
            transactions.append(txn)
            
            logger.info(
                f"Reservation released: {product.name} {quantity} for order {order_id}"
            )
        
        cls._emit_hook('INVENTORY_RELEASED', {
            'order_id': order_id,
            'transactions': transactions,
            'reason': reason,
        })
        
        return transactions
    
    # ========================================================================
    # RETURN STOCK (After return approved)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def return_stock(
        cls,
        order_items: List[dict],
        user=None,
        order_id=None,
        reason: str = 'Customer return',
    ) -> List[InventoryTransaction]:
        """
        Return stock to inventory (after return is approved by admin).
        
        Args:
            order_items: List of dicts with 'product' and 'quantity'
            user: User approving the return
            order_id: Original order ID
            reason: Reason for return
            
        Returns:
            List of InventoryTransactions
        """
        transactions = []
        
        for item in order_items:
            product = item['product']
            quantity = item['quantity']
            
            try:
                inventory = Inventory.objects.select_for_update().get(product=product)
            except Inventory.DoesNotExist:
                raise ProductNotFoundError(str(product))
            
            stock_before = inventory.quantity
            
            inventory.return_stock(quantity)
            
            txn = InventoryTransaction.create_transaction(
                inventory=inventory,
                change_type='return',
                quantity_change=quantity,
                reason=f'{reason} (order {order_id})',
                reference_type='order',
                reference_id=order_id,
                user=user,
            )
            
            txn.stock_before = stock_before
            txn.stock_after = inventory.quantity
            txn.save()
            
            transactions.append(txn)
            
            logger.info(
                f"Stock returned: {product.name} +{quantity} for order {order_id}"
            )
        
        cls._emit_hook('INVENTORY_RETURNED', {
            'order_id': order_id,
            'transactions': transactions,
        })
        
        return transactions
    
    # ========================================================================
    # STOCK ADJUSTMENT (Inventory reconciliation)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def adjust_stock(
        cls,
        product: Product,
        new_quantity: Decimal,
        reason: str = 'Inventory adjustment',
        user=None,
    ) -> InventoryTransaction:
        """
        Adjust stock to match physical count (inventory reconciliation).
        
        Args:
            product: Product to adjust
            new_quantity: Actual physical count
            reason: Reason for adjustment
            user: User performing adjustment
            
        Returns:
            Created InventoryTransaction
        """
        try:
            inventory = Inventory.objects.select_for_update().get(product=product)
        except Inventory.DoesNotExist:
            raise ProductNotFoundError(str(product))
        
        stock_before = inventory.quantity
        change = new_quantity - stock_before
        
        # Update quantity directly
        inventory.quantity = new_quantity
        inventory.save()
        
        change_type = 'adjustment'
        
        txn = InventoryTransaction.create_transaction(
            inventory=inventory,
            change_type=change_type,
            quantity_change=change,
            reason=reason,
            reference_type='adjustment',
            reference_id=None,
            user=user,
        )
        
        txn.stock_before = stock_before
        txn.stock_after = new_quantity
        txn.save()
        
        logger.info(
            f"Stock adjusted: {product.name} {stock_before} -> {new_quantity}"
        )
        
        cls._check_low_stock(inventory)
        
        return txn
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    @classmethod
    def check_availability(cls, product: Product, quantity: Decimal) -> bool:
        """Check if product has enough available stock."""
        try:
            inventory = Inventory.objects.get(product=product)
            return inventory.can_reserve(quantity)
        except Inventory.DoesNotExist:
            return False
    
    @classmethod
    def get_available_stock(cls, product: Product) -> Decimal:
        """Get available stock for a product."""
        try:
            inventory = Inventory.objects.get(product=product)
            return inventory.available_quantity
        except Inventory.DoesNotExist:
            return Decimal('0')
    
    @classmethod
    def get_low_stock_products(cls) -> List[Inventory]:
        """Get all products with low stock."""
        low_stock = []
        for inventory in Inventory.objects.select_related('product').all():
            if inventory.is_low_stock:
                low_stock.append(inventory)
        return low_stock
    
    @classmethod
    def get_product_history(
        cls,
        product: Product,
        limit: int = 50,
    ) -> List[InventoryTransaction]:
        """Get transaction history for a product."""
        try:
            inventory = Inventory.objects.get(product=product)
            return list(
                inventory.transactions.all()[:limit]
            )
        except Inventory.DoesNotExist:
            return []
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    @classmethod
    def _emit_hook(cls, hook_name: str, data: dict):
        """Emit hook to HookSystem (if available)."""
        try:
            from src.core.hooks import hooks
            # Use getattr with safe default to avoid import errors
            hook_attr = getattr(hooks, 'fire', None)
            if hook_attr and callable(hook_attr):
                hook_attr(hook_name, **data)
        except Exception as e:
            logger.debug(f"Hook emission failed for {hook_name}: {e}")
    
    @classmethod
    def _check_low_stock(cls, inventory: Inventory):
        """Check and emit low stock warning."""
        if inventory.is_low_stock:
            logger.warning(
                f"Low stock alert: {inventory.product.name} - "
                f"{inventory.available_quantity} remaining"
            )
            cls._emit_hook('INVENTORY_LOW_STOCK', {
                'product': inventory.product,
                'inventory': inventory,
                'available': inventory.available_quantity,
            })
