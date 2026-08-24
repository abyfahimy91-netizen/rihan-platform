"""
VariantStockService - مدیریت موجودی واریانت‌های محصول (D-094)

مطابق الگوی InventoryService (D-045) اما در سطح واریانت:
- موجودی در سطح واریانت نگهداری می‌شود (الگوی استاندارد Shopify/WooCommerce)
- رزرو فقط در لحظه ساخت سفارش (نه هنگام افزودن به سبد)
- تبدیل رزرو به فروش پس از تایید پرداخت
- آزادسازی رزرو در صورت انصراف از سفارش

نکته معماری: موجودی واریانت روی خود مدل ProductVariant ذخیره می‌شود و
Inventory والد دست نمی‌خورد تا گزارش‌های مالی/انباری محصول ساده باقی بمانند.
"""
import logging
from decimal import Decimal
from typing import List

from django.db import transaction

logger = logging.getLogger(__name__)


class VariantStockService:
    """سرویس موجودی واریانت - mirror of InventoryService semantics"""

    @classmethod
    def get_available_stock(cls, variant) -> int:
        """موجودی قابل فروش = کل منهای رزرو شده"""
        return max(0, int(variant.stock_quantity) - int(variant.reserved_quantity))

    @classmethod
    @transaction.atomic
    def reserve_for_order(cls, order_items: List[dict], user=None, order_id=None):
        """
        Reserve stock for variant order items (called when order is created).

        Args:
            order_items: List of dicts with keys:
                - 'variant': ProductVariant instance
                - 'quantity': Decimal/int quantity
            user: User creating the order
            order_id: Order number (for reference/logging)

        Raises:
            InsufficientStockError: If any variant lacks sufficient stock
        """
        from src.modules.catalog.services.exceptions import InsufficientStockError
        from src.modules.catalog.models import ProductVariant

        if not order_items:
            return []

        # First pass: validate all items have sufficient stock
        for item in order_items:
            variant = ProductVariant.objects.select_for_update().get(pk=item['variant'].pk)
            quantity = item['quantity']
            available = cls.get_available_stock(variant)
            if available < quantity:
                raise InsufficientStockError(
                    product_name=f"{variant.product.name} ({variant.title})",
                    requested=quantity,
                    available=available,
                )

        # Second pass: perform reservations
        reserved = []
        for item in order_items:
            variant = ProductVariant.objects.select_for_update().get(pk=item['variant'].pk)
            quantity = int(item['quantity'])
            variant.reserved_quantity += quantity
            variant.save(update_fields=['reserved_quantity'])
            reserved.append(variant)
            logger.info(
                f"Variant stock reserved: {variant} x{quantity} for order {order_id}"
            )

        return reserved

    @classmethod
    @transaction.atomic
    def confirm_sale(cls, order_items: List[dict], user=None, order_id=None):
        """
        Convert reservation to sale (called after payment verified):
        stock -= qty, reserved -= qty
        """
        from src.modules.catalog.models import ProductVariant

        sold = []
        for item in order_items:
            variant = ProductVariant.objects.select_for_update().get(pk=item['variant'].pk)
            quantity = int(item['quantity'])
            variant.reserved_quantity = max(0, variant.reserved_quantity - quantity)
            variant.stock_quantity = max(0, variant.stock_quantity - quantity)
            variant.save(update_fields=['reserved_quantity', 'stock_quantity'])
            sold.append(variant)
            logger.info(f"Variant sale confirmed: {variant} x{quantity} (order {order_id})")

        return sold

    @classmethod
    @transaction.atomic
    def release_reservation(cls, order_items: List[dict], user=None, order_id=None, reason=''):
        """
        Release reservation (called on cancel):
        reserved -= qty  (stock stays untouched)
        """
        from src.modules.catalog.models import ProductVariant

        released = []
        for item in order_items:
            variant = ProductVariant.objects.select_for_update().get(pk=item['variant'].pk)
            quantity = int(item['quantity'])
            variant.reserved_quantity = max(0, variant.reserved_quantity - quantity)
            variant.save(update_fields=['reserved_quantity'])
            released.append(variant)
            logger.info(
                f"Variant reservation released: {variant} x{quantity} "
                f"(order {order_id}, reason: {reason})"
            )

        return released

    @classmethod
    @transaction.atomic
    def return_stock(cls, order_items, user=None, order_id=None, reason=""):
        """بازگشت کالای مرجوع‌شده به موجودی واریانت (پس از تایید ادمین)"""
        from src.modules.catalog.models import ProductVariant

        restored = []
        for item in order_items:
            variant = ProductVariant.objects.select_for_update().get(pk=item["variant"].pk)
            quantity = int(item["quantity"])
            variant.stock_quantity = max(0, int(variant.stock_quantity)) + quantity
            variant.save(update_fields=["stock_quantity"])
            restored.append(variant)
            logger.info(
                f"Variant stock returned: {variant} x{quantity} "
                f"(order {order_id}, reason: {reason})"
            )
        return restored
