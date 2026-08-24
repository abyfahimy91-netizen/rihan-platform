"""
ثبت مدل‌های ماژول مالی در پنل ادمین - نمایش تاریخ شمسی و اعداد فارسی
"""
from django.contrib import admin

from src.core.fa import money as fa_money, jalali_datetime_str

from .models import SupplierLedger, SupplierTransaction, Settlement


@admin.register(SupplierLedger)
class SupplierLedgerAdmin(admin.ModelAdmin):
    list_display = ("supplier", "total_sales_fa", "total_settlements_fa", "balance_fa")
    search_fields = ("supplier__name",)
    readonly_fields = ("created_at", "updated_at")

    def total_sales_fa(self, obj):
        return fa_money(obj.total_sales)
    total_sales_fa.short_description = 'جمع فروش'

    def total_settlements_fa(self, obj):
        return fa_money(obj.total_settlements)
    total_settlements_fa.short_description = 'جمع تسویه'

    def balance_fa(self, obj):
        return fa_money(obj.balance)
    balance_fa.short_description = 'موجودی (طلب)'


class SupplierTransactionInline(admin.TabularInline):
    model = SupplierTransaction
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(SupplierTransaction)
class SupplierTransactionAdmin(admin.ModelAdmin):
    list_display = ("ledger", "transaction_type", "amount_fa", "order", "created_at_fa")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("ledger__supplier__name", "description")
    readonly_fields = ("created_at",)

    def amount_fa(self, obj):
        return fa_money(obj.amount)
    amount_fa.short_description = 'مبلغ'
    amount_fa.admin_order_field = 'amount'

    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ'
    created_at_fa.admin_order_field = 'created_at'


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ("ledger", "amount_fa", "status", "settled_at_fa", "created_at_fa")
    list_filter = ("status", "settled_at")
    search_fields = ("ledger__supplier__name", "notes")
    readonly_fields = ("created_at",)

    def amount_fa(self, obj):
        return fa_money(obj.amount)
    amount_fa.short_description = 'مبلغ'
    amount_fa.admin_order_field = 'amount'

    def settled_at_fa(self, obj):
        return jalali_datetime_str(obj.settled_at)
    settled_at_fa.short_description = 'زمان تسویه'
    settled_at_fa.admin_order_field = 'settled_at'

    def created_at_fa(self, obj):
        return jalali_datetime_str(obj.created_at)
    created_at_fa.short_description = 'تاریخ ثبت'
    created_at_fa.admin_order_field = 'created_at'
