"""
Rate Limiter برای ماژول احراز هویت
منطبق بر ADR-006 بخش ۴: Rate Limiting و ضدسوءاستفاده

محدودیت‌ها:
- درخواست OTP per شماره: ۳ بار در ۱۰ دقیقه
- درخواست OTP per IP: ۱۰ بار در ساعت
- تأیید OTP per شماره: ۳ بار در ۱۰ دقیقه
"""
from __future__ import annotations

import logging
from typing import Tuple

from django.core.cache import cache

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate Limiter مبتنی بر کش.
    
    منطبق بر ADR-006 بخش ۴:
    - جلوگیری از SMS bombing
    - جلوگیری از brute-force
    - لاگ کامل در AuditLog
    """
    
    # محدودیت‌های پیش‌فرض (ADR-006)
    OTP_REQUEST_PER_PHONE = 3      # ۳ بار در ۱۰ دقیقه
    OTP_REQUEST_PER_IP = 10        # ۱۰ بار در ساعت
    OTP_VERIFY_PER_PHONE = 3       # ۳ بار در ۱۰ دقیقه
    LOCKOUT_DURATION = 30          # ۳۰ دقیقه قفل موقت
    HARD_LOCKOUT_DURATION = 24 * 60  # ۲۴ ساعت قفل سخت
    
    CACHE_PREFIX = 'rihan:ratelimit:'
    
    @classmethod
    def check_otp_request(cls, phone: str, ip: str = None) -> Tuple[bool, str]:
        """
        بررسی امکان درخواست OTP.
        
        Args:
            phone: شماره موبایل
            ip: آدرس IP (اختیاری)
            
        Returns:
            (allowed, message) - اگر allowed=False، message دلیل را توضیح می‌دهد
        """
        # بررسی per شماره
        phone_key = f"{cls.CACHE_PREFIX}otp_req_phone:{phone}"
        phone_count = cache.get(phone_key, 0)
        
        if phone_count >= cls.OTP_REQUEST_PER_PHONE:
            logger.warning(f"Rate limit exceeded for phone: {phone}")
            return False, "به دلیل درخواست‌های متعدد، لطفاً چند دقیقه صبر کنید."
        
        # بررسی per IP
        if ip:
            ip_key = f"{cls.CACHE_PREFIX}otp_req_ip:{ip}"
            ip_count = cache.get(ip_key, 0)
            
            if ip_count >= cls.OTP_REQUEST_PER_IP:
                logger.warning(f"Rate limit exceeded for IP: {ip}")
                return False, "به دلیل درخواست‌های متعدد، لطفاً چند دقیقه صبر کنید."
        
        return True, ""
    
    @classmethod
    def record_otp_request(cls, phone: str, ip: str = None) -> None:
        """ثبت درخواست OTP در کش"""
        # per شماره (۱۰ دقیقه)
        phone_key = f"{cls.CACHE_PREFIX}otp_req_phone:{phone}"
        phone_count = cache.get(phone_key, 0)
        cache.set(phone_key, phone_count + 1, timeout=600)  # ۱۰ دقیقه
        
        # per IP (۱ ساعت)
        if ip:
            ip_key = f"{cls.CACHE_PREFIX}otp_req_ip:{ip}"
            ip_count = cache.get(ip_key, 0)
            cache.set(ip_key, ip_count + 1, timeout=3600)  # ۱ ساعت
    
    @classmethod
    def check_otp_verify(cls, phone: str) -> Tuple[bool, str]:
        """
        بررسی امکان تأیید OTP.
        
        Args:
            phone: شماره موبایل
            
        Returns:
            (allowed, message)
        """
        key = f"{cls.CACHE_PREFIX}otp_verify:{phone}"
        count = cache.get(key, 0)
        
        if count >= cls.OTP_VERIFY_PER_PHONE:
            logger.warning(f"OTP verify rate limit exceeded for phone: {phone}")
            return False, "به دلیل تلاش‌های متعدد، لطفاً چند دقیقه صبر کنید."
        
        return True, ""
    
    @classmethod
    def record_otp_verify(cls, phone: str) -> None:
        """ثبت تلاش تأیید OTP در کش"""
        key = f"{cls.CACHE_PREFIX}otp_verify:{phone}"
        count = cache.get(key, 0)
        cache.set(key, count + 1, timeout=600)  # ۱۰ دقیقه
    
    @classmethod
    def check_lockout(cls, phone: str) -> Tuple[bool, int]:
        """
        بررسی قفل موقت.
        
        Returns:
            (is_locked, minutes_remaining)
        """
        key = f"{cls.CACHE_PREFIX}lockout:{phone}"
        locked_until = cache.get(key)
        
        if locked_until:
            import time
            remaining = int((locked_until - time.time()) / 60)
            if remaining > 0:
                return True, remaining
        
        return False, 0
    
    @classmethod
    def set_lockout(cls, phone: str, minutes: int = None) -> None:
        """تنظیم قفل موقت"""
        import time
        if minutes is None:
            minutes = cls.LOCKOUT_DURATION
        
        key = f"{cls.CACHE_PREFIX}lockout:{phone}"
        cache.set(key, time.time() + (minutes * 60), timeout=minutes * 60)
        logger.info(f"Lockout set for phone: {phone} ({minutes} minutes)")
    
    @classmethod
    def clear_lockout(cls, phone: str) -> None:
        """پاکسازی قفل موقت"""
        key = f"{cls.CACHE_PREFIX}lockout:{phone}"
        cache.delete(key)
    
    @classmethod
    def clear_all(cls, phone: str) -> None:
        """پاکسازی تمام محدودیت‌های یک شماره"""
        keys = [
            f"{cls.CACHE_PREFIX}otp_req_phone:{phone}",
            f"{cls.CACHE_PREFIX}otp_verify:{phone}",
            f"{cls.CACHE_PREFIX}lockout:{phone}",
        ]
        for key in keys:
            cache.delete(key)
