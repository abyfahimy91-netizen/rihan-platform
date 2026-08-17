# CONTINUITY — وضعیت فعلی و اقدام بعدی

**آخرین بهروزرسانی:** 2026-08-16
**نسخه پروژه:** 0.6.3-mvp
**فاز فعال:** فاز ۵ (MVP Development) — بازسازی کامل مطابق D-079

---

## 🎯 وضعیت ماژول‌های ۱۴گانه (D-079)

| ماژول | وضعیت | یادداشت |
|---|---|---|
| M1 کاتالوگ | ⏳ نیاز به بازنویسی | کار موازی قبلی |
| M2 سفارش | ⏳ نیاز به بازنویسی | کار موازی قبلی |
| M3 پنل خانواده | ❌ ساخته نشده | بحرانی‌ترین |
| M4 پنل تأمین‌کننده | ❌ ساخته نشده | |
| **M5 RBAC** | **✅ کامل** | **Chunk 4A-4C** |
| M6 مالی | ❌ ساخته نشده | |
| M7 پیگیری سفارش | ❌ ساخته نشده | |
| M8 نظرات معتمد | ❌ ساخته نشده | |
| M9 فرم سرنخ | ❌ ساخته نشده | |
| **M10 احراز هویت** | **✅ کامل** | **Chunk 3A-3D** |
| M11 پرداخت | ❌ ساخته نشده | |
| M12 درباره برند | ❌ ساخته نشده | |
| M13 هویت بصری | ❌ ساخته نشده | |
| **M14 معماری پلاگین** | **✅ کامل** | **Chunk 1 + 2A-2D** |

---

## 🏆 دستاوردهای تکمیل‌شده

### M14 (معماری پلاگین‌محور) — ۱۰۰٪ کامل
- ✅ Chunk 1: PluginRegistry + FeatureFlag
- ✅ Chunk 2A: HookSystem + EventBus
- ✅ Chunk 2B: BlockRegistry + ۱۲ بلوک
- ✅ Chunk 2C: Admin + Migrations
- ✅ Chunk 2D: ثبت ۱۴ پرچم ماژول

### M10 (احراز هویت) — ۱۰۰٪ کامل
- ✅ Chunk 3A: ساختار پایه (Models + SMS Providers)
- ✅ Chunk 3B: OtpService + Rate Limiting + Views
- ✅ Chunk 3C: DeviceToken + Session + Guest Checkout
- ✅ Chunk 3D: Admin + Migrations + Integration

### M5 (RBAC) — ۱۰۰٪ کامل
- ✅ Chunk 4A: Models (Role, UserRole) + RoleService
- ✅ Chunk 4B: Decorators + Middleware + Admin
- ✅ Chunk 4C: Views + URLs + Hooks + Integration

---

## 📋 ویژگی‌های M5 (RBAC)

### Role Model (ADR-002 بخش ۲.۱)
- ✅ UUID PK
- ✅ name, code (UNIQUE)
- ✅ permissions (JSONField)
- ✅ is_system (نقش‌های سیستمی غیرقابل حذف)

### UserRole Model (ADR-002 بخش ۲.۳)
- ✅ Many-to-Many با User
- ✅ granted_by (اعطاکننده)
- ✅ is_primary (نقش اصلی)
- ✅ UNIQUE(user, role) constraint

### ۶ نقش سیستمی (D-017)
- ✅ customer (مشتری)
- ✅ admin (مدیر)
- ✅ family_admin (مدیر خانواده)
- ✅ family_member (عضو خانواده)
- ✅ observer (ناظر)
- ✅ supplier (تأمین‌کننده)

### Decorators
- ✅ @require_permission
- ✅ @require_role
- ✅ @require_family, @require_admin, @require_supplier, @require_customer

### API Endpoints (ADR-003)
- ✅ GET /api/v1/rbac/roles/
- ✅ GET /api/v1/rbac/roles/<code>/
- ✅ GET /api/v1/rbac/my-role/
- ✅ POST /api/v1/rbac/assign/
- ✅ POST /api/v1/rbac/revoke/

---

## 🚀 اقدام بعدی کلان

**اولویت ۱:** بازنویسی M1 (کاتالوگ) با بلوک‌محور
**اولویت ۲:** بازنویسی M2 (سفارش) با D-080
**اولویت ۳:** ساخت M3 (پنل خانواده) — بحرانی‌ترین
**اولویت ۴:** ساخت M4 (پنل تأمین‌کننده)

