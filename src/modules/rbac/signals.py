"""
Signal handlers for RBAC module.
Creates system roles after migration (not during app load).
"""
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_system_roles(sender, **kwargs):
    """
    Create default system roles after migrations are applied.
    Only runs for rbac app migrations.
    """
    if sender.name != 'src.modules.rbac':
        return
    
    try:
        from .services.role_service import RoleService
        RoleService.create_system_roles()
    except Exception as e:
        # Log but don't fail - roles may already exist
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"System roles already exist or error: {e}")
