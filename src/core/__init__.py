"""
Core Module - هسته معماری پلاگین‌محور ریهان
========================================

این ماژول شامل:
- PluginRegistry: ثبت و مدیریت پلاگین‌ها
- FeatureFlag: مدل پرچم‌های قابلیت (Lazy Load)
- FeatureFlagService: سرویس بررسی پرچم‌ها (Lazy Load)
- Middlewareهای هسته (Lazy Load)

منطبق بر:
- ADR-004 (معماری افزونه‌محور)
- D-079 (معماری پلاگین‌محور)
- ARCHITECTURE-PRINCIPLES (الگوی ۵)

نکته مهم: فقط PluginRegistry و PluginManifest به صورت eager import می‌شوند
چون به Django وابسته نیستند. بقیه موارد lazy import می‌شوند تا
قبل از django.setup() خطا ایجاد نکنند.
"""
# Eager imports (no Django dependency)
from .plugin_registry import (
    PluginRegistry,
    PluginManifest,
    register_plugin,
    get_plugin,
    get_all_plugins,
)


def __getattr__(name):
    """
    Lazy import for Django-dependent components.
    This prevents AppRegistryNotReady errors before django.setup().
    """
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
    # Eager
    'PluginRegistry',
    'PluginManifest',
    'register_plugin',
    'get_plugin',
    'get_all_plugins',
    # Lazy (via __getattr__)
    'FeatureFlagService',
    'feature_flags',
    'FeatureFlagMiddleware',
    'AuditLogMiddleware',
    'FeatureFlag',
    'AuditLog',
]
