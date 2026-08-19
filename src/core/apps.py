"""
Core Module AppConfig
FIX: No database operations in ready() - all moved to signals.py
FIX D-081: Import blocks in ready() to register them in block_registry
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.core'
    label = 'core'
    verbose_name = 'Core Module (M14)'

    def ready(self):
        """
        Only import signals and blocks here.
        Database operations moved to post_migrate signal.
        """
        # Import signal handlers to register them
        from . import signals  # noqa: F401
        
        # Import blocks to register them in block_registry (D-081)
        from . import blocks  # noqa: F401
