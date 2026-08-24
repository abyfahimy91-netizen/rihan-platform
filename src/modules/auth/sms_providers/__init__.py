"""
SMS Providers ریهان
منطبق بر ADR-006 بخش ۶: اصل ۹ (مستقل از خارج)

Providers:
- MockSmsProvider: برای توسعه و تست
- KavenegarProvider: Provider اصلی (ایرانی)
- build_provider: ساخت Provider از رکورد دیتابیس (D-103)
"""
from .base import SmsProvider
from .mock import MockSmsProvider
from .kavenegar import KavenegarProvider

__all__ = [
    'SmsProvider',
    'MockSmsProvider',
    'KavenegarProvider',
    'build_provider',
    'PROVIDER_CLASSES',
]

# رجیستری انواع سرویس — نوع‌های جدید اینجا اضافه می‌شوند (D-103)
PROVIDER_CLASSES = {
    'kavenegar': KavenegarProvider,
    # قاصدک / اس‌ام‌اس آی‌آر / فراز — به‌زودی؛ تا آن موقع انتخابشان خطای واضح می‌دهد
}


def build_provider(row):
    """
    ساخت نمونه Provider از رکورد SmsProvider دیتابیس.
    اگر نوع سرویس هنوز پیاده‌سازی نشده باشد None برمی‌گرداند.
    """
    cls = PROVIDER_CLASSES.get(row.provider_type)
    if cls is None:
        return None
    return cls(
        api_key=row.api_key,
        template=row.otp_template,
        sender=getattr(row, 'sender', '') or '',
    )
