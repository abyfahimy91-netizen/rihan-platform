# پروژه ریهان — وضعیت جاری (CONTINUITY)

**Last Update:** 2026-08-23 (۱ شهریور ۱۴۰۵)
**Project Version:** 0.14.0-mvp (D-091 Luxury Design)
**Active Phase:** Phase 5 (MVP Development)

## 🚨 وضعیت زیرساخت — 1405/06/01 (گزارش کامل: AUDIT-INFRA-1405-06-01.md)

- ✅ سرویس پس از یک دوره قطعی طولانی **کاملاً بازیابی و پایدار** شد (rihan360.ir)
- ✅ ریشه خرابی: قطع شبکه کانتینر وب + حذف .env + requirements ناقص + مسیر WSGI غلط
- 🔒 سخت‌سازی امنیتی انجام شد: DEBUG=False، SECRET_KEY واقعی، ALLOWED_HOSTS محدود، CSRF origins، whitenoise، سرو مستقیم media در nginx
- 🗃️ مهاجرت‌های معوق core/rihan_auth اعمال شد؛ `manage.py check` بدون خطا
- 💾 پشتیبان دستی دیتابیس: `/root/backups/rihan_db_20260823_0517.sql.gz`
- ⏭️ بعدی: نصب TLS، بکاپ خودکار cron، جایگزینی داده تست با داده واقعی

## Module Status (14 modules per D-079)

| Module | Status |
|--------|--------|
| M1 Catalog | Complete (Category, Supplier, Product, Inventory) |
| M2 Order | Complete (Cart, Order, Payment, Address) |
| M3 Family Panel | Complete + Real Interfaces (D-081) |
| M4 Supplier Panel | Complete (D-085) |
| M5 RBAC | Complete |
| M6 Finance | Complete (D-086) |
| M7 Order Tracking | Complete (D-082) |
| M8 Reviews | Complete (D-083) |
| M9 Leads | Complete (D-084) |
| M10 Authentication | Complete |
| M11 Payment | Complete (Card-to-Card, D-067) |
| M12 About | Complete (D-088) |
| M13 Design | Complete (D-090 + D-091 Luxury) |
| M14 Plugin Architecture | Complete |

**Progress:** 14/14 modules = 100%

## Achievements This Session (2026-08-22)

### D-091: Luxury Design Implementation
- Hero Section with brand story and green gradient
- Luxury product cards with hover effects (translateY, scale)
- Colors per VISUAL-IDENTITY.md (D-042): #0D3B2E, #C9A961, #FAF7F0
- Vazirmatn font local (4 weights: Regular, Medium, Bold, Black)
- Persian numerals enabled (font-feature-settings: "ss01")
- SEO meta tags complete (Open Graph, Twitter Card)
- Cart icon SVG in header (replaced emoji)
- Removed emoji from logo and footer
- Nginx config cleaned (removed rihan.ir)

### D-090: UI سبد خرید (M2)
- cart.html complete
- cart_views.py with modern features
- page_urls.py for routing

### D-089: Excel Export (US-031)
- openpyxl installed
- Finance reports export capability

### D-087: Trust Badges ایرانی (US-058)
- 4 Iranian trust badges
- Minimal and classy design

## Server Configuration

| Item | Value |
|------|-------|
| OS | Ubuntu 22.04 LTS |
| IP | 146.19.212.212 |
| Domain | rihan360.ir |
| Web Server | Nginx (reverse proxy to 127.0.0.1:8000) |
| Backend | Django 5.2 + Python 3.10 |
| Virtual Env | /root/rihan-platform/venv |
| Static Files | /root/rihan-platform/staticfiles |
| PYTHONPATH | /root/rihan-platform |

## Recent Decisions

