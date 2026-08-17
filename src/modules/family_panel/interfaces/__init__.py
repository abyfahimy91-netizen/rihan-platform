"""
Interfaces ماژول family_panel

این interface‌ها برای ارتباط با ماژول‌های دیگر (M1, M2, ...) هستند.
در حال حاضر M1 و M2 بازنویسی نشده‌اند، پس interface‌ها داده mock برمی‌گردانند.
پس از بازنویسی M1 و M2، این interface‌ها به پیاده‌سازی واقعی متصل می‌شوند.
"""
from .m1_interface import M1Interface
from .m2_interface import M2Interface

__all__ = ['M1Interface', 'M2Interface']
