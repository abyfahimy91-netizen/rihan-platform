"""
ثبت مدل‌های ماژول مالی در پنل ادمین
"""
from django.contrib import admin
from .models import SupplierLedger, SupplierTransaction, Settlement


@admin.register(SupplierLedger)
class SupplierLedgerAdmin(admin.ModelAdmin):
    list_display = ("supplier", "total_sales", "total_settlements", "balance")
    search_fields = ("supplier__name",)
    readonly_fields = ("created_at", "updated_at")


class SupplierTransactionInline(admin.TabularInline):
    model = SupplierTransaction
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(SupplierTransaction)
class SupplierTransactionAdmin(admin.ModelAdmin):
    list_display = ("ledger", "transaction_type", "amount", "order", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("ledger__supplier__name", "description")
    readonly_fields = ("created_at",)


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ("ledger", "amount", "status", "settled_at", "created_at")
    list_filter = ("status", "settled_at")
    search_fields = ("ledger__supplier__name", "notes")
    readonly_fields = ("created_at",)
