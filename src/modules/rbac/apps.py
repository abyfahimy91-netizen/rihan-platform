"""
AppConfig for Rihan RBAC Module (M5)
Based on ADR-002 and D-017
FIX: Remove database access in ready() to avoid RuntimeWarning
"""
from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.rbac'
    label = 'rbac'
    verbose_name = 'Role-Based Access Control (M5)'

    def ready(self):
        """
        Import hooks only. Database operations moved to post_migrate signal.
        """
        # Import signal handlers (must be here for Django to register them)
        from . import signals  # noqa: F401
