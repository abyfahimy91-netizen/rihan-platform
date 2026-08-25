"""
MockSmsProvider - برای توسعه و تست
"""
import logging
from typing import Optional

from .base import SmsProvider

logger = logging.getLogger(__name__)


class MockSmsProvider(SmsProvider):
    """
    Provider شبیه‌سازی برای توسعه و تست.
    OTP را در لاگ نمایش می‌دهد.
    """
    
    @property
    def name(self) -> str:
        return 'Mock SMS Provider'
    
    def send_otp(self, phone: str, otp_code: str) -> bool:
        """ارسال OTP (فقط لاگ می‌شود)"""
        logger.info(
            f"[MOCK SMS] Phone: {phone}, OTP: {otp_code}"
        )
        return True

    def send_sms(self, phone: str, message: str) -> bool:
        """پیامک عملیاتی — در محیط توسعه فقط لاگ می‌شود"""
        logger.info("[MOCK SMS] Phone: %s | Message: %s", phone, message.replace('\n', ' ⏎ '))
        return True
    
    def is_available(self) -> bool:
        """همیشه در دسترس است"""
        return True
