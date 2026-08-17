"""
M1 Interface - رابط موقت برای ماژول کاتالوگ

وضعیت فعلی: M1 بازنویسی نشده، داده mock برمی‌گرداند
وضعیت آینده: پس از بازنویسی M1، به models واقعی متصل می‌شود
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class M1Interface:
    """
    رابط ماژول کاتالوگ (M1).
    
    این کلاس یک interface موقت است که:
    - در حال حاضر داده mock برمی‌گرداند
    - پس از بازنویسی M1، به models واقعی متصل می‌شود
    """
    
    # Flag برای فعال‌سازی mock mode
    MOCK_MODE = True
    
    @classmethod
    def get_products_count(cls) -> int:
        """تعداد کل محصولات"""
        if cls.MOCK_MODE:
            return 25  # Mock data
        # TODO: اتصال به M1 واقعی
        return 0
    
    @classmethod
    def get_low_stock_products(cls, threshold: int = 5) -> List[Dict]:
        """
        دریافت محصولات با موجودی کم.
        
        Args:
            threshold: آستانه موجودی کم (پیش‌فرض: ۵)
            
        Returns:
            لیست محصولات با موجودی کم
        """
        if cls.MOCK_MODE:
            return [
                {'id': 1, 'name': 'زعفران نگین ۱ مثقال', 'stock': 2},
                {'id': 2, 'name': 'زیره سبز ۵۰۰ گرم', 'stock': 3},
                {'id': 3, 'name': 'گلپر ۲۵۰ گرم', 'stock': 4},
            ]
        # TODO: اتصال به M1 واقعی
        return []
    
    @classmethod
    def get_categories(cls) -> List[Dict]:
        """دریافت لیست دسته‌بندی‌ها"""
        if cls.MOCK_MODE:
            return [
                {'id': 1, 'name': 'ادویه‌جات', 'products_count': 12},
                {'id': 2, 'name': 'زعفران', 'products_count': 5},
                {'id': 3, 'name': 'چای و دمنوش', 'products_count': 8},
            ]
        # TODO: اتصال به M1 واقعی
        return []
    
    @classmethod
    def get_recent_products(cls, days: int = 7) -> List[Dict]:
        """دریافت محصولات اضافه‌شده اخیر"""
        if cls.MOCK_MODE:
            return [
                {'id': 4, 'name': 'دارچین ۱۰۰ گرم', 'created_days_ago': 1},
                {'id': 5, 'name': 'هل سبز ۵۰ گرم', 'created_days_ago': 2},
            ]
        # TODO: اتصال به M1 واقعی
        return []
