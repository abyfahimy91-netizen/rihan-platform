import uuid
import jdatetime
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_order_number():
    '''تولید شماره سفارش فرمت RH-1405-XXXXX با jdatetime (پویا و شمسی)'''
    year_str = str(jdatetime.date.today().year)
    latest_order = Order.objects.filter(
        order_number__startswith=f"RH-{year_str}-"
    ).order_by('-order_number').first()
    
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



    variant = models.ForeignKey(
        'catalog.ProductVariant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='cart_items',
        verbose_name="واریانت انتخابی")

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
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="هزینه ارسال (در قیمت نهایی نهفته)")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="مبلغ نهایی")

    # D-099: مهلت رزرو موجودی برای سفارش پرداخت‌نشده؛ پس از آن رزرو خودکار آزاد می‌شود
    expires_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="مهلت پرداخت (رزرو موجودی)",
        help_text="سفارش‌های در انتظار پرداخت بعد از این زمان به‌صورت خودکار لغو و موجودی آزاد می‌شود",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارشات"
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number
    
    # M7 - Tracking fields (D-082)
    tracking_code = models.CharField(
        max_length=100, blank=True,
        verbose_name="کد رهگیری پست/باربری"
    )
    shipping_method = models.CharField(
        max_length=50, blank=True,
        verbose_name="روش ارسال",
        help_text="پست، تیپاکس، باربری، پیک"
    )
    shipped_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="تاریخ ارسال"
    )
    delivered_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="تاریخ تحویل"
    )
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

    def calculate_totals(self):
        self.subtotal = sum(item.subtotal for item in self.items.all())
        # شفافیت قیمت (D-080): هزینه ارسال در قیمت نهایی نهفته است
        # برای نمایش "ارسال رایگان" در ظاهر، shipping_cost را 0 در نظر می‌گیریم
        self.shipping_cost = 0
        self.total_price = self.subtotal
        self.save()

    # ── D-099: کمکی‌های مهلت رزرو ──
    @property
    def is_payable(self):
        """سفارش هنوز در وضعیت پرداخت‌نشده و داخل مهلت رزرو است"""
        return self.status == self.OrderStatus.PENDING and not self.is_reservation_expired

    @property
    def is_reservation_expired(self):
        """مهلت رزرو تمام شده است (فقط برای سفارش‌های در انتظار پرداخت معنا دارد)"""
        return bool(
            self.status == self.OrderStatus.PENDING
            and self.expires_at
            and timezone.now() > self.expires_at
        )

    @property
    def remaining_seconds(self):
        """ثانیه‌های باقی‌مانده تا پایان مهلت رزرو (۰ یعنی تمام‌شده یا بدون مهلت)"""
        if self.status != self.OrderStatus.PENDING or not self.expires_at:
            return 0
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))


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



    variant = models.ForeignKey(
        'catalog.ProductVariant', on_delete=models.PROTECT,
        null=True, blank=True, related_name='order_items',
        verbose_name="واریانت خریداری‌شده")
    variant_title = models.CharField(max_length=120, blank=True, default='',
                                     verbose_name="عنوان واریانت در لحظه خرید")

