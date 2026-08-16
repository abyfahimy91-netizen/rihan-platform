"""
PluginRegistry - نقطه مرکزی ثبت و مدیریت پلاگین‌های ریهان
منطبق بر:
- ADR-004 (معماری افزونه‌محور)
- D-079 (معماری پلاگین‌محور)
- ARCHITECTURE-PRINCIPLES (الگوی ۵)
"""
from __future__ import annotations
import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PluginManifest:
    """مانیفست هر پلاگین (ماژول)"""
    name: str                           # نام یکتا (مثلاً 'catalog')
    code: str                           # کد یکتا (مثلاً 'M1')
    version: str = '1.0.0'
    description: str = ''
    author: str = 'Rihan Team'
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    app_module: Optional[str] = None    # مسیر کامل app (مثلاً 'modules.catalog')


class PluginRegistry:
    """
    Singleton Registry برای تمام پلاگین‌ها.
    - ثبت/لغو ثبت پلاگین
    - بررسی وابستگی‌ها
    - دریافت پلاگین‌های فعال
    """

    _plugins: Dict[str, PluginManifest] = {}
    _initialized: bool = False

    def __init__(self):
        raise RuntimeError(
            "PluginRegistry is a Singleton. Use PluginRegistry.get_instance()"
        )

    @classmethod
    def get_instance(cls) -> "PluginRegistry":
        """دریافت نمونه Singleton"""
        if not hasattr(cls, "_instance"):
            # دور زدن __init__ برای ساخت Singleton
            cls._instance = object.__new__(cls)
            cls._instance._plugins = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, manifest: PluginManifest) -> None:
        """ثبت پلاگین با بررسی وابستگی‌ها"""
        if not isinstance(manifest, PluginManifest):
            raise TypeError("manifest must be an instance of PluginManifest")

        if manifest.name in self._plugins:
            raise ValueError(f"Plugin '{manifest.name}' is already registered")

        # بررسی وابستگی‌ها
        for dep in manifest.dependencies:
            if dep not in self._plugins:
                raise ValueError(
                    f"Plugin '{manifest.name}' depends on '{dep}' which is not registered"
                )

        self._plugins[manifest.name] = manifest

    def unregister(self, name: str) -> None:
        """لغو ثبت پلاگین (فقط در صورتی که هیچ پلاگین دیگری به آن وابسته نباشد)"""
        if name not in self._plugins:
            raise ValueError(f"Plugin '{name}' is not registered")

        # بررسی وابستگی‌های معکوس
        for other_name, other_manifest in self._plugins.items():
            if name in other_manifest.dependencies:
                raise ValueError(
                    f"Cannot unregister '{name}': plugin '{other_name}' depends on it"
                )

        del self._plugins[name]

    def get(self, name: str) -> Optional[PluginManifest]:
        """دریافت مانیفست یک پلاگین"""
        return self._plugins.get(name)

    def get_all(self) -> Dict[str, PluginManifest]:
        """دریافت تمام پلاگین‌های ثبت‌شده"""
        return dict(self._plugins)

    def get_active(self) -> List[PluginManifest]:
        """دریافت لیست پلاگین‌های فعال"""
        return [m for m in self._plugins.values() if m.is_active]

    def is_registered(self, name: str) -> bool:
        """بررسی ثبت‌شدن یک پلاگین"""
        return name in self._plugins

    def clear(self) -> None:
        """پاکسازی کامل registry (فقط برای تست)"""
        self._plugins.clear()

    @classmethod
    def reset(cls) -> None:
        """Reset کامل (برای تست‌ها)"""
        if hasattr(cls, "_instance"):
            del cls._instance


# نمونه سراسری برای استفاده آسان
_registry = PluginRegistry.get_instance()


def register_plugin(manifest: PluginManifest) -> None:
    """تابع کمکی برای ثبت پلاگین"""
    _registry.register(manifest)


def get_plugin(name: str) -> Optional[PluginManifest]:
    """تابع کمکی برای دریافت پلاگین"""
    return _registry.get(name)


def get_all_plugins() -> Dict[str, PluginManifest]:
    """تابع کمکی برای دریافت تمام پلاگین‌ها"""
    return _registry.get_all()
