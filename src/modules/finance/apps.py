from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.modules.finance"
    label = "finance"
    verbose_name = "ماژول مالی (D-113)"
    # محاسبات و سیگنال‌های مالی در src.modules.order.finance ثبت می‌شوند (OrderConfig.ready)
