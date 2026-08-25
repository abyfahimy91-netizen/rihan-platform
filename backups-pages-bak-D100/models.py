"""
تنظیمات سراسری سایت (Singleton) — کنترل محتوای صفحه اصلی، اطلاعیه،
اطلاعات تماس و فوتر، همه از داخل پنل ادمین و بدون نیاز به تغییر کد.
"""
from django.db import models


class SiteSettings(models.Model):
    """تنظیمات سایت — همیشه فقط یک رکورد وجود دارد (pk=1)."""

    # ── برند ──
    site_name = models.CharField(
        'نام فروشگاه', max_length=100, default='ریهان',
        help_text='این نام در لوگوی هدر و پنل مدیریت نمایش داده می‌شود.',
    )

    # ── صفحه اصلی (بخش هیرو) ──
    hero_badge = models.CharField(
        'برچسب بالای عنوان', max_length=120,
        default='فروشگاه آنلاین اعتمادمحور',
    )
    hero_title = models.TextField(
        'عنوان اصلی صفحه اول', default='انتخاب مطمئن،\nهر محصولی که باشد',
        help_text='هر خط با کلید Enter جدا می‌شود و در دو سطر نمایش داده می‌شود.',
    )
    hero_subtitle = models.TextField(
        'توضیح زیر عنوان', default='ریهان یک فروشگاه عمومی با تعداد زیاد کالا نیست.\nارزش ریهان در انتخاب‌های دقیق و معنادار است.',
    )
    hero_quote = models.TextField(
        'پیام ویژه / نقل‌قول', blank=True, default='',
        help_text='اگر خالی بماند این بخش نمایش داده نمی‌شود.',
    )
    featured_title = models.CharField(
        'عنوان بخش محصولات', max_length=120, default='محصولات برگزیده',
    )

    # ── نوار اطلاعیه ──
    announcement_active = models.BooleanField(
        'نمایش نوار اطلاعیه بالای سایت', default=False,
    )
    announcement_text = models.CharField(
        'متن اطلاعیه', max_length=250, blank=True, default='',
        help_text='مثال: ارسال رایگان برای خریدهای بالای ۵۰۰ هزار تومان',
    )

    # ── اطلاعات تماس ──
    contact_phone = models.CharField('تلفن تماس', max_length=30, blank=True, default='')
    contact_email = models.EmailField('ایمیل', blank=True, default='')
    contact_address = models.TextField(
        'آدرس / توضیح تماس', blank=True, default='فروشگاه آنلاین — ارسال به سراسر ایران',
    )
    contact_hours = models.CharField(
        'ساعات پاسخگویی', max_length=120, default='هر روز ۱۱ تا ۱۹',
    )

    # ── شبکه‌های اجتماعی ──
    instagram_url = models.URLField('آدرس اینستاگرام', blank=True, default='')
    telegram_url = models.URLField('آدرس تلگرام', blank=True, default='')
    whatsapp_number = models.CharField(
        'شماره واتساپ', max_length=30, blank=True, default='',
        help_text='فقط شماره با کد کشور، مثال: 989123456789',
    )

    # ── فوتر ──
    footer_tagline = models.CharField(
        'شعار زیر نام برند در فوتر', max_length=200,
        default='انتخاب مطمئن، هر محصولی که باشد',
    )
    footer_description = models.TextField(
        'توضیح کوتاه فوتر', default='فروشگاه آنلاین اعتمادمحور با محصولات اصیل و با کیفیت',
    )
    footer_copyright = models.CharField(
        'متن کپی‌رایت', max_length=200, default='© ۱۴۰۵ ریهان. تمام حقوق محفوظ است.',
    )

    updated_at = models.DateTimeField('آخرین به‌روزرسانی', auto_now=True)

    class Meta:
        verbose_name = '⚙️ تنظیمات سایت'
        verbose_name_plural = '⚙️ تنظیمات سایت'

    def __str__(self):
        return f'تنظیمات «{self.site_name}»'

    def save(self, *args, **kwargs):
        self.pk = 1  # همیشه تک‌رکورد
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj
