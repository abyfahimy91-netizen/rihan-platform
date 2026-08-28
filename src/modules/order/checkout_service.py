"""
CheckoutService - Central orchestrator for order creation and fulfillment.

Based on:
- D-045 (Inventory flow)
- D-080 (Order architecture)
- INVENTORY-FLOW.md (Business rules)

Flow:
1. Cart -> Order (DRAFT -> PENDING): Reserve stock via InventoryService
2. PENDING -> PAID: Confirm sale via InventoryService (after payment)
3. PENDING -> CANCELLED: Release reservation via InventoryService
4. 24-hour timeout: Auto-release reservation (future enhancement)
"""
import logging
from datetime import timedelta
from decimal import Decimal
from typing import List, Optional, Dict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from src.modules.order.variant_dispatch import InventoryService
from src.modules.catalog.services.exceptions import (
    InsufficientStockError,
    ProductNotFoundError,
)
from .models import Cart, CartItem, Order, OrderItem, Payment

logger = logging.getLogger(__name__)


class CheckoutService:
    """
    Orchestrates order creation with inventory management.
    
    All operations are atomic and fully logged via:
    - InventoryTransaction (in catalog module)
    - Payment records (in order module)
    - Order status transitions
    """
    
    # ========================================================================
    # ORDER CREATION (Reserve stock)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def create_order(
        cls,
        cart: Cart,
        guest_info: Optional[Dict] = None,
        user=None,
    ) -> Order:
        """
        Create order from cart with inventory reservation.
        
        Args:
            cart: Cart instance
            guest_info: Optional dict with guest info
            user: User instance (for logged-in users)
            
        Returns:
            Created Order with PENDING status
            
        Raises:
            ValidationError: If cart is empty
            InsufficientStockError: If any item lacks stock
        """
        from django.core.exceptions import ValidationError
        
        if not cart.items.exists():
            raise ValidationError("سبد خرید شما خالی است؛ ابتدا محصولی به سبد اضافه بفرمایید.")
        
        # Step 1: Prepare order items data for reservation
        order_items_data = []
        for cart_item in cart.items.all():
            order_items_data.append({
                'product': cart_item.product,
                'quantity': Decimal(str(cart_item.quantity)),
                'unit_price': cart_item.unit_price_at_add,
                'snapshot_name': cart_item.product.name,
                'variant': cart_item.variant,
                # D-113: snapshot قیمت خرید برای گزارش سود (None برای سبد قدیمی بدون واریانت)
                'unit_cost': (cart_item.variant.cost_price
                              if cart_item.variant is not None else None),
            })
        
        # Step 2: Create Order with DRAFT status first
        guest_info = guest_info or {}
        order = Order.objects.create(
            user=user or cart.user,
            session_key=cart.session_key if not (user or cart.user) else '',
            status=Order.OrderStatus.DRAFT,
            guest_name=guest_info.get('name', ''),
            guest_phone=guest_info.get('phone', ''),
            guest_address=guest_info.get('address', ''),
            guest_postal_code=guest_info.get('postal_code', ''),
            shipping_cost=Decimal(str(guest_info.get('shipping_cost', 0))),
        )
        
        # Step 3: Create OrderItems with product snapshots (ADR-002)
        for item_data in order_items_data:
            OrderItem.objects.create(
                order=order,
                product=item_data['product'],
                product_name_snapshot=item_data['snapshot_name'],
                variant=item_data['variant'],
                variant_title=(item_data['variant'].title if item_data['variant'] else ''),
                quantity=item_data['quantity'],
                unit_price_at_purchase=item_data['unit_price'],
                unit_cost_at_purchase=item_data.get('unit_cost'),
            )
        
        # Step 4: Calculate totals
        order.calculate_totals()
        
        # Step 5: Reserve stock via InventoryService
        try:
            reservation_items = [
                {'product': d['product'], 'quantity': d['quantity'],
                 'variant': d.get('variant')}
                for d in order_items_data
            ]
            InventoryService.reserve_for_order(
                order_items=reservation_items,
                user=user,
                order_id=str(order.order_number),
            )
        except (InsufficientStockError, ProductNotFoundError) as e:
            # Rollback: delete order and items
            order.delete()
            raise
        
        # Step 6: Update status to PENDING + مهلت رزرو موجودی (D-099)
        order.status = Order.OrderStatus.PENDING
        ttl_minutes = int(getattr(settings, 'ORDER_PAYMENT_TTL_MINUTES', 60))
        order.expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
        order.save(update_fields=['status', 'expires_at'])
        
        # Step 7: Deactivate cart (keep for history)
        cart.is_active = False
        cart.save()
        
        logger.info(
            f"Order created: {order.order_number} with "
            f"{len(order_items_data)} items, stock reserved"
        )
        
        # Emit hook
        cls._emit_hook('ORDER_CREATED', {
            'order': order,
            'user': user,
        })
        
        return order
    
    # ========================================================================
    # PAYMENT CONFIRMATION (Convert reservation to sale)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def confirm_payment(
        cls,
        order: Order,
        payment: 'Payment' = None,
        payment_data: Optional[Dict] = None,
        admin_user=None,
    ) -> Order:
        """
        Confirm payment and convert reservation to actual sale.
        
        Per D-045: This happens after admin verifies payment receipt.
        
        Args:
            order: Order instance (must be PENDING)
            payment: Payment instance (if provided, will be updated - recommended)
            payment_data: Optional dict with payment info (for creating new payment)
            admin_user: User confirming the payment
            
        Returns:
            Updated Order with PAID status
        """
        if order.status != Order.OrderStatus.PENDING:
            raise ValueError(
                f"Order must be PENDING to confirm payment, "
                f"got {order.status}"
            )
        
        # Step 1: Update existing Payment OR create new one
        if payment:
            # Update existing payment (e.g., card-to-card with evidence)
            # This preserves sender_card_last4, transfer_time, receipt_image
            payment.status = Payment.PaymentStatus.SUCCESS
            payment.reviewed_by = admin_user
            payment.reviewed_at = timezone.now()
            payment.admin_notes = (payment_data or {}).get('notes', 'تایید از طریق پنل ادمین')
            payment.save()
        elif payment_data:
            # Create new payment (legacy behavior)
            Payment.objects.create(
                order=order,
                amount=payment_data.get('amount', order.total_price),
                status=Payment.PaymentStatus.SUCCESS,
                gateway=payment_data.get('gateway', 'MANUAL'),
                ref_id=payment_data.get('ref_id', ''),
                gateway_response=payment_data.get('response'),
            )
        
        # Step 2: Convert reservation to sale via InventoryService
        sale_items = [
            {
                'product': item.product,
                'variant': item.variant,
                'quantity': Decimal(str(item.quantity)),
            }
            for item in order.items.all()
        ]
        
        InventoryService.confirm_sale(
            order_items=sale_items,
            user=admin_user,
            order_id=str(order.order_number),
        )
        
        # Step 3: Update order status
        order.status = Order.OrderStatus.PAID
        order.save()
        
        logger.info(
            f"Payment confirmed: {order.order_number}, "
            f"reservation converted to sale"
        )
        
        # Emit hook
        cls._emit_hook('ORDER_CONFIRMED', {
            'order': order,
            'admin_user': admin_user,
        })

        # D-105: ساخت خودکار مرسوله‌ها (تفکیک بر اساس تامین‌کننده / ریهان) + پیامک تامین‌کننده
        # هرگز نباید خطای این بخش، تایید پرداخت را بشکند
        try:
            from .fulfillment import build_shipments
            build_shipments(order, user=admin_user)
        except Exception:
            logger.exception('Fulfillment shipments build failed for %s', order.order_number)

        return order
    
    # ========================================================================
    # ORDER CANCELLATION (Release reservation)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def cancel_order(
        cls,
        order: Order,
        reason: str = 'Customer request',
        user=None,
    ) -> Order:
        """
        Cancel order and release inventory reservation.
        
        Per D-045: Reservation released on cancel.
        
        Args:
            order: Order instance (must be PENDING or DRAFT)
            reason: Reason for cancellation
            user: User performing cancellation
            
        Returns:
            Updated Order with CANCELLED status
        """
        # Only PENDING orders have reservations to release
        if order.status == Order.OrderStatus.PENDING:
            release_items = [
                {
                    'product': item.product,
                    'variant': item.variant,
                    'quantity': Decimal(str(item.quantity)),
                }
                for item in order.items.all()
            ]
            
            InventoryService.release_reservation(
                order_items=release_items,
                user=user,
                order_id=str(order.order_number),
                reason=reason,
            )
        
        # Update order status
        order.status = Order.OrderStatus.CANCELLED
        order.save()
        
        logger.info(
            f"Order cancelled: {order.order_number}, reason: {reason}"
        )
        
        # Emit hook
        cls._emit_hook('ORDER_CANCELLED', {
            'order': order,
            'reason': reason,
            'user': user,
        })
        
        return order
    
    # ========================================================================
    # REFUND / RETURN (Return stock)
    # ========================================================================
    
    @classmethod
    @transaction.atomic
    def process_return(
        cls,
        order: Order,
        items_to_return: List[Dict],
        reason: str = 'Customer return',
        admin_user=None,
    ) -> Order:
        """
        Process return for a paid order.
        
        Per D-045: Stock returned after admin approves return.
        
        Args:
            order: Order instance (must be PAID, PROCESSING, SHIPPED, or DELIVERED)
            items_to_return: List of dicts with 'product' and 'quantity'
            reason: Reason for return
            admin_user: Admin approving the return
            
        Returns:
            Updated Order
        """
        if order.status not in [
            Order.OrderStatus.PAID,
            Order.OrderStatus.PROCESSING,
            Order.OrderStatus.SHIPPED,
            Order.OrderStatus.DELIVERED,
        ]:
            raise ValueError(
                f"Order must be paid or later to process return, "
                f"got {order.status}"
            )
        
        # Convert quantities to Decimal
        return_items = []
        for item in items_to_return:
            return_items.append({
                'product': item['product'],
                'quantity': Decimal(str(item['quantity'])),
            })
        
        InventoryService.return_stock(
            order_items=return_items,
            user=admin_user,
            order_id=str(order.order_number),
            reason=reason,
        )
        
        logger.info(
            f"Return processed for order {order.order_number}: "
            f"{len(return_items)} items"
        )
        
        cls._emit_hook('ORDER_RETURNED', {
            'order': order,
            'items': return_items,
            'reason': reason,
            'admin_user': admin_user,
        })
        
        return order
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    @classmethod
    def _emit_hook(cls, hook_name: str, data: dict):
        """Emit hook to HookSystem if available."""
        try:
            from src.core.hooks import hooks
            hook_attr = getattr(hooks, 'fire', None)
            if hook_attr and callable(hook_attr):
                hook_attr(hook_name, **data)
        except Exception as e:
            logger.debug(f"Hook emission failed for {hook_name}: {e}")
