"""
M14: Event Bus (D-079)
سیستم رویدادها برای ارتباط غیرمستقیم ماژول‌ها (جلوگیری از Coupling)
"""
class EventBus:
    _listeners = {}

    @classmethod
    def subscribe(cls, event_name, callback):
        if event_name not in cls._listeners:
            cls._listeners[event_name] = []
        cls._listeners[event_name].append(callback)

    @classmethod
    def publish(cls, event_name, data=None):
        for callback in cls._listeners.get(event_name, []):
            callback(data)
