"""
تنظیمات سراسری سایت (Singleton) — کنترل محتوای صفحه اصلی، اطلاعیه،
اطلاعات تماس، صفحات ثابت (درباره ما / سیاست مرجوعی / سوالات متداول)
و فوتر، همه از داخل پنل ادمین و بدون نیاز به تغییر کد. (D-100)
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

    # ── D-105: اطلاع‌رسانی پیامکی زنجیره ارسال ──
    sms_notify_suppliers = models.BooleanField(
        'پیامک سفارش جدید به تامین‌کننده', default=True,
        help_text='با ثبت سفارشِ محصولِ تامین‌کننده‌دار، پیامک خودکار دریافت کند',
    )
    sms_notify_customers = models.BooleanField(
        'پیامک کد رهگیری به مشتری', default=True,
        help_text='پس از ثبت کد رهگیری، مشتری لینک پیگیری یک‌کلیکی دریافت کند',
    )

    # ── D-107: برند لاتین + قالب پیامک‌ها + اشتراک‌گذاری ──
    brand_name_latin = models.CharField(
        'نام برند (لاتین، برای پیامک و استوری)', max_length=40, default='Rihan',
        help_text='در همه پیامک‌ها، متن دستور ارسال و تصویر استوری با همین املای لاتین نمایش داده می‌شود',
    )
    sms_text_customer_shipped = models.TextField(
        'قالب پیامک رهگیری به مشتری', blank=True, default='',
        help_text='متغیرها: {order_number} {carrier} {tracking_code} {link} {brand} — خالی = قالب پیش‌فرض',
    )
    sms_text_supplier_assign = models.TextField(
        'قالب پیامک سفارش جدید به تامین‌کننده', blank=True, default='',
        help_text='متغیرها: {order_number} {items} {link} {brand} — خالی = قالب پیش‌فرض',
    )
    share_message_text = models.TextField(
        'متن پیام اشتراک‌گذاری محصول', blank=True, default='',
        help_text='اول پیام هنگام ارسال محصول در پیام‌رسان‌ها؛ بعد از آن نام محصول، لینک کوتاه و هشتگ‌ها خودکار می‌آید',
    )
    share_hashtags = models.CharField(
        'هشتگ‌های اشتراک‌گذاری', max_length=300, blank=True,
        default='#Rihan #فروشگاه_آنلاین #خرید_آنلاین',
        help_text='با فاصله جدا شود؛ در کپشن استوری و پیام اشتراک‌گذاری می‌آید',
    )

    # ── شبکه‌های اجتماعی ──
    instagram_url = models.URLField('آدرس اینستاگرام', blank=True, default='')
    telegram_url = models.URLField('آدرس تلگرام', blank=True, default='')
    whatsapp_number = models.CharField(
        'شماره واتساپ', max_length=30, blank=True, default='',
        help_text='فقط شماره با کد کشور، مثال: 989123456789',
    )

    # ── صفحه درباره ما (D-100) ──
    about_title = models.CharField(
        'عنوان صفحه درباره ما', max_length=120, default='درباره ریهان',
    )
    about_body = models.TextField(
        'متن صفحه درباره ما',
        default=(
            'ریهان یک فروشگاه آنلاین اعتمادمحور است.\n'
            '\n'
            'تیم ریهان سال‌هاست تجربه خرید و ارزیابی دقیق کالاها را برای اطرافیان داشته است؛ '
            'از اقلام روزمره تا محصولات خاص - هر محصولی که ارزش و کیفیت داشته باشد.\n'
            '\n'
            'حالا این تجربه را در قالب یک وب‌سایت حرفه‌ای ارائه می‌دهیم؛ '
            'بدون برندسازی شخصی، لوکس، باوقار، تدریجی و خانوادگی.\n'
            '\n'
            '> محصول متغیر است؛ اعتماد ثابت.\n'
            '\n'
            '# اصول دهگانه ما\n'
            '\n'
            '۱. داستان‌محور: هر محصول داستانی دارد\n'
            '۲. اعتماد ثابت، محصول متغیر: برند به محصول گره نمی‌خورد\n'
            '۳. انعطاف کامل: آماده تغییر بر اساس نیاز مشتری\n'
            '۴. شأن و شخصیت: احترام به مشتری در همه مراحل\n'
            '۵. خانوادگی: کسب‌وکار خانوادگی با رشد تدریجی\n'
            '۶. تدریجی: رشد ۵ ساله بدون عجله\n'
            '۷. مستند و سیستمی: همه چیز ثبت و قابل پیگیری\n'
            '۸. محدودیت‌ها محترم: پذیرش واقعیت‌ها و کار با آن‌ها\n'
            '۹. مستقل از خارج: عدم وابستگی به پلتفرم‌های خارجی\n'
            '۱۰. کنترل کامل ادمین: مدیریت همه جنبه‌ها از پنل'
        ),
        help_text=(
            'قواعد نوشتن: خط خالی = پاراگراف جدید | خطی که با «#» شروع شود = تیتر بخش | '
            'خطوطی که با «-» شروع شوند = فهرست نقطه‌ای | '
            'خطوطی که با «۱.» «۲.» شروع شوند = فهرست شماره‌ای | '
            'خطی که با «>» شروع شود = نقل‌قول برجسته'
        ),
    )

    # ── صفحه سیاست مرجوعی (D-100) ──
    return_policy_title = models.CharField(
        'عنوان صفحه سیاست مرجوعی', max_length=120, default='سیاست مرجوعی',
    )
    return_policy_body = models.TextField(
        'متن کامل سیاست مرجوعی',
        default=(
            'ما در ریهان به کیفیت محصولات خود اطمینان داریم؛ اگر به هر دلیلی '
            'از خرید خود راضی نبودید، تا ۷ روز فرصت مرجوعی دارید.\n'
            '\n'
            '# شرایط مرجوعی\n'
            '\n'
            '- محصول باید در بسته‌بندی اصلی و استفاده نشده باشد\n'
            '- برچسب‌ها و اتیکت‌ها نباید کنده شده باشند\n'
            '- محصول نباید آسیب دیده یا لکه‌دار شده باشد\n'
            '- فقط تا ۷ روز پس از تحویل قابل مرجوع است\n'
            '\n'
            '# فرآیند مرجوعی\n'
            '\n'
            '۱. با پشتیبانی تماس بگیرید\n'
            '۲. شماره سفارش و دلیل مرجوعی را اعلام کنید\n'
            '۳. هماهنگی برای ارسال محصول انجام می‌شود\n'
            '۴. پس از دریافت و تأیید سلامت محصول، مبلغ به حساب شما بازگردانده می‌شود\n'
            '۵. بازگشت وجه طی ۳ تا ۵ روز کاری انجام می‌شود\n'
            '\n'
            '# هزینه‌ها\n'
            '\n'
            'نکته مهم: هزینه ارسال مرجوعی بر عهده مشتری است؛ مگر اینکه محصول '
            'آسیب‌دیده یا اشتباه ارسال شده باشد.\n'
            '\n'
            '# استثنائات\n'
            '\n'
            'موارد زیر قابل مرجوع نیستند:\n'
            '\n'
            '- محصولات بهداشتی و شخصی (به دلایل بهداشتی)\n'
            '- محصولات سفارشی‌سازی شده\n'
            '- محصولاتی که بیش از ۷ روز از تحویل آن‌ها گذشته باشد'
        ),
        help_text=(
            'قواعد نوشتن: خط خالی = پاراگراف جدید | خطی که با «#» شروع شود = تیتر بخش | '
            'خطوطی که با «-» شروع شوند = فهرست نقطه‌ای | '
            'خطوطی که با «۱.» «۲.» شروع شوند = فهرست شماره‌ای | '
            'خطی که با «>» شروع شود = نقل‌قول برجسته'
        ),
    )

    # ── صفحه سوالات متداول (D-100) ──
    faq_intro = models.TextField(
        'متن بالای سوالات متداول', blank=True, default='',
        help_text='اگر خالی بماند هیچ متنی بالای سوالات نمایش داده نمی‌شود. خودِ سوال‌ها از بخش «سوالات متداول» پنل مدیریت شده‌اند.',
    )

    # ── تعهدات زیر دکمه خرید (D-104) ──
    buy_commitments = models.TextField(
        'تعهدهای زیر دکمه خرید',
        help_text='هر خط یک تعهد. در صفحه محصول زیر دکمه خرید نمایش داده می‌شود. اگر خالی باشد هیچ تعهدی نشان داده نمی‌شود.',
        default=(
            '۷ روز ضمانت بازگشت وجه\n'
            'ارسال ایمن و بیمه‌شده\n'
            'تضمین سلامت و اصالت کالا'
        ),
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


class FaqItem(models.Model):
    """یک سوال متداول — در صفحه «سوالات متداول» سایت نمایش داده می‌شود."""

    question = models.CharField('سوال', max_length=250)
    answer = models.TextField(
        'پاسخ',
        help_text='می‌تواند چند خط باشد؛ هر Enter یک خط جدید نمایش داده می‌شود.',
    )
    sort_order = models.PositiveIntegerField('ترتیب نمایش', default=0)
    is_active = models.BooleanField('فعال (نمایش در سایت)', default=True)
    created_at = models.DateTimeField('ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'سوال متداول'
        verbose_name_plural = '❓ سوالات متداول'
        ordering = ('sort_order', 'id')

    def __str__(self):
        return self.question
