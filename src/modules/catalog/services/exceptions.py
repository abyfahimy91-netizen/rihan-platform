"""
Custom exceptions for Inventory operations.
Used by InventoryService to provide clear error messages.
"""


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
            f"Insufficient stock for '{product_name}': "
            f"requested {requested}, only {available} available"
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
        message = f"No inventory record found for product '{product_name}'"
        super().__init__(message)
