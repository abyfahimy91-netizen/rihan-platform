# PROJECT-INDEX — نقشه جامع و مانیفست مخزن ریهان

**نسخه پروژه:** 0.5.6-dev
**آخرین بهروزرسانی:** 2026-08-14
**وضعیت:** منبع یگانه حقیقت (Single Source of Truth)

---

## ۱. فایل‌های ریشه و اسناد حاکمیتی

| مسیر فایل | دسته‌بندی | شرح سند |
|:---|:---|:---|
| `AI-ENTRY.md` | حاکمیت AI | نقطه ورود و قوانین کاربری سیستم‌عامل AI-VOS |
| `CENTRAL-STORY.md` | قانون اساسی | داستان اصالت، رسالت برند و اصول اعتمادمحور |
| `FUNDAMENTAL-PRINCIPLES.md` | قانون اساسی | اصول ۱۱ گانه تغییرناپذیر (کرامت مشتری و Zero Dark Patterns) |
| `CONTINUITY.md` | تداوم | وضعیت لحظه‌ای، ماتریس ۱۴ ماژول و اقدام بعدی |
| `PROJECT-INDEX.md` | مانیفست | نقشه کامل تمامی فایل‌های موجود در مخزن |
| `README.md` | شناسنامه | شناسنامه عمومی پروژه و پلتفرم ریهان |
| `Dockerfile` | زیرساخت | پیکربندی ایمیج کانتینر پایتون ۳.۱۰ و وابستگی‌ها |
| `docker-compose.yml` | زیرساخت | ارکستراسیون سرویس‌های Django, PostgreSQL 16, Redis 7 |
| `requirements.txt` | پکیج‌ها | لیست وابستگی‌های بک‌اند (Django, DRF, Celery/Redis, Gunicorn) |
| `.env.example` | امنیت | الگوی متغیرهای محیطی امن پروژه |

---

## ۲. ساختار کدهای منبع (`src/`)

| مسیر پکیج / فایل | ماژول مرتبط | شرح کارکرد |
|:---|:---:|:---|
| `src/manage.py` | هسته | اسکریپت مدیریت و اجرای فرامین جنگو |
| `src/rihan/settings.py` | هسته | پیکربندی ماژولار جنگو، دیتابیس، کش و زبان |
| `src/rihan/urls.py` | هسته | مسیریاب سراسری و نگاشت Sitemaps |
| `src/rihan/wsgi.py` | زیرساخت | نقطه اتصال وب‌سرور Gunicorn |
| `src/apps/core/feature_flags.py` | **M14** | موتور پرچم‌های قابلیت و معماری افزونه‌محور (ADR-004) |
| `src/apps/catalog/models.py` | **M1, M9** | دسته‌بندی‌ها، محصولات، تصاویر و ContentBlocks |
| `src/apps/catalog/views.py` | **M1, M13** | ویوهای کاتالوگ HTMX و اندپوینت‌های REST API |
| `src/apps/catalog/sitemaps.py` | **M7** | تولید پویای sitemap.xml و سئو تکنیکال |
| `src/apps/orders/models.py` | **M2, M3** | مدل‌های سفارش، آیتم‌های سفارش و شماره فاکتور RH-1405 |
| `src/apps/orders/cart.py` | **M2** | مدیریت سشن سبد خرید و محاسبه قیمت تمام‌شده (D-046) |
| `src/apps/orders/admin.py` | **M3** | پنل مدیریت خانواده، نشان‌های وضعیت و صدور فاکتور |
| `src/apps/orders/views.py` | **M2, M7** | ویوهای سبد خرید، تسویه‌حساب و استعلام /track/ |
| `src/apps/accounts/models.py` | **M10** | مدل کدهای یکبارمصرف (PhoneOTP ۶ رقمی) |
| `src/apps/accounts/services.py` | **M10** | سرویس پیامکی OTP ردیس و انتزاع کاوه‌نگار |
| `src/modules/finance/models.py` | **M6** | SupplierLedger، SupplierTransaction، Settlement |
| `src/modules/finance/services.py` | **M6** | FinanceService - محاسبات مالی و آمار داشبورد |
| `src/modules/finance/views.py` | **M6** | داشبورد مالی ادمین و تأمین‌کننده |
| `src/modules/finance/signals.py` | **M6** | سیگنال ثبت خودکار تراکنش فروش |
| `src/apps/accounts/views.py` | **M10** | ورود پیامکی پیش‌فرض + ورود با پسورد پشتیبان (Fallback) |

---

## ۳. قالب‌های وب (`src/templates/`)

| مسیر قالب | کاربرد | ویژگی‌ها |
|:---|:---|:---|
| `src/templates/base.html` | تمپلیت والد | تم لوکس مینیمال، تایپوگرافی Vazirmatn، پشتیبانی HTMX/Alpine |
| `src/templates/catalog/list.html` | کاتالوگ | لیست محصولات با فیلتر لحظه‌ای دسته‌بندی بدون رفرش |
| `src/templates/catalog/detail.html` | جزئیات کالا | گالری تصاویر، بلوک‌های روایتی، قیمت تمام‌شده و اسکیما سئو |
| `src/templates/orders/cart.html` | سبد خرید | شفافیت کامل مالی (ارسال لحاظ‌شده)، حذف ۱ کلیکی |
| `src/templates/orders/checkout.html` | تسویه‌حساب | فرم ثبت سفارش سریع با کمترین اصطکاک (Guest Checkout) |
| `src/templates/orders/order_success.html` | تایید سفارش | صدور فاکتور، راهنمای کارت‌به‌کارت و دکمه بارگذاری رسید |
| `src/templates/orders/tracking.html` | **M7** | سامانه پیگیری با تایم‌لاین ۵ مرحله‌ای و لینک پست |
| `src/templates/admin/orders/invoice.html` | **M3** | برگه فاکتور چاپی فاخر جهت قرار در بسته مرسوله |
| `src/templates/accounts/login.html` | **M10** | فرم ورود پیامکی ۶ رقمی + سوئیچ رمز پشتیبان |
| `src/templates/accounts/profile.html` | **M10** | پنل کاربری خریدار و ثبت رمز عبور پشتیبان |

---

## ۴. آزمون‌های خودکار (`tests/`)

| فایل تست | ماژول‌های تحت پوشش | تعداد تست‌ها |
|:---|:---:|:---:|
| `tests/test_catalog.py` | M1, M7, M9, M13 | ۲ تست (پاس ✅) |
| `tests/test_orders.py` | M2 | ۲ تست (پاس ✅) |
| `tests/test_family_admin.py` | M3 | ۱ تست (پاس ✅) |
| `tests/test_tracking.py` | M7 | ۲ تست (پاس ✅) |
| `tests/test_accounts.py` | M10 | ۲ تست (پاس ✅) |
