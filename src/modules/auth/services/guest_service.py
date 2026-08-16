"""
Guest Service برای ماژول احراز هویت
منطبق بر ADR-006 بخش ۳: Guest Checkout

ویژگی‌ها:
- مهمان می‌تواند بدون ثبت‌نام سفارش دهد
- سقف: ۵ سفارش مهمان per device
- پس از ۵ سفارش: الزام به ثبت‌نام
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


class GuestService:
    """
    سرویس مدیریت Guest Checkout.
    
    منطبق بر ADR-006 بخش ۳:
    - سقف: ۵ سفارش مهمان per device
    - Guest Review با توکن ۷ روزه
    """
    
    MAX_GUEST_ORDERS = 5
    GUEST_REVIEW_TOKEN_TTL_DAYS = 7
    CACHE_PREFIX = 'rihan:guest:'
    
    @classmethod
    def create_guest_session(cls) -> str:
        """
        ایجاد Session مهمان.
        
        Returns:
            guest_session_id (UUID)
        """
        guest_session_id = str(uuid.uuid4())
        
        # ذخیره در کش (۷ روز)
        cache_key = f"{cls.CACHE_PREFIX}session:{guest_session_id}"
        cache.set(cache_key, {
            'order_count': 0,
            'created_at': None,  # Django auto sets this
        }, timeout=7 * 24 * 60 * 60)
        
        logger.info(f"Guest session created: {guest_session_id}")
        return guest_session_id
    
    @classmethod
    def get_guest_order_count(cls, guest_session_id: str) -> int:
        """
        دریافت تعداد سفارش‌های مهمان.
        
        Args:
            guest_session_id: شناسه Session مهمان
            
        Returns:
            تعداد سفارش‌ها
        """
        cache_key = f"{cls.CACHE_PREFIX}session:{guest_session_id}"
        data = cache.get(cache_key)
        
        if data is None:
            return 0
        
        return data.get('order_count', 0)
    
    @classmethod
    def increment_guest_order(cls, guest_session_id: str) -> int:
        """
        افزایش تعداد سفارش‌های مهمان.
        
        Args:
            guest_session_id: شناسه Session مهمان
            
        Returns:
            تعداد سفارش‌های جدید
        """
        cache_key = f"{cls.CACHE_PREFIX}session:{guest_session_id}"
        data = cache.get(cache_key) or {'order_count': 0}
        
        data['order_count'] += 1
        cache.set(cache_key, data, timeout=7 * 24 * 60 * 60)
        
        logger.info(
            f"Guest order count: {data['order_count']} "
            f"(session: {guest_session_id})"
        )
        
        return data['order_count']
    
    @classmethod
    def can_guest_order(cls, guest_session_id: str) -> bool:
        """
        بررسی امکان سفارش مهمان.
        
        Args:
            guest_session_id: شناسه Session مهمان
            
        Returns:
            True اگر امکان سفارش وجود دارد
        """
        count = cls.get_guest_order_count(guest_session_id)
        return count < cls.MAX_GUEST_ORDERS
    
    @classmethod
    def create_guest_review_token(cls, guest_session_id: str) -> str:
        """
        ایجاد توکن Guest Review.
        
        Args:
            guest_session_id: شناسه Session مهمان
            
        Returns:
            guest_review_token (UUID)
        """
        token = str(uuid.uuid4())
        
        # ذخیره در کش (۷ روز)
        cache_key = f"{cls.CACHE_PREFIX}review:{token}"
        cache.set(cache_key, guest_session_id, timeout=cls.GUEST_REVIEW_TOKEN_TTL_DAYS * 24 * 60 * 60)
        
        logger.info(f"Guest review token created: {token}")
        return token
    
    @classmethod
    def verify_guest_review_token(cls, token: str) -> Optional[str]:
        """
        تأیید توکن Guest Review.
        
        Args:
            token: توکن
            
        Returns:
            guest_session_id یا None
        """
        cache_key = f"{cls.CACHE_PREFIX}review:{token}"
        return cache.get(cache_key)
    
    @classmethod
    def get_guest_status(cls, guest_session_id: str) -> dict:
        """
        دریافت وضعیت مهمان.
        
        Args:
            guest_session_id: شناسه Session مهمان
            
        Returns:
            dict با وضعیت مهمان
        """
        count = cls.get_guest_order_count(guest_session_id)
        
        return {
            'order_count': count,
            'max_orders': cls.MAX_GUEST_ORDERS,
            'can_order': count < cls.MAX_GUEST_ORDERS,
            'orders_remaining': max(0, cls.MAX_GUEST_ORDERS - count),
        }
