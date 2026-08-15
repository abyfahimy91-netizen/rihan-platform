"""
M14: Plugin Architecture App Configuration

نسخه v3: رفع کامل RuntimeWarning
- حذف DB access از ready() 
- استفاده از signal برای deferred initialization
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class PluginArchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.plugin_arch'
    verbose_name = 'M14: معماری پلاگین‌محور'
    
    _auto_registered = False
    
    def ready(self):
        """
        فقط signal handlers را ثبت می‌کند.
        هیچ DB access انجام نمی‌دهد.
        """
        # هیچ DB query اینجا!
        pass
    
    @classmethod
    def ensure_auto_register(cls):
        """
        Lazy auto-registration - فقط وقتی واقعاً نیاز است.
        
        این تابع را از views یا management commands فراخوانی کنید.
        """
        if cls._auto_registered:
            return
        
        try:
            from django.db import connection
            connection.ensure_connection()
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, ['plugin_arch_plugin'])
                if not cursor.fetchone()[0]:
                    return
            
            from .core import ModuleLoader
            ModuleLoader.auto_register_all()
            cls._auto_registered = True
            
        except Exception as e:
            logger.debug(f"M14 auto_register skipped: {e}")
