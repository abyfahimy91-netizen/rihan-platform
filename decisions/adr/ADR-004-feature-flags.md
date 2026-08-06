# ADR-004: معماری افزونه‌محور و Feature Flags

| شناسه | ADR-004 |
| --- | --- |
| عنوان | معماری افزونه‌محور و Feature Flags |
| وضعیت | **Proposed** — پیش‌نویس اولیه، در انتظار تأیید مشاور |
| تاریخ | ۲۰۲۶-۰۸-۰۶ |
| تصمیم‌گیرنده | عبدالحسین فهیمی (بنیان‌گذار) + تحلیلگر فنی |
| مرتبط | ADR-001, ADR-002, ADR-003, D-004, D-023, D-028 |

> این سند پیش‌نویس است. تا تصویب مشاور، کد plugin یا feature flag تولید نشود.

## ۱. هدف و مرز

**هدف:** طراحی معماری افزونه‌محور برای ریهان که:
- با اصل انعطاف کامل (FUNDAMENTAL-PRINCIPLES - اصل ۳) هم‌راستا باشد
- با معماری Plugin Architecture (ARCHITECTURE-PRINCIPLES - الگوی ۵) سازگار باشد
- اجازه فعال/غیرفعال کردن هر ماژول از پنل ادمین (بدون deploy) را بدهد
- آماده برای ماژول‌های آینده (Not Yet در MVP-SCOPE)

**مرز:**
- مدل Plugin بر پایه Django Apps
- سیستم Feature Flags از روز اول
- مرز فعال/غیرفعال ماژول‌ها
- قواعد isolation تا حد لازم برای MVP

**Out of Scope صریح:**
- Event bus کامل (Celery/Redis Pub/Sub)
- Microservice architecture
- Hot-plugging پیچیده (بارگذاری plugin بدون restart)
- Plugin marketplace (فروشگاه افزونه)
- Dependency resolution خودکار بین pluginها

## ۲. اصول کلیدی

### اصل ۱: هر ماژول = یک Django App مستقل
- هر ماژول MVP یک Django App جداگانه است
- Appها از طریق INSTALLED_APPS ثبت می‌شوند
- هر App دارای models.py, views.py, urls.py, services.py مخصوص خود است
- هیچ App نباید مستقیماً به App دیگر وابسته باشد (فقط از طریق Service Layer)

### اصل ۲: Feature Flag به‌عنوان سوئیچ اصلی
- هر ماژول یک Feature Flag دارد (boolean)
- فعال/غیرفعال از پنل ادمین (M3)
- تغییر فوری (بدون نیاز به restart)
- لاگ کامل تغییرات در AuditLog

### اصل ۳: Isolation تا حد لازم
- Appها از طریق Django Apps جدا می‌شوند
- Service Layer برای ارتباط بین ماژول‌ها (نه import مستقیم)
- دیتابیس: جداول هر App با prefix مشخص (مثلاً orders_order, payments_payment)
- URL namespace: هر App مسیرهای خود را در namespace جدا ثبت می‌کند

### اصل ۴: آماده برای آینده (Not Yet modules)
- معماری باید اجازه دهد ماژول‌های Not Yet (مثل درگاه پرداخت، بلاگ، اپ موبایل) در آینده اضافه شوند
- بدون نیاز به بازنویسی کد هسته
- فقط ساخت App جدید + ثبت در INSTALLED_APPS + افزودن Feature Flag

## ۳. مدل داده برای Feature Flags

### جدول FeatureFlag (مرکزی)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| module_key | VARCHAR(50) UNIQUE | کلید ماژول |
| display_name | VARCHAR(100) | نام نمایشی |
| description | TEXT | توضیح ماژول |
| is_enabled | BOOLEAN | فعال/غیرفعال |
| is_system | BOOLEAN | ماژول سیستمی |
| enabled_at | TIMESTAMP NULL | تاریخ فعال‌سازی |
| disabled_at | TIMESTAMP NULL | تاریخ غیرفعال‌سازی |
| updated_by | UUID FK->User NULL | کاربر تغییردهنده |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

**قیود:**
- UNIQUE(module_key)
- ماژول‌های سیستمی همیشه فعال (is_system = true → is_enabled = true)

### ماژول‌های سیستمی (غیرقابل غیرفعال‌سازی)
- catalog (M1), order_form (M2), admin_panel (M3)
- rbac (M5), ui_design (M13), plugin_arch (M14)

### ماژول‌های قابل غیرفعال‌سازی
- supplier_panel (M4), finance (M6), tracking (M7)
- reviews (M8), leads (M9), auth (M10)
- payment (M11), brand_page (M12)

## ۴. ساختار Django App برای هر ماژول

### ساختار استاندارد هر App
هر ماژول MVP یک Django App جداگانه در پوشه apps/ است:
- apps/catalog/ — M1 کاتالوگ
- apps/order_form/ — M2 فرم سفارش
- apps/admin_panel/ — M3 پنل خانواده
- apps/supplier_panel/ — M4 پنل تأمین‌کننده
- apps/rbac/ — M5 نقش‌ها
- apps/finance/ — M6 مالی
- apps/tracking/ — M7 پیگیری
- apps/reviews/ — M8 نظرات
- apps/leads/ — M9 سرنخ
- apps/auth/ — M10 احراز هویت
- apps/payment/ — M11 پرداخت
- apps/brand_page/ — M12 درباره برند
- apps/ui_design/ — M13 طراحی
- apps/plugin_arch/ — M14 معماری افزونه‌محور