| Date | Decision |
|------|----------|
| 2026-08-22 | D-091: Luxury Design Implementation |
| 2026-08-21 | D-090: UI سبد خرید |
| 2026-08-21 | D-089: Excel Export (US-031) |
| 2026-08-21 | D-088: Integration Testing |
| 2026-08-21 | D-087: Trust Badges ایرانی (US-058) |
| 2026-08-21 | D-086: Finance Module Implementation (M6) |
| 2026-08-21 | D-085: Supplier Panel with User-Supplier Link |
| 2026-08-20 | D-084: Leads Module Implementation |
| 2026-08-20 | D-083: Reviews Module Implementation |
| 2026-08-20 | D-082: Order Tracking Implementation |
| 2026-08-18 | D-079: Return to Original Vision |

## Next Major Actions

**Priority 1:** Test complete purchase flow (customer → order → payment → delivery)
**Priority 2:** US-059 — Complete sales funnel
**Priority 3:** Luxury design for product_detail.html (M1)
**Priority 4:** Luxury design for cart.html (M2)
**Priority 5:** Performance optimization (cache, image optimization)
**Priority 6:** Security testing (OWASP checklist)
**Priority 7:** Admin documentation

## Known Technical Debt

| Item | Severity | Notes |
|------|----------|-------|
| RuntimeWarning naive datetime | Low | jdatetime integration needed |
| No refund signal | Medium | TODO: connect Order cancellation to finance |
| product_detail.html | Low | Not yet luxury-designed |
| cart.html | Low | Not yet luxury-designed |
| PROJECT-INDEX.md | Medium | Uses src/apps/ instead of src/modules/ |

## Commands

Activate environment:
cd ~/rihan-platform && source venv/bin/activate

Start server:
PYTHONPATH=/root/rihan-platform nohup python src/manage.py runserver 0.0.0.0:8000 > /tmp/django.log 2>&1 &

Check status:
curl -s -o /dev/null -w "HTTP: %{http_code}" http://rihan360.ir/

Collect static:
PYTHONPATH=/root/rihan-platform python src/manage.py collectstatic --noinput

Restart nginx:
nginx -t && systemctl restart nginx

## Git Info

- **Latest commit:** 860ffab
- **Commit message:** feat(D-091): Luxury Design - Hero Section + Product Cards + Vazirmatn Local
- **Branch:** main
- **Remote:** https://github.com/abyfahimy91-netizen/rihan-platform.git

## Purchase Flow Test Results (2026-08-22)

**Test Method:** Django Direct (shell)
**Status:** ✅ ALL PASSED

| Step | Action | Result |
|------|--------|--------|
| 1 | Add 1 item to cart | ✅ Success (10,000 تومان) |
| 2 | Update quantity (1 → 3) | ✅ Success (30,000 تومان) |
| 3 | Add second product | ✅ Success (310,000 تومان) |
| 4 | Remove first item | ✅ Success |
| 5 | Clear entire cart | ✅ Success |

**Conclusion:** Cart logic is 100% functional. Session management, price calculation, and quantity updates all work correctly.

---

## Admin UI Overhaul + Production Hotfixes (2026-08-23, ۱۴۰۵/۰۶/۰۱)

**Scope:** Admin redesign (D-092), unicode slug hotfix (D-093), trust-badges template fix, variants proposal (D-094)

| Item | Status | Commit |
|------|--------|--------|
| Brand admin theme (`rihan_admin.css/js`) + grouped sidebar + contrast dashboard | ✅ Live | `c72fd8b` |
| `SiteSettings` singleton (pages app) + context processor → hero/announcement/footer editable in `/admin/pages/sitesettings/1/change/` | ✅ Live | `c72fd8b` |
| `<slug:>` → `<str:>` in catalog/leads/reviews urls (Persian slugs broke homepage with 500) | ✅ Fixed | `ab1aa11` |
| Multiline `{# #}` comment leaking into HTML (trust_badges partial) — replaced with single-line | ✅ Fixed | `8e5ef15` |
| Product image pipeline verified end-to-end (upload → /app/media/products/... → nginx 200) | ✅ Tested | — |
| Product Variants system | 🟡 Proposed (D-094) — NOT implemented yet | — |

**Gotchas for next developer:**
- Template changes require `docker restart rihan_web`; static changes require `collectstatic`
- Any URL pattern taking a product slug MUST use `<str:...>` (slugs can be Unicode)
- Never write multiline `{# #}` comments in Django templates
- `SiteSettings.load()` is called on every request via context processor — keep it cheap; if the model is renamed/removed, update `modules/pages/context_processors.py` or the whole site 500s

