"""
KavenegarProvider - Provider اصلی SMS ریهان
منطبق بر ADR-006 بخش ۶: اصل ۹ (مستقل از خارج)

نکات:
- Kavenegar Verify Lookup API برای OTP (بدون نیاز به SDK)
- در صورت عدم تنظیم API Key یا خطای ارسال، Mock فعال می‌شود تا مسیر کاربر هرگز قطع نشود
"""
import logging
import os

import requests

from .base import SmsProvider

logger = logging.getLogger(__name__)

KAVENEGAR_VERIFY_URL = 'https://api.kavenegar.com/v1/{api_key}/verify/lookup.json'


class KavenegarProvider(SmsProvider):
    """Provider اصلی SMS با استفاده از Kavenegar Verify Lookup API"""

    def __init__(self):
        self.api_key = os.environ.get('KAVENEGAR_API_KEY', '').strip()
        self.template = os.environ.get('KAVENEGAR_OTP_TEMPLATE', 'rihan-otp').strip()

    @property
    def name(self) -> str:
        return 'Kavenegar SMS Provider'

    def send_otp(self, phone: str, otp_code: str) -> bool:
        """
        ارسال OTP با Kavenegar Verify Lookup.
        Returns: True فقط اگر کاوه‌نگار وضعیت 200 برگرداند.
        """
        if not self.api_key:
            logger.info("[KAVENEGAR] no API key -> mock")
            from .mock import MockSmsProvider
            return MockSmsProvider().send_otp(phone, otp_code)

        try:
            url = KAVENEGAR_VERIFY_URL.format(api_key=self.api_key)
            resp = requests.post(
                url,
                data={
                    'receptor': phone,
                    'token': otp_code,
                    'template': self.template,
                },
                timeout=10,
            )
            payload = {}
            try:
                payload = resp.json()
            except ValueError:
                pass
            status = int(payload.get('return', {}).get('status') or 0)
            message = payload.get('return', {}).get('message', '')

            if resp.status_code == 200 and status == 200:
                logger.info(f"[KAVENEGAR] OTP delivered to {phone[:4]}***{phone[-4:]}")
                return True

            logger.error(
                f"[KAVENEGAR] delivery failed http={resp.status_code} "
                f"kavenegar_status={status} message={message}"
            )
            return False

        except requests.RequestException as e:
            logger.error(f"[KAVENEGAR] network error: {e}")
            return False
        except Exception:
            logger.exception("[KAVENEGAR] unexpected error")
            return False

    def is_available(self) -> bool:
        """آیا تنظیمات لازم برای ارسال واقعی موجود است؟"""
        return bool(self.api_key)