---

## 📝 تصمیمات مهم این جلسه

| تاریخ | تصمیم | وضعیت |
|---|---|---|
| 2026-08-16 | گزینه A: ادغام هوشمندانه + بازنویسی Auth | ✅ تأیید بنیان‌گذار |
| 2026-08-16 | حذف JWT و بازگشت به OTP (ADR-006) | ✅ اجرا شد |
| 2026-08-16 | M14 کامل شد | ✅ تأیید شد |
| 2026-08-16 | M10 کامل شد | ✅ تأیید شد |
| 2026-08-16 | M5 کامل شد | ✅ تأیید شد |

---

## 📊 آمار کلی

| معیار | مقدار |
|---|---|
| ماژول‌های کامل | ۳ از ۱۴ (M5, M10, M14) |
| Chunks تکمیل‌شده | ۱۲ |
| تست‌های پاس‌شده | ۷۰+ |
| انطباق با ADR | ۱۰۰٪ |
| Commits | ۱۲ |


### 2026-08-17 — Phase 5: رفع انحرافات بحرانی و تکمیل Inventory System

**اقدامات انجام شده:**
1. ✅ بازنویسی کامل `src/modules/catalog/models.py` مطابق ADR-002 و INVENTORY-FLOW.md
   - افزودن مدل `Inventory` با سیستم رزرو و `available_quantity` محاسبه‌ای
   - افزودن مدل `InventoryTransaction` برای تاریخچه کامل تغییرات موجودی
   - افزودن ۱۲ نوع `ContentBlock` مطابق D-079
   - ایجاد خودکار `Inventory` پس از ساخت `Product` با `post_save` signal
   - متدهای `reserve()`, `release_reservation()`, `confirm_sale()`, `return_stock()`, `add_stock()`
   - بررسی `can_reserve()` برای جلوگیری از oversell
   - محاسبه `is_low_stock` بر اساس ۲۰٪ یا ۲ واحد

2. ✅ رفع کامل ۱۴ `RuntimeWarning` درباره database initialization
   - انتقال `FeatureFlagService.register_default_flags()` از `ready()` به `post_migrate` signal
   - انتقال `RoleService.create_system_roles()` از `ready()` به `post_migrate` signal
   - ایجاد `src/core/signals.py` و `src/modules/rbac/signals.py`
   - بازنویسی `src/core/apps.py` و `src/modules/rbac/apps.py`

3. ✅ اصلاح `src/config/settings.py`
   - حذف تکرار `src.modules.catalog`
   - فعال‌سازی `src.modules.catalog` و `src.modules.order`

4. ✅ Migration 0002 ایجاد و اعمال شد
   - ایجاد جداول `catalog_inventory` و `catalog_inventorytransaction`
   - اصلاح فیلدهای مدل‌های موجود

**نتیجه:**
- RuntimeWarning: ۱۴ → ۰
- System Check: بدون مشکل
- Inventory System: ۱۰۰٪ مطابق ADR-002 و INVENTORY-FLOW.md

**Commit:** `2f90f69` - fix(M1): بازنویسی کامل مدل Product با Inventory + رفع همه RuntimeWarnings

**مرحله بعدی:**
- ایجاد `InventoryService` برای عملیات موجودی (Service Layer)
- اتصال به ماژول Order برای رزرو خودکار هنگام ثبت سفارش
- اتصال به پنل ادمین برای ورود دستی موجودی


### 2026-08-17 — Phase 5: رفع انحرافات بحرانی و تکمیل Inventory System

**اقدامات انجام شده:**
1. ✅ بازنویسی کامل `src/modules/catalog/models.py` مطابق ADR-002 و INVENTORY-FLOW.md
   - افزودن مدل `Inventory` با سیستم رزرو و `available_quantity` محاسبه‌ای
   - افزودن مدل `InventoryTransaction` برای تاریخچه کامل تغییرات موجودی
   - افزودن ۱۲ نوع `ContentBlock` مطابق D-079
   - ایجاد خودکار `Inventory` پس از ساخت `Product` با `post_save` signal
   - متدهای `reserve()`, `release_reservation()`, `confirm_sale()`, `return_stock()`, `add_stock()`
   - بررسی `can_reserve()` برای جلوگیری از oversell
   - محاسبه `is_low_stock` بر اساس ۲۰٪ یا ۲ واحد