---

## Product Edit & Registration Verification (2026-08-23)

- Edit page for Persian-named product «سماق قرمز هوراند»: HTTP 200 ✅
- Product creation incl. fully-Persian names/slugs: works ✅ (after D-093)
- Variant support: **not available yet** — see D-094


## 1405/06/01 - سیستم تنوع محصول (واریانت) راه‌اندازی شد — D-094 تایید و اجرا شد
- هر محصول می‌تواند چند «بسته/سایز/رنگ» با قیمت و موجودی مستقل داشته باشد (مدل ProductVariant)
- موجودی در سطح واریانت نگهداری می‌شود؛ برای محصولات واریانت‌دار، Inventory والد صرفاً نمایشی است — خرید فقط از واریانت‌ها
- فایل کلیدی جدید: modules/catalog/services/variant_stock_service.py + modules/order/variant_dispatch.py (پوشش dispatch — قبل از تغییر مسیر رزرو این فایل را ببینید!)
- قالب variant_picker.html در صفحه محصول؛ اگر محصول واریانت دارد، فرم خرید از آن سرو می‌شود
- قانون: هنگام افزودن مدل جدید مرتبط با محصول، dispatch را در variant_dispatch هم پوشش دهید

## 1405/06/01 - پاکسازی دیتابیس + دکمه ویرایش محصول
- کل داده‌های تستی حذف شد: ۵ محصول تست، ۶ دسته تست، ۵ تامین‌کننده تست، ۲ سفارش قدیمی «مریم تست»، همه سبدخریدهای مهمان
- وضعیت نهایی: فقط ۱ محصول (سماق قرمز هوراند با دو واریانت)، ۱ دسته (مواد غذایی ارگانیک)، ۱ تامین‌کننده (میر سجاد نبوی)، صفر سفارش
- ProductAdmin حالا ستون «عملیات» با دکمه ویرایش سریع دارد (.rihan-edit-btn در rihan_admin.css)

## 1405/06/01 - احراز هویت دوکاناله + یادآوری دستگاه — D-095
- ورود OTP و رمز عبور هر دو فعال؛ رمز از پروفایل ساخته می‌شود؛ فراموشی رمز = OTP سه مرحله‌ای
- DeviceTokenMiddleware فعال شد؛ کوکی rihan_device_token با هش SHA-256 (نه bcrypt — جستجوی مستقیم)
- SESSION/CSRF کوکی‌ها Secure شدند (سایت فقط HTTPS)
- اعتبار کد OTP از ۲ به ۵ دقیقه افزایش یافت
- نکته: تغییر MIDDLEWARE/urls/تنظیمات = docker restart کافی است (env تغییر نکرده)
- تست E2E کامل سبز + تست زنده مرورگر؛ داده‌های تست حذف شد

## 1405/06/02 — D-098: سفر پرداخت جدید + کارت‌های بانکی ادمین‌محور
- استپر ۴ مرحله‌ای مشترک (partials/checkout_steps.html) در سبد/تسویه/پرداخت/موفقیت
- صفحه پرداخت یکپارچه: کارت‌های مقصد با کپی + فرم رسید فقط ۴ رقمی (زمان خودکار=اکنون، رسید اختیاری)
- مدل BankAccount + ادمین؛ Gateway از DB می‌خواند (fallback به settings) — مایگریشن‌های order.0008/0009
- باگ رفع‌شده: دکمه «ثبت اطلاعات پرداخت» به lookup می‌رفت؛ فرم رسید یتیم بود (بدون URL)
- کدهای D-XXX از قالب‌های مشتری پاک شد؛ برچسب PENDING_REVIEW بدون واژه «ادمین»
- پیگیری: پروفایل=مسیر اصلی، lookup=پشتیبان مهمان (پذیرش شماره بدون خط تیره)
- E2E: ۳۱ چک سبز؛ سفارش واقعی RH-1405-00001 دست‌نخورده
