"""
M14: Hook System (D-079)
سیستم هوک‌ها برای توسعه‌پذیری بدون تغییر کد هسته
"""
class HookManager:
    _hooks = {}

    @classmethod
    def register_hook(cls, hook_name, callback):
        if hook_name not in cls._hooks:
            cls._hooks[hook_name] = []
        cls._hooks[hook_name].append(callback)

    @classmethod
    def execute_hook(cls, hook_name, *args, **kwargs):
        for callback in cls._hooks.get(hook_name, []):
            callback(*args, **kwargs)
