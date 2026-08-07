# متمم ADR-003: بهینه‌سازی برای شبکه‌های ضعیف (Offline-First / Caching / PWA)

| شناسه | ADR-003-Appendix |
| --- | --- |
| عنوان | متمم ADR-003: بهینه‌سازی برای شبکه‌های ضعیف (Offline-First / Caching / PWA) |
| وضعیت | **Proposed** — پیش‌نویس، در انتظار تأیید ناظر |
| تاریخ | ۲۰۲۶-۰۸-۰۷ |
| تصمیم‌گیرنده | عبدالحسین فهیمی (بنیان‌گذار) + تحلیلگر فنی |
| مرتبط | ADR-003, ADR-004, USER-PERSONAS.md, CENTRAL-STORY.md, اصل ۱۱ |

> این متمم، مکمل ADR-003 (API Strategy) است و الزامات شبکه‌های ضعیف را پوشش می‌دهد.

## ۱. زمینه و ضرورت (چرا این متمم لازم است؟)

### کشف مغایرت در گزارش ارزیابی فاز ۴
تحقیقات فاز ۱ و پرسوناهای فاز ۳ (USER-PERSONAS.md) نشان می‌دهند که بخش قابل‌توجهی از کاربران و ذی‌نفعان در **مناطق با اینترنت محدود یا پایداری پایین** (مانند هوراند، مناطق روستایی و حاشیه شهرها) حضور دارند.

**مغایرت شناسایی‌شده:** ADR-003 اصلی به الزامات Caching، حجم کم Payloadها و قابلیت Offline-First اشاره نکرده بود. عدم رعایت این موارد در معماری API باعث کندی شدید سامانه در شرایط شبکه ضعیف خواهد شد.

### هم‌راستایی با داستان محوری و اصل ۱۱
- **داستان محوری (CENTRAL-STORY.md):** ریهان یک کسب‌وکار خانوادگی برای خدمت به مردم عادی است، نه فقط کاربران شهری با اینترنت پرسرعت.
- **اصل ۱۱ (کرامت مشتری):** مشتری در هوراند نباید به دلیل کندی شبکه، از خرید منصرف شود.
- **پرسونای «خانم مریم ۵۲ ساله» (هوراند):** کاربر غیرفنی با اینترنت ۳G که حوصله لود طولانی صفحات را ندارد.

## ۲. استراتژی فشرده‌سازی Payload (Payload Compression)

### الزامات فشرده‌سازی در لایه وب‌سرور (Nginx)
- **Gzip:** برای همه پاسخ‌های JSON, HTML, CSS, JS با `Content-Type` مناسب
- **سطح فشرده‌سازی:** `gzip_comp_level 6` (تعادل بین CPU و حجم)
- **حداقل حجم برای فشرده‌سازی:** ۱۰۲۴ بایت (برای پاسخ‌های کوچک سربار نباشد)
- **Brotli (آینده):** در فاز ۶ (بهینه‌سازی عملکرد) ارزیابی می‌شود، نه در MVP

### طراحی پاسخ‌های API (API-First + Minimal Responses)
- **Sparse Fieldsets:** کاربر می‌تواند فقط فیلدهای مورد نیاز را درخواست کند.
  - مثال: `GET /api/v1/products/?fields=id,name,price`
  - جلوگیری از ارسال فیلدهای اضافی (description, images, metadata) در لیست‌ها
- **Pagination اجباری:** تمام endpointهای لیست باید paginated باشند (حداکثر ۵۰ رکورد per صفحه).
  - مثال: `GET /api/v1/products/?page=1&page_size=20`
- **حذف داده‌های تکراری:** در لیست محصولات، تصاویر کامل ارسال نمی‌شوند — فقط `thumbnail_url`.
- **ETag برای همه پاسخ‌های GET:** برای جلوگیری از ارسال مجدد داده‌های بدون تغییر (Cache Validation).

### اندازه هدف پاسخ‌ها
| نوع درخواست | هدف حجم پاسخ | دلیل |
| --- | --- | --- |
| لیست محصولات (۲۰ آیتم) | < ۵۰ KB (پس از Gzip) | بارگذاری سریع در ۳G |
| جزئیات محصول | < ۱۵ KB (پس از Gzip) | فقط اطلاعات ضروری |
| صفحه اصلی | < ۸۰ KB (HTML + Critical CSS) | First Meaningful Paint سریع |
| صفحه لاگین | < ۱۰ KB | در شرایط بحرانی شبکه |

