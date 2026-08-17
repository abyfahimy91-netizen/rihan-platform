"""
Core Module AppConfig
FIX: No database operations in ready() - all moved to signals.py
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.core'
    label = 'core'
    verbose_name = 'Core Module (M14)'

    def ready(self):
        """
        Only import signals here.
        Database operations moved to post_migrate signal.
        """
        # Import signal handlers to register them
        from . import signals  # noqa: F401
