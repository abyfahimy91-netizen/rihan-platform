# M14: Plugin Architecture, Hook System & Event Bus (ADR-004)
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class HookManager:
    """سیستم قلاب‌ها و رویدادهای هسته پلتفرم ریهان (ADR-004)"""
    _hooks: Dict[str, List[Callable]] = {}

    @classmethod
    def register_hook(cls, event_name: str, handler: Callable):
        if event_name not in cls._hooks:
            cls._hooks[event_name] = []
        cls._hooks[event_name].append(handler)
        logger.info(f"Hook registered: {event_name} -> {handler.__name__}")

    @classmethod
    def trigger_hook(cls, event_name: str, **kwargs) -> List[Any]:
        results = []
        if event_name in cls._hooks:
            for handler in cls._hooks[event_name]:
                try:
                    res = handler(**kwargs)
                    results.append(res)
                except Exception as e:
                    logger.error(f"Error in hook {handler.__name__} on {event_name}: {e}")
        return results

class PluginRegistry:
    """رجیستری رسمی ۱۴ ماژول و پلاگین‌های ریهان"""
    _plugins: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, plugin_id: str, name: str, version: str = "1.0.0", description: str = "", is_system: bool = False):
        cls._plugins[plugin_id] = {
            'id': plugin_id,
            'name': name,
            'version': version,
            'description': description,
            'is_system': is_system,
            'enabled': True
        }

    @classmethod
    def get_all_plugins(cls):
        return cls._plugins

    @classmethod
    def is_plugin_active(cls, plugin_id: str) -> bool:
        return cls._plugins.get(plugin_id, {}).get('enabled', False)

# پیش‌ثبت ماژول‌های فعال ریهان
PluginRegistry.register("M1", "کاتالوگ محصولات و بلوک‌محور", "0.5.6", is_system=True)
PluginRegistry.register("M2", "سبد خرید و سفارش شفاف", "0.5.6", is_system=True)
PluginRegistry.register("M3", "پنل مدیریت خانواده", "0.5.6", is_system=True)
PluginRegistry.register("M7", "پیگیری سفارش بدون لاگین", "0.5.6", is_system=True)
PluginRegistry.register("M10", "احراز هویت پیامکی و رمز پشتیبان", "0.5.6", is_system=True)
PluginRegistry.register("M11", "پرداخت کارت‌به‌کارت", "0.5.6", is_system=True)
PluginRegistry.register("M13", "طراحی تجربه کاربری بومی RTL", "0.5.6", is_system=True)
PluginRegistry.register("M14", "معماری افزونه‌محور و Feature Flags", "0.5.6", is_system=True)

PluginRegistry.register("M5", "سیستم کنترل دسترسی نقش‌محور RBAC", "0.5.8", is_system=True)
