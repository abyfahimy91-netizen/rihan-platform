"""
سرویس ارسال پیامک (D-103) — مدیریت متمرکز سرویس‌دهنده‌ها

منطق:
۱. سرویس «فعال» (انتخاب ادمین) اول امتحان می‌شود
۲. اگر شکست خورد، بقیه سرویس‌های دارای کلید به ترتیب «اولویت» امتحان می‌شوند (failover خودکار)
۳. اگر هیچ سرویسی نبود/شکست خورد، مسیر Mock طبق تنظیمات ادمین باز می‌گردد
هر نتیجه در فیلد last_status رکورد سرویس ثبت می‌شود تا ادمین وضعیت را ببیند.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from django.utils import timezone

from ..models import AuthSettings, SmsProvider
from ..sms_providers import MockSmsProvider, build_provider

logger = logging.getLogger(__name__)


class SmsService:
    """ارسال OTP از طریق سرویس‌دهنده فعال با جایگزینی خودکار"""

    @staticmethod
    def get_active_row() -> Optional[SmsProvider]:
        return SmsProvider.objects.filter(is_active=True).first()

    @staticmethod
    def _mark(row: SmsProvider, status: str, used: bool = False):
        """ثبت وضعیت آخرین ارسال روی رکورد سرویس (برای دید ادمین)"""
        try:
            row.last_status = status[:250]
            if used:
                row.last_used_at = timezone.now()
            row.save(update_fields=['last_status', 'last_used_at'])
        except Exception:
            pass

    @classmethod
    def send_otp(cls, phone: str, code: str) -> Tuple[bool, str]:
        """
        ارسال کد OTP.
        خروجی: (sent, provider_name) — sent=False یعنی هیچ سرویسی موفق نشد.
        """
        rows = list(SmsProvider.objects.all())
        active = [r for r in rows if r.is_active]
        standbys = sorted(
            (r for r in rows if not r.is_active and r.api_key.strip()),
            key=lambda r: (r.priority, r.id),
        )
        ordered = active + standbys

        if not ordered:
            # هیچ رکوردی نیست → رفتار قدیمی: کاوه‌نگار از متغیر محیطی (سازگاری عقب)
            from ..sms_providers import KavenegarProvider
            env_provider = KavenegarProvider()
            if env_provider.is_available() and env_provider.send_otp(phone, code):
                return True, 'env:kavenegar'
            return False, ''

        errors = []
        for row in ordered:
            provider = build_provider(row)
            if provider is None:
                cls._mark(row, f'نوع سرویس «{row.get_provider_type_display()}» هنوز پیاده‌سازی نشده است')
                errors.append(f'{row.name}: نوع پشتیبانی‌نشده')
                continue
            if not provider.is_available():
                cls._mark(row, 'کلید API تنظیم نشده است')
                errors.append(f'{row.name}: بدون کلید')
                continue
            try:
                ok = provider.send_otp(phone, code)
            except Exception as e:  # قطعی شبکه و... نباید ویو را بترکاند
                logger.warning('SMS send failed via %s: %s', row.name, e)
                ok = False
            if ok:
                cls._mark(row, '✅ ارسال موفق', used=True)
                return True, row.name
            cls._mark(row, '❌ ارسال ناموفق — سرویس جایگزین امتحان شد')
            errors.append(f'{row.name}: ناموفق')

        logger.error('All SMS providers failed: %s', ' | '.join(errors))
        return False, ''

    @classmethod
    def send_otp_or_mock(cls, phone: str, code: str) -> Tuple[bool, bool, str]:
        """
        ارسال OTP با fallback به Mock طبق تنظیمات ادمین.
        خروجی: (sent_via_sms, show_code_allowed, provider_name)
        show_code_allowed یعنی مجاز است کد روی صفحه نمایش داده شود.
        """
        settings = AuthSettings.load()
        sent, provider_name = cls.send_otp(phone, code)
        if sent:
            return True, False, provider_name

        if settings.show_code_on_sms_fail:
            MockSmsProvider().send_otp(phone, code)  # فقط لاگ
            return False, True, 'screen'
        return False, False, ''

    # ────────────────────────────────────────────────
    # D-105: پیامک عملیاتی (غیر OTP) — اطلاع به تامین‌کننده و مشتری
    # همان زنجیره failover؛ بدون fallback صفحه (پیامک عملیاتی جای نمایش ندارد)
    # ────────────────────────────────────────────────

    @classmethod
    def send_sms(cls, phone: str, message: str) -> Tuple[bool, str]:
        """
        ارسال پیامک متنی.
        خروجی: (sent, provider_name)
        """
        message = (message or '').strip()
        if not phone or not message:
            return False, ''

        rows = list(SmsProvider.objects.all())
        active = [r for r in rows if r.is_active]
        standbys = sorted(
            (r for r in rows if not r.is_active and r.api_key.strip()),
            key=lambda r: (r.priority, r.id),
        )
        ordered = active + standbys

        if not ordered:
            from ..sms_providers import KavenegarProvider
            env_provider = KavenegarProvider()
            try:
                if env_provider.is_available() and env_provider.send_sms(phone, message):
                    return True, 'env:kavenegar'
            except Exception as e:
                logger.warning('env kavenegar send_sms failed: %s', e)
            return False, ''

        errors = []
        for row in ordered:
            provider = build_provider(row)
            if provider is None:
                errors.append(f'{row.name}: نوع پشتیبانی‌نشده')
                continue
            if not provider.is_available():
                cls._mark(row, 'کلید API تنظیم نشده است')
                errors.append(f'{row.name}: بدون کلید')
                continue
            try:
                ok = provider.send_sms(phone, message)
            except Exception as e:
                logger.warning('SMS send failed via %s: %s', row.name, e)
                ok = False
            if ok:
                cls._mark(row, '✅ ارسال موفق', used=True)
                return True, row.name
            cls._mark(row, '❌ پیامک عملیاتی ناموفق')
            errors.append(f'{row.name}: ناموفق')

        logger.error('All SMS providers failed for send_sms: %s', ' | '.join(errors))
        return False, ''
