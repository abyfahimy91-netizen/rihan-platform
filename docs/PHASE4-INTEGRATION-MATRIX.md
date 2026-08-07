# ماتریس یکپارچگی نهایی فاز ۴ (Phase 4 Master Integration Matrix)

| شناسه | PHASE4-INTEGRATION |
| --- | --- |
| عنوان | ماتریس یکپارچگی نهایی فاز ۴ (۹ سند معماری) |
| وضعیت | **Active ✅** |
| تاریخ | ۲۰۲۶-۰۸-۰۷ |
| هدف | تأیید هماهنگی ۱۰۰٪ تمام ADRهای فاز ۴ پیش از ورود به فاز ۵ |

> این سند، جمع‌بندی یکپارچگی ۹ سند معماری فاز ۴ است و به‌عنوان پیش‌نیاز صدور مجوز فاز ۵ (کدنویسی) تهیه شده است.

---

## ۱. لیست کامل اسناد فاز ۴

| # | سند | عنوان | وضعیت | Commit |
|---|------|--------|--------|--------|
| 1 | ADR-001 | Backend Framework (Django 5.2 LTS) | **Approved ✅** | - |
| 2 | ADR-002 | Database / مدل داده (۱۷ موجودیت) | **Approved ✅** | - |
| 3 | ADR-003 | API Strategy + API-First | **Approved ✅** | - |
| 4 | ADR-003-Appendix | متمم: Offline-First / Caching / PWA | **Approved ✅** | 1505105 |
| 5 | ADR-004 | Feature Flags / Plugin Architecture | **Approved ✅** | - |
| 6 | ADR-005 | Payment Abstraction (Strategy Pattern) | **Approved ✅** | 7b52740 |
| 7 | ADR-006 | Authentication (Passwordless + Hybrid Auth) | **Approved ✅ v2** | 7a376e7 |
| 8 | ADR-007 | Frontend Stack (HTML+HTMX+Alpine+Tailwind) | **Approved ✅ v2** | fb5a4d3 |
| 9 | ADR-008 | Deployment / Docker / CI-CD / Backup | **Approved ✅** | f7c9e8e |

**جمع:** ۸ ADR اصلی + ۱ متمم = **۹ سند معماری، همه Approved**

---

## ۲. ماتریس ارتباطات بین اسناد (Cross-Reference Matrix)

این جدول نشان می‌دهد هر جفت سند چگونه با هم هماهنگ هستند:

| از ↓ / به → | ADR-001 | ADR-002 | ADR-003 | ADR-003+ | ADR-004 | ADR-005 | ADR-006 | ADR-007 | ADR-008 |
|---|---|---|---|---|---|---|---|---|---|
| **ADR-001** (Django) | — | ORM | Views | Views | Apps | Services | Auth | Templates | Gunicorn |
| **ADR-002** (DB) | ORM | — | Models | - | - | Payment | User/Token | - | Postgres |
| **ADR-003** (API) | Views | Models | — | ETag/Cache | - | - | JWT/Session | Fetch/HTMX | Nginx |
| **ADR-003+** (Offline) | - | - | ETag | — | Flags | - | - | LocalStorage | Static |
| **ADR-004** (Flags) | Apps | - | Middleware | Flags | — | - | - | UI Toggles | Env Vars |
| **ADR-005** (Payment) | Services | Payment | - | - | - | — | Auth Required | Forms | - |
| **ADR-006** (Auth) | Auth | User/Token | JWT | - | - | Auth Required | — | Session/CSRF | Env Vars |
| **ADR-007** (Frontend) | Templates | - | Fetch/HTMX | LocalStorage | Toggles | Forms | CSRF Token | — | Static/Media |
| **ADR-008** (Deploy) | Gunicorn | Postgres | Nginx | Static | Env | - | Env | Static/Media | — |

---

## ۳. یکپارچگی بر اساس لایه‌های معماری

