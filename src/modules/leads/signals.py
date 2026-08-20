"""
Signals for Leads Module (M9)

Auto-notifies pending leads when a product becomes available.
Tracks lead conversion when orders are paid/delivered.

Design notes (D-084):
- Only triggers when product transitions from out-of-stock to in-stock
- Uses QuerySet.update() for bulk status change (efficient)
- Handles both Order and OrderItem signals for conversion tracking
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender='catalog.Inventory')
def notify_leads_when_product_available(sender, instance, **kwargs):
    """
    When inventory changes, check if product became available.
    If so, notify all pending leads for this product.
    """
    try:
        product = instance.product
        if not product:
            return
        
        if not instance.available_quantity > 0:
            return
        
        from .models import Lead
        pending_leads = Lead.objects.filter(
            product=product,
            status=Lead.LeadStatus.PENDING
        )
        
        pending_count = pending_leads.count()
        if pending_count == 0:
            return
        
        updated = pending_leads.update(
            status=Lead.LeadStatus.NOTIFIED,
            notified_at=timezone.now(),
            notification_method='AUTO'
        )
        
        logger.info(
            f"Product '{product.name}' became available. "
            f"Auto-notified {updated} lead(s)."
        )
    
    except Exception as e:
        logger.error(f"Failed to notify leads for inventory {instance.id}: {e}")


def _check_and_convert_leads(order):
    """
    Shared logic: check if order matches any leads and convert them.
    
    Matching:
    - Order phone matches lead phone
    - Order has items matching lead product
    - Lead is PENDING or NOTIFIED
    """
    try:
        if order.status not in ['PAID', 'DELIVERED']:
            return
        
        # Get phone
        phone = None
        if order.user:
            phone = order.user.username
        elif order.guest_phone:
            phone = order.guest_phone
        
        if not phone:
            return
        
        # Get products in this order
        order_products = list(
            order.items.values_list('product_id', flat=True)
        )
        
        if not order_products:
            return
        
        from .models import Lead
        
        matching_leads = Lead.objects.filter(
            phone=phone,
            product_id__in=order_products,
            status__in=[Lead.LeadStatus.PENDING, Lead.LeadStatus.NOTIFIED]
        )
        
        converted_count = 0
        for lead in matching_leads:
            lead.convert(order)
            converted_count += 1
        
        if converted_count > 0:
            logger.info(
                f"Order {order.order_number}: "
                f"Converted {converted_count} lead(s)"
            )
    
    except Exception as e:
        logger.error(f"Failed to track lead conversion: {e}")


@receiver(post_save, sender='order.Order')
def track_lead_conversion_on_order(sender, instance, created, **kwargs):
    """Track conversion when order status changes to PAID/DELIVERED."""
    _check_and_convert_leads(instance)


@receiver(post_save, sender='order.OrderItem')
def track_lead_conversion_on_item(sender, instance, **kwargs):
    """
    Track conversion when order items are added.
    
    This handles the case where order is created with PAID status
    but items are added afterwards (common in tests and imports).
    """
    _check_and_convert_leads(instance.order)
