"""
Hook System ریهان
==================
برای ارتباط همگام (synchronous) بین ماژول‌ها.

تفاوت با EventBus:
- Hook: برای تغییر داده یا متوقف کردن فرآیند (sync, با priority)
- Event: برای اطلاع‌رسانی (async fire-and-forget)

منطبق بر:
- D-079 بخش ۸.۱ (Hook System)
- ADR-004 (Isolation بین ماژول‌ها)
- ARCHITECTURE-PRINCIPLES (الگوی ۵)

نحوه استفاده در یک ماژول:
    from core.hooks import hooks, HOOKS

    # ثبت handler
    hooks.register(HOOKS.BEFORE_ORDER_CREATE, my_validator, priority=5)

    # trigger از ماژول دیگر
    results = hooks.trigger(HOOKS.BEFORE_ORDER_CREATE, order=order)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from weakref import WeakMethod

logger = logging.getLogger(__name__)


class HookNames:
    """
    نام‌های استاندارد hookها.
    ماژول‌ها باید از این کلاس استفاده کنند، نه رشته مستقیم.
    این کار از typo جلوگیری می‌کند و IDE autocomplete می‌دهد.
    """

    # --- Order Hooks (M2) ---
    BEFORE_ORDER_CREATE = 'before_order_create'
    AFTER_ORDER_CREATE = 'after_order_create'
    BEFORE_ORDER_STATUS_CHANGE = 'before_order_status_change'
    AFTER_ORDER_STATUS_CHANGE = 'after_order_status_change'

    # --- Payment Hooks (M11) ---
    BEFORE_PAYMENT_CONFIRM = 'before_payment_confirm'
    AFTER_PAYMENT_CONFIRM = 'after_payment_confirm'
    PAYMENT_REJECTED = 'payment_rejected'

    # --- Cart Hooks (M2) ---
    BEFORE_CART_ADD = 'before_cart_add'
    AFTER_CART_ADD = 'after_cart_add'
    BEFORE_CART_REMOVE = 'before_cart_remove'
    AFTER_CART_REMOVE = 'after_cart_remove'

    # --- Catalog Hooks (M1) ---
    BEFORE_PRODUCT_SAVE = 'before_product_save'
    AFTER_PRODUCT_SAVE = 'after_product_save'
    BEFORE_PRODUCT_DELETE = 'before_product_delete'

    # --- Auth Hooks (M10) ---
    BEFORE_USER_LOGIN = 'before_user_login'
    AFTER_USER_LOGIN = 'after_user_login'
    BEFORE_USER_REGISTER = 'before_user_register'
    AFTER_USER_REGISTER = 'after_user_register'

    # --- Review Hooks (M8) ---
    BEFORE_REVIEW_CREATE = 'before_review_create'
    AFTER_REVIEW_CREATE = 'after_review_create'
    AFTER_REVIEW_APPROVE = 'after_review_approve'

    # --- Lead Hooks (M9) ---
    AFTER_LEAD_CREATE = 'after_lead_create'
    AFTER_LEAD_FULFILLED = 'after_lead_fulfilled'

    # --- Feature Flag Hooks (M14) ---
    BEFORE_FLAG_CHANGE = 'before_flag_change'
    AFTER_FLAG_CHANGE = 'after_flag_change'

    # --- Block Hooks ---
    BEFORE_BLOCK_RENDER = 'before_block_render'
    AFTER_BLOCK_RENDER = 'after_block_render'

    # --- Admin Hooks (M3) ---
    BEFORE_ADMIN_ACTION = 'before_admin_action'
    AFTER_ADMIN_ACTION = 'after_admin_action'


HOOKS = HookNames()


@dataclass
class HookHandler:
    """نمایانگر یک handler ثبت‌شده"""
    callback: Callable
    priority: int
    module: str
    description: str = ''


class HookSystem:
    """
    سیستم Hook مرکزی ریهان.

    ویژگی‌ها:
    - ثبت handler با priority (کمتر = زودتر اجرا می‌شود)
    - trigger با ارسال kwargs به همه handlerها
    - قابلیت stop_propagation (با بازگرداندن HookStop)
    - Isolation بین ماژول‌ها
    - Logging خودکار خطاها (یک handler خراب، بقیه را متوقف نمی‌کند)
    """

    _instance: Optional[HookSystem] = None
    _handlers: Dict[str, List[HookHandler]] = defaultdict(list)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> HookSystem:
        """دریافت نمونه Singleton"""
        return cls()

    def register(
        self,
        hook_name: str,
        callback: Callable,
        priority: int = 10,
        module: str = 'unknown',
        description: str = '',
    ) -> None:
        """
        ثبت یک handler برای یک hook.

        Args:
            hook_name: نام hook (از HOOKS.xxx استفاده کنید)
            callback: تابع handler
            priority: اولویت (۱ = بالاترین، پیش‌فرض ۱۰)
            module: نام ماژول (برای logging و debugging)
            description: توضیح کوتاه

        Raises:
            ValueError: اگر hook_name یا callback معتبر نباشد
        """
        if not hook_name:
            raise ValueError("hook_name cannot be empty")
        if not callable(callback):
            raise ValueError("callback must be callable")

        handler = HookHandler(
            callback=callback,
            priority=priority,
            module=module,
            description=description,
        )

        # افزودن و مرتب‌سازی بر اساس priority
        self._handlers[hook_name].append(handler)
        self._handlers[hook_name].sort(key=lambda h: h.priority)

        logger.debug(
            f"Hook registered: {hook_name} from {module} (priority={priority})"
        )

    def unregister(
        self,
        hook_name: str,
        callback: Optional[Callable] = None,
        module: Optional[str] = None,
    ) -> int:
        """
        لغو ثبت handler(ها).

        Args:
            hook_name: نام hook
            callback: اگر داده شود، فقط این callback حذف می‌شود
            module: اگر داده شود، همه handlerهای این ماژول حذف می‌شوند

        Returns:
            تعداد handlerهای حذف‌شده
        """
        if hook_name not in self._handlers:
            return 0

        original_count = len(self._handlers[hook_name])

        if callback is not None:
            self._handlers[hook_name] = [
                h for h in self._handlers[hook_name]
                if h.callback != callback
            ]
        elif module is not None:
            self._handlers[hook_name] = [
                h for h in self._handlers[hook_name]
                if h.module != module
            ]
        else:
            self._handlers[hook_name] = []

        removed = original_count - len(self._handlers[hook_name])
        return removed

    def trigger(self, hook_name: str, **kwargs) -> List[Any]:
        """
        اجرای تمام handlerهای یک hook.

        Args:
            hook_name: نام hook
            **kwargs: پارامترهایی که به handler ارسال می‌شود

        Returns:
            لیست نتیجه‌های برگشتی از handlerها

        Note:
            - اگر یک handler HookStop برگرداند، بقیه اجرا نمی‌شوند
            - خطا در یک handler، بقیه را متوقف نمی‌کند (logging می‌شود)
        """
        results = []
        handlers = self._handlers.get(hook_name, [])

        for handler in handlers:
            try:
                result = handler.callback(**kwargs)
                results.append(result)

                # بررسی HookStop
                if isinstance(result, HookStop):
                    logger.info(
                        f"Hook {hook_name} stopped by {handler.module}: {result.reason}"
                    )
                    break

            except Exception as e:
                logger.error(
                    f"Hook {hook_name} failed in module {handler.module}: {e}",
                    exc_info=True
                )
                # ادامه می‌دهیم - یک handler خراب نباید بقیه را متوقف کند

        return results

    def get_handlers(self, hook_name: str) -> List[HookHandler]:
        """دریافت لیست handlerهای یک hook"""
        return list(self._handlers.get(hook_name, []))

    def get_all_hooks(self) -> Dict[str, List[HookHandler]]:
        """دریافت تمام hookهای ثبت‌شده (برای debugging و admin panel)"""
        return dict(self._handlers)

    def get_hooks_for_module(self, module: str) -> Dict[str, List[HookHandler]]:
        """دریافت تمام hookهای یک ماژول خاص"""
        result = {}
        for hook_name, handlers in self._handlers.items():
            module_handlers = [h for h in handlers if h.module == module]
            if module_handlers:
                result[hook_name] = module_handlers
        return result

    def clear_module(self, module: str) -> int:
        """
        پاکسازی تمام handlerهای یک ماژول.
        مفید برای غیرفعال‌سازی کامل یک ماژول.
        """
        total_removed = 0
        for hook_name in list(self._handlers.keys()):
            original = len(self._handlers[hook_name])
            self._handlers[hook_name] = [
                h for h in self._handlers[hook_name]
                if h.module != module
            ]
            total_removed += original - len(self._handlers[hook_name])
        return total_removed

    def clear_all(self) -> None:
        """پاکسازی کامل (فقط برای تست)"""
        self._handlers.clear()


class HookStop:
    """
    اگر یک handler این کلاس را برگرداند،
    اجرای بقیه handlerهای آن hook متوقف می‌شود.

    مثال:
        def validate_order(user, order, **kwargs):
            if not user.is_active:
                return HookStop("User is not active")
            # ادامه بررسی...
    """
    def __init__(self, reason: str = ''):
        self.reason = reason

    def __repr__(self) -> str:
        return f"HookStop({self.reason!r})"


class HookError(Exception):
    """استثنای پایه برای خطاهای Hook System"""
    pass


# نمونه سراسری (Singleton)
hooks = HookSystem.get_instance()


def register_hook(
    hook_name: str,
    callback: Callable,
    priority: int = 10,
    module: str = 'unknown',
) -> Callable:
    """
    Decorator برای ثبت hook.

    مثال:
        @register_hook(HOOKS.AFTER_ORDER_CREATE, module='catalog')
        def log_order_creation(order, **kwargs):
            logger.info(f"Order created: {order.id}")
    """
    def decorator(func: Callable) -> Callable:
        hooks.register(hook_name, func, priority=priority, module=module)
        return func

    if callable(callback):
        # استفاده به‌عنوان تابع (نه decorator)
        hooks.register(hook_name, callback, priority=priority, module=module)
        return callback

    # استفاده به‌عنوان decorator
    return decorator
