"""
M2 Interface - Real Connection to Order Module
Based on D-081: Remove Mock Mode
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional
from datetime import timedelta

from django.utils import timezone
from django.db.models import Sum, Count, Q

logger = logging.getLogger(__name__)


class M2Interface:
    """Real interface to Order module (M2)"""
    
    SAFE_MODE = True
    
    @classmethod
    def get_orders_count(cls, status: Optional[str] = None) -> int:
        """Count orders with optional status filter"""
        try:
            from src.modules.order.models import Order
            
            qs = Order.objects.all()
            if status:
                status_map = {
                    'pending': ['PENDING', 'DRAFT'],
                    'approved': ['PAID', 'PROCESSING'],
                    'shipped': ['SHIPPED'],
                    'delivered': ['DELIVERED'],
                    'cancelled': ['CANCELLED'],
                }
                status_codes = status_map.get(status.lower(), [status.upper()])
                qs = qs.filter(status__in=status_codes)
            
            return qs.count()
        except Exception as e:
            logger.error(f"M2Interface.get_orders_count error: {e}")
            return 0
    
    @classmethod
    def get_pending_orders(cls) -> List[Dict]:
        """Get orders pending approval"""
        try:
            from src.modules.order.models import Order
            
            orders = Order.objects.filter(
                status__in=['PENDING', 'PAID']
            ).order_by('-created_at')[:50]
            
            return [
                {
                    'id': str(o.id),
                    'order_number': o.order_number,
                    'customer_name': cls._get_customer_name(o),
                    'total': str(cls._get_order_total(o)),
                    'status': o.status,
                    'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
                }
                for o in orders
            ]
        except Exception as e:
            logger.error(f"M2Interface.get_pending_orders error: {e}")
            return []
    
    @classmethod
    def get_revenue(cls, period: str = 'today') -> int:
        """Get revenue for a time period"""
        try:
            from src.modules.order.models import Order
            
            now = timezone.now()
            if period == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'week':
                start_date = now - timedelta(days=7)
            elif period == 'month':
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=365)
            
            orders = Order.objects.filter(
                status__in=['PAID', 'PROCESSING', 'SHIPPED', 'DELIVERED'],
                created_at__gte=start_date
            )
            
            total = 0
            for o in orders:
                total += float(cls._get_order_total(o))
            
            return int(total)
        except Exception as e:
            logger.error(f"M2Interface.get_revenue error: {e}")
            return 0
    
    @classmethod
    def get_sales_chart_data(cls, days: int = 30) -> List[Dict]:
        """Get sales chart data"""
        try:
            from src.modules.order.models import Order
            
            now = timezone.now()
            start_date = now - timedelta(days=days)
            
            orders = Order.objects.filter(
                status__in=['PAID', 'PROCESSING', 'SHIPPED', 'DELIVERED'],
                created_at__gte=start_date
            ).order_by('created_at')
            
            data_map = {}
            for o in orders:
                date_str = o.created_at.strftime('%Y-%m-%d')
                if date_str not in data_map:
                    data_map[date_str] = {'revenue': 0, 'orders_count': 0}
                data_map[date_str]['revenue'] += float(cls._get_order_total(o))
                data_map[date_str]['orders_count'] += 1
            
            result = []
            for i in range(days):
                date = now - timedelta(days=days - i - 1)
                date_str = date.strftime('%Y-%m-%d')
                stats = data_map.get(date_str, {'revenue': 0, 'orders_count': 0})
                result.append({
                    'date': date_str,
                    'revenue': int(stats['revenue']),
                    'orders_count': stats['orders_count'],
                })
            
            return result
        except Exception as e:
            logger.error(f"M2Interface.get_sales_chart_data error: {e}")
            return []
    
    @classmethod
    def get_orders_without_receipt(cls) -> List[Dict]:
        """Get orders without payment receipt"""
        try:
            from src.modules.order.models import Order
            
            # Orders with PAID status but need receipt verification
            orders = Order.objects.filter(
                status='PENDING'
            ).order_by('-created_at')[:50]
            
            return [
                {
                    'id': str(o.id),
                    'order_number': o.order_number,
                    'customer_name': cls._get_customer_name(o),
                    'total': str(cls._get_order_total(o)),
                    'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
                }
                for o in orders
            ]
        except Exception as e:
            logger.error(f"M2Interface.get_orders_without_receipt error: {e}")
            return []
    
    @classmethod
    def _get_customer_name(cls, order) -> str:
        """Extract customer name from order"""
        try:
            # Try user first
            if hasattr(order, 'user') and order.user:
                if order.user.first_name:
                    return f"{order.user.first_name} {order.user.last_name}"
                return order.user.username
            
            # Try shipping address
            if hasattr(order, 'shipping_address') and order.shipping_address:
                return order.shipping_address.full_name
            
            # Try billing address
            if hasattr(order, 'billing_address') and order.billing_address:
                return order.billing_address.full_name
            
            # Try direct field
            if hasattr(order, 'customer_name'):
                return order.customer_name
            
            return 'Customer'
        except Exception:
            return 'Customer'
    
    @classmethod
    def _get_order_total(cls, order) -> int:
        """Calculate order total from items"""
        try:
            # Try direct total field
            if hasattr(order, 'total_amount'):
                return int(order.total_amount)
            if hasattr(order, 'total'):
                return int(order.total)
            
            # Calculate from items
            if hasattr(order, 'items'):
                total = sum(
                    float(item.subtotal) 
                    for item in order.items.all()
                )
                return int(total)
            
            return 0
        except Exception:
            return 0
