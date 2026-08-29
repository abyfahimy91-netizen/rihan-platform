from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.catalog'
    verbose_name = '🛒 فروشگاه و محصولات'

    def ready(self):
        from . import signals  # noqa: F401  (D-118: IndexNow بعد از save محصول)