### لایه ۱: زیرساخت (ADR-008)
**ارتباطات:**
- ✅ با ADR-001: Gunicorn برای اجرای Django
- ✅ با ADR-002: کانتینر PostgreSQL 16 با Volume persistence
- ✅ با ADR-003: Nginx به‌عنوان Reverse Proxy
- ✅ با ADR-007: Serve کردن /static/ و /media/ از Named Volumes
- ✅ با ADR-006: Environment Variables امن در .env
- ✅ Cold Start خودکار با deploy/entrypoint.sh (مigrate + collectstatic + seed)

### لایه ۲: Backend (ADR-001 + ADR-002 + ADR-006)
**ارتباطات:**
- ✅ ADR-001 (Django) از Django ORM برای ارتباط با ADR-002 (PostgreSQL) استفاده می‌کند
- ✅ ADR-006 (Auth) از مدل User تعریف‌شده در ADR-002 استفاده می‌کند
- ✅ ADR-006 (Auth) از Django Auth System داخلی ADR-001 استفاده می‌کند
- ✅ DeviceToken و AuditLog (ADR-002) با ADR-006 کاملاً هم‌راستا هستند

### لایه ۳: API (ADR-003 + متمم ADR-003)
**ارتباطات:**
- ✅ ADR-003 سه کانال تعریف می‌کند: Web Session، API JWT، Device Token
- ✅ متمم ADR-003 استراتژی Caching و ETag را به ADR-003 اضافه می‌کند
- ✅ Sparse Fieldsets و Pagination (متمم) با API-First (ADR-003) سازگارند
- ✅ هر دو ADR-006 و ADR-003 از Idempotency Key استفاده می‌کنند

### لایه ۴: منطق کسب‌وکار (ADR-004 + ADR-005)
**ارتباطات:**
- ✅ ADR-004 (Feature Flags) قابلیت‌های ADR-005 (Payment) را کنترل می‌کند
- ✅ ADR-005 (Payment) از Strategy Pattern برای Gateway استفاده می‌کند
- ✅ موجودی سه‌مرحله‌ای (ADR-005) با مدل InventoryTransaction (ADR-002) هم‌راستاست
- ✅ هر دو ADR-004 و ADR-005 از Django Apps استفاده می‌کنند (ADR-001)

### لایه ۵: Frontend (ADR-007)
**ارتباطات:**
- ✅ ADR-007 با Django Templates (ADR-001) یکپارچه است
- ✅ HTMX با ADR-003 (API) از طریق Partial Rendering کار می‌کند
- ✅ CSRF Token از ADR-006 به‌صورت خودکار در HTMX تزریق می‌شود
- ✅ LocalStorage (متمم ADR-003) برای سبد خرید در ADR-007 استفاده می‌شود
- ✅ Tailwind با RTL و Vazirmatn Font کاملاً بومی‌شده

---

## ۴. بررسی تناقضات احتمالی (Conflict Resolution)

### بررسی ۱: Session vs JWT (ADR-003 + ADR-006)
**سؤال:** آیا تضادی بین Session cookie و JWT وجود دارد؟
**پاسخ:** ❌ تضاد وجود ندارد
- Web: Session cookie (HttpOnly, Secure)
- API (آینده): JWT در Header
- Device: DeviceToken جداگانه
- **نتیجه:** سه کانال مجزا، هیچ تداخلی ندارند

### بررسی ۲: Cache Strategy (ADR-004 + متمم ADR-003)
**سؤال:** آیا استراتژی‌های Cache هم‌راستا هستند؟
**پاسخ:** ❌ تضاد وجود ندارد
- ADR-004: Cache in-process برای Feature Flags (سریع)
- متمم ADR-003: Browser Cache برای Static، Server Cache برای API
- **نتیجه:** سه لایه Cache مکمل هم هستند

### بررسی ۳: احراز هویت Guest (ADR-006 + ADR-002 + ADR-005)
**سؤال:** مهمان چگونه سفارش می‌دهد؟
**پاسخ:** ❌ تضاد وجود ندارد
- ADR-002: فیلد guest_phone در Order
- ADR-006: سقف ۵ سفارش مهمان per device
- ADR-005: پرداخت بدون نیاز به ورود (guest_phone کافی است)
- **نتیجه:** Guest Checkout کاملاً تعریف‌شده است

