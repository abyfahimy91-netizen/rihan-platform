"""
KavenegarProvider - Provider اصلی SMS ریهان
منطبق بر ADR-006 بخش ۶: اصل ۹ (مستقل از خارج)

نکات:
- Kavenegar Verify API برای OTP
- در صورت عدم تنظیم API Key، از Mock استفاده می‌شود
"""
import logging
import os
from typing import Optional

from .base import SmsProvider

logger = logging.getLogger(__name__)


class KavenegarProvider(SmsProvider):
    """
    Provider اصلی SMS با استفاده از Kavenegar Verify API.
    
    منطبق بر ADR-006:
    - سرویس SMS داخلی ایران
    - بدون نیاز به حساب ارزی
    - قابلیت Verify (OTP آماده)
    """
    
    def __init__(self):
        self.api_key = os.environ.get('KAVENEGAR_API_KEY', '')
        self.template = os.environ.get('KAVENEGAR_OTP_TEMPLATE', 'rihan-otp')
    
    @property
    def name(self) -> str:
        return 'Kavenegar SMS Provider'
    
    def send_otp(self, phone: str, otp_code: str) -> bool:
        """
        ارسال OTP با استفاده از Kavenegar Verify API.
        
        در صورت عدم تنظیم API Key، از Mock استفاده می‌شود.
        """
        if not self.api_key:
            logger.warning(
                "KAVENEGAR_API_KEY not set, using MockSmsProvider"
            )
            from .mock import MockSmsProvider
            return MockSmsProvider().send_otp(phone, otp_code)
        
        try:
            # در نسخه واقعی، از kavenegar SDK استفاده می‌شود:
            # from kavenegar import KavenegarAPI
            # api = KavenegarAPI(self.api_key)
            # params = {
            #     'receptor': phone,
            #     'template': self.template,
            #     'token': otp_code,
            # }
            # response = api.verify_lookup(params)
            # return response is not None
            
            # فعلاً Mock (تا زمان فعال‌سازی Kavenegar)
            logger.info(
                f"[KAVENEGAR] Sending OTP to {phone}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Kavenegar error: {e}")
            return False
    
    def is_available(self) -> bool:
        """بررسی در دسترس بودن Kavenegar"""
        return bool(self.api_key)
