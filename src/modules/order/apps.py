"""
AppConfig for Order Module (M2)
"""
from django.apps import AppConfig


class OrderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.order'
    label = 'order'
    verbose_name = "Order Module (M2)"

    def ready(self):
        """Import hooks to register them with HookSystem."""
        try:
            from . import hooks  # noqa: F401
        except Exception:
            pass
