"""
Hook handlers ماژول احراز هویت
منطبق بر ADR-006 و D-079

این فایل hook های ماژول auth را به HookSystem ثبت می‌کند.
"""
from core.hooks import hooks, HOOKS

# ثبت hook برای لاگ ورود
def log_user_login(user=None, **kwargs):
    """لاگ ورود کاربر"""
    import logging
    logger = logging.getLogger(__name__)
    if user:
        logger.info(f"User logged in: {user.username}")

# ثبت در HookSystem
hooks.register(
    HOOKS.AFTER_USER_LOGIN,
    log_user_login,
    priority=10,
    module='auth'
)
