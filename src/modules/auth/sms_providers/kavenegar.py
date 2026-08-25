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
KAVENEGAR_SMS_URL = 'https://api.kavenegar.com/v1/{api_key}/sms/send.json'


class KavenegarProvider(SmsProvider):
    """Provider اصلی SMS با استفاده از Kavenegar Verify Lookup API"""

    def __init__(self, api_key: str = None, template: str = None, sender: str = None):
        # D-103: اولویت با مقادیر دیتابیس (پنل ادمین)؛ fallback به متغیرهای محیطی
        self.api_key = (api_key or os.environ.get('KAVENEGAR_API_KEY', '') or '').strip()
        self.template = (template or os.environ.get('KAVENEGAR_OTP_TEMPLATE', '') or 'rihan-otp').strip()
        self.sender = (sender or '').strip()

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

    # ────────────────────────────────────────────────
    # D-105: پیامک متنی عملیاتی (اطلاع به تامین‌کننده / کد رهگیری مشتری)
    # ────────────────────────────────────────────────
    def send_sms(self, phone: str, message: str) -> bool:
        """ارسال پیامک ساده با Kavenegar SMS API (بدون قالب)"""
        if not self.api_key:
            logger.info('[KAVENEGAR] no API key -> send_sms skipped')
            return False
        try:
            url = KAVENEGAR_SMS_URL.format(api_key=self.api_key)
            data = {'receptor': phone, 'message': message}
            if self.sender:
                data['sender'] = self.sender
            resp = requests.post(url, data=data, timeout=10)
            payload = {}
            try:
                payload = resp.json()
            except ValueError:
                pass
            status = int(payload.get('return', {}).get('status') or 0)
            if resp.status_code == 200 and status == 200:
                logger.info('[KAVENEGAR] SMS delivered to %s***%s', phone[:4], phone[-4:])
                return True
            logger.error(
                '[KAVENEGAR] send_sms failed http=%s kavenegar_status=%s message=%s',
                resp.status_code, status, payload.get('return', {}).get('message', ''),
            )
            return False
        except requests.RequestException as e:
            logger.error('[KAVENEGAR] network error on send_sms: %s', e)
            return False
        except Exception:
            logger.exception('[KAVENEGAR] unexpected error on send_sms')
            return False

    def is_available(self) -> bool:
        """آیا تنظیمات لازم برای ارسال واقعی موجود است؟"""
        return bool(self.api_key)