### بررسی ۴: PII Anonymization (ADR-006 v2 + ADR-002)
**سؤال:** آیا قوانین مالیاتی با حق فراموش‌شدن تضاد دارند؟
**پاسخ:** ❌ تضاد وجود ندارد
- PII (نام، تلفن، آدرس) → حذف/گمنام‌سازی در ۷ روز
- سوابق مالی (فاکتور، پرداخت) → نگهداری ۳-۵ سال با anonymous_user_id
- **نتیجه:** تفکیک کامل PII از Financial Ledger

### بررسی ۵: Offline Queue (متمم ADR-003 + ADR-003)
**سؤال:** آیا POSTهای queued با Idempotency Key سازگارند؟
**پاسخ:** ❌ تضاد وجود ندارد
- متمم ADR-003: POSTها در IndexedDB queue می‌شوند
- ADR-003: هر POST دارای Idempotency Key یکتاست
- **نتیجه:** جلوگیری کامل از duplicate شدن

### بررسی ۶: Docker و Secrets (ADR-008 + ADR-006)
**سؤال:** چگونه کلیدهای امن مدیریت می‌شوند؟
**پاسخ:** ❌ تضاد وجود ندارد
- ADR-008: فایل .env (خارج از مخزن)
- ADR-006: KAVENEGAR_API_KEY در .env
- **.env.template** در مخزن (بدون مقادیر واقعی)
- **نتیجه:** امنیت کامل Secrets

### بررسی ۷: Cold Start (ADR-008 + ADR-002 + ADR-006)
**سؤال:** اولین اجرای Docker چگونه کار می‌کند؟
**پاسخ:** ❌ تضاد وجود ندارد
- deploy/entrypoint.sh به‌صورت خودکار اجرا می‌شود
- منتظر PostgreSQL می‌ماند
- migrations را اجرا می‌کند
- collectstatic را اجرا می‌کند
- superuser اولیه را می‌سازد (اگر وجود نداشته باشد)
- Gunicorn را شروع می‌کند
- **نتیجه:** اپراتور غیربرنامه‌نویس هیچ کاری جز `docker-compose up -d --build` انجام نمی‌دهد

### بررسی ۸: HTMX + Alpine.js (ADR-007)
**سؤال:** آیا HTMX و Alpine با هم تداخل دارند؟
**پاسخ:** ❌ تضاد وجود ندارد (با mitigation)
- ADR-007 v2: استفاده از htmx:afterSettle + Alpine.initTree()
- Re-bind خودکار کامپوننت‌های Alpine پس از هر Swap
- **نتیجه:** مشکل حل شده است

### بررسی ۹: Static Files Hosting (ADR-007 + ADR-008)
**سؤال:** فایل‌های استاتیک چگونه serve می‌شوند؟
**پاسخ:** ❌ تضاد وجود ندارد
- ADR-007: تمام کتابخانه‌ها در /static/vendor/ محلی هستند (اصل ۹)
- ADR-008: Nginx از static_volume استفاده می‌کند
- collectstatic در entrypoint.sh اجرا می‌شود
- **نتیجه:** بدون وابستگی به CDN خارجی

### بررسی ۱۰: Rate Limiting (ADR-006 + ADR-008 + ADR-003)
**سؤال:** آیا Rate Limiting در لایه‌های مختلف تضاد دارد؟
**پاسخ:** ❌ تضاد وجود ندارد
- ADR-006: Rate Limit در سطح اپلیکیشن (Django)
- ADR-008: Rate Limit در Nginx (لایه دفاع اول)
- ADR-003: Idempotency Key برای جلوگیری از duplicate
- **نتیجه:** دفاع چندلایه (Defense in Depth)

---

## ۵. پوشش اصول بنیادین توسط اسناد فاز ۴

