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
        """Import hooks and signals to register them."""
        try:
            from . import hooks  # noqa: F401
        except Exception:
            pass
        
        # D-082: Import signals for auto status history capture
        try:
            from . import signals  # noqa: F401
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to import signals: {e}")
