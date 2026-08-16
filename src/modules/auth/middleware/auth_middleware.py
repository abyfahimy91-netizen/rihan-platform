"""
DeviceToken Middleware
منطبق بر ADR-006 بخش ۵: سه کانال احراز هویت

این Middleware:
1. Session را بررسی می‌کند (کانال Web)
2. DeviceToken را بررسی می‌کند (کانال Device)
3. request.user را تنظیم می‌کند
"""
from __future__ import annotations

import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class DeviceTokenMiddleware:
    """
    Middleware برای Device Remembering.
    
    منطبق بر ADR-006 بخش ۵:
    - اگر Session معتبر است، از آن استفاده کن
    - اگر Session معتبر نیست، DeviceToken را بررسی کن
    """
    
    DEVICE_TOKEN_HEADER = 'HTTP_X_DEVICE_TOKEN'
    DEVICE_TOKEN_COOKIE = 'rihan_device_token'
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # اگر Session معتبر است، نیازی به DeviceToken نیست
        if hasattr(request, 'user') and request.user.is_authenticated:
            return self.get_response(request)
        
        # بررسی DeviceToken در Header
        device_token = request.META.get(self.DEVICE_TOKEN_HEADER)
        
        # بررسی DeviceToken در Cookie
        if not device_token:
            device_token = request.COOKIES.get(self.DEVICE_TOKEN_COOKIE)
        
        # اگر DeviceToken وجود دارد، تأیید کن
        if device_token:
            from ..services.device_service import DeviceService
            user = DeviceService.verify_device_token(device_token)
            
            if user:
                # تنظیم request.user
                request.user = user
                logger.info(
                    f"Device token authenticated: {user.username}"
                )
        
        return self.get_response(request)
