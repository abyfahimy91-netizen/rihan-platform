"""
ماژول RBAC ریهان (M5)
منطبق بر ADR-002 و D-017

نکته مهم: از lazy imports استفاده می‌کنیم تا در زمان django.setup()
خطای AppRegistryNotReady ندهد (مشابه src/core/__init__.py).
"""


def __getattr__(name):
    """Lazy import برای جلوگیری از AppRegistryNotReady"""
    
    # Decorators
    if name == 'require_permission':
        from .decorators import require_permission
        return require_permission
    if name == 'require_role':
        from .decorators import require_role
        return require_role
    if name == 'require_family':
        from .decorators import require_family
        return require_family
    if name == 'require_admin':
        from .decorators import require_admin
        return require_admin
    if name == 'require_supplier':
        from .decorators import require_supplier
        return require_supplier
    if name == 'require_customer':
        from .decorators import require_customer
        return require_customer
    
    # Models
    if name == 'Role':
        from .models import Role
        return Role
    if name == 'UserRole':
        from .models import UserRole
        return UserRole
    
    # Services
    if name == 'RoleService':
        from .services import RoleService
        return RoleService
    if name == 'PermissionChecker':
        from .services import PermissionChecker
        return PermissionChecker
    
    # Middleware
    if name == 'RbacMiddleware':
        from .middleware import RbacMiddleware
        return RbacMiddleware
    
    raise AttributeError(f"module 'src.modules.rbac' has no attribute {name!r}")


__all__ = [
    # Decorators
    'require_permission',
    'require_role',
    'require_family',
    'require_admin',
    'require_supplier',
    'require_customer',
    # Models
    'Role',
    'UserRole',
    # Services
    'RoleService',
    'PermissionChecker',
    # Middleware
    'RbacMiddleware',
]