## ۳. استراتژی Caching و CDN

### لایه‌های Caching (از نزدیک‌ترین به کاربر تا دورترین)

**لایه ۱: Cache مرورگر (Browser Cache) — هم‌راستا با ADR-004**
- **Static Assets (CSS/JS/Images):** `Cache-Control: public, max-age=31536000, immutable`
  - با hash در نام فایل (مثلاً `main.a1b2c3d4.js`) — تغییر فقط با تغییر فایل
- **API پاسخ‌های عمومی (محصولات، دسته‌ها):** `Cache-Control: public, max-age=300` (۵ دقیقه)
  - برای داده‌هایی که هر ۵ دقیقه یک‌بار تغییر می‌کنند
- **API پاسخ‌های شخصی (سبد خرید، پروفایل):** `Cache-Control: private, no-cache`
  - هرگز در مرورگر cache نشوند
- **HTML صفحات:** `Cache-Control: no-cache` (همیشه fresh از سرور)

**لایه ۲: Cache سرور (Django Cache Framework) — هم‌راستا با ADR-004**
- **Backend Cache:** `in-process/local` با TTL ۵ دقیقه (ADR-004)
- **Cache Key Strategy:** `prefix:module:entity:id` (مثلاً `rihan:catalog:product:123`)
- **Cache Invalidation:** پس از هر تغییر در موجودی یا قیمت، cache مربوطه باطل می‌شود

**لایه ۳: CDN (آینده - فاز ۶)**
- در MVP از CDN استفاده نمی‌شود (هزینه + پیچیدگی)
- اما معماری آماده است: static files در `/static/` با hash در نام
- افزودن CDN در فاز ۶ فقط نیاز به تغییر DNS و Nginx config دارد

### Cache Validation با ETag
- همه پاسخ‌های GET دارای هدر `ETag` هستند
- مرورگر در درخواست بعدی `If-None-Match` را ارسال می‌کند
- سرور در صورت عدم تغییر، `304 Not Modified` برمی‌گرداند (بدون body)
- صرفه‌جویی عظیم در پهنای باند برای داده‌های تغییرناپذیر

## ۴. ملاحظات PWA و Offline-First

### استراتژی MVP: "Offline-Aware" نه "Offline-First"
**تصمیم آگاهانه:** در MVP یک PWA کامل با Service Worker پیچیده پیاده‌سازی نمی‌کنیم (به دلیل پیچیدگی و سربار). در عوض، یک **Offline-Aware Application** می‌سازیم:

### قابلیت‌های MVP برای شرایط آفلاین

**۱. ذخیره‌سازی محلی داده‌های مهم (LocalStorage/IndexedDB):**
- **لیست محصولات اخیر مشاهده‌شده:** حداکثر ۲۰ محصول اخیر در `LocalStorage` ذخیره می‌شود
- **سبد خرید:** در `LocalStorage` ذخیره می‌شود (تا ۷ روز)
  - اگر اینترنت قطع شد، سبد خرید از دست نمی‌رود
  - وقتی اینترنت برگشت، با سرور sync می‌شود
- **اطلاعات کاربر:** JWT token و اطلاعات اولیه پروفایل
  - کاربر در شرایط آفلاین هم می‌تواند وارد پنل خودش شود

**۲. Queue درخواست‌های POST (Write Operations):**
- اگر کاربر در شرایط آفلاین سفارش ثبت کند:
  - درخواست در `IndexedDB` queue می‌شود
  - UI پیام "سفارش شما ثبت شد و پس از اتصال اینترنت ارسال می‌شود" نمایش می‌دهد
  - وقتی اینترنت برگشت، به‌صورت خودکار ارسال می‌شود
  - با Idempotency Key (ADR-003) از duplicate شدن جلوگیری می‌شود

**۳. نشانگر وضعیت اتصال (Online/Offline Indicator):**
- یک Toast/banner در بالای صفحه که وضعیت اتصال را نشان می‌دهد
- وقتی آنلاین می‌شود: sync خودکار queue با سرور

