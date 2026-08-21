# D-089: Excel Export گزارش مالی (US-031)

**تاریخ:** ۲۰۲۶-۰۸-۲۱
**وضعیت:** Approved
**فاز:** ۵ (Development)
**مرتبط با:** US-031, M6

## ۱. تصمیم
پیاده‌سازی export گزارش مالی به Excel با کتابخانه openpyxl

## ۲. ویژگی‌ها
- فایل .xlsx با دو شیت:
  - Sheet 1: "تراکنش‌های مالی" - تمام تراکنش‌ها با تاریخ شمسی
  - Sheet 2: "خلاصه" - آمار کلی (درآمد، تعداد سفارش، میانگین، بدهی)
- طراحی RTL
- Header با رنگ برند (#2D5A2D)
- تاریخ‌ها به فرمت شمسی (jdatetime)
- مبلغ‌ها با هزارگان

## ۳. دسترسی
- فقط staff (ادمین)
- URL: `/finance/export/excel/`
- نام فایل: `finance-report-YYYY-MM-DD.xlsx`

## ۴. فایل‌ها
- `src/modules/finance/exports.py` - کلاس FinanceExporter
- `src/modules/finance/views.py` - View finance_export_excel
- `src/modules/finance/urls.py` - مسیر export
- `admin_dashboard.html` - دکمه دانلود

## ۵. تست‌ها
- Runtime test: تولید فایل > 1KB
- System check: بدون خطا

## ۶. توسعه‌های آینده
- فیلتر بازه زمانی (From/To)
- فیلتر تأمین‌کننده
- Export ماهانه به صورت خودکار
- افزودن به API
