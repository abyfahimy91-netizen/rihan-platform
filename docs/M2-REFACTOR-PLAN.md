# M2-REFACTOR-PLAN.md — برنامه جامع بازنویسی ماژول سفارش

**تاریخ تصویب:** ۲۰۲۶-۰۸-۱۸
**وضعیت:** Approved ✅ (تصویب بنیان‌گذار)
**مرجع اصلی:** ADR-005 (لایه انتزاع پرداخت)
**ماژول:** M2 (Order)
**اسپرینت:** ۲

---

## ۱. هدف بازنویسی

بازنویسی ماژول Order برای **رعایت کامل ADR-005 و D-067**:
- پشتیبانی از پرداخت کارت‌به‌کارت (Card-to-Card) به عنوان روش پیش‌فرض MVP
- پیاده‌سازی لایه انتزاع پرداخت (Payment Abstraction Layer)
- تایید دستی پرداخت توسط ادمین (manual review)
- شفافیت قیمت (ارسال رایگان در ظاهر - D-080)
- شماره سفارش پویا با jdatetime

---

## ۲. ماتریس شکاف کامل

| بخش | وضعیت فعلی | وضعیت مطلوب (ADR-005) | Chunk |
|-----|-----------|----------------------|-------|
| مدل Payment | ۴ فیلد | ۸+ فیلد (evidence کامل) | 2.1 |
| Gateway Interface | Mock/Zarinpal | CardToCardGateway پیش‌فرض | 2.2 |
| PaymentViewSet | verify خودکار | submit_evidence + admin_review | 2.3 |
| پنل ادمین | ساخته نشده | OrderAdmin + PaymentAdmin | 2.4 |
| شماره سفارش | سال هاردکد | jdatetime پویا | 2.5 |
| شفافیت قیمت | هزینه جدا | ارسال رایگان در ظاهر | 2.5 |
| Templates | ساخته نشده | payment_submit + tracking | 2.6 |
| تست‌ها | ناقص | جامع (۱۰+ تست) | 2.7 |

---

## ۳. برنامه ۷ Chunk

### 🟢 Chunk 2.1: مدل Payment
- افزودن: sender_card_last4, transfer_time, receipt_image, reviewed_by, reviewed_at, admin_notes
- افزودن: gateway = 'MANUAL' به choices
- Migration: 0004_card_to_card_fields.py

### 🟡 Chunk 2.2: CardToCardGateway
- پیاده‌سازی CardToCardGateway (Strategy Pattern)
- BankAccountConfig برای خواندن شماره کارت از settings
- حذف یا غیرفعال‌سازی Zarinpal/IDPay

### 🔴 Chunk 2.3: PaymentViewSet
- جایگزینی initiate() با get_payment_info()
- جایگزینی verify() با submit_evidence()
- افزودن admin_confirm() و admin_reject()

### 🟣 Chunk 2.4: admin.py
- OrderAdmin با لیست سفارشات
- PaymentAdmin با قابلیت تایید/رد
- Actionهای سفارشی

### 🔵 Chunk 2.5: شماره سفارش + شفافیت
- نصب jdatetime
- شماره سفارش پویا
- منطق "ارسال رایگان در ظاهر"

### 🟤 Chunk 2.6: Templates
- payment_submit.html
- order_tracking.html
- payment_success.html

### ⚫ Chunk 2.7: تست‌ها
- test_card_to_card_payment.py
- ۱۰+ تست پاس شده

---

## ۴. ارجاعات

- ADR-005: لایه انتزاع پرداخت
- D-067: پرداخت کارت‌به‌کارت
- D-080: شفافیت قیمت
- D-045: Inventory Flow
- MVP-SCOPE.md: M2 (Order)

---

## ۵. اصول رعایت‌شده

- **اصل ۱۱ کرامت مشتری:** ارسال رایگان در ظاهر، بدون هزینه پنهان
- **P1 - Repository is Truth:** این سند منبع حقیقت است
- **P3 - Human Approval:** تایید بنیان‌گذار دریافت شد
- **P5 - Understanding Before Execution:** تمام فایل‌های M2 از گیت‌هاب خوانده شدند
- **P7 - Project Continuity:** تمام تغییرات ثبت می‌شوند

---

## ۶. تاریخچه تغییرات

| تاریخ | تغییر | وضعیت |
|-------|-------|-------|
| ۲۰۲۶-۰۸-۱۸ | تایید برنامه توسط بنیان‌گذار | ✅ تصویب شد |
| ۲۰۲۶-۰۸-۱۸ | شروع Chunk 2.1 | 🟡 در حال اجرا |
