"""
Session Service برای ماژول احراز هویت
منطبق بر ADR-006 بخش ۵: Session/Token Strategy

سه کانال:
- کانال ۱: Web (Session cookie)
- کانال ۲: API (JWT - در MVP فعال نیست)
- کانال ۳: Device Remembering
"""
from __future__ import annotations

import logging
from typing import Optional

from django.contrib.auth import get_user_model, login, logout

logger = logging.getLogger(__name__)

User = get_user_model()


class SessionService:
    """
    سرویس مدیریت Session.
    
    منطبق بر ADR-006 بخش ۵:
    - کانال ۱: Web Session (HttpOnly, Secure, SameSite=Strict)
    - طول عمر: ۳۰ روز با تمدید خودکار
    """
    
    SESSION_TTL_DAYS = 30
    
    @classmethod
    def create_session(cls, request, user: User) -> None:
        """
        ایجاد Session برای کاربر.
        
        Args:
            request: HttpRequest
            user: کاربر
        """
        login(request, user)
        request.session.set_expiry(cls.SESSION_TTL_DAYS * 24 * 60 * 60)
        logger.info(f"Session created for user {user.username}")
    
    @classmethod
    def destroy_session(cls, request) -> None:
        """
        حذف Session کاربر.
        
        Args:
            request: HttpRequest
        """
        logout(request)
        logger.info("Session destroyed")
    
    @classmethod
    def get_current_user(cls, request) -> Optional[User]:
        """
        دریافت کاربر فعلی از Session.
        
        Args:
            request: HttpRequest
            
        Returns:
            user یا None
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user
        return None
    
    @classmethod
    def refresh_session(cls, request) -> None:
        """
        تمدید Session (sliding window).
        
        Args:
            request: HttpRequest
        """
        if hasattr(request, 'session'):
            request.session.set_expiry(cls.SESSION_TTL_DAYS * 24 * 60 * 60)
