# D-086: پیاده‌سازی ماژول مالی (M6)

**تاریخ:** ۲۰۲۶-۰۸-۲۱
**وضعیت:** Approved
**فاز:** ۵ (Development)
**مرتبط با:** US-021, US-030, US-045, D-079

---

## ۱. تصمیم

پیاده‌سازی کامل ماژول مالی (M6) با معماری زیرساخت مستقل:
- SupplierLedger: دفتر حساب یک‌به‌یک برای هر تأمین‌کننده
- SupplierTransaction: ثبت تراکنش‌های فروش/تسویه/مرجوعی
- Settlement: مدیریت تسویه‌های مالی
- FinanceService: سرویس محاسباتی مرکزی
- سیگنال خودکار: ثبت تراکنش فروش هنگام DELIVERED شدن سفارش

## ۲. دلایل و زمینه

### چرا M6 اولویت اول پس از M4 بود؟
- کسب‌وکار بدون شفافیت مالی نمی‌تواند مستقل شود
- تأمین‌کنندگان بدون دید از حسابشان اعتماد نمی‌کنند
- مدیریت ریهان برای تصمیم‌گیری استراتژیک نیاز به آمار دقیق دارد

### User Stories پوشش داده شده:
- US-021 (Must): گزارش مالی ادمین
- US-030 (Must): حساب ماهانه تأمین‌کننده
- US-045 (Must): قیمت‌گذاری شفاف (زیرساخت داده‌ای)

## ۳. معماری انتخاب‌شده

### ۳.۱ ساختار اپ:

    src/modules/finance/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── services.py
    ├── signals.py
    ├── tests.py
    ├── urls.py
    ├── views.py
    ├── migrations/
    └── templates/finance/
        ├── base.html
        ├── admin_dashboard.html
        └── supplier_dashboard.html

### ۳.۲ الگوهای کلیدی:
- Property-based Calculation: ledger.balance به صورت @property محاسبه می‌شود
- Idempotent Signals: جلوگیری از ثبت تکراری تراکنش
- Decorator Pattern: کنترل دسترسی با require_staff و require_supplier
- Safe Navigation: hasattr(user, 'supplier_profile')

### ۳.۳ وابستگی‌ها:
- src.modules.catalog.Supplier (OneToOneField user)
- src.modules.order.Order و OrderItem (foreign key)

## ۴. تست‌ها (۱۱ تست - ۱۰۰٪ پاس)

### FinanceServiceTestCase (۶ تست):
- ایجاد دفتر حساب (get_or_create)
- ثبت تراکنش فروش
- جلوگیری از ثبت تکراری
- ایجاد تسویه
- محاسبه موجودی (فروش - تسویه)
- رد کردن محصول بدون تأمین‌کننده

### FinanceDashboardTestCase (۱ تست):
- آمار داشبورد (فقط DELIVERED شمرده می‌شود)

### FinanceViewsTestCase (۴ تست):
- دسترسی staff به داشبورد ادمین
- دسترسی تأمین‌کننده به داشبورد تأمین‌کننده
- رد کاربر عادی از داشبورد ادمین
- نمایش لیست دفاتر در داشبورد ادمین

## ۵. کارهای باقی‌مانده (Should/Could)

### US-031 (Should): خروجی اکسل گزارش مالی
- پیاده‌سازی با کتابخانه openpyxl یا pandas
- فیلتر بازه زمانی

### بهبودهای آینده:
- نمودار فروش ۳۰ روزه (Chart.js)
- فیلتر تاریخ شمسی (jdatetime)
- گزارش مالیاتی
- API برای ادغام با نرم‌افزار حسابداری

## ۶. ریسک‌های شناسایی‌شده

| ریسک | شدت | وضعیت |
|------|------|-------|
| RuntimeWarning naive datetime | کم | TODO |
| وابستگی به D-085 (User-Supplier Link) | بالا | حل شده |
| عدم ثبت اتوماتیک مرجوعی | متوسط | TODO |

## ۷. فایل‌های تغییر یافته

- src/modules/finance/ - کل ماژول جدید
- src/config/settings.py - اضافه کردن finance به INSTALLED_APPS
- src/config/urls.py - path /finance/
