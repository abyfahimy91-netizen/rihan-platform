"""
M14: Plugin Architecture App Configuration

رفع RuntimeWarning: DB access فقط وقتی connection آماده است
نسخه v2: رفع UnboundLocalError با یک import واحد
"""
from django.apps import AppConfig
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError
import logging

logger = logging.getLogger(__name__)


class PluginArchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.plugin_arch'
    verbose_name = 'M14: معماری پلاگین‌محور'
    
    def ready(self):
        """
        پس از آماده شدن Django، ماژول‌ها را ثبت می‌کند.
        
        نکات مهم:
        - فقط اگر DB connection آماده است اجرا شود
        - در زمان migrations سکوت کند
        - در زمان tests سکوت کند
        """
        # بررسی آماده بودن DB
        try:
            connection.ensure_connection()
        except (OperationalError, ProgrammingError):
            # DB آماده نیست (مثلاً در migrations)
            return
        except Exception as e:
            logger.debug(f"M14: DB not ready: {e}")
            return
        
        # بررسی اینکه جدول Plugin وجود دارد
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, ['plugin_arch_plugin'])
                table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                return
            
            # حالا می‌توانیم auto-register کنیم
            from .core import ModuleLoader
            ModuleLoader.auto_register_all()
            
        except (OperationalError, ProgrammingError) as e:
            # خطاهای DB (جدول وجود ندارد، مهاجرت در جریان)
            logger.debug(f"M14 ready() skipped (DB error): {e}")
        except Exception as e:
            # هر خطای دیگر: سکوت (بهتر از crash)
            logger.debug(f"M14 ready() skipped: {e}")
