"""
M14: Plugin Architecture App Configuration
"""
from django.apps import AppConfig


class PluginArchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.plugin_arch'
    verbose_name = 'M14: معماری پلاگین‌محور'
    
    def ready(self):
        """
        پس از آماده شدن Django:
        1. ثبت همه ماژول‌های موجود
        2. بارگذاری hooks
        """
        try:
            from .core import ModuleLoader
            ModuleLoader.auto_register_all()
        except Exception as e:
            # در زمان migrations نباید crash کند
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ auto_register_all در startup: {e}")
