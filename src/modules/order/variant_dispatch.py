"""لایه مسیریابی موجودی — D-094

با همان API اینونتوری سرویس عمل می‌کند ولی آیتم‌های واریانت‌دار را به
VariantStockService می‌فرستد؛ بقیه کد بدون تغییر باطل/رزرو/تایید را پشتیبانی می‌کند.
"""
from src.modules.catalog.services.inventory_service import InventoryService as _InvSvc
from src.modules.catalog.services.variant_stock_service import VariantStockService


def _split(items):
    simple, varr = [], []
    for it in items:
        (varr if it.get("variant") else simple).append(it)
    return simple, varr


class InventoryService:
    @classmethod
    def get_available_stock(cls, product=None, variant=None):
        if variant is not None:
            return VariantStockService.get_available_stock(variant)
        return _InvSvc.get_available_stock(product)

    @classmethod
    def reserve_for_order(cls, order_items, user=None, order_id=None):
        simple, varr = _split(order_items)
        out = []
        if varr:
            out += VariantStockService.reserve_for_order(
                order_items=varr, user=user, order_id=order_id)
        if simple:
            out += _InvSvc.reserve_for_order(
                order_items=simple, user=user, order_id=order_id) or []
        return out

    @classmethod
    def confirm_sale(cls, order_items, user=None, order_id=None):
        simple, varr = _split(order_items)
        out = []
        if varr:
            out += VariantStockService.confirm_sale(
                order_items=varr, user=user, order_id=order_id)
        if simple:
            out += _InvSvc.confirm_sale(
                order_items=simple, user=user, order_id=order_id) or []
        return out

    @classmethod
    def release_reservation(cls, order_items, user=None, order_id=None, reason=""):
        simple, varr = _split(order_items)
        out = []
        if varr:
            out += VariantStockService.release_reservation(
                order_items=varr, user=user, order_id=order_id, reason=reason)
        if simple:
            out += _InvSvc.release_reservation(
                order_items=simple, user=user, order_id=order_id, reason=reason) or []
        return out

    @classmethod
    def return_stock(cls, order_items, user=None, order_id=None, reason=""):
        simple, varr = _split(order_items)
        out = []
        if varr:
            out += VariantStockService.return_stock(
                order_items=varr, user=user, order_id=order_id, reason=reason)
        if simple:
            out += _InvSvc.return_stock(
                order_items=simple, user=user, order_id=order_id, reason=reason) or []
        return out
