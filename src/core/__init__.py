"""
Core Module - هسته معماری پلاگین‌محور ریهان
"""
from .plugin_registry import (
    PluginRegistry, PluginManifest, register_plugin,
    get_plugin, get_all_plugins,
)
from .hooks import (
    HookSystem, HookNames, HOOKS, HookStop, hooks, register_hook,
)
from .events import (
    EventBus, EventNames, EVENTS, Event, events, subscribe,
)
from .block_base import BaseBlock, SimpleBlock, BlockValidationError
from .block_registry import BlockRegistry, block_registry, register_block


def __getattr__(name):
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
    'PluginRegistry', 'PluginManifest', 'register_plugin', 'get_plugin', 'get_all_plugins',
    'HookSystem', 'HookNames', 'HOOKS', 'HookStop', 'hooks', 'register_hook',
    'EventBus', 'EventNames', 'EVENTS', 'Event', 'events', 'subscribe',
    'BaseBlock', 'SimpleBlock', 'BlockValidationError',
    'BlockRegistry', 'block_registry', 'register_block',
    'FeatureFlagService', 'feature_flags', 'FeatureFlagMiddleware',
    'AuditLogMiddleware', 'FeatureFlag', 'AuditLog',
]
