"""
Permission Checker با پشتیبانی wildcard
"""
from __future__ import annotations

from typing import List, Optional

from django.contrib.auth import get_user_model

from .role_service import RoleService

User = get_user_model()


class PermissionChecker:
    """
    بررسی پیشرفته مجوزها.
    
    ویژگی‌ها:
    - پشتیبانی از wildcard (مثال: 'product.*')
    - بررسی چند مجوز به‌صورت AND/OR
    - کش درونی برای عملکرد
    """
    
    _cache: dict = {}
    
    @classmethod
    def check(cls, user: User, permission: str) -> bool:
        """
        بررسی یک مجوز.
        
        Args:
            user: کاربر
            permission: مجوز (مثال: 'product.create' یا 'product.*')
            
        Returns:
            True اگر کاربر مجوز را دارد
        """
        if not user or not user.is_authenticated:
            return False
        
        # بررسی کش
        cache_key = f"{user.id}:{permission}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        primary_role = RoleService.get_user_primary_role(user)
        if not primary_role:
            cls._cache[cache_key] = False
            return False
        
        # admin همه مجوزها را دارد
        if '*' in primary_role.permissions:
            cls._cache[cache_key] = True
            return True
        
        # بررسی دقیق
        if permission in primary_role.permissions:
            cls._cache[cache_key] = True
            return True
        
        # بررسی wildcard (مثال: 'product.*' باید 'product.create' را پوشش دهد)
        for granted_perm in primary_role.permissions:
            if granted_perm.endswith('.*'):
                prefix = granted_perm[:-2]
                if permission.startswith(prefix + '.'):
                    cls._cache[cache_key] = True
                    return True
        
        cls._cache[cache_key] = False
        return False
    
    @classmethod
    def check_all(cls, user: User, permissions: List[str]) -> bool:
        """بررسی همه مجوزها (AND logic)"""
        return all(cls.check(user, p) for p in permissions)
    
    @classmethod
    def check_any(cls, user: User, permissions: List[str]) -> bool:
        """بررسی حداقل یک مجوز (OR logic)"""
        return any(cls.check(user, p) for p in permissions)
    
    @classmethod
    def get_missing_permissions(
        cls, user: User, permissions: List[str]
    ) -> List[str]:
        """دریافت لیست مجوزهای ناکافی"""
        return [p for p in permissions if not cls.check(user, p)]
    
    @classmethod
    def clear_cache(cls) -> None:
        """پاکسازی کش"""
        cls._cache.clear()