### هر App شامل:
- apps.py — AppConfig
- models.py — مدل‌ها
- views.py — API + Template views
- urls.py — URL patterns با namespace
- services.py — Service Layer
- serializers.py — DRF serializers
- admin.py — Admin customization
- migrations/ — مایگریشن‌ها
- templates/app_name/ — قالب‌ها
- static/app_name/ — فایل‌های استاتیک
- tests/ — تست‌ها

### قوانین Appها
1. عدم وابستگی مستقیم بین Appها
2. ارتباط فقط از طریق Service Layer
3. URL namespace جدا برای هر App
4. Template namespace جدا
5. Static namespace جدا

## ۵. مکانیزم فعال/غیرفعال کردن ماژول

### لایه‌های بررسی Feature Flag

**لایه ۱: Middleware (سطح درخواست)**
- بررسی module_key از URL path
- اگر غیرفعال: HTTP 404 یا redirect به صفحه «موقتاً در دسترس نیست»
- Cache در Redis (TTL: ۵ دقیقه)

**لایه ۲: View Decorator (سطح endpoint)**
- decorator require_feature(module_key)
- اگر غیرفعال: HTTP 404 یا HTTP 503

**لایه ۳: Template Tag (سطح UI)**
- if_feature module_key ... endif_feature
- مخفی کردن عناصر UI ماژول غیرفعال

**لایه ۴: Navigation (سطح منو)**
- منوها فقط ماژول‌های فعال را نمایش می‌دهند
- dynamic navigation از دیتابیس

### فرآیند فعال/غیرفعال کردن (ادمین)
1. ادمین به /admin/plugin-arch/features/ می‌رود
2. لیست ماژول‌ها با وضعیت فعلی
3. کلیک روی toggle
4. ماژول‌های حساس (order_form, payment): تأیید دو مرحله‌ای
5. ثبت در AuditLog (چه کسی، چه زمانی، از چه به چه)

### رفتار ماژول غیرفعال
**مشتری:** HTTP 404 با پیام دوستانه، لینک‌ها مخفی
**ادمین:** HTTP 403 با پیام «ماژول غیرفعال است»، هشدار در Dashboard

## ۶. Isolation Rules (قواعد جداسازی)

### سطح دیتابیس
- جداول جدا با prefix نام App (مثلاً orders_order)
- Foreign Keys مجاز اما از طریق Service Layer
- Migrations جدا برای هر App

### سطح کد
- Service Layer برای منطق مشترک
- App Services برای منطق خاص هر App
- Import مستقیم بین Appها ممنوع

### سطح URL
- Namespace جدا برای هر App
- Reverse URL با namespace در templateها

### سطح Static/Media
- Static: static/app_name/
- Media: media/app_name/
- Template: templates/app_name/

## ۷. رابطه با ۱۴ ماژول MVP

### ماژول‌های Must Have (همه با Feature Flag)
| ماژول | کلید | سیستمی | توضیح |
| --- | --- | --- | --- |
| M1 کاتالوگ | catalog | بله | بدون کاتالوگ سایت بی‌معنی است |
| M2 فرم سفارش | order_form | بله | بدون سفارش فروشگاه نیست |
| M3 پنل خانواده | admin_panel | بله | مدیریت لازم است |
| M4 پنل تأمین‌کننده | supplier_panel | خیر | قابل غیرفعال‌سازی |
| M5 نقش‌ها | rbac | بله | امنیت لازم است |
| M6 مالی | finance | خیر | قابل غیرفعال‌سازی |
| M7 پیگیری | tracking | خیر | قابل غیرفعال‌سازی |
| M8 نظرات | reviews | خیر | قابل غیرفعال‌سازی |
| M9 سرنخ | leads | خیر | قابل غیرفعال‌سازی |
| M10 احراز هویت | auth | بله | ورود لازم است |
| M11 پرداخت | payment | بله | پرداخت لازم است |
| M12 درباره برند | brand_page | خیر | قابل غیرفعال‌سازی |
| M13 طراحی | ui_design | بله | UI لازم است |
| M14 معماری افزونه | plugin_arch | بله | خود معماری |

### ماژول‌های Not Yet (آماده برای آینده)
- درگاه پرداخت آنلاین (payment_gateway)
- اپلیکیشن موبایل (mobile_app)
- بلاگ و محتوا (blog)
- سیستم وفاداری (loyalty)
- چندزبانه (i18n)

**روش افزودن ماژول جدید:**
1. ساخت App جدید در apps/
2. ثبت در INSTALLED_APPS
3. افزودن رکورد در جدول FeatureFlag
4. افزودن URL به urls.py اصلی
5. بدون نیاز به تغییر کد هسته

## ۸. Out of Scope صریح

- Event bus کامل (Celery/Redis Pub/Sub)
- Microservice architecture
- Hot-plugging پیچیده (بارگذاری plugin بدون restart)
- Plugin marketplace (فروشگاه افزونه)
- Dependency resolution خودکار بین pluginها
- Multi-tenancy
- Plugin versioning پیچیده

## ۹. ارجاعات

- ADR-001: Backend Framework (Django 5.2 LTS)
- ADR-002: معماری دیتابیس (۱۷ موجودیت)
- ADR-003: استراتژی API-First
- D-004: معماری افزونه‌محور (Plugin Architecture)
- D-023: Feature Flags — فعال‌سازی با سوئیچ
- D-028: انعطاف کامل — ماژول‌های ناموجود هم قابل اضافه
- FUNDAMENTAL-PRINCIPLES.md: اصل ۳ (انعطاف کامل)
- ARCHITECTURE-PRINCIPLES.md: الگوی ۵ (Plugin Architecture)
- MVP-SCOPE.md: ۱۴ ماژول Must Have + Not Yet
