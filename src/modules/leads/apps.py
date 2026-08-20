"""
AppConfig for Leads Module (M9)
"""
from django.apps import AppConfig


class LeadsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.leads'
    label = 'leads'
    verbose_name = "Leads Module (M9)"

    def ready(self):
        """Import signals for auto-notification."""
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