class Payment(models.Model):
    '''
    تراکنش پرداخت - منطبق بر ADR-005 و D-067
    
    پشتیبانی از چندین Gateway:
    - MANUAL: کارت‌به‌کارت با تایید دستی (پیش‌فرض MVP)
    - MOCK: درگاه شبیه‌سازی برای تست
    - ZARINPAL/IDPAY: درگاه‌های آنلاین آینده
    '''
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار پرداخت'
        PENDING_REVIEW = 'PENDING_REVIEW', 'در انتظار بررسی و تایید'  # NEW - برای کارت‌به‌کارت
        SUCCESS = 'SUCCESS', 'پرداخت موفق'
        FAILED = 'FAILED', 'پرداخت ناموفق'
        CANCELLED = 'CANCELLED', 'لغو شده توسط کاربر'
    
    class PaymentGateway(models.TextChoices):
        MANUAL = 'MANUAL', 'کارت‌به‌کارت (دستی)'  # NEW - پیش‌فرض MVP
        MOCK = 'MOCK', 'درگاه شبیه‌سازی شده'
        ZARINPAL = 'ZARINPAL', 'زرین‌پال'
        IDPAY = 'IDPAY', 'آیدی‌پی'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ پرداختی")
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    gateway = models.CharField(max_length=20, choices=PaymentGateway.choices, default=PaymentGateway.MANUAL)
    
    # فیلدهای عمومی درگاه (برای درگاه‌های آنلاین)
    authority = models.CharField(max_length=100, blank=True, verbose_name="شناسه یکتا در درگاه")
    ref_id = models.CharField(max_length=100, blank=True, verbose_name="کد پیگیری (پس از پرداخت)")
    gateway_response = models.JSONField(null=True, blank=True, verbose_name="پاسخ کامل درگاه")
    
    # فیلدهای کارت‌به‌کارت (ADR-005 + D-067) - ۳ evidence اجباری + رسید اختیاری
    sender_card_last4 = models.CharField(
        max_length=4, 
        blank=True,
        verbose_name="۴ رقم آخر کارت فرستنده"
    )
    transfer_time = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="زمان واریز"
    )
    receipt_image = models.ImageField(
        upload_to='payment_receipts/%Y/%m/', 
        null=True, 
        blank=True, 
        verbose_name="تصویر رسید پرداخت"
    )
    
    # فیلدهای تایید ادمین (manual review)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_payments',
        verbose_name="تاییدکننده (ادمین)"
    )
    reviewed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="زمان تایید"
    )
    admin_notes = models.TextField(
        blank=True, 
        verbose_name="یادداشت ادمین (در صورت رد یا تایید)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "تراکنش پرداخت"
        verbose_name_plural = "تراکنش‌های پرداخت"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"پرداخت {self.order.order_number} - {self.get_status_display()}"
    
    def submit_evidence(self, sender_card_last4, transfer_time, receipt_image=None):
        '''
        ثبت evidence کارت‌به‌کارت توسط مشتری (D-067)
        پس از ثبت، وضعیت به PENDING_REVIEW تغییر می‌کند
        '''
        if len(str(sender_card_last4)) != 4:
            raise ValueError("۴ رقم آخر کارت باید دقیقاً ۴ رقم باشد")
        
        self.sender_card_last4 = str(sender_card_last4)
        self.transfer_time = transfer_time
        if receipt_image:
            self.receipt_image = receipt_image
        self.status = self.PaymentStatus.PENDING_REVIEW
        self.save()
        return self
    
    def confirm(self, admin_user, notes=''):
        '''تایید پرداخت توسط ادمین - وضعیت به SUCCESS تغییر می‌کند'''
        self.status = self.PaymentStatus.SUCCESS
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_notes = notes
        self.save()
        return self
    
    def reject(self, admin_user, notes=''):
        '''رد پرداخت توسط ادمین - وضعیت به FAILED تغییر می‌کند'''
        self.status = self.PaymentStatus.FAILED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_notes = notes
        self.save()
        return self


class Address(models.Model):
    '''آدرس‌های کاربر - برای استفاده مجدد در خریدهای بعدی'''
    class AddressType(models.TextChoices):
        HOME = 'HOME', 'منزل'
        WORK = 'WORK', 'محل کار'
        OTHER = 'OTHER', 'سایر'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    
    title = models.CharField(max_length=50, verbose_name="عنوان آدرس")
    address_type = models.CharField(max_length=10, choices=AddressType.choices, default=AddressType.HOME)
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی گیرنده")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس گیرنده")
    province = models.CharField(max_length=50, verbose_name="استان")
    city = models.CharField(max_length=50, verbose_name="شهر")
    postal_code = models.CharField(max_length=20, verbose_name="کد پستی")
    detailed_address = models.TextField(verbose_name="آدرس دقیق")
    
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
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """
    History of order status changes (M7 - D-082)
    
    Every time order status changes, a record is created here.
    Used to show real timeline on tracking page.
    """
    class HistoryStatus(models.TextChoices):
        ORDER_CREATED = 'ORDER_CREATED', 'سفارش ثبت شد'
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'در انتظار پرداخت'
        PAYMENT_SUBMITTED = 'PAYMENT_SUBMITTED', 'پرداخت ارسال شد'
        PAYMENT_CONFIRMED = 'PAYMENT_CONFIRMED', 'پرداخت تایید شد'
        PAYMENT_REJECTED = 'PAYMENT_REJECTED', 'پرداخت رد شد'
        PROCESSING = 'PROCESSING', 'در حال آماده‌سازی'
        SHIPPED = 'SHIPPED', 'ارسال شد'
        DELIVERED = 'DELIVERED', 'تحویل داده شد'
        CANCELLED = 'CANCELLED', 'لغو شد'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(
        max_length=30,
        choices=HistoryStatus.choices,
        verbose_name="Status"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    tracking_code = models.CharField(
        max_length=100, blank=True,
        verbose_name="Tracking Code"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Changed By"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    
    class Meta:
        verbose_name = "Order Status History"
        verbose_name_plural = "Order Status Histories"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()}"


# ═══════════════════════════════════════════════════════════════
# حساب‌های بانکی مقصد (پرداخت کارت‌به‌کارت) — قابل مدیریت از ادمین
# ═══════════════════════════════════════════════════════════════

class BankAccount(models.Model):
    """حساب بانکی مقصد برای واریز کارت‌به‌کارت.
    ادمین می‌تواند یک یا چند حساب فعال تعریف کند؛ همه در صفحه پرداخت
    به صورت کارت‌های زیبا با دکمه کپی نمایش داده می‌شوند."""

    bank_name = models.CharField(max_length=50, verbose_name="نام بانک")
    card_number = models.CharField(
        max_length=24, verbose_name="شماره کارت",
        help_text="۱۶ رقمی — جداکننده لازم نیست، خودکار تمیز می‌شود",
    )
    card_holder = models.CharField(max_length=100, verbose_name="نام صاحب حساب")
    iban = models.CharField(
        max_length=30, blank=True, default='',
        verbose_name="شماره شبا", help_text="اختیاری — با یا بدون IR",
    )
    label = models.CharField(
        max_length=60, blank=True, default='',
        verbose_name="برچسب نمایشی", help_text="مثلاً: کارت اصلی فروشگاه (اختیاری)",
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "حساب بانکی مقصد"
        verbose_name_plural = "حساب‌های بانکی مقصد"
        ordering = ['sort_order', 'created_at']

    def clean(self):
        from django.core.exceptions import ValidationError as VE
        trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
        digits = ''.join(ch for ch in str(self.card_number).translate(trans) if ch.isdigit())
        if len(digits) != 16:
            raise VE({'card_number': 'شماره کارت باید دقیقاً ۱۶ رقم باشد.'})
        self.card_number = digits
        if self.iban:
            ib = ''.join(ch for ch in str(self.iban).translate(trans).upper()
                         if ch.isalnum())
            if not ib.startswith('IR'):
                ib = 'IR' + ib
            self.iban = ib

    @property
    def card_grouped(self):
        """نمایش گروه‌بندی‌شده: 6037-9975-XXXX-XXXX"""
        c = self.card_number
        if len(c) == 16:
            return '-'.join(c[i:i + 4] for i in range(0, 16, 4))
        return c

    @property
    def card_digits(self):
        """فقط ارقام — مناسب دکمه کپی"""
        return self.card_number

    def __str__(self):
        return '{} - {}'.format(self.bank_name, self.card_grouped)
