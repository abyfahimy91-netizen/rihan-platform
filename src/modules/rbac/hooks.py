"""
Hook handlers ماژول RBAC
منطبق بر D-079 بخش ۸.۱
"""
import logging

from core.hooks import hooks, HOOKS
from core.events import events, EVENTS

logger = logging.getLogger(__name__)


def log_role_assignment(user=None, role=None, **kwargs):
    """لاگ اعطای نقش"""
    if user and role:
        logger.info(f"Role assigned: {role} to {user.username}")


def publish_role_change_event(user=None, role=None, action='assigned', **kwargs):
    """انتشار رویداد تغییر نقش"""
    if user:
        events.publish(
            'rbac.role_changed',
            {
                'username': user.username,
                'role': role,
                'action': action,
            },
            source_module='rbac'
        )


# ثبت hooks
hooks.register(
    'rbac.role_assigned',
    log_role_assignment,
    priority=10,
    module='rbac'
)

hooks.register(
    'rbac.role_assigned',
    publish_role_change_event,
    priority=20,
    module='rbac'
)
