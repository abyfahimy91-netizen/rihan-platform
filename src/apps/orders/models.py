from django.db import models
from django.utils.crypto import get_random_string

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending_payment', 'در انتظار پرداخت'),
        ('payment_submitted', 'رسید ثبت‌شده / در حال بررسی'),
        ('confirmed', 'تأییدشده و آماده‌سازی'),
        ('shipped', 'ارسال‌شده به مقصد'),
        ('delivered', 'تحویل داده‌شده'),
        ('cancelled', 'لغوشده'),
    ]

    PAYMENT_METHODS = [
        ('card_to_card', 'کارت‌به‌کارت'),
        ('online_gateway', 'درگاه پرداخت آنلاین'),
    ]

    order_number = models.CharField(max_length=50, unique=True, editable=False, verbose_name="شماره سفارش")
    customer_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")
    customer_phone = models.CharField(max_length=20, verbose_name="شماره موبایل")
    customer_email = models.EmailField(blank=True, verbose_name="ایمیل (اختیاری)")
    
    province = models.CharField(max_length=100, verbose_name="استان")
    city = models.CharField(max_length=100, verbose_name="شهر")
    shipping_address = models.TextField(verbose_name="نشانی دقیق پستی")
    postal_code = models.CharField(max_length=20, verbose_name="کد پستی")
    customer_notes = models.TextField(blank=True, verbose_name="یادداشت سفارش")

    items_total = models.PositiveBigIntegerField(default=0, verbose_name="جمع اقلام (تومان)")
    shipping_cost = models.PositiveBigIntegerField(default=0, verbose_name="هزینه ارسال (D-046: لحاظ در قیمت کالا)")
    grand_total = models.PositiveBigIntegerField(default=0, verbose_name="مبلغ نهایی (تومان)")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment', verbose_name="وضعیت سفارش")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='card_to_card', verbose_name="روش پرداخت")
    tracking_code = models.CharField(max_length=100, blank=True, verbose_name="کد رهگیری پستی / باربری")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            random_suffix = get_random_string(length=5, allowed_chars='123456789ABCDEFGHJKLMNPQRSTUVWXYZ')
            self.order_number = f"RH-1405-{random_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سفارش {self.order_number} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="سفارش")
    product = models.ForeignKey('catalog.Product', on_delete=models.SET_NULL, null=True, related_name='order_items', verbose_name="محصول")
    product_title = models.CharField(max_length=255, verbose_name="عنوان محصول")
    product_sku = models.CharField(max_length=50, verbose_name="کد کالا")
    unit_price = models.PositiveBigIntegerField(verbose_name="قیمت واحد (تومان)")
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    subtotal = models.PositiveBigIntegerField(verbose_name="جمع ردیف (تومان)")

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_title} x {self.quantity}"
