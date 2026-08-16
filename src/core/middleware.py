"""
Middlewareهای هسته ریهان
- FeatureFlagMiddleware: بررسی پرچم‌ها برای درخواست‌ها
"""
from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound

from .services import FeatureFlagService


class FeatureFlagMiddleware:
    """
    Middleware برای غیرفعال کردن مسیرهای خاص بر اساس Feature Flag.
    اگر ماژولی غیرفعال باشد، مسیرهای آن ۴۰۴ برمی‌گردانند.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # بررسی مسیرهای ماژول‌ها
        # فرمت استاندارد: /modules/<module_name>/...
        path = request.path_info
        if path.startswith('/modules/'):
            parts = path.split('/')
            if len(parts) >= 3:
                module_name = parts[2]
                code = f"MODULE_{module_name.upper()}"
                if not FeatureFlagService.is_enabled(code, default=True):
                    return HttpResponseNotFound(
                        f"Module '{module_name}' is currently disabled"
                    )

        return self.get_response(request)


class AuditLogMiddleware:
    """
    Middleware برای ثبت درخواست‌های ادمین در AuditLog.
    فقط درخواست‌های POST/PUT/DELETE به مسیرهای ادمین را ثبت می‌کند.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # ثبت درخواست‌های تغییردهنده در ادمین
        if (
            request.method in ('POST', 'PUT', 'PATCH', 'DELETE')
            and request.path.startswith('/admin/')
            and hasattr(request, 'user')
            and request.user.is_authenticated
        ):
            try:
                from .models import AuditLog
                ip = self._get_client_ip(request)
                AuditLog.objects.create(
                    user=request.user,
                    action='update',
                    entity_type='admin_request',
                    entity_id=request.path,
                    changes={'method': request.method, 'path': request.path},
                    ip_address=ip,
                )
            except Exception:
                pass

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
