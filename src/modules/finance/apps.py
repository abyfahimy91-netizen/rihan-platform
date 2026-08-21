from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.modules.finance"
    label = "finance"
    verbose_name = "ماژول مالی (M6)"

    def ready(self):
        # Import signals
        import src.modules.finance.signals  # noqa: F401
