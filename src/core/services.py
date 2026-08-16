"""
Service Layer هسته ریهان
منطبق بر ADR-004: ارتباط بین ماژول‌ها فقط از طریق Service Layer

نکته مهم:
- پرچم‌های ماژول (MODULE_*) باید is_system=False باشند
- ادمین باید بتواند ماژول‌ها را فعال/غیرفعال کند (ADR-004)
- is_system=True فقط برای پرچم‌های حیاتی سیستمی است
"""
from __future__ import annotations

import logging
from typing import List, Optional
from django.core.cache import cache

from .models import FeatureFlag

logger = logging.getLogger(__name__)

CACHE_PREFIX = 'rihan:ff:'
CACHE_TTL = 300  # 5 دقیقه

# ۱۴ ماژول استاندارد ریهان (D-079)
STANDARD_MODULES = [
    ('catalog', 'M1', 'کاتالوگ محصول با روایت‌گری اصیل'),
    ('order', 'M2', 'فرم سفارش و سبد خرید ۳ مرحله‌ای'),
    ('family_panel', 'M3', 'پنل خانواده (مدیریت سفارش‌ها و فاکتور چاپی)'),
    ('supplier_panel', 'M4', 'پنل تأمین‌کننده (مشاهده سفارش‌های مرتبط)'),
    ('rbac', 'M5', 'سیستم دسترسی و نقش‌ها'),
    ('finance', 'M6', 'حساب و کتاب مالی و حاشیه سود'),
    ('tracking', 'M7', 'پیگیری سفارش بدون لاگین'),
    ('reviews', 'M8', 'نظرات، بازخورد و رضایت خریداران'),
    ('leads', 'M9', 'فرم ثبت سرنخ و اطلاع‌رسانی موجودی'),
    ('auth', 'M10', 'احراز هویت مشتری (OTP ۶ رقمی + پسورد)'),
    ('payment', 'M11', 'پرداخت کارت‌به‌کارت و بارگذاری رسید'),
    ('about', 'M12', 'صفحه اصالت و داستان برند ریهان'),
    ('design', 'M13', 'طراحی حرفه‌ای و تجربه کاربری بومی'),
    ('architecture', 'M14', 'معماری افزونه‌محور و Feature Flags'),
]


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
        if code in cls._cache:
            return cls._cache[code]

        cache_key = f"{CACHE_PREFIX}{code}"
        cached = cache.get(cache_key)
        if cached is not None:
            cls._cache[code] = cached
            return cached

        try:
            flag = FeatureFlag.objects.filter(code=code).only('is_enabled').first()
            if flag is None:
                return default
            result = flag.is_enabled
            cache.set(cache_key, result, CACHE_TTL)
            cls._cache[code] = result
            return result
        except Exception as e:
            logger.warning(f"Error checking feature flag {code}: {e}")
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
    def get_disabled_flags(cls) -> List[str]:
        """لیست کد پرچم‌های غیرفعال"""
        try:
            return list(
                FeatureFlag.objects.filter(is_enabled=False)
                .values_list('code', flat=True)
            )
        except Exception:
            return []

    @classmethod
    def clear_cache(cls) -> None:
        """پاکسازی کش (برای تست یا پس از تغییر در ادمین)"""
        cls._cache.clear()
        try:
            codes = FeatureFlag.objects.values_list('code', flat=True)
            for code in codes:
                cache.delete(f"{CACHE_PREFIX}{code}")
        except Exception:
            pass

    @classmethod
    def register_default_flags(cls) -> int:
        """
        ثبت پرچم‌های پیش‌فرض ۱۴ ماژول (D-079).
        
        این متد مستقیماً ۱۴ پرچم ماژول را ثبت می‌کند
        (نه از طریق PluginRegistry که ممکن است خالی باشد).
        
        Returns:
            تعداد پرچم‌های ایجاد شده
        """
        created = 0
        for name, code, description in STANDARD_MODULES:
            flag_code = f"MODULE_{name.upper()}"
            if not FeatureFlag.objects.filter(code=flag_code).exists():
                FeatureFlag.objects.create(
                    code=flag_code,
                    name=description,
                    description=f"فعال‌سازی ماژول {code}: {description}",
                    category=FeatureFlag.Category.MODULE,
                    is_enabled=True,  # پیش‌فرض فعال
                    is_system=False,  # ادمین می‌تواند غیرفعال کند
                )
                created += 1
                logger.info(f"Registered flag: {flag_code}")
        return created

    @classmethod
    def get_module_status(cls) -> dict:
        """
        دریافت وضعیت تمام ماژول‌ها (برای داشبورد ادمین).
        
        Returns:
            dict با ساختار: {module_name: {'code': ..., 'enabled': bool}}
        """
        status = {}
        for name, code, description in STANDARD_MODULES:
            flag_code = f"MODULE_{name.upper()}"
            enabled = cls.is_enabled(flag_code, default=False)
            status[name] = {
                'code': code,
                'description': description,
                'enabled': enabled,
            }
        return status


# نمونه سراسری برای استفاده آسان
feature_flags = FeatureFlagService()