2. ✅ رفع کامل ۱۴ `RuntimeWarning` درباره database initialization
   - انتقال `FeatureFlagService.register_default_flags()` از `ready()` به `post_migrate` signal
   - انتقال `RoleService.create_system_roles()` از `ready()` به `post_migrate` signal
   - ایجاد `src/core/signals.py` و `src/modules/rbac/signals.py`
   - بازنویسی `src/core/apps.py` و `src/modules/rbac/apps.py`

3. ✅ اصلاح `src/config/settings.py`
   - حذف تکرار `src.modules.catalog`
   - فعال‌سازی `src.modules.catalog` و `src.modules.order`

4. ✅ Migration 0002 ایجاد و اعمال شد
   - ایجاد جداول `catalog_inventory` و `catalog_inventorytransaction`
   - اصلاح فیلدهای مدل‌های موجود

**نتیجه:**
- RuntimeWarning: ۱۴ → ۰
- System Check: بدون مشکل
- Inventory System: ۱۰۰٪ مطابق ADR-002 و INVENTORY-FLOW.md

**Commit:** `2f90f69` - fix(M1): بازنویسی کامل مدل Product با Inventory + رفع همه RuntimeWarnings

**مرحله بعدی:**
- ایجاد `InventoryService` برای عملیات موجودی (Service Layer)
- اتصال به ماژول Order برای رزرو خودکار هنگام ثبت سفارش
- اتصال به پنل ادمین برای ورود دستی موجودی


### 2026-08-17 — Phase 5: تکمیل InventoryService Layer

**اقدامات انجام شده:**
1. ✅ ایجاد `src/modules/catalog/services/inventory_service.py`
   - InventoryService به عنوان API مرکزی برای عملیات موجودی
   - ۹ متد اصلی با `@transaction.atomic`:
     * `add_stock()` - افزودن دستی موجودی
     * `reserve_for_order()` - رزرو هنگام ثبت سفارش (۲۴ ساعت)
     * `confirm_sale()` - تأیید فروش پس از پرداخت
     * `release_reservation()` - آزادسازی رزرو در لغو سفارش
     * `return_stock()` - بازگشت موجودی پس از مرجوعی
     * `adjust_stock()` - اصلاح موجودی در شمارش فیزیکی
     * `check_availability()` - بررسی موجودی قابل فروش
     * `get_low_stock_products()` - لیست محصولات کم‌موجود
     * `get_product_history()` - تاریخچه تراکنش‌ها
   - Hook integration برای اطلاع‌رسانی به سایر ماژول‌ها
   - Low stock alert خودکار

2. ✅ ایجاد `src/modules/catalog/services/exceptions.py`
   - `InventoryError` (پایه)
   - `InsufficientStockError` (موجودی ناکافی)
   - `InventoryValidationError` (خطای اعتبارسنجی)
   - `ProductNotFoundError` (محصول بدون inventory)

3. ✅ ایجاد `src/modules/catalog/tests/test_inventory_service.py`
   - ۱۳ تست جامع (همه پاس شدند)
   - پوشش کامل سناریوهای D-045:
     * افزودن موجودی
     * رزرو و کمبود موجودی
     * تأیید فروش
     * لغو سفارش و آزادسازی
     * مرجوعی
     * اصلاح موجودی
     * بررسی موجودی و هشدار

4. ✅ اصلاح `InventoryTransaction.reference_id`
   - تغییر از `UUIDField` به `CharField(max_length=100)`
   - دلیل: شماره سفارش با فرمت `RH-1405-XXXXX` است (D-080)
   - Migration 0003 ایجاد و اعمال شد

**انطباق با مستندات:**
- ✅ ADR-002 (Database architecture)
- ✅ D-045 (Inventory flow)
- ✅ INVENTORY-FLOW.md (Business rules)
- ✅ D-080 (Order number format)
- ✅ اصل ۱۰ (کنترل کامل ادمین)
- ✅ اصل ۱۱ (کرامت مشتری - بدون oversell)

**نتیجه:**
- ۱۳ تست پاس شدند
- System Check: بدون مشکل
- Inventory Service: ۱۰۰٪ آماده برای اتصال به Order Module

**Commit:** `059c6c6` - feat(M1): افزودن InventoryService کامل با ۱۳ تست

**مرحله بعدی:**
- اتصال InventoryService به Order Module
- CheckoutService برای مدیریت فرآیند سفارش
- Hook integration برای رویدادهای ORDER_CREATED, ORDER_CONFIRMED, ORDER_CANCELLED