### مرز دقیق PWA در MVP
| قابلیت | وضعیت در MVP | دلیل |
| --- | --- | --- |
| Web App Manifest (Add to Home Screen) | ✅ بله | ساده، UX بهبود می‌دهد |
| Service Worker (Caching هوشمند) | ❌ خیر | پیچیدگی بالا، تست سنگین |
| Push Notifications | ❌ خیر | نیاز به زیرساخت جداگانه |
| Background Sync | ✅ بله (basic) | فقط برای queue درخواست‌های POST |
| Offline Full App | ❌ خیر | خارج از محدوده MVP |

## ۵. هم‌راستایی با سایر ADRها و اصول

### با ADR-003 (API Strategy)
- همه endpointها از Sparse Fieldsets و Pagination پشتیبانی می‌کنند
- ETag در همه پاسخ‌های GET
- Idempotency Key برای POSTهای queued

### با ADR-004 (Feature Flags)
- قابلیت‌های PWA/Offline با Feature Flag کنترل می‌شوند
- اگر PWA در MVP مشکل‌ساز شد، می‌توان با یک toggle غیرفعال کرد
- `offline_features_enabled` flag برای کنترل کلی

### با اصل ۱۱ (کرامت مشتری)
- مشتری در هوراند تجربه قابل قبولی خواهد داشت
- پیام‌های خطای محترمانه در شرایط آفلاین
- عدم از دست رفتن سبد خرید در قطعی شبکه

### با محدودیت‌های بنیان‌گذار
- پیاده‌سازی ساده با ابزارهای built-in Django
- بدون نیاز به زیرساخت پیچیده (CDN، Redis Cluster)
- قابل مدیریت از طریق پنل ادمین

## ۶. معیارهای پذیرش

| معیار | هدف | روش اندازه‌گیری |
| --- | --- | --- |
| حجم پاسخ لیست محصولات | < ۵۰ KB (gzip) | DevTools Network |
| Time to First Byte (TTFB) | < ۵۰۰ ms در ۳G | Lighthouse |
| First Meaningful Paint | < ۳ ثانیه در ۳G | Lighthouse |
| سبد خرید در آفلاین | ۱۰۰٪ حفظ می‌شود | E2E test |
| Queue sync پس از اتصال | < ۱۰ ثانیه | Unit test |
| ETag 304 responses | فعال برای همه GET | API test |

## ۷. Out of Scope صریح

### در MVP اجرا نمی‌شود
- **Service Worker کامل با caching استراتژی‌های پیچیده**
- **CDN خارجی (CloudFlare, ArvanCloud)** — در فاز ۶ ارزیابی می‌شود
- **Push Notifications**
- **Background Sync پیشرفته** (فقط basic queue sync)
- **App Shell Model** — پیچیدگی بالا
- **Pre-fetching هوشمند** (ML-based)
- **Brotli Compression** — فقط Gzip در MVP

## ۸. ریسک‌ها و Mitigation

| ریسک | احتمال | تأثیر | Mitigation |
| --- | --- | --- | --- |
| Stale Data در Browser Cache | متوسط | متوسط | TTL کوتاه (۵ دقیقه) + ETag |
| پیچیدگی Queue Sync | بالا | بالا | شروع با سناریوهای محدود (فقط سبد خرید) |
| تداخل با ADR-006 (Auth) | پایین | بالا | JWT token در LocalStorage با HttpOnly fallback |
| LocalStorage پر شود | پایین | پایین | LRU eviction پس از ۵ MB |

## ۹. ارجاعات

### تصمیمات و اسناد
- **ADR-003:** استراتژی API-First (مادر این متمم)
- **ADR-004:** Cache in-process + Feature Flags
- **USER-PERSONAS.md:** پرسونای خانم مریم ۵۲ ساله از هوراند
- **CENTRAL-STORY.md:** داستان محوری و اصل اعتماد محلی
- **FUNDAMENTAL-PRINCIPLES.md:** اصل ۱۱ (کرامت مشتری)

### استانداردها
- **HTTP Caching (RFC 7234):** پایه Cache-Control و ETag
- **PWA Checklist (web.dev):** معیارهای Progressive Web App
- **Google Web Vitals:** TTFB, LCP, FID

