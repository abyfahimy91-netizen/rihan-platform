"""
ماژول RBAC ریهان (M5)
منطبق بر ADR-002 و D-017
"""
from .decorators import (
    require_permission,
    require_role,
    require_family,
    require_admin,
    require_supplier,
    require_customer,
)

__all__ = [
    'require_permission',
    'require_role',
    'require_family',
    'require_admin',
    'require_supplier',
    'require_customer',
]
