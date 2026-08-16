"""
AppConfig برای ماژول RBAC ریهان (M5)
منطبق بر ADR-002 و D-017
"""
from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.rbac'
    label = 'rbac'
    verbose_name = 'کنترل دسترسی (M5)'

    def ready(self):
        """ایجاد نقش‌های سیستمی پیش‌فرض"""
        try:
            from .services.role_service import RoleService
            RoleService.create_system_roles()
        except Exception:
            # در زمان migration نباید خطا بدهد
            pass
