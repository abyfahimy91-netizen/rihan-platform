"""
Signal handlers for Core module.
Registers default feature flags after migrations (not during app load).
This prevents RuntimeWarning about database access during initialization.
"""
import logging
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def register_default_feature_flags(sender, **kwargs):
    """
    Register default feature flags after migrations are applied.
    Only runs for core app migrations.
    """
    if sender.name != 'src.core':
        return
    
    try:
        from .services import FeatureFlagService
        created = FeatureFlagService.register_default_flags()
        if created > 0:
            logger.info(f"Created {created} default feature flags")
    except Exception as e:
        logger.debug(f"Feature flags already exist or error: {e}")
