"""
Order Module Services
Integrated with InventoryService per D-045, D-080, INVENTORY-FLOW.md

Key changes from original:
- Uses InventoryService for stock operations (not product.stock_quantity)
- Reserves stock at order creation (not direct deduction)
- Follows D-045 flow: cart add (no reserve) -> order create (reserve) -> payment confirm (sale)
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from src.modules.catalog.models import Product
from src.modules.catalog.services.inventory_service import InventoryService
from src.modules.catalog.services.exceptions import (
    InsufficientStockError,
    ProductNotFoundError,
)
from .models import Cart, CartItem, Order, OrderItem


def get_or_create_cart(request):
    """Get or create cart - Session-based (ADR-002)"""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    
    user = request.user if request.user.is_authenticated else None
    
    # Priority: logged-in user cart, then session cart
    if user:
        cart = Cart.objects.filter(user=user, is_active=True).first()
        if not cart:
            # Merge guest cart with user cart
            guest_cart = Cart.objects.filter(session_key=session_key, is_active=True).first()
            if guest_cart:
                guest_cart.user = user
                guest_cart.session_key = ''
                guest_cart.save()
                return guest_cart
            cart = Cart.objects.create(user=user)
        return cart
    
    cart, created = Cart.objects.get_or_create(
        session_key=session_key,
        user=None,
        is_active=True
    )
    return cart


def add_to_cart(cart, product_id, quantity=1):
    """
    Add item to cart with availability check.
    Per D-045: NO reservation at cart add - only check availability.
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ValidationError("Product not found")
    
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1")
    
    # Check availability via InventoryService (NOT reservation)
    available = InventoryService.get_available_stock(product)
    
    existing_item = CartItem.objects.filter(cart=cart, product=product).first()
    new_quantity = (existing_item.quantity + quantity) if existing_item else quantity
    
    if available < new_quantity:
        raise ValidationError(
            f"Insufficient stock. Maximum available: {available}"
        )
    
    if existing_item:
        existing_item.quantity = new_quantity
        existing_item.unit_price_at_add = product.final_price
        existing_item.save()
        return existing_item
    else:
        return CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            unit_price_at_add=product.final_price
        )


def update_cart_item(cart, item_id, quantity):
    """Update item quantity with availability check."""
    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
    except CartItem.DoesNotExist:
        raise ValidationError("Item not found in cart")
    
    if quantity < 1:
        item.delete()
        return None
    
    available = InventoryService.get_available_stock(item.product)
    if available < quantity:
        raise ValidationError(
            f"Insufficient stock. Maximum available: {available}"
        )
    
    item.quantity = quantity
    item.save()
    return item


def remove_from_cart(cart, item_id):
    """Remove item from cart."""
    CartItem.objects.filter(id=item_id, cart=cart).delete()


def create_order_from_cart(cart, guest_info=None, user=None):
    """
    Create final order from cart.
    
    Per D-045:
    - Reservation happens ONLY at order creation (not at cart add)
    - 24-hour reservation timeout
    - Inventory managed via InventoryService
    
    This function:
    1. Creates Order and OrderItems (with product snapshots per ADR-002)
    2. Reserves stock via InventoryService
    3. Sets status to PENDING (awaiting payment)
    4. Deactivates cart
    
    Returns:
        Created Order instance
        
    Raises:
        ValidationError: If cart is empty or stock insufficient
        InsufficientStockError: If any product lacks stock
    """
    from .checkout_service import CheckoutService
    
    return CheckoutService.create_order(
        cart=cart,
        guest_info=guest_info,
        user=user,
    )


def confirm_payment(order, payment_data=None, admin_user=None):
    """
    Confirm payment and convert reservation to sale.
    
    Called after admin verifies payment receipt (D-045 flow).
    
    Args:
        order: Order instance
        payment_data: Optional payment info
        admin_user: User confirming the payment
        
    Returns:
        Updated Order with PAID status
    """
    from .checkout_service import CheckoutService
    
    return CheckoutService.confirm_payment(order, payment_data, admin_user)


def cancel_order(order, reason='Customer request', user=None):
    """
    Cancel order and release reservation.
    
    Args:
        order: Order instance
        reason: Reason for cancellation
        user: User performing cancellation
        
    Returns:
        Updated Order with CANCELLED status
    """
    from .checkout_service import CheckoutService
    
    return CheckoutService.cancel_order(order, reason, user)
