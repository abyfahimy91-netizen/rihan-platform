from django.db import models
from django.utils import timezone

class Payment(models.Model):
    GATEWAY_TYPES = [
        ('card_to_card', 'کارت‌به‌کارت'),
        ('online_gateway', 'درگاه آنلاین'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار واریز'),
        ('submitted', 'رسید ثبت‌شده / در حال بررسی'),
        ('verified', 'تأییدشده'),
        ('rejected', 'ردشده'),
    ]

    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='payment', verbose_name="سفارش")
    amount = models.PositiveBigIntegerField(verbose_name="مبلغ تراکنش (تومان)")
    gateway_type = models.CharField(max_length=30, choices=GATEWAY_TYPES, default='card_to_card', verbose_name="روش پرداخت")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت پرداخت")
    
    receipt_image = models.ImageField(upload_to='receipts/%Y/%m/', null=True, blank=True, verbose_name="تصویر فیش واریزی")
    transaction_reference = models.CharField(max_length=100, blank=True, verbose_name="شماره پیگیری / ارجاع")
    card_last_four = models.CharField(max_length=4, blank=True, verbose_name="۴ رقم آخر کارت واریزکننده")
    destination_card = models.CharField(max_length=50, default='۶۰۳۷-۹۹۷۵-۱۲۳۴-۵۶۷۸', verbose_name="شماره کارت مقصد")
    
    admin_notes = models.TextField(blank=True, verbose_name="توضیحات و بررسی ادمین")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تأیید")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"پرداخت سفارش {self.order.order_number} ({self.get_status_display()})"
