"""
Core Module - هسته معماری پلاگین‌محور ریهان
========================================

اجزا:
- PluginRegistry: ثبت و مدیریت ماژول‌ها
- HookSystem: ارتباط همگام بین ماژول‌ها
- EventBus: ارتباط غیرهمگام بین ماژول‌ها
- FeatureFlag: پرچم‌های قابلیت
- AuditLog: لاگ ممیزی
- Middlewareها
"""
# Eager imports (no Django dependency)
from .plugin_registry import (
    PluginRegistry,
    PluginManifest,
    register_plugin,
    get_plugin,
    get_all_plugins,
)

from .hooks import (
    HookSystem,
    HookNames,
    HOOKS,
    HookStop,
    hooks,
    register_hook,
)

from .events import (
    EventBus,
    EventNames,
    EVENTS,
    Event,
    events,
    subscribe,
)


def __getattr__(name):
    """Lazy import for Django-dependent components."""
    if name == 'FeatureFlagService':
        from .services import FeatureFlagService
        return FeatureFlagService
    if name == 'feature_flags':
        from .services import feature_flags
        return feature_flags
    if name == 'FeatureFlagMiddleware':
        from .middleware import FeatureFlagMiddleware
        return FeatureFlagMiddleware
    if name == 'AuditLogMiddleware':
        from .middleware import AuditLogMiddleware
        return AuditLogMiddleware
    if name == 'FeatureFlag':
        from .models import FeatureFlag
        return FeatureFlag
    if name == 'AuditLog':
        from .models import AuditLog
        return AuditLog

    raise AttributeError(f"module 'core' has no attribute {name!r}")


__all__ = [
    # Plugin Registry
    'PluginRegistry', 'PluginManifest', 'register_plugin',
    'get_plugin', 'get_all_plugins',
    # Hook System
    'HookSystem', 'HookNames', 'HOOKS', 'HookStop',
    'hooks', 'register_hook',
    # Event Bus
    'EventBus', 'EventNames', 'EVENTS', 'Event',
    'events', 'subscribe',
    # Lazy (Django-dependent)
    'FeatureFlagService', 'feature_flags',
    'FeatureFlagMiddleware', 'AuditLogMiddleware',
    'FeatureFlag', 'AuditLog',
]
