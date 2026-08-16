"""
Service Layer هسته ریهان
منطبق بر ADR-004: ارتباط بین ماژول‌ها فقط از طریق Service Layer

نکته مهم:
- پرچم‌های ماژول (MODULE_*) باید is_system=False باشند
- ادمین باید بتواند ماژول‌ها را فعال/غیرفعال کند (ADR-004)
- is_system=True فقط برای پرچم‌های حیاتی سیستمی است
"""
from __future__ import annotations

from typing import List, Optional
from django.core.cache import cache

from .models import FeatureFlag


CACHE_PREFIX = 'rihan:ff:'
CACHE_TTL = 300  # 5 دقیقه


class FeatureFlagService:
    """
    سرویس مرکزی برای بررسی وضعیت پرچم‌ها.
    - کش درونی برای عملکرد بالا
    - API ساده برای استفاده در ماژول‌ها
    """

    _instance = None
    _cache: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def is_enabled(cls, code: str, default: bool = False) -> bool:
        """
        بررسی فعال بودن یک پرچم.
        اول کش، بعد دیتابیس.
        اگر پرچم وجود نداشت، مقدار پیش‌فرض برمی‌گرداند.
        """
        # بررسی کش درونی
        if code in cls._cache:
            return cls._cache[code]

        # بررسی کش Django
        cache_key = f"{CACHE_PREFIX}{code}"
        cached = cache.get(cache_key)
        if cached is not None:
            cls._cache[code] = cached
            return cached

        # بررسی دیتابیس
        try:
            flag = FeatureFlag.objects.filter(code=code).only('is_enabled').first()
            if flag is None:
                return default
            result = flag.is_enabled
            cache.set(cache_key, result, CACHE_TTL)
            cls._cache[code] = result
            return result
        except Exception:
            # اگر دیتابیس آماده نباشد (مثلاً در migration)
            return default

    @classmethod
    def require_enabled(cls, code: str) -> None:
        """اگر پرچم فعال نباشد، استثنا ایجاد می‌کند"""
        from django.core.exceptions import PermissionDenied
        if not cls.is_enabled(code):
            raise PermissionDenied(f"Feature '{code}' is disabled")

    @classmethod
    def get_enabled_flags(cls) -> List[str]:
        """لیست کد پرچم‌های فعال"""
        try:
            return list(
                FeatureFlag.objects.filter(is_enabled=True)
                .values_list('code', flat=True)
            )
        except Exception:
            return []

    @classmethod
    def clear_cache(cls) -> None:
        """پاکسازی کش (برای تست یا پس از تغییر در ادمین)"""
        cls._cache.clear()
        # پاکسازی کش Django برای تمام کدها
        try:
            codes = FeatureFlag.objects.values_list('code', flat=True)
            for code in codes:
                cache.delete(f"{CACHE_PREFIX}{code}")
        except Exception:
            pass

    @classmethod
    def register_default_flags(cls) -> int:
        """
        ثبت پرچم‌های پیش‌فرض ۱۴ ماژول (برای شروع پروژه).
        فقط اگر وجود نداشته باشند ثبت می‌شوند.

        نکته: پرچم‌های ماژول با is_system=False ایجاد می‌شوند
        تا ادمین بتواند آن‌ها را فعال/غیرفعال کند (ADR-004).
        """
        from .plugin_registry import get_all_plugins
        created = 0
        for name, manifest in get_all_plugins().items():
            code = f"MODULE_{name.upper()}"
            if not FeatureFlag.objects.filter(code=code).exists():
                FeatureFlag.objects.create(
                    code=code,
                    name=manifest.description or manifest.name,
                    description=f"فعال‌سازی ماژول {name}",
                    category=FeatureFlag.Category.MODULE,
                    is_enabled=manifest.is_active,
                    is_system=False,  # ✅ اصلاح: ماژول‌ها قابل غیرفعال‌سازی هستند
                )
                created += 1
        return created


# نمونه سراسری برای استفاده آسان
feature_flags = FeatureFlagService()
