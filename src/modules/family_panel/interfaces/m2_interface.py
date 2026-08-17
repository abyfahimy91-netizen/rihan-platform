"""
M2 Interface - رابط موقت برای ماژول سفارش

وضعیت فعلی: M2 بازنویسی نشده، داده mock برمی‌گرداند
وضعیت آینده: پس از بازنویسی M2، به models واقعی متصل می‌شود
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class M2Interface:
    """
    رابط ماژول سفارش (M2).
    
    این کلاس یک interface موقت است که:
    - در حال حاضر داده mock برمی‌گرداند
    - پس از بازنویسی M2، به models واقعی متصل می‌شود
    """
    
    # Flag برای فعال‌سازی mock mode
    MOCK_MODE = True
    
    @classmethod
    def get_orders_count(cls, status: Optional[str] = None) -> int:
        """
        تعداد سفارش‌ها.
        
        Args:
            status: وضعیت سفارش (None = همه)
        """
        if cls.MOCK_MODE:
            counts = {
                None: 45,
                'pending': 8,
                'approved': 12,
                'shipped': 15,
                'delivered': 10,
            }
            return counts.get(status, 0)
        # TODO: اتصال به M2 واقعی
        return 0
    
    @classmethod
    def get_pending_orders(cls) -> List[Dict]:
        """دریافت سفارش‌های در انتظار تأیید"""
        if cls.MOCK_MODE:
            return [
                {'id': 101, 'customer_name': 'علی محمدی', 'total': 250000, 'created_at': '2026-08-17'},
                {'id': 102, 'customer_name': 'فاطمه احمدی', 'total': 180000, 'created_at': '2026-08-17'},
                {'id': 103, 'customer_name': 'رضا کریمی', 'total': 320000, 'created_at': '2026-08-16'},
            ]
        # TODO: اتصال به M2 واقعی
        return []
    
    @classmethod
    def get_revenue(cls, period: str = 'today') -> int:
        """
        دریافت درآمد.
        
        Args:
            period: 'today', 'week', 'month'
            
        Returns:
            درآمد به تومان
        """
        if cls.MOCK_MODE:
            revenues = {
                'today': 850000,
                'week': 5200000,
                'month': 21500000,
            }
            return revenues.get(period, 0)
        # TODO: اتصال به M2 واقعی
        return 0
    
    @classmethod
    def get_sales_chart_data(cls, days: int = 30) -> List[Dict]:
        """
        دریافت داده‌های نمودار فروش.
        
        Args:
            days: تعداد روزهای گذشته
            
        Returns:
            لیست داده‌های نمودار
        """
        if cls.MOCK_MODE:
            # Mock data برای ۳۰ روز گذشته
            import random
            data = []
            for i in range(days):
                date = datetime.now() - timedelta(days=days - i - 1)
                data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'revenue': random.randint(200000, 1500000),
                    'orders_count': random.randint(1, 10),
                })
            return data
        # TODO: اتصال به M2 واقعی
        return []
    
    @classmethod
    def get_orders_without_receipt(cls) -> List[Dict]:
        """دریافت سفارش‌های بدون رسید پرداخت"""
        if cls.MOCK_MODE:
            return [
                {'id': 104, 'customer_name': 'مریم حسینی', 'total': 150000},
                {'id': 105, 'customer_name': 'حسن رضایی', 'total': 220000},
            ]
        # TODO: اتصال به M2 واقعی
        return []
