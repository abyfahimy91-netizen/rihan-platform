"""
M14: Plugin Registry (D-079, ADR-004)
سیستم ثبت و مدیریت ماژول‌های پلاگین‌محور
"""
class PluginRegistry:
    _plugins = {}

    @classmethod
    def register(cls, plugin_name, app_config):
        cls._plugins[plugin_name] = app_config

    @classmethod
    def get_plugin(cls, plugin_name):
        return cls._plugins.get(plugin_name)

    @classmethod
    def get_all_plugins(cls):
        return cls._plugins
