import uuid
from django.db import models
from django.conf import settings

def generate_order_number():
    '''تولید شماره سفارش فرمت RH-1405-XXXXX (منطبق بر D-080)'''
    # سال جاری شمسی (در فازهای بعد با کتابخانه jdatetime کاملاً پویا می‌شود)
    year_str = "1405"
    latest_order = Order.objects.filter(order_number__startswith=f"RH-{year_str}-").order_by('order_number').last()
    if not latest_order:
        return f"RH-{year_str}-00001"
    last_num = int(latest_order.order_number.split('-')[-1])
    return f"RH-{year_str}-{str(last_num + 1).zfill(5)}"


class Cart(models.Model):
    '''سبد خرید - منطبق بر D-079 و D-080'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=100, blank=True, verbose_name="شناسه نشست (برای مهمان)")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"
        ordering = ['-created_at']

    def __str__(self):
        return f"سبد {self.id} ({self.items.count()} کالا)"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    '''اقلام سبد خرید - بدون هزینه پنهان (D-046)'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    unit_price_at_add = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت واحد در لحظه افزودن")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "کالای سبد"
        verbose_name_plural = "کالاهای سبد"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price_at_add * self.quantity

    def clean(self):
        if self.quantity < 1:
            self.quantity = 1


class Order(models.Model):
    '''سفارش نهایی - منطبق بر ADR-002 با Snapshot مهمان'''
    class OrderStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'پیش‌نویس'
        PENDING = 'PENDING', 'در انتظار پرداخت'
        PAID = 'PAID', 'پرداخت شده'
        PROCESSING = 'PROCESSING', 'در حال پردازش'
        SHIPPED = 'SHIPPED', 'ارسال شده'
        DELIVERED = 'DELIVERED', 'تحویل داده شده'
        CANCELLED = 'CANCELLED', 'لغو شده'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, blank=True, verbose_name="شماره سفارش")
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    session_key = models.CharField(max_length=100, blank=True, verbose_name="شناسه نشست (برای مهمان)")
    
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    
    # Snapshot اطلاعات کاربر مهمان (ADR-002)
    guest_name = models.CharField(max_length=150, blank=True, verbose_name="نام خریدار (مهمان)")
    guest_phone = models.CharField(max_length=20, blank=True, verbose_name="تلفن تماس (مهمان)")
    guest_address = models.TextField(blank=True, verbose_name="آدرس کامل (مهمان)")
    guest_postal_code = models.CharField(max_length=20, blank=True, verbose_name="کد پستی (مهمان)")
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="جمع کل کالاها")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="هزینه ارسال")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="مبلغ نهایی")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارشات"
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

    def calculate_totals(self):
        self.subtotal = sum(item.subtotal for item in self.items.all())
        self.total_price = self.subtotal + self.shipping_cost
        self.save()


class OrderItem(models.Model):
    '''اقلام سفارش نهایی'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, verbose_name="محصول")
    
    quantity = models.PositiveIntegerField(default=1)
    unit_price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Snapshot محصول در لحظه خرید تا در صورت تغییر نام محصول در آینده، فاکتور دست‌نخورده بماند
    product_name_snapshot = models.CharField(max_length=200, verbose_name="نام محصول در لحظه خرید")

    class Meta:
        verbose_name = "قلم سفارش"
        verbose_name_plural = "اقلام سفارش"

    def __str__(self):
        return f"{self.product_name_snapshot} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price_at_purchase


class Payment(models.Model):
    '''تراکنش پرداخت - منطبق بر D-079 (شفافیت)'''
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار پرداخت'
        SUCCESS = 'SUCCESS', 'پرداخت موفق'
        FAILED = 'FAILED', 'پرداخت ناموفق'
        CANCELLED = 'CANCELLED', 'لغو شده توسط کاربر'
    
    class PaymentGateway(models.TextChoices):
        MOCK = 'MOCK', 'درگاه شبیه‌سازی شده'
        ZARINPAL = 'ZARINPAL', 'زرین‌پال'
        IDPAY = 'IDPAY', 'آیدی‌پی'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ پرداختی")
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    gateway = models.CharField(max_length=20, choices=PaymentGateway.choices, default=PaymentGateway.MOCK)
    authority = models.CharField(max_length=100, blank=True, verbose_name="شناسه یکتا در درگاه")
    ref_id = models.CharField(max_length=100, blank=True, verbose_name="کد پیگیری (پس از پرداخت)")
    gateway_response = models.JSONField(null=True, blank=True, verbose_name="پاسخ کامل درگاه")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "تراکنش پرداخت"
        verbose_name_plural = "تراکنش‌های پرداخت"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"پرداخت {self.order.order_number} - {self.get_status_display()}"
import uuid
from django.db import models
from django.conf import settings


class Address(models.Model):
    '''آدرس‌های کاربر - برای استفاده مجدد در خریدهای بعدی'''
    class AddressType(models.TextChoices):
        HOME = 'HOME', 'منزل'
        WORK = 'WORK', 'محل کار'
        OTHER = 'OTHER', 'سایر'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    
    # اطلاعات آدرس
    title = models.CharField(max_length=50, verbose_name="عنوان آدرس")
    address_type = models.CharField(max_length=10, choices=AddressType.choices, default=AddressType.HOME)
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی گیرنده")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس گیرنده")
    province = models.CharField(max_length=50, verbose_name="استان")
    city = models.CharField(max_length=50, verbose_name="شهر")
    postal_code = models.CharField(max_length=20, verbose_name="کد پستی")
    detailed_address = models.TextField(verbose_name="آدرس دقیق")
    
    # تنظیمات
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        # اگر این آدرس پیش‌فرض شد، آدرس‌های دیگر را غیرپیش‌فرض کن
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)
