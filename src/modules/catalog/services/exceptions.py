"""
Custom exceptions for Inventory operations.
Used by InventoryService to provide clear error messages.
"""


from src.core.fa import fa_digits


class InventoryError(Exception):
    """Base exception for all inventory-related errors."""
    pass


class InsufficientStockError(InventoryError):
    """Raised when requested quantity exceeds available stock."""
    
    def __init__(self, product_name, requested, available):
        self.product_name = product_name
        self.requested = requested
        self.available = available
        message = (
            f"موجودی «{product_name}» کافی نیست؛ "
            f"{fa_digits(requested)} عدد درخواست کرده‌اید، اما تنها "
            f"{fa_digits(available)} عدد موجود است. لطفاً تعداد را تعدیل بفرمایید."
        )
        super().__init__(message)


class InventoryValidationError(InventoryError):
    """Raised when inventory operation validation fails."""
    pass


class ReservationError(InventoryError):
    """Raised when reservation operation fails."""
    pass


class ProductNotFoundError(InventoryError):
    """Raised when product has no inventory record."""
    
    def __init__(self, product_name):
        self.product_name = product_name
        message = f"برای محصول «{product_name}» رکورد موجودی ثبت نشده است."
        super().__init__(message)
