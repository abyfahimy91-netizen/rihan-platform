# ADR-003: استراتژی API و طراحی API-First

| شناسه | ADR-003 |
| --- | --- |
| عنوان | استراتژی API و طراحی API-First |
| وضعیت | **Proposed** — پیش‌نویس اولیه |
| تاریخ | ۲۰۲۶-۰۸-۰۶ |
| مرتبط | ADR-001, ADR-002, D-040 |

> این سند پیش‌نویس است. تا تصویب مشاور، کد API تولید نشود.

## ۱. هدف و مرز

**هدف:** استراتژی API برای ریهان:
- هم‌راستا با API-First (ARCHITECTURE-PRINCIPLES)
- آماده برای اپ موبایل آینده
- سازگار با DRF (ADR-001)
- پوشش ۱۴ ماژول MVP

**مرز:** اصول، ساختار endpoints، فرمت پاسخ، خطاها، Pagination

**Out of Scope:** GraphQL, gRPC, WebSocket, Mobile-only API, Versioning پیچیده, کد پیاده‌سازی

## ۲. اصول API-First

### اصل ۱: Service Layer منبع حقیقت
- API (DRF): Presentation برای کلاینت‌های خارجی
- Web (Template/HTMX): Presentation برای مرورگر
- Service Layer: منطق مشترک

### اصل ۲: هر قابلیت = Endpoint
- هر User Story حداقل یک endpoint
- بر اساس موجودیت‌های ADR-002
- RESTful: GET, POST, PUT, PATCH, DELETE

### اصل ۳: API برای ماشین، Web برای انسان
- API: JSON خالص
- Web: HTML + HTMX
- بدون تداخل

## ۳. پایه فنی

**تکنولوژی:** Django REST Framework (آخرین نسخه سازگار با Django 5.2 LTS)

**نسخه‌بندی:** /api/v1/ (فقط یک نسخه در MVP)

**ساختار URL:**
- /api/v1/auth/ — احراز هویت
- /api/v1/products/ — محصولات
- /api/v1/cart/ — سبد خرید
- /api/v1/orders/ — سفارشات
- /api/v1/payments/ — پرداخت‌ها
- /api/v1/reviews/ — نظرات
- /api/v1/leads/ — سرنخ‌ها
- /api/v1/addresses/ — آدرس‌ها
- /api/v1/user/ — کاربر فعلی

**Content Type:** application/json (UTF-8)

**زمان‌بندی:** p95 زیر ۵۰۰ میلی‌ثانیه، هر endpoint زیر ۲۰۰ میلی‌ثانیه پردازش

## ۴. فرمت پاسخ استاندارد

### پاسخ موفقیت
ساختار: success (boolean) + data (object/array) + meta (timestamp, request_id)

مثال لیست محصولات:
- success: true
- data: آرایه‌ای از محصولات (id, name, slug, price, currency, unit, available)
- meta: timestamp, request_id, pagination (page, per_page, total, total_pages)

مثال ایجاد سفارش:
- success: true
- data: id, order_number, status, total_amount
- meta: timestamp, request_id

### پاسخ خطا
ساختار: success (false) + error (code, message, details) + meta

مثال:
- success: false
- error.code: VALIDATION_ERROR
- error.message: شماره موبایل نامعتبر است (فارسی)
- error.details.phone: آرایه‌ای از پیام‌های خطای فیلد
- meta: timestamp, request_id

### کدهای خطای استاندارد

| HTTP | کد برنامه | توضیح |
| --- | --- | --- |
| 400 | VALIDATION_ERROR | ورودی نامعتبر |
| 400 | BUSINESS_LOGIC_ERROR | خطای منطق (موجودی کافی نیست) |
| 401 | UNAUTHORIZED | احراز هویت نشده |
| 401 | TOKEN_EXPIRED | توکن منقضی |
| 403 | FORBIDDEN | مجوز کافی ندارد |
| 404 | NOT_FOUND | منبع یافت نشد |
| 409 | CONFLICT | تضاد (موجودی رزرو شده) |
| 429 | RATE_LIMIT_EXCEEDED | محدودیت نرخ |
| 500 | INTERNAL_ERROR | خطای سرور |

**اصل:** پیام‌های خطا فارسی و کاربرپسند. جزئیات فنی فقط در details.

## ۵. احراز هویت در لایه API (اصول)

**روش‌ها:**
1. Session-based: برای Web (مرورگر) — HttpOnly Cookie
2. Token-based (JWT): برای API (اپ موبایل آینده) — در Header
3. Device Token: برای Device Remembering (D-040) — ۳۰ روز

**نکته:** پیاده‌سازی کامل OTP/Kavenegar در ADR-006. اینجا فقط اصول.

**قوانین:**
- JWT در HttpOnly + Secure + SameSite Cookie
- Token دستگاه جدا از JWT — بلندمدت — قابل ابطال
- Rate Limit: ۱۰۰ درخواست/دقیقه per IP
- پیام خطای احراز هویت مبهم: شماره یا کد اشتباه است

## ۶. Pagination, Filtering, Ordering

### Pagination
- نوع: Page-based (نه Cursor)
- پیش‌فرض: ۲۰ آیتم per page
- حداکثر: ۱۰۰ آیتم per page
- پارامترها: page و per_page

