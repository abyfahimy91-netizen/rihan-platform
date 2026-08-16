"""
Event Bus ریهان
================
برای ارتباط غیرهمگام (asynchronous) و fire-and-forget بین ماژول‌ها.

تفاوت با HookSystem:
- Hook: sync، برای تغییر داده یا متوقف کردن فرآیند
- Event: async، برای اطلاع‌رسانی و واکنش‌های جانبی

منطبق بر:
- D-079 بخش ۸.۱ (ارتباط بین ماژول‌ها)
- ADR-004 (Isolation)

نحوه استفاده:
    from core.events import events, EVENTS

    # انتشار رویداد (publisher)
    events.publish(EVENTS.ORDER_CREATED, {'order_id': order.id})

    # گوش دادن به رویداد (subscriber)
    @events.subscribe(EVENTS.ORDER_CREATED)
    def send_sms_on_order(data):
        send_sms(data['order_id'])
"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ThreadPool برای اجرای async رویدادها
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='rihan-events')


class EventNames:
    """
    نام‌های استاندارد رویدادها.
    ماژول‌ها باید از این کلاس استفاده کنند.
    """

    # --- Order Events ---
    ORDER_CREATED = 'order.created'
    ORDER_UPDATED = 'order.updated'
    ORDER_CANCELLED = 'order.cancelled'
    ORDER_COMPLETED = 'order.completed'

    # --- Payment Events ---
    PAYMENT_SUBMITTED = 'payment.submitted'
    PAYMENT_CONFIRMED = 'payment.confirmed'
    PAYMENT_REJECTED = 'payment.rejected'

    # --- Cart Events ---
    CART_ITEM_ADDED = 'cart.item.added'
    CART_ITEM_REMOVED = 'cart.item.removed'
    CART_ABANDONED = 'cart.abandoned'

    # --- Catalog Events ---
    PRODUCT_CREATED = 'product.created'
    PRODUCT_UPDATED = 'product.updated'
    PRODUCT_DELETED = 'product.deleted'
    PRODUCT_OUT_OF_STOCK = 'product.out_of_stock'
    PRODUCT_LOW_STOCK = 'product.low_stock'

    # --- Auth Events ---
    USER_REGISTERED = 'user.registered'
    USER_LOGGED_IN = 'user.logged_in'
    USER_LOGGED_OUT = 'user.logged_out'

    # --- Review Events ---
    REVIEW_SUBMITTED = 'review.submitted'
    REVIEW_APPROVED = 'review.approved'
    REVIEW_REJECTED = 'review.rejected'

    # --- Lead Events ---
    LEAD_CREATED = 'lead.created'
    LEAD_FULFILLED = 'lead.fulfilled'

    # --- System Events ---
    FLAG_CHANGED = 'system.flag_changed'
    MODULE_ENABLED = 'system.module_enabled'
    MODULE_DISABLED = 'system.module_disabled'
    ADMIN_ACTION = 'system.admin_action'

    # --- Notification Events ---
    SMS_SENT = 'notification.sms_sent'
    SMS_FAILED = 'notification.sms_failed'


EVENTS = EventNames()


class Event:
    """نمایانگر یک رویداد منتشرشده"""
    __slots__ = ('name', 'data', 'timestamp', 'source_module')

    def __init__(
        self,
        name: str,
        data: Optional[Dict] = None,
        source_module: str = 'unknown'
    ):
        import time
        self.name = name
        self.data = data or {}
        self.timestamp = time.time()
        self.source_module = source_module

    def __repr__(self) -> str:
        return f"Event({self.name!r}, source={self.source_module!r})"


class EventBus:
    """
    Event Bus مرکزی ریهان.

    ویژگی‌ها:
    - publish/subscribe pattern
    - اجرای sync یا async
    - پشتیبانی از wildcard subscription
    - Logging خودکار خطاها
    - Thread-safe
    - تاریخچه با ترتیب انتشار (FIFO)
    """

    _instance: Optional[EventBus] = None
    _subscribers: Dict[str, List[Dict]] = defaultdict(list)
    _history: List[Event] = []
    _history_max: int = 1000  # حداکثر ۱۰۰۰ رویداد اخیر

    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> EventBus:
        return cls()

    def subscribe(
        self,
        event_name: str,
        callback: Callable,
        async_execution: bool = True,
        module: str = 'unknown',
    ) -> None:
        """
        ثبت subscriber برای یک رویداد.

        Args:
            event_name: نام رویداد (از EVENTS.xxx) یا pattern با * (wildcard)
            callback: تابعی که رویداد را دریافت می‌کند
            async_execution: اگر True، در thread جداگانه اجرا می‌شود
            module: نام ماژول

        مثال wildcard:
            events.subscribe('order.*', log_all_order_events)
        """
        if not event_name:
            raise ValueError("event_name cannot be empty")
        if not callable(callback):
            raise ValueError("callback must be callable")

        with self._lock:
            self._subscribers[event_name].append({
                'callback': callback,
                'async_execution': async_execution,
                'module': module,
            })

        logger.debug(
            f"Subscribed to {event_name} from {module} (async={async_execution})"
        )

    def unsubscribe(
        self,
        event_name: Optional[str] = None,
        callback: Optional[Callable] = None,
        module: Optional[str] = None,
    ) -> int:
        """
        لغو ثبت subscriber(ها).

        Returns:
            تعداد subscriberهای حذف‌شده
        """
        with self._lock:
            if event_name:
                original = len(self._subscribers.get(event_name, []))
                if callback:
                    self._subscribers[event_name] = [
                        s for s in self._subscribers[event_name]
                        if s['callback'] != callback
                    ]
                elif module:
                    self._subscribers[event_name] = [
                        s for s in self._subscribers[event_name]
                        if s['module'] != module
                    ]
                else:
                    self._subscribers[event_name] = []
                return original - len(self._subscribers.get(event_name, []))

            elif module:
                total = 0
                for name in list(self._subscribers.keys()):
                    original = len(self._subscribers[name])
                    self._subscribers[name] = [
                        s for s in self._subscribers[name]
                        if s['module'] != module
                    ]
                    total += original - len(self._subscribers[name])
                return total

        return 0

    def publish(
        self,
        event_name: str,
        data: Optional[Dict] = None,
        source_module: str = 'unknown',
        async_publish: bool = True,
    ) -> Event:
        """
        انتشار یک رویداد.

        Args:
            event_name: نام رویداد
            data: داده‌های رویداد (dict)
            source_module: ماژول منتشرکننده
            async_publish: اگر True، subscriberهای async در thread دیگر اجرا می‌شوند

        Returns:
            Event object منتشرشده
        """
        event = Event(event_name, data, source_module)

        # افزودن به history
        self._history.append(event)
        if len(self._history) > self._history_max:
            self._history.pop(0)

        # پیدا کردن subscribers مرتبط
        subscribers_to_notify = self._find_subscribers(event_name)

        # اجرای subscribers
        for sub in subscribers_to_notify:
            try:
                if async_publish and sub['async_execution']:
                    _executor.submit(self._invoke_subscriber, sub, event)
                else:
                    self._invoke_subscriber(sub, event)
            except Exception as e:
                logger.error(
                    f"Failed to invoke subscriber for {event_name} "
                    f"from {sub['module']}: {e}",
                    exc_info=True
                )

        return event

    def _invoke_subscriber(self, sub: Dict, event: Event) -> None:
        """اجرای یک subscriber"""
        try:
            sub['callback'](event)
        except Exception as e:
            logger.error(
                f"Subscriber {sub['module']} failed on event {event.name}: {e}",
                exc_info=True
            )

    def _find_subscribers(self, event_name: str) -> List[Dict]:
        """پیدا کردن subscribers مرتبط (با پشتیبانی wildcard)"""
        result = []
        with self._lock:
            # Exact match
            if event_name in self._subscribers:
                result.extend(self._subscribers[event_name])

            # Wildcard match (مثلاً 'order.*' برای 'order.created')
            parts = event_name.split('.')
            for i in range(len(parts)):
                pattern = '.'.join(parts[:i + 1]) + '.*'
                if pattern in self._subscribers:
                    result.extend(self._subscribers[pattern])

            # Global wildcard
            if '*' in self._subscribers:
                result.extend(self._subscribers['*'])

        return result

    def get_history(
        self,
        limit: int = 50,
        event_name: Optional[str] = None,
    ) -> List[Event]:
        """
        دریافت تاریخچه رویدادهای اخیر.
        
        **اصلاح:** ترتیب انتشار حفظ می‌شود (FIFO - اولین منتشر شده = اولین در لیست).
        
        Args:
            limit: تعداد رویداد
            event_name: فیلتر بر اساس نام رویداد
        
        Returns:
            لیست رویدادها به ترتیب انتشار (قدیمی‌ترین اول)
        """
        events = self._history[-limit:]
        if event_name:
            events = [e for e in events if e.name == event_name]
        return list(events)  # بدون reversed - ترتیب انتشار حفظ می‌شود

    def get_subscriptions(self) -> Dict[str, List[Dict]]:
        """دریافت تمام subscriptions (برای admin panel)"""
        with self._lock:
            return {k: list(v) for k, v in self._subscribers.items()}

    def clear_module(self, module: str) -> int:
        """پاکسازی تمام subscriptions یک ماژول"""
        return self.unsubscribe(module=module)

    def clear_history(self) -> None:
        """پاکسازی تاریخچه"""
        with self._lock:
            self._history.clear()


# نمونه سراسری
events = EventBus.get_instance()


def subscribe(
    event_name: str,
    async_execution: bool = True,
    module: str = 'unknown',
):
    """
    Decorator برای subscribe به رویداد.

    مثال:
        @subscribe(EVENTS.ORDER_CREATED, module='notifications')
        def send_order_sms(event):
            send_sms(event.data['phone'])
    """
    def decorator(func: Callable) -> Callable:
        events.subscribe(
            event_name,
            func,
            async_execution=async_execution,
            module=module,
        )
        return func
    return decorator
