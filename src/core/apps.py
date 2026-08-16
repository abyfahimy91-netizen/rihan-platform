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
        - ثبت پرچم‌های پیش‌فرض ماژول‌ها (مستقیم)
        """
        try:
            # import کردن بلوک‌ها برای ثبت خودکار در registry
            from . import blocks  # noqa: F401

            # ثبت پرچم‌های پیش‌فرض ماژول‌ها (مستقیم)
            from .services import FeatureFlagService
            FeatureFlagService.register_default_flags()

        except Exception as e:
            # در زمان migration نباید خطا بدهد
            import logging
            logging.getLogger(__name__).debug(f"Core ready() skipped: {e}")
