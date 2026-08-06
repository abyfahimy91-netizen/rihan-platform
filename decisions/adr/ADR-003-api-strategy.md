# ADR-003: استراتژی API و طراحی API-First

| شناسه | ADR-003 |
| --- | --- |
| عنوان | استراتژی API و طراحی API-First |
| وضعیت | **Approved ✅** — مصوب شده توسط مشاور پروژه (۱۴۰۵/۰۵/۱۶) |
| تاریخ | ۲۰۲۶-۰۸-۰۶ |
| مرتبط | ADR-001, ADR-002, D-040 |

> **✅ این سند مصوب است.** هر تغییر اساسی نیاز به ADR جدید دارد.
> **تاریخ تصویب:** ۱۴۰۵/۰۵/۱۶
> **تأییدکننده:** مشاور پروژه

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

**زمان‌بندی (هدف عملکردی، نه تعهد سخت فاز ۴):**
- p95 زیر ۵۰۰ میلی‌ثانیه برای درخواست‌های عمومی
- هر endpoint زیر ۲۰۰ میلی‌ثانیه پردازش سرور
- **نکته:** این اهداف در فاز ۸ (Deployment) با monitoring واقعی سنجیده می‌شوند

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

### سه کانال جداگانه (غیرقابل ترکیب):

**۱. Web (مرورگر فعلی):**
- روش: Session cookie
- ویژگی: HttpOnly, Secure, SameSite=Strict
- استفاده: تمام درخواست‌های HTMX و Template
- انقضا: ۳۰ روز (با تمدید خودکار)

**۲. API (کلاینت‌های آینده - اپ موبایل):**
- روش: Bearer Token در Authorization header
- فرمت: JWT
- ویژگی: Stateless، قابل ابطال
- استفاده: فقط درخواست‌های /api/v1/ از اپ موبایل
- **نکته:** در MVP فعال نمی‌شود. پیاده‌سازی در آینده با ADR جدید.

**۳. Device Remembering (D-040):**
- روش: Device Token جداگانه
- ویژگی: بلندمدت (۳۰ روز)، قابل ابطال از پنل کاربر
- استفاده: حذف نیاز به OTP مجدد برای دستگاه شناخته‌شده
- پیاده‌سازی: در ADR-006

**قوانین کلی:**
- Rate Limit: ۱۰۰ درخواست/دقیقه per IP
- پیام خطای احراز هویت مبهم: شماره یا کد اشتباه است
- **هرگز JWT را هم در Header و هم در Cookie نفرستید** — فقط یکی بسته به کانال

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
- GET /api/v1/products/{slug}/ — جزئیات محصول (فقط slug، نه id — URL-friendly)
- POST /api/v1/products/ — ایجاد (فقط ادمین، با permission class)
- PATCH /api/v1/products/{id}/ — ویرایش (فقط ادمین، با permission class)
- DELETE /api/v1/products/{id}/ — Soft delete (فقط ادمین، با permission class)

**نکته:** در MVP فقط slug برای نمایش عمومی استفاده می‌شود. id فقط در پنل ادمین.

### Cart (مهمان + کاربر)

**مکانیزم شناسایی:**
- **کاربر لاگین:** سبد از طریق session cookie به user_id متصل می‌شود
- **مهمان:** سبد از طریق X-Session-Key header (تولیدشده توسط مرورگر) شناسایی می‌شود
- **Merge پس از login:** هنگام ورود کاربر مهمان، سبد session به کاربر منتقل می‌شود (Cart.session_key → Cart.user_id)

**Endpoints:**
- GET /api/v1/cart/ — سبد فعلی (بر اساس session یا user)
- POST /api/v1/cart/items/ — افزودن به سبد
- PATCH /api/v1/cart/items/id/ — تغییر مقدار
- DELETE /api/v1/cart/items/id/ — حذف از سبد

### Orders (کاربر + مهمان + ادمین)

**POST /api/v1/orders/ — ایجاد سفارش:**
- **حالت ۱ (کاربر لاگین):** از سبد کاربر + آدرس ذخیره‌شده
- **حالت ۲ (مهمان):** نیاز به body شامل:
  - guest_phone (شماره موبایل مهمان)
  - shipping_full_name, shipping_phone, shipping_province, shipping_city, shipping_address, shipping_postal_code
  - (هم‌راستا با ADR-002 - Order.shipping_* fields)

**Endpoints:**
- POST /api/v1/orders/ — ایجاد سفارش (از سبد، با دو حالت بالا)
- GET /api/v1/orders/ — لیست سفارشات کاربر لاگین
- GET /api/v1/orders/id/ — جزئیات سفارش (با guest_phone برای مهمان)
- PATCH /api/v1/orders/id/status/ — تغییر وضعیت (فقط ادمین)
- GET /api/v1/admin/orders/ — لیست همه سفارش‌ها با فیلتر (فقط admin/family_admin)
- GET /api/v1/admin/payments/ — لیست پرداخت‌های در انتظار تأیید (فقط admin/family_admin)

### Payments (کاربر + ادمین)
- POST /api/v1/orders/order_id/payments/ — ثبت پرداخت (D-067) — شماره کارت مقصد از settings خوانده می‌شود، نه از body درخواست
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

## ۷.۱ Supplier Endpoints (برای M4 - پنل تأمین‌کننده)

**مجوز:** فقط نقش supplier (از طریق RBAC - ADR-002)

**Endpoints:**
- GET /api/v1/supplier/orders/ — لیست سفارش‌های مرتبط (فقط OrderItemهایی که supplier_id = کاربر فعلی)
- GET /api/v1/supplier/orders/id/ — جزئیات سفارش مرتبط
- PATCH /api/v1/supplier/orders/id/tracking/ — ثبت کد رهگیری ارسال
- GET /api/v1/supplier/monthly-report/ — گزارش ماهانه (تعداد، مبلغ، طلب)

**نکته:** تأمین‌کننده فقط اطلاعات مرتبط با محصولات خودش را می‌بیند. قیمت فروش به مشتری و حاشیه سود ریهان نمایش داده نمی‌شود.

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

### Idempotency (برای عملیات حساس)
**مشکل:** اگر کاربر دکمه ثبت سفارش را دو بار بزند، دو سفارش ایجاد نشود

**راه‌حل:** Idempotency-Key در Header
- کلاینت یک UUID تولید می‌کند و در Header می‌فرستد: `Idempotency-Key: uuid-here`
- سرور: اگر همان Key قبلاً پردازش شده، همان پاسخ قبلی را برمی‌گرداند (بدون اجرای مجدد منطق)

**حداقل endpoints مشمول در MVP (قفل شده):**
1. `POST /api/v1/orders/` — ایجاد سفارش
2. `POST /api/v1/orders/{id}/payments/` — ثبت پرداخت (D-067)

**نکته:** سایر endpoints (مثل افزودن به سبد، ثبت نظر) در MVP نیاز به Idempotency ندارند. اگر در آینده نیاز شد، با ADR جدید اضافه می‌شود.

**پیاده‌سازی:** ذخیره Idempotency-Key + Response در جدول موقت (۲۴ ساعت TTL)

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


---

## تأیید نهایی مشاور

**تاریخ تصویب:** ۱۴۰۵/۰۵/۱۶  
**تأییدکننده:** مشاور پروژه

این سند اکنون **مصوب** است و مبنای اجرایی برای طراحی تمام API های ریهان می‌باشد.
