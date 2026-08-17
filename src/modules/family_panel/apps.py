"""
AppConfig برای ماژول پنل خانواده ریهان (M3)

اصلاح شده:
- بدون FamilyAdmin (استفاده از M10 + M5)
- فقط ActivityLog + SiteSettings
"""
from django.apps import AppConfig


class FamilyPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.family_panel'
    label = 'family_panel'
    verbose_name = 'پنل خانواده (M3)'

    def ready(self):
        """ثبت signal ها و hook های ماژول"""
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
