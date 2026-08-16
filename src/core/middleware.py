"""
Middlewareهای هسته ریهان
- FeatureFlagMiddleware: بررسی پرچم‌ها برای درخواست‌ها
- AuditLogMiddleware: ثبت درخواست‌های ادمین

اصلاح ناظر: پشتیبانی از مسیرهای سفارشی هر ماژول
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound

from .services import FeatureFlagService


class FeatureFlagMiddleware:
    """
    Middleware برای غیرفعال کردن مسیرهای خاص بر اساس Feature Flag.
    اگر ماژولی غیرفعال باشد، مسیرهای آن ۴۰۴ برمی‌گردانند.

    اصلاح ناظر: پشتیبانی از مسیرهای سفارشی هر ماژول.
    ماژول‌ها می‌توانند مسیرهای خود را در manifest ثبت کنند.
    """

    # مسیرهای پیش‌فرض هر ماژول (می‌تواند در manifest بازنویسی شود)
    DEFAULT_MODULE_PATHS: Dict[str, str] = {
        'catalog': '/catalog/',
        'orders': '/orders/',
        'family_panel': '/family/',
        'supplier_panel': '/supplier/',
        'rbac': '/rbac/',
        'finance': '/finance/',
        'tracking': '/track/',
        'reviews': '/reviews/',
        'leads': '/leads/',
        'auth': '/auth/',
        'payment': '/payment/',
        'about': '/about/',
        'design': '/design/',
        'architecture': '/architecture/',
    }

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self._path_cache: Dict[str, str] = {}
        self._build_path_cache()

    def _build_path_cache(self) -> None:
        """ساخت کش مسیرها از Registry"""
        from .plugin_registry import get_all_plugins
        for name, manifest in get_all_plugins().items():
            # اگر ماژول مسیر سفارشی دارد، از manifest بخوان
            custom_path = manifest.config.get('base_path')
            if custom_path:
                self._path_cache[custom_path] = f"MODULE_{name.upper()}"
            else:
                # مسیر پیش‌فرض
                default = self.DEFAULT_MODULE_PATHS.get(name, f"/{name}/")
                self._path_cache[default] = f"MODULE_{name.upper()}"

        # مسیر استاندارد /modules/
        self._path_cache['/modules/'] = None  # نیاز به بررسی دقیق‌تر دارد

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path_info

        # بررسی مسیرهای /modules/
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

        # بررسی مسیرهای سفارشی
        for base_path, code in self._path_cache.items():
            if code and path.startswith(base_path):
                if not FeatureFlagService.is_enabled(code, default=True):
                    return HttpResponseNotFound(
                        f"Module '{code.replace('MODULE_', '')}' is currently disabled"
                    )
                break

        return self.get_response(request)


class AuditLogMiddleware:
    """
    Middleware برای ثبت درخواست‌های ادمین در AuditLog.
    فقط درخواست‌های POST/PUT/DELETE به مسیرهای ادمین را ثبت می‌کند.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
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
