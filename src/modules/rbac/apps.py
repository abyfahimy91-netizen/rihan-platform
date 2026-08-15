"""
M5: RBAC App Configuration
"""
from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.rbac'
    verbose_name = 'M5: کنترل دسترسی نقش‌محور'
    
    def ready(self):
        """پس از آماده شدن Django"""
        pass  # هیچ auto-registration لازم نیست
