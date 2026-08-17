"""
Dashboard Service برای ماژول family_panel
منطبق بر US-017: مشاهده داشبورد
"""
from __future__ import annotations

import logging
from typing import Dict, List

from ..interfaces import M1Interface, M2Interface
from ..models import SiteSettings

logger = logging.getLogger(__name__)


class DashboardService:
    """
    سرویس داشبورد پنل خانواده.
    
    منطبق بر US-017:
    - سفارش‌های جدید + درآمد امروز/هفته/ماه
    - نظرات در انتظار + سرنخ‌های جدید
    - نمودار فروش ۳۰ روزه
    - هشدار موجودی کم (< ۵)
    """
    
    @classmethod
    def get_dashboard_data(cls) -> Dict:
        """
        دریافت داده‌های کامل داشبورد.
        
        Returns:
            dict با تمام داده‌های مورد نیاز داشبورد
        """
        settings = SiteSettings.get_settings()
        
        return {
            # خلاصه سفارش‌ها
            'orders': {
                'total': M2Interface.get_orders_count(),
                'pending': M2Interface.get_orders_count('pending'),
                'approved': M2Interface.get_orders_count('approved'),
                'shipped': M2Interface.get_orders_count('shipped'),
                'delivered': M2Interface.get_orders_count('delivered'),
            },
            # درآمد
            'revenue': {
                'today': M2Interface.get_revenue('today'),
                'week': M2Interface.get_revenue('week'),
                'month': M2Interface.get_revenue('month'),
            },
            # محصولات
            'products': {
                'total': M1Interface.get_products_count(),
                'low_stock': M1Interface.get_low_stock_products(
                    threshold=settings.low_stock_threshold
                ),
                'low_stock_count': len(M1Interface.get_low_stock_products(
                    threshold=settings.low_stock_threshold
                )),
                'categories': M1Interface.get_categories(),
            },
            # سفارش‌های در انتظار
            'pending_orders': M2Interface.get_pending_orders(),
            # سفارش‌های بدون رسید
            'orders_without_receipt': M2Interface.get_orders_without_receipt(),
            # نمودار فروش
            'sales_chart': M2Interface.get_sales_chart_data(days=30),
            # تنظیمات
            'settings': {
                'site_name': settings.site_name,
                'low_stock_threshold': settings.low_stock_threshold,
            },
        }
    
    @classmethod
    def get_alerts(cls) -> List[Dict]:
        """
        دریافت هشدارهای داشبورد.
        
        Returns:
            لیست هشدارها
        """
        alerts = []
        settings = SiteSettings.get_settings()
        
        # هشدار موجودی کم
        low_stock = M1Interface.get_low_stock_products(
            threshold=settings.low_stock_threshold
        )
        if low_stock:
            alerts.append({
                'type': 'low_stock',
                'severity': 'warning',
                'message': f"{len(low_stock)} محصول با موجودی کم",
                'data': low_stock,
            })
        
        # هشدار سفارش‌های بدون رسید
        orders_without_receipt = M2Interface.get_orders_without_receipt()
        if orders_without_receipt:
            alerts.append({
                'type': 'missing_receipt',
                'severity': 'warning',
                'message': f"{len(orders_without_receipt)} سفارش بدون رسید پرداخت",
                'data': orders_without_receipt,
            })
        
        # هشدار سفارش‌های در انتظار
        pending_count = M2Interface.get_orders_count('pending')
        if pending_count > 0:
            alerts.append({
                'type': 'pending_orders',
                'severity': 'info',
                'message': f"{pending_count} سفارش در انتظار تأیید",
                'data': {'count': pending_count},
            })
        
        return alerts
    
    @classmethod
    def get_summary_stats(cls) -> Dict:
        """
        دریافت آمار خلاصه برای نمایش سریع.
        
        Returns:
            dict با آمار خلاصه
        """
        return {
            'revenue_today': M2Interface.get_revenue('today'),
            'orders_today': M2Interface.get_orders_count('pending'),
            'products_total': M1Interface.get_products_count(),
            'low_stock_count': len(M1Interface.get_low_stock_products()),
        }
