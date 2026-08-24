# D-096 — فارسی‌سازی کامل پیام‌ها، اعداد و تاریخ‌ها

**تاریخ:** 1405/06/02
**وضعیت:** Accepted (پیاده‌سازی و تست شد)
**کامیت:** 413beb8

## زمینه

کاربر هنگام افزودن سماق به سبد با تعداد بیشتر از موجودی انبار، هشدار انگلیسی
`Insufficient stock. Maximum available: 8` دریافت کرد. قانون پروژه: **هر اطلاع‌رسانی
و هشدار به کاربر در هر نقشی باید فارسی، محترمانه و با تایپوگرافی فارسی باشد؛
همه اعداد با ارقام فارسی و جداکننده هزارگان؛ همه تاریخ‌ها شمسی.**

## تصمیم

### ۱) زیرساخت مرکزی (نه پراکندگی)

- `src/core/fa.py`: توابع `fa_digits` (تبدیل ارقام)، `money` (جداکننده هزارگان ٬ + ارقام فارسی)，
  `jalali_date/jalali_datetime_str/jalali_human` (تاریخ شمسی با jdatetime و منطقه زمانی تهران)
- `src/core/templatetags/fa_tags.py`: فیلترهای قالبی `fa | money | jdate | jtime | jdate_human`
  — استفاده: `{% load fa_tags %}` در هر قالب

### ۲) پیام‌های کاربر-facing

منبع پیام = لایه سرویس، نه ویو. ترجمه شد:
- `order/services.py`: «محصول پیدا نشد / تعداد حداقل ۱ / گزینه معتبر نیست /
  موجودی کافی نیست؛ حداکثر مقدار قابل سفارش X عدد است. لطفاً تعداد را تعدیل بفرمایید.»
- `checkout_service.py`: «سبد خرید شما خالی است؛ ...»
- `catalog/services/exceptions.py`: InsufficientStockError/ProductNotFoundError با ارقام فارسی داخل خود پیام (`fa_digits`)
- ویوها دیگر متن خام exception را لو نمی‌دهند: `e.messages[0]` برای ValidationError،
  متن ثابت محترمانه برای Exception عمومی + catch اختصاصی InsufficientStockError در تسویه
- پیام بلوک‌های محتوا (core/blocks/*) هم فارسی شد (نمایش به ادمین در ویرایشگر بلوک)

### ۳) اعداد و تاریخ

- تمام `floatformat:0` های نمایشی → فیلتر `money`؛ شمارنده‌ها → `fa`
- تمام `date:"Y/m/d"` ها → `jdate`/`jtime` شمسی
- ستون‌های تاریخ ادمین → متدهای `created_at_fa` (Order/Payment/Cart/Finance/Audit/Review/Pages)
- مبالغ ادمین → `money()` (toman، total_amount، amount_display، stock_display، ...)
- داشبورد ادمین: آمارها و «آخرین سفارش‌ها» کاملاً فارسی
- **استثنا:** شماره کارت بانکی در صفحه پرداخت عمداً لاتین می‌ماند (قابلیت کپی/انتقال به اپ بانک)

### ۴) رفع باگ قدینی کشف‌شده

`variant_dispatch.InventoryService.return_stock` وجود نداشت → تست مرجوعی خطا می‌داد.
پیاده شد: `VariantStockService.return_stock` (افزودن stock_quantity) + مسیریابی dispatch.

## پیامد

- هر عدد/تاریخ جدید باید با همین فیلترها نمایش داده شود؛ رشته خام `{{ x }}` برای عدد ممنوع
- ورودی‌های فرم (تعداد، موبایل، کد پستی) لاتین می‌مانند تا منطق parseInt/اعتبارسنجی نشکند
- JS واریانت از قبل `toLocaleString("fa-IR")` داشت — حفظ شد
