"""
AppConfig برای ماژول core ریهان
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.core'
    label = 'core'
    verbose_name = 'هسته پلتفرم ریهان'

    def ready(self):
        """
        هنگام آماده شدن اپ:
        - ثبت بلوک‌های پیش‌فرض
        - ثبت hook ها و event های سیستمی
        - ثبت پرچم‌های پیش‌فرض ماژول‌ها
        """
        try:
            # import کردن بلوک‌ها برای ثبت خودکار در registry
            from . import blocks  # noqa: F401

            # ثبت پرچم‌های پیش‌فرض ماژول‌ها
            from .services import FeatureFlagService
            FeatureFlagService.register_default_flags()

        except Exception:
            # در زمان migration نباید خطا بدهد
            pass
