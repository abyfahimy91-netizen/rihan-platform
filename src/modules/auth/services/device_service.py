"""
Device Service برای ماژول احراز هویت
منطبق بر ADR-006 بخش ۲.۲: Device Remembering

ویژگی‌ها:
- طول عمر: ۳۰ روز
- فرمت: UUID v4
- محدودیت: حداکثر ۵ دستگاه per کاربر
"""
from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

try:
    from django.contrib.auth.hashers import make_password, check_password
except ImportError:
    from django.contrib.auth.hashers import make_password, check_password

from ..models import DeviceToken, LoginAttempt

logger = logging.getLogger(__name__)

User = get_user_model()


class DeviceService:
    """
    سرویس مدیریت DeviceToken.
    
    منطبق بر ADR-006 بخش ۲.۲:
    - طول عمر: ۳۰ روز
    - فرمت: UUID v4
    - محدودیت: حداکثر ۵ دستگاه per کاربر
    """
    
    MAX_DEVICES_PER_USER = 5
    TOKEN_TTL_DAYS = 30
    
    @classmethod
    def create_device_token(
        cls,
        user: User,
        device_fingerprint: str = '',
        user_agent: str = '',
        ip_address: str = None
    ) -> str:
        """
        ایجاد DeviceToken جدید.
        
        Args:
            user: کاربر
            device_fingerprint: اثر انگشت دستگاه
            user_agent: User Agent مرورگر
            ip_address: آدرس IP
            
        Returns:
            token (UUID string)
        """
        # بررسی تعداد دستگاه‌های فعال
        active_count = DeviceToken.get_active_count(user)
        if active_count >= cls.MAX_DEVICES_PER_USER:
            # حذف قدیمی‌ترین‌ها
            DeviceToken.cleanup_old_tokens(user)
            logger.info(
                f"Cleaned up old tokens for user {user.username}"
            )
        
        # تولید UUID v4
        token = str(uuid.uuid4())
        token_hash = make_password(token)
        
        # ایجاد DeviceToken
        device_token = DeviceToken.objects.create(
            user=user,
            token_hash=token_hash,
            device_fingerprint=device_fingerprint,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(days=cls.TOKEN_TTL_DAYS),
            is_active=True
        )
        
        logger.info(
            f"Device token created for user {user.username} "
            f"(device: {device_fingerprint[:20]}...)"
        )
        
        return token
    
    @classmethod
    def verify_device_token(cls, token: str) -> Optional[User]:
        """
        تأیید DeviceToken.
        
        Args:
            token: DeviceToken (UUID string)
            
        Returns:
            user یا None اگر نامعتبر باشد
        """
        try:
            # پیدا کردن DeviceToken با hash
            device_tokens = DeviceToken.objects.filter(is_active=True)
            
            for dt in device_tokens:
                if check_password(token, dt.token_hash):
                    # بررسی انقضا
                    if dt.is_expired:
                        dt.revoke()
                        logger.info(f"Device token expired: {dt.id}")
                        return None
                    
                    # تمدید انقضا
                    dt.refresh_expiry()
                    
                    # ثبت در LoginAttempt
                    LoginAttempt.objects.create(
                        phone=dt.user.username,
                        action='device_login',
                        ip_address=dt.ip_address,
                        user_agent=dt.user_agent,
                        success=True,
                        user=dt.user
                    )
                    
                    logger.info(f"Device token verified: {dt.id}")
                    return dt.user
            
            return None
            
        except Exception as e:
            logger.error(f"Device token verification error: {e}")
            return None
    
    @classmethod
    def revoke_device_token(cls, token: str) -> bool:
        """
        ابطال DeviceToken.
        
        Args:
            token: DeviceToken (UUID string)
            
        Returns:
            True اگر ابطال موفق بود
        """
        try:
            device_tokens = DeviceToken.objects.filter(is_active=True)
            
            for dt in device_tokens:
                if check_password(token, dt.token_hash):
                    dt.revoke()
                    logger.info(f"Device token revoked: {dt.id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Device token revocation error: {e}")
            return False
    
    @classmethod
    def revoke_all_devices(cls, user: User) -> int:
        """
        ابطال تمام دستگاه‌های کاربر.
        
        Args:
            user: کاربر
            
        Returns:
            تعداد دستگاه‌های ابطال شده
        """
        count = DeviceToken.objects.filter(
            user=user,
            is_active=True
        ).update(is_active=False)
        
        logger.info(f"Revoked {count} device tokens for user {user.username}")
        return count
    
    @classmethod
    def get_user_devices(cls, user: User) -> List[dict]:
        """
        دریافت لیست دستگاه‌های فعال کاربر.
        
        Args:
            user: کاربر
            
        Returns:
            لیست دیکشنری‌های اطلاعات دستگاه
        """
        devices = []
        
        for dt in DeviceToken.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-last_used_at'):
            devices.append({
                'id': str(dt.id),
                'device_fingerprint': dt.device_fingerprint,
                'user_agent': dt.user_agent,
                'ip_address': dt.ip_address,
                'last_used_at': dt.last_used_at,
                'created_at': dt.created_at,
            })
        
        return devices
