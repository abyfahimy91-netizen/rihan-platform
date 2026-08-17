"""
Hook handlers for Order module.
Registers hooks to integrate Order events with other modules.
"""
import logging

logger = logging.getLogger(__name__)

try:
    from src.core.hooks import hooks, HOOKS
    
    # ========================================================================
    # Register hooks (called when module is imported)
    # ========================================================================
    
    def on_order_created(order=None, user=None, **kwargs):
        """Handle ORDER_CREATED event."""
        if order:
            logger.info(
                f"Order created: {order.order_number} "
                f"(status: {order.status})"
            )
    
    def on_order_confirmed(order=None, admin_user=None, **kwargs):
        """Handle ORDER_CONFIRMED event."""
        if order:
            logger.info(
                f"Order confirmed: {order.order_number} "
                f"by {admin_user or 'system'}"
            )
    
    def on_order_cancelled(order=None, reason=None, user=None, **kwargs):
        """Handle ORDER_CANCELLED event."""
        if order:
            logger.info(
                f"Order cancelled: {order.order_number}, reason: {reason}"
            )
    
    def on_order_returned(order=None, items=None, reason=None, admin_user=None, **kwargs):
        """Handle ORDER_RETURNED event."""
        if order:
            logger.info(
                f"Return processed for order {order.order_number}, "
                f"reason: {reason}"
            )
    
    # Register hooks
    hooks.register(
        'ORDER_CREATED',
        on_order_created,
        priority=10,
        module='order'
    )
    
    hooks.register(
        'ORDER_CONFIRMED',
        on_order_confirmed,
        priority=10,
        module='order'
    )
    
    hooks.register(
        'ORDER_CANCELLED',
        on_order_cancelled,
        priority=10,
        module='order'
    )
    
    hooks.register(
        'ORDER_RETURNED',
        on_order_returned,
        priority=10,
        module='order'
    )
    
    logger.debug("Order module hooks registered successfully")
    
except Exception as e:
    logger.warning(f"Could not register Order hooks: {e}")
