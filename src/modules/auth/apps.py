"""
AppConfig برای ماژول احراز هویت ریهان (M10)
منطبق بر ADR-006: احراز هویت Passwordless
"""
from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.auth'
    label = 'auth'
    verbose_name = 'احراز هویت (M10)'

    def ready(self):
        """ثبت hook ها و event های ماژول auth"""
        try:
            from . import hooks  # noqa: F401
        except Exception:
            pass
