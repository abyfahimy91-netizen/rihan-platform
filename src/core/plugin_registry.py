class PluginRegistry:
    _plugins = {}
    @classmethod
    def register(cls, name, config): cls._plugins[name] = config
    @classmethod
    def get_all(cls): return cls._plugins
