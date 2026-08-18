from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.audit'
    verbose_name = 'Audit Log'