### Filtering
- نوع: Query parameters ساده
- مثال: category, min_price, max_price
- بدون Filter پیچیده (GraphQL-style)

### Ordering
- پارامتر: sort و order
- پیش‌فرض: created_at desc
- مجاز: فقط فیلدهای ایندکس‌شده (ADR-002)

## ۷. منابع اصلی (هم‌راستا با ADR-002)

### Products (عمومی)
- GET /api/v1/products/ — لیست + فیلتر + pagination
- GET /api/v1/products/slug/ — جزئیات محصول
- POST /api/v1/products/ — ایجاد (فقط ادمین)
- PATCH /api/v1/products/id/ — ویرایش (فقط ادمین)

### Cart (مهمان + کاربر)
- GET /api/v1/cart/ — سبد فعلی
- POST /api/v1/cart/items/ — افزودن به سبد
- PATCH /api/v1/cart/items/id/ — تغییر مقدار
- DELETE /api/v1/cart/items/id/ — حذف از سبد

### Orders (کاربر + ادمین)
- POST /api/v1/orders/ — ایجاد سفارش (از سبد)
- GET /api/v1/orders/ — لیست سفارشات کاربر
- GET /api/v1/orders/id/ — جزئیات سفارش
- PATCH /api/v1/orders/id/status/ — تغییر وضعیت (فقط ادمین)

### Payments (کاربر + ادمین)
- POST /api/v1/orders/order_id/payments/ — ثبت پرداخت (D-067)
- GET /api/v1/orders/order_id/payments/ — لیست پرداخت‌ها
- PATCH /api/v1/payments/id/confirm/ — تأیید (فقط ادمین)
- PATCH /api/v1/payments/id/reject/ — رد (فقط ادمین)

### Reviews (کاربر + ادمین)
- POST /api/v1/products/product_id/reviews/ — ثبت نظر
- GET /api/v1/products/product_id/reviews/ — لیست نظرات تأییدشده
- PATCH /api/v1/reviews/id/approve/ — تأیید (فقط ادمین)

### Leads (عمومی)
- POST /api/v1/leads/ — ثبت سرنخ
- GET /api/v1/leads/ — لیست (فقط ادمین)

### Addresses (کاربر)
- GET /api/v1/addresses/ — لیست آدرس‌های کاربر
- POST /api/v1/addresses/ — افزودن آدرس
- PATCH /api/v1/addresses/id/ — ویرایش
- DELETE /api/v1/addresses/id/ — حذف (soft)

### Auth (عمومی)
- POST /api/v1/auth/otp/request/ — درخواست OTP
- POST /api/v1/auth/otp/verify/ — تأیید OTP
- POST /api/v1/auth/logout/ — خروج
- GET /api/v1/user/ — اطلاعات کاربر فعلی

## ۸. مجوزها و نقش‌ها (ارجاع به RBAC)

**نقش‌ها (از ADR-002 - Role/UserRole):**
- customer: دسترسی به سفارشات و پروفایل خود
- admin: دسترسی کامل
- family_admin: دسترسی ادمین بدون مدیریت کاربر
- family_member: دسترسی محدود
- observer: فقط خواندن
- supplier: فقط سفارشات مرتبط با محصولات خود

**اصل:** هر endpoint باید نقش‌های مجاز را مشخص کند.
**پیاده‌سازی:** در ADR-006 (Authentication) و ADR-007 (Admin/UI)

## ۹. Idempotency و ایمنی عملیات حساس

### Idempotency (برای عملیات ایجاد)
- مشکل: اگر کاربر دکمه ثبت سفارش را دو بار بزند، دو سفارش ایجاد نشود
- راه‌حل: Idempotency-Key در Header
- پیاده‌سازی: کلاینت یک UUID تولید می‌کند و در Header می‌فرستد
- سرور: اگر همان Key قبلاً پردازش شده، همان پاسخ قبلی را برمی‌گرداند

### عملیات حساس
- تأیید پرداخت: نیاز به تأیید دو مرحله‌ای در آینده (ADR-007)
- حذف محصول: Soft delete + لاگ در AuditLog
- تغییر قیمت: لاگ در AuditLog + تاریخچه (در آینده)

### Rate Limiting
- عمومی: ۱۰۰ درخواست/دقیقه per IP
- احراز هویت: ۳ OTP در ۱۰ دقیقه per شماره (D-040)
- پیاده‌سازی: در ADR-006

## ۱۰. Out of Scope صریح

- GraphQL
- gRPC
- WebSocket (Real-time)
- Mobile-only API (API جداگانه)
- Versioning پیچیده (فقط /api/v1/)
- پیاده‌سازی کامل OTP/Kavenegar (ADR-006)
- طراحی UI (فرانت‌اند)
- کد پیاده‌سازی (فقط اصول)
- نصب پکیج (در فاز ۵)

## ۱۱. ارجاعات

- ADR-001: Backend Framework (Django 5.2 LTS)
- ADR-002: معماری دیتابیس (۱۷ موجودیت)
- D-040: احراز هویت Passwordless
- D-067: پرداخت کارت‌به‌کارت
- ARCHITECTURE-PRINCIPLES.md: الگوی ۱ (API-First)
- MVP-SCOPE.md: ۱۴ ماژول Must Have
- USER-STORIES.md: ۵۱ داستان کاربر
