"""
ماژول مالی (M6) - مدل‌های دیتابیس

User Stories پوشش داده شده:
- US-030: حساب ماهانه تأمین‌کننده
- US-021: گزارش مالی (زیرساخت داده‌ای)
- US-045: قیمت‌گذاری شفاف (جزئیات سهم تأمین‌کننده)
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class SupplierLedger(models.Model):
    """دفتر حساب هر تأمین‌کننده"""
    supplier = models.OneToOneField(
        "catalog.Supplier",
        on_delete=models.CASCADE,
        related_name="ledger",
        verbose_name=_("تأمین‌کننده")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخرین به‌روزرسانی"))

    class Meta:
        verbose_name = _("دفتر حساب تأمین‌کننده")
        verbose_name_plural = _("دفاتر حساب تأمین‌کنندگان")

    def __str__(self):
        return f"دفتر حساب: {self.supplier}"

    @property
    def total_sales(self):
        """جمع کل فروش‌ها"""
        return self.transactions.filter(
            transaction_type=SupplierTransaction.TransactionType.SALE
        ).aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def total_settlements(self):
        """جمع کل تسویه‌های تأیید شده"""
        return self.settlements.filter(
            status=Settlement.SettlementStatus.COMPLETED
        ).aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def balance(self):
        """موجودی (طلب تأمین‌کننده)"""
        return self.total_sales - self.total_settlements


class SupplierTransaction(models.Model):
    """تراکنش‌های مالی مربوط به تأمین‌کننده"""

    class TransactionType(models.TextChoices):
        SALE = "SALE", _("فروش")
        SETTLEMENT = "SETTLEMENT", _("تسویه")
        ADJUSTMENT = "ADJUSTMENT", _("اصلاحیه دستی")
        REFUND = "REFUND", _("مرجوعی")

    ledger = models.ForeignKey(
        SupplierLedger,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("دفتر حساب")
    )
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_transactions",
        verbose_name=_("سفارش")
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name=_("نوع تراکنش")
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("مبلغ")
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("توضیحات")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ثبت"))
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_supplier_transactions",
        verbose_name=_("ثبت‌کننده")
    )

    class Meta:
        verbose_name = _("تراکنش تأمین‌کننده")
        verbose_name_plural = _("تراکنش‌های تأمین‌کنندگان")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount}"


class Settlement(models.Model):
    """تسویه حساب با تأمین‌کننده"""

    class SettlementStatus(models.TextChoices):
        PENDING = "PENDING", _("در انتظار")
        COMPLETED = "COMPLETED", _("تکمیل شده")
        REJECTED = "REJECTED", _("رد شده")

    ledger = models.ForeignKey(
        SupplierLedger,
        on_delete=models.CASCADE,
        related_name="settlements",
        verbose_name=_("دفتر حساب")
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("مبلغ تسویه")
    )
    status = models.CharField(
        max_length=20,
        choices=SettlementStatus.choices,
        default=SettlementStatus.PENDING,
        verbose_name=_("وضعیت")
    )
    notes = models.TextField(blank=True, verbose_name=_("یادداشت"))
    settled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("تاریخ تسویه")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ثبت"))
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_settlements",
        verbose_name=_("ثبت‌کننده")
    )

    class Meta:
        verbose_name = _("تسویه حساب")
        verbose_name_plural = _("تسویه حساب‌ها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"تسویه {self.ledger.supplier} - {self.amount}"
