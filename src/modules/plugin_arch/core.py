"""
M14: Core Plugin System

سه کلاس اصلی:
1. PluginRegistry: مدیریت ماژول‌ها با DB backend
2. HookManager: سیستم event dispatcher  
3. ModuleLoader: بارگذاری داینامیک ماژول‌ها
"""
import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    رجیستری مرکزی ماژول‌ها با persistence در database
    
    تفاوت با نسخه قبلی:
    - قبلی: فقط in-memory (با restart از دست می‌رفت)
    - جدید: database-backed + in-memory cache
    """
    
    _cache: Dict[str, Any] = {}
    _loaded = False
    
    @classmethod
    def _load_from_db(cls):
        """بارگذاری همه پلاگین‌ها از DB به cache"""
        if cls._loaded:
            return
        
        try:
            from .models import Plugin
            plugins = Plugin.objects.filter(status='active')
            for plugin in plugins:
                cls._cache[plugin.name] = {
                    'plugin': plugin,
                    'enabled': True,
                    'version': plugin.version,
                }
            cls._loaded = True
            logger.info(f"✅ {len(cls._cache)} پلاگین از DB بارگذاری شد")
        except Exception as e:
            logger.warning(f"⚠️ خطا در بارگذاری از DB: {e}")
            cls._loaded = True
    
    @classmethod
    def register(cls, name: str, display_name: str, description: str = "", 
                 version: str = "1.0.0", is_system: bool = False,
                 manifest_data: dict = None) -> Any:
        """
        ثبت یک ماژول (create یا update)
        
        اگر وجود نداشته باشد، ایجاد می‌کند.
        اگر وجود داشته باشد، به‌روزرسانی می‌کند.
        """
        from .models import Plugin
        
        plugin, created = Plugin.objects.update_or_create(
            name=name,
            defaults={
                'display_name': display_name,
                'description': description,
                'version': version,
                'is_system': is_system,
                'manifest_data': manifest_data or {},
                'status': 'active',
            }
        )
        
        # اضافه به cache
        cls._cache[name] = {
            'plugin': plugin,
            'enabled': True,
            'version': version,
        }
        
        action = "ایجاد شد" if created else "به‌روزرسانی شد"
        logger.info(f"✅ پلاگین {name} {action}")
        
        return plugin
    
    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        """دریافت یک پلاگین"""
        cls._load_from_db()
        cached = cls._cache.get(name)
        return cached['plugin'] if cached else None
    
    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """بررسی فعال بودن یک پلاگین"""
        cls._load_from_db()
        cached = cls._cache.get(name)
        return cached['enabled'] if cached else False
    
    @classmethod
    def enable(cls, name: str, user=None) -> bool:
        """فعال‌سازی یک پلاگین"""
        from .models import Plugin
        try:
            plugin = Plugin.objects.get(name=name)
            plugin.enable()
            if name in cls._cache:
                cls._cache[name]['enabled'] = True
            logger.info(f"✅ پلاگین {name} فعال شد")
            return True
        except Plugin.DoesNotExist:
            logger.error(f"❌ پلاگین {name} یافت نشد")
            return False
    
    @classmethod
    def disable(cls, name: str, user=None) -> bool:
        """غیرفعال‌سازی یک پلاگین"""
        from .models import Plugin
        try:
            plugin = Plugin.objects.get(name=name)
            plugin.disable()
            if name in cls._cache:
                cls._cache[name]['enabled'] = False
            logger.info(f"⏸️ پلاگین {name} غیرفعال شد")
            return True
        except Plugin.DoesNotExist:
            logger.error(f"❌ پلاگین {name} یافت نشد")
            return False
    
    @classmethod
    def list_all(cls) -> List[Dict]:
        """لیست همه پلاگین‌ها"""
        from .models import Plugin
        return list(Plugin.objects.all().values(
            'name', 'display_name', 'version', 'status', 'is_system'
        ))
    
    @classmethod
    def reload(cls):
        """بارگذاری مجدد از DB"""
        cls._cache.clear()
        cls._loaded = False
        cls._load_from_db()


class HookManager:
    """
    سیستم Event Dispatcher
    
    Event types تعریف‌شده:
    - order.created, order.paid, order.shipped, order.delivered
    - user.login, user.register
    - product.created, product.updated
    - review.created, review.approved
    - lead.created
    - inventory.low
    """
    
    _handlers: Dict[str, List[Callable]] = {}
    
    @classmethod
    def register(cls, event: str, handler: Callable, priority: int = 100):
        """ثبت یک handler برای یک event"""
        if event not in cls._handlers:
            cls._handlers[event] = []
        
        cls._handlers[event].append({
            'handler': handler,
            'priority': priority,
        })
        
        # مرتب‌سازی بر اساس priority
        cls._handlers[event].sort(key=lambda x: x['priority'])
        
        logger.debug(f"🪝 Hook ثبت شد: {event} -> {handler.__name__}")
    
    @classmethod
    def unregister(cls, event: str, handler: Callable):
        """حذف یک handler"""
        if event in cls._handlers:
            cls._handlers[event] = [
                h for h in cls._handlers[event] 
                if h['handler'] != handler
            ]
    
    @classmethod
    def dispatch(cls, event: str, **kwargs) -> List[Any]:
        """
        فراخوانی همه handlers یک event
        
        Args:
            event: نام event (مثلاً 'order.created')
            **kwargs: داده‌های ارسالی به handlers
        
        Returns:
            لیست مقادیر برگشتی از handlers
        """
        from .models import EventLog
        
        results = []
        handlers = cls._handlers.get(event, [])
        
        # لاگ event
        try:
            EventLog.objects.create(
                event_type=event,
                level='info',
                message=f"Event {event} با {len(handlers)} handler",
                data={k: str(v) for k, v in kwargs.items()},
                user=kwargs.get('user'),
                ip_address=kwargs.get('ip_address'),
            )
        except Exception as e:
            logger.warning(f"⚠️ خطا در لاگ event: {e}")
        
        # فراخوانی handlers
        for item in handlers:
            try:
                result = item['handler'](**kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"❌ خطا در handler {item['handler'].__name__}: {e}")
                
                # لاگ خطا
                try:
                    EventLog.objects.create(
                        event_type=event,
                        level='error',
                        message=f"خطا در handler {item['handler'].__name__}: {str(e)}",
                        data={'error': str(e)},
                    )
                except:
                    pass
        
        return results
    
    @classmethod
    def list_hooks(cls) -> Dict[str, int]:
        """لیست همه events و تعداد handlers"""
        return {event: len(handlers) for event, handlers in cls._handlers.items()}


class ModuleLoader:
    """
    بارگذاری داینامیک ماژول‌ها از src/modules/
    
    هر ماژول باید داشته باشد:
    - manifest.yaml (metadata)
    - hooks.py (اختیاری)
    - models.py (اختیاری)
    """
    
    MODULES_DIR = Path(__file__).parent.parent  # src/modules/
    
    @classmethod
    def load_manifest(cls, module_name: str) -> Optional[Dict]:
        """بارگذاری manifest.yaml یک ماژول"""
        manifest_path = cls.MODULES_DIR / module_name / "manifest.yaml"
        
        if not manifest_path.exists():
            return None
        
        try:
            # استفاده از json به جای yaml (ایمن‌تر، بدون dependency جدید)
            # اگر manifest.yaml باشد، با regex ساده به json تبدیل می‌کنیم
            with open(manifest_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # تبدیل ساده YAML به dict (برای manifestهای ساده)
            result = {}
            for line in raw_content.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, _, value = line.partition(':')
                    key = key.strip()
                    value = value.strip()
                    if key and not key.startswith('-'):
                        # حذف کوتیشن‌ها
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        result[key] = value
            return result
        except Exception as e:
            logger.error(f"❌ خطا در خواندن {manifest_path}: {e}")
            return None
    
    @classmethod
    def load_hooks(cls, module_name: str):
        """بارگذاری و ثبت hooks یک ماژول"""
        hooks_module_name = f"modules.{module_name}.hooks"
        
        try:
            hooks_module = importlib.import_module(hooks_module_name)
            
            # اگر register_hooks وجود دارد، فراخوانی کن
            if hasattr(hooks_module, 'register_hooks'):
                hooks_module.register_hooks()
                logger.info(f"✅ hooks ماژول {module_name} بارگذاری شد")
                return True
        except ImportError:
            # hooks.py اختیاری است
            logger.debug(f"ℹ️ {module_name} hooks.py ندارد")
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری hooks {module_name}: {e}")
        
        return False
    
    @classmethod
    def discover_modules(cls) -> List[str]:
        """کشف همه ماژول‌های موجود در src/modules/"""
        if not cls.MODULES_DIR.exists():
            return []
        
        modules = []
        for item in cls.MODULES_DIR.iterdir():
            if item.is_dir() and (item / "manifest.yaml").exists():
                modules.append(item.name)
        
        return sorted(modules)
    
    @classmethod
    def auto_register_all(cls):
        """ثبت خودکار همه ماژول‌های کشف‌شده"""
        modules = cls.discover_modules()
        
        for module_name in modules:
            manifest = cls.load_manifest(module_name)
            if not manifest:
                continue
            
            PluginRegistry.register(
                name=manifest.get('name', module_name),
                display_name=manifest.get('description', module_name),
                description=manifest.get('description', ''),
                version=manifest.get('version', '1.0.0'),
                is_system=manifest.get('is_system', False),
                manifest_data=manifest,
            )
            
            # بارگذاری hooks
            cls.load_hooks(module_name)
        
        logger.info(f"✅ {len(modules)} ماژول کشف و ثبت شد")


# تابع کمکی برای لاگ فعالیت ادمین
def log_admin_activity(user, action: str, resource_type: str, 
                       resource_id: int = None, description: str = "",
                       old_value: dict = None, new_value: dict = None,
                       request=None):
    """
    لاگ فعالیت ادمین (مورد نیاز M3 و M5)
    
    مثال استفاده:
        log_admin_activity(
            user=request.user,
            action='create',
            resource_type='Product',
            resource_id=product.id,
            description=f"محصول {product.name} ایجاد شد",
            request=request,
        )
    """
    from .models import AdminActivityLog
    
    try:
        log = AdminActivityLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_value=old_value or {},
            new_value=new_value or {},
            ip_address=_get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        )
        return log
    except Exception as e:
        logger.error(f"❌ خطا در لاگ activity: {e}")
        return None


def _get_client_ip(request) -> Optional[str]:
    """دریافت IP کاربر از request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