| اصل | اسناد پوشش‌دهنده |
|------|-------------------|
| **اصل ۹: مستقل از خارج** | ADR-006 (Kavenegar داخلی)، ADR-007 (vendor محلی)، ADR-008 (VPS ایرانی) |
| **اصل ۱۰: کنترل کامل ادمین** | ADR-004 (Admin Panel)، ADR-006 (پارامترهای قابل تنظیم)، ADR-008 (لاگ‌ها و بکاپ‌ها) |
| **اصل ۱۱: کرامت مشتری** | ADR-005 (پرداخت بدون اصطکاک)، ADR-006 (بدون رمز عبور)، متمم ADR-003 (اینترنت ضعیف)، ADR-007 (RTL و UX) |
| **اصل تدریجی بودن** | ADR-004 (Feature Flags)، ADR-005 (چند تلاش پرداخت) |
| **اصل اعتماد محلی** | ADR-006 v2 (PII Anonymization + نگهداری مالیاتی) |

---

## ۶. پوشش محدودیت‌های بنیان‌گذار

| محدودیت | راه‌حل در اسناد فاز ۴ |
|---------|----------------------|
| **غیربرنامه‌نویس** | ADR-001 (Django ساده)، ADR-007 (HTML ساده)، ADR-008 (One-Command Deploy) |
| **پاره‌وقت / شاغل** | ADR-008 (CI/CD خودکار)، ADR-004 (Feature Flags برای انتشار تدریجی) |
| **استفاده از Termius** | ADR-008 (دستورات ساده docker-compose)، deploy/OPERATOR-GUIDE.md |
| **۵ سال تا بازنشستگی** | معماری قابل نگهداری، مستندسازی کامل (۹ سند)، عدم وابستگی به AI خاص |

---

## ۷. پوشش داستان محوری (CENTRAL-STORY.md)

| عنصر داستان | پوشش در اسناد |
|-------------|----------------|
| **زوج بنیان‌گذار** | ADR-004 (پنل خانواده M3) |
| **خدمت به مناطق محروم (هوراند)** | متمم ADR-003 (Offline-Aware برای اینترنت ضعیف) |
| **اعتماد ثابت، محصول متغیر** | ADR-004 (Plugin Architecture)، ADR-005 (Strategy Pattern) |
| **کسب‌وکار آبرومند** | ADR-006 v2 (قوانین مالیاتی)، ADR-008 (Backup و Disaster Recovery) |

---

## ۸. چک‌لیست نهایی پیش از فاز ۵

### اسناد تکمیل‌شده
- [x] ۹ سند معماری (۸ ADR + ۱ متمم)
- [x] همه اسناد Approved هستند
- [x] تمام ۴ مغایرت گزارش ممیزی بسته شده‌اند
- [x] تمام ۱۰ بررسی تناقض (بالا) پاس شده‌اند

### تکالیف پیش‌نیاز
- [x] فایل `.env.template` در ریشه مخزن
- [x] اسکریپت `deploy/entrypoint.sh` برای Cold Start خودکار
- [x] ماتریس یکپارچگی (این سند)
- [x] به‌روزرسانی PROJECT-INDEX.md
- [x] به‌روزرسانی CONTINUITY.md
- [x] به‌روزرسانی ROADMAP.md

### اصول تأیید‌شده
- [x] اصل ۹ (مستقل از خارج): ✅ رعایت شده
- [x] اصل ۱۰ (کنترل کامل ادمین): ✅ رعایت شده
- [x] اصل ۱۱ (کرامت مشتری): ✅ رعایت شده
- [x] اصل P1 (Repository Is Truth): ✅ رعایت شده
- [x] اصل P10 (Incremental Progress): ✅ رعایت شده

---

## ۹. نتیجه‌گیری نهایی

**فاز ۴ (Software Planning) از نظر معماری تکمیل شده است.**

تمام ۹ سند معماری:
1. با هم هماهنگ هستند (ماتریس بالا)
2. اصول بنیادین را پوشش می‌دهند
3. محدودیت‌های بنیان‌گذار را در نظر گرفته‌اند
4. داستان محوری را منعکس می‌کنند
5. هیچ تناقض داخلی ندارند

**پروژه آماده ورود به فاز ۵ (کدنویسی MVP) است**، منوط به تأیید نهایی ناظر.

---

**تاریخ تهیه:** ۱۴۰۵/۰۵/۱۷
**تهیه‌کننده:** تحلیلگر فنی (Developer AI)
**وضعیت:** در انتظار تأیید ناظر برای صدور مجوز فاز ۵
