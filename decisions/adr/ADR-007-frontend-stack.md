# ADR-007: استک و معماری فرانت‌اند (Frontend Stack)

| شناسه | ADR-007 |
| --- | --- |
| عنوان | استک و معماری فرانت‌اند (Frontend Stack) |
| وضعیت | **Approved ✅ v2** — مصوب با ۴ متمم فنی ناظر (۱۴۰۵/۰۵/۱۷) |
| تاریخ | ۲۰۲۶-۰۸-۰۷ |
| تصمیم‌گیرنده | عبدالحسین فهیمی (بنیان‌گذار) + تحلیلگر فنی |
| مرتبط | ADR-001, ADR-003, ADR-003-Appendix, ADR-006, ADR-004, CENTRAL-STORY.md, اصل ۹, ۱۰, ۱۱ |

> این سند پیش‌نویس است. تا تصویب ناظر، کد فرانت‌اند تولید نشود.

## ۱. زمینه و ارجاعات

### چرا این ADR مهم است؟
- **داستان محوری (CENTRAL-STORY.md):** ریهان باید برای کاربران غیرفنی در مناطق روستایی (مانند هوراند) قابل استفاده باشد.
- **اصل ۱۱ (کرامت مشتری):** کاربر نباید منتظر لود طولانی صفحات بماند.
- **محدودیت بنیان‌گذار:** غیربرنامه‌نویس است و باید بتواند کد فرانت‌اند را بفهمد و debug کند.
- **سازگاری با Django (ADR-001):** فرانت‌اند باید با Django templates کار کند، نه اینکه یک SPA جداگانه باشد.

### ارجاعات
- **ADR-001:** Django 5.2 LTS (backend framework)
- **ADR-003:** API Strategy + API-First
- **متمم ADR-003:** Offline-First / Caching / PWA
- **ADR-006:** احراز هویت Passwordless (OTP + Hybrid Auth)
- **ADR-004:** Feature Flags + Cache in-process

## ۲. انتخاب فریم‌ورک فرانت‌اند

### گزینه‌های بررسی‌شده

| گزینه | مزایا | معایب | مناسب برای ریهان؟ |
| --- | --- | --- | --- |
| Next.js (React) | SSR, SEO عالی, اکوسیستم بزرگ | پیچیدگی بالا، نیاز به Node.js در production | خیر |
| Nuxt.js (Vue) | SSR, SEO عالی, ساختار منظم | پیچیدگی بالا، نیاز به Node.js | خیر |
| HTML + HTMX + Alpine.js + Tailwind | سبک، سازگار با Django، SEO طبیعی | اکوسیستم کوچک‌تر | **بله** |
| Django Templates خالص | ساده‌ترین، کاملاً یکپارچه با Django | بدون interactivity، UX ضعیف | خیر |
| Svelte/SvelteKit | سبک، سریع، یادگیری آسان | اکوسیستم کوچک | خیر |

### تصمیم نهایی: HTML + HTMX + Alpine.js + Tailwind CSS

**چرا این ترکیب؟**

**۱. HTMX (سازگاری با Django):**
- بدون نیاز به JavaScript پیچیده
- درخواست‌های AJAX مستقیم از HTML
- کاملاً سازگار با Django templates
- Server-side rendering طبیعی (SEO عالی)

**۲. Alpine.js (interactivity سبک):**
- سبک (فقط ۱۵ KB gzip)
- syntax شبیه Vue.js اما ساده‌تر
- برای کارهای کوچک مانند dropdown, modal

**۳. Tailwind CSS (utility-first):**
- بدون نوشتن CSS جداگانه
- طراحی سریع با utility classes
- سازگار با RTL (با plugin tailwindcss-rtl)

**۴. HTML استاندارد (SEO و سادگی):**
- SEO عالی (server-side rendering طبیعی)
- بدون نیاز به JavaScript برای محتوای اصلی

### مزایای این ترکیب برای ریهان

| مزیت | توضیح |
| --- | --- |
| SEO عالی | Server-side rendering طبیعی با Django |
| سبک و سریع | بدون JavaScript سنگین، مناسب برای شبکه ضعیف |
| سازگار با Django | بدون نیاز به جدا کردن frontend از backend |
| یادگیری آسان | بنیان‌گذار غیرفنی می‌تواند بفهمد و debug کند |
| RTL native | با tailwindcss-rtl و dir="rtl" |

## ۳. معماری فرانت‌اند

### ساختار فایل‌ها

templates/
├── base.html (layout اصلی با Tailwind + Alpine + HTMX)
├── partials/ (navbar.html, footer.html, messages.html)
├── catalog/ (product_list.html, product_detail.html)
├── cart/ (cart.html, partials/cart_item.html)
├── checkout/ (checkout.html, payment.html)
├── auth/ (login.html, otp_verify.html)
└── user/ (profile.html, orders.html, devices.html)

static/
├── css/main.css (Tailwind output)
├── js/ (htmx.min.js, alpine.min.js, app.js)
└── images/ (logo.png, products/)

### الگوی درخواست‌ها

**درخواست‌های عادی (صفحه کامل):**
- لینک ساده به /products/
- Django view → render کامل template → ارسال HTML

**درخواست‌های HTMX (partial update):**
- دکمه با hx-get و hx-target
- Django view → render partial template → ارسال فقط HTML fragment
- بدون reload صفحه، UX سریع‌تر

**درخواست‌های Alpine.js (client-side only):**
- برای dropdown, modal, form validation
- بدون درخواست به سرور، فقط client-side


## ۴. سازگاری با PWA و متمم ADR-003

### Web App Manifest

فایل static/manifest.json شامل:
- name: "ریهان - فروشگاه محصولات طبیعی"
- short_name: "ریهان"
- start_url: "/"
- display: "standalone"
- background_color: "#ffffff"
- theme_color: "#10b981"
- icons: 192x192 و 512x512

لینک در base.html:
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#10b981">

### Offline-Aware Features (متمم ADR-003)

**۱. ذخیره‌سازی سبد خرید در LocalStorage:**
- سبد خرید در localStorage ذخیره می‌شود
- TTL: ۷ روز
- sync خودکار با سرور هنگام اتصال اینترنت

**۲. Queue درخواست‌های POST:**
- اگر اینترنت قطع شد، POST در IndexedDB queue می‌شود
- UI پیام "سفارش شما ثبت شد و پس از اتصال اینترنت ارسال می‌شود" نمایش می‌دهد
- sync خودکار با Idempotency Key (ADR-003)

**۳. نشانگر وضعیت اتصال (Online/Offline Indicator):**
- یک Toast/banner در بالای صفحه که وضعیت اتصال را نشان می‌دهد
- وقتی آنلاین می‌شود: sync خودکار queue با سرور

### مرز دقیق PWA در MVP

| قابلیت | وضعیت در MVP | دلیل |
| --- | --- | --- |
| Web App Manifest | بله | ساده، UX بهبود می‌دهد |
| Service Worker (Caching هوشمند) | خیر | پیچیدگی بالا |
| Push Notifications | خیر | نیاز به زیرساخت جداگانه |
| Background Sync | بله (basic) | فقط برای queue درخواست‌های POST |
| Offline Full App | خیر | خارج از محدوده MVP |

## ۵. سازگاری با لایه API (ADR-003) و احراز هویت (ADR-006)

### تعامل با API

**برای درخواست‌های HTML (Django templates):**
- Session cookie خودکار ارسال می‌شود
- بدون نیاز به JavaScript برای احراز هویت
- CSRF token در فرم‌ها

**برای درخواست‌های HTMX:**
- Session cookie خودکار ارسال می‌شود
- CSRF token به‌صورت خودکار در header X-CSRFToken تزریق می‌شود (الزام ناظر)
- Idempotency Key برای POST

**برای درخواست‌های API (آینده - اپ موبایل):**
- JWT در Authorization header
- Refresh Token Rotation (ADR-006)
- Idempotency Key برای POST

### 🔧 کانفیگ سراسری HTMX (الزام ناظر - آسیب ۳)

**تزریق خودکار CSRF Token در تمام درخواست‌های غیر-GET:**

فایل static/js/htmx-csrf.js در base.html لود می‌شود و به‌صورت سراسری CSRF Token را از cookie یا meta tag خوانده و به هدر X-CSRFToken اضافه می‌کند. این کار از خطای 403 Forbidden در تمام فرم‌های HTMX جلوگیری می‌کند.

**نکته:** این فایل قبل از htmx.min.js لود نمی‌شود، بلکه پس از آن و با استفاده از event listener روی document.body ثبت می‌شود تا htmx:configRequest را catch کند.

### 🔧 سازگاری DOM بین HTMX و Alpine.js (الزام ناظر - آسیب ۱)

**مشکل:** هنگامی که HTMX بخشی از HTML را با hx-swap جایگزین می‌کند، کامپوننت‌های Alpine.js درون آن بخش Event Listenerها و State خود را از دست می‌دهند.

**راه‌حل:** استفاده از هوک htmx:afterSettle + Alpine.initTree()

پس از هر Swap موفق HTMX، event listener روی document.body فعال می‌شود و روی عنصر جایگزین‌شده (detail.elt) تابع Alpine.initTree() را فراخوانی می‌کند. این کار باعث Re-bind خودکار تمام کامپوننت‌های Alpine.js در محتوای جدید می‌شود.

**گزینه جایگزین:** استفاده از کتابخانه hx-alpine-compat (در صورت نیاز به پیچیدگی بیشتر). در MVP از روش دستی (Alpine.initTree) استفاده می‌شود که سبک‌تر و قابل فهم‌تر است.

### Middleware Integration (متمم ADR-006)

**AuthenticationMiddleware:**
- قبل از رسیدن درخواست به View اجرا می‌شود
- استخراج توکن از cookie یا header
- اعتبارسنجی و تنظیم request.user

**FeatureFlagMiddleware:**
- پس از احراز هویت اجرا می‌شود
- بررسی Feature Flag برای ماژول مربوطه
- رد درخواست با 404 اگر ماژول غیرفعال باشد

## ۶. RTL و زبان فارسی

### RTL Support

**Tailwind CSS:**
- plugin tailwindcss-rtl نصب می‌شود
- همه utility classes به‌صورت خودکار RTL-aware می‌شوند
- مثال: mr-4 در RTL به ml-4 تبدیل می‌شود

**HTML:**
- <html lang="fa" dir="rtl">
- همه text-alignها به‌صورت پیش‌فرض right

**فونت:**
- فونت Vazirmatn از CDN
- font-family: 'Vazirmatn', sans-serif
- font-weight: 400 (regular), 700 (bold)

### i18n-Ready (آینده)

- Django i18n framework آماده است
- در MVP فقط فارسی
- اما ساختار آماده برای افزودن زبان‌های دیگر در آینده
- همه متن‌ها در locale/fa/LC_MESSAGES/django.po

### اعداد فارسی

- اعداد در UI به‌صورت فارسی نمایش داده می‌شوند
- اعداد در API به‌صورت انگلیسی (برای سازگاری)
- Django template filter برای تبدیل: {{ price|persian_digits }}



## ۷. Asset Pipeline و Build Process

### 🔧 میزبانی محلی تمام کتابخانه‌ها (الزام ناظر - اصل ۹ - آسیب ۲)

**اصل ۹ (استقلال از سیستم‌های خارجی) ایجاب می‌کند:**
تمام کتابخانه‌های فرانت‌اند (htmx.min.js، alpine.min.js، فونت Vazirmatn) باید به‌صورت فایل‌های استاتیک محلی در پوشه /static/vendor/ ذخیره شوند. **هیچ فراخوانی به CDN خارجی (unpkg, cdnjs, Google Fonts) در Runtime صورت نمی‌گیرد** تا قطعی اینترنت بین‌الملل یا فیلترینگ سایت را فلج نکند.

**ساختار پوشه vendor:**
- /static/vendor/htmx/htmx.min.js (نسخه پایداری که تست شده)
- /static/vendor/alpine/alpine.min.js (نسخه پایداری که تست شده)
- /static/vendor/fonts/vazirmatn/Vazirmatn-Regular.woff2
- /static/vendor/fonts/vazirmatn/Vazirmatn-Bold.woff2

**بارگذاری در base.html:**
همه کتابخانه‌ها از مسیرهای محلی (/static/vendor/...) لود می‌شوند، نه از CDN. این کار باعث می‌شود سایت در شرایط قطعی اینترنت بین‌الملل نیز کاملاً عملیاتی بماند.

### Tailwind CSS Build (الزام ناظر - آسیب ۴)

**توسعه (Development):**
- Tailwind CLI در حالت watch
- npx tailwindcss -i ./static/css/input.css -o ./static/css/dist/styles.css --watch
- تغییر فوری با هر تغییر در HTML

**Production:**
- Tailwind CLI برای build نهایی
- npx tailwindcss -i ./static/css/input.css -o ./static/css/dist/styles.css --minify
- PurgeCSS برای حذف کلاس‌های استفاده‌نشده
- **فایل نهایی:** /static/css/dist/styles.css
- حجم نهایی: < 50 KB gzip

**نکته مهم (الزام ناظر):**
فایل کامپایل‌شده (static/css/dist/styles.css) به مخزن commit می‌شود. این یعنی در سرور تولید (production) **نیازی به Node.js یا اجرای Tailwind CLI نیست**. فقط فایل CSS نهایی توسط Nginx serve می‌شود. این هم‌راستا با تصمیم "بدون Node.js در production" در بخش ۲ است.

**Build Script:**
- scripts/build_css.sh در مخزن
- اجرای خودکار قبل از deploy (در ADR-008)
- یا اجرای دستی توسط توسعه‌دهنده قبل از commit

### JavaScript Libraries (میزبانی محلی)

**HTMX:**
- /static/vendor/htmx/htmx.min.js
- حجم: ۱۴ KB gzip
- نسخه pinned در مخزن

**Alpine.js:**
- /static/vendor/alpine/alpine.min.js
- حجم: ۱۵ KB gzip
- نسخه pinned در مخزن

**Custom JS (app.js):**
- /static/js/app.js
- فقط برای Offline-Aware features + HTMX/Alpine integration (CSRF, initTree)
- حجم: < 5 KB

**htmx-csrf.js:**
- /static/js/htmx-csrf.js
- کانفیگ سراسری CSRF برای HTMX

### Images و Assets

**Optimization:**
- تصاویر محصولات: WebP format با JPEG fallback
- Lazy loading با loading="lazy"
- srcset برای responsive images
- thumbnail: 300x300، full: 1200x1200

**CDN (آینده - فاز ۶):**
- در MVP از CDN استفاده نمی‌شود (اصل ۹)
- اما ساختار آماده است: static files در /static/
- افزودن CDN فقط نیاز به تغییر Nginx config دارد (در ADR-008)

## ۸. معیارهای پذیرش و ریسک‌ها

### معیارهای پذیرش

| معیار | هدف | روش اندازه‌گیری |
| --- | --- | --- |
| حجم صفحه اصلی | < 80 KB (HTML + Critical CSS) | DevTools Network |
| حجم صفحه محصول | < 15 KB (gzip) | DevTools Network |
| Time to First Byte (TTFB) | < 500 ms | Lighthouse |
| First Meaningful Paint | < 3 ثانیه در 3G | Lighthouse |
| Lighthouse Performance | > 90 | Lighthouse |
| Lighthouse SEO | > 95 | Lighthouse |
| Lighthouse Accessibility | > 90 | Lighthouse |
| سبد خرید در آفلاین | ۱۰۰٪ حفظ می‌شود | E2E test |
| RTL correctness | ۱۰۰٪ | Visual test |

### ریسک‌ها و Mitigation

| ریسک | احتمال | تأثیر | Mitigation |
| --- | --- | --- | --- |
| پیچیدگی HTMX برای interactivity پیچیده | متوسط | متوسط | استفاده از Alpine.js برای کارهای پیچیده |
| Tailwind CSS یادگیری سخت برای non-developer | پایین | متوسط | مستندات داخلی، کلاس‌های پرکاربرد |
| عدم سازگاری HTMX با برخی Django features | پایین | بالا | تست کامل قبل از production |
| حجم JavaScript زیاد (HTMX + Alpine + Custom) | پایین | متوسط | Lazy loading، فقط در صفحات مورد نیاز |
| LocalStorage پر شود | پایین | پایین | LRU eviction پس از 5 MB |

## ۹. Out of Scope صریح

### در MVP اجرا نمی‌شود

- **Next.js یا Nuxt.js:** پیچیدگی بالا، نیاز به Node.js
- **Service Worker کامل با caching استراتژی‌های پیچیده**
- **CDN خارجی (CloudFlare, ArvanCloud)** — در فاز ۶ ارزیابی می‌شود
- **Push Notifications**
- **App Shell Model** — پیچیدگی بالا
- **Pre-fetching هوشمند** (ML-based)
- **GraphQL:** REST API کافی است (ADR-003)
- **WebSocket برای real-time:** polling کافی است در MVP
- **Micro-frontends:** single monolith کافی است
- **Storybook برای component library:** overhead بالا

## ۱۰. هم‌راستایی با سایر ADRها و اصول

### با ADR-001 (Django)
- کاملاً سازگار با Django templates
- بدون نیاز به جدا کردن frontend از backend
- Session cookie برای احراز هویت

### با ADR-003 (API Strategy)
- همه endpointها از Sparse Fieldsets و Pagination پشتیبانی می‌کنند
- ETag در همه پاسخ‌های GET
- Idempotency Key برای POSTهای queued

### با متمم ADR-003 (Offline-First)
- LocalStorage برای سبد خرید
- IndexedDB queue برای POST
- Web App Manifest برای Add to Home Screen

### با ADR-006 (احراز هویت)
- Session cookie برای وب
- JWT برای API (آینده)
- DeviceToken برای Remember Me

### با ADR-004 (Feature Flags)
- قابلیت‌های PWA/Offline با Feature Flag کنترل می‌شوند
- اگر PWA در MVP مشکل‌ساز شد، می‌توان با یک toggle غیرفعال کرد

### با اصل ۱۱ (کرامت مشتری)
- کاربر در هوراند تجربه قابل قبولی خواهد داشت
- پیام‌های خطای محترمانه در شرایط آفلاین
- عدم از دست رفتن سبد خرید در قطعی شبکه

### با محدودیت‌های بنیان‌گذار
- پیاده‌سازی ساده با ابزارهای built-in Django
- بدون نیاز به زیرساخت پیچیده
- قابل مدیریت از طریق پنل ادمین

## ۱۱. ارجاعات

### تصمیمات و اسناد
- **ADR-001:** Django 5.2 LTS (backend framework)
- **ADR-003:** API Strategy + API-First
- **متمم ADR-003:** Offline-First / Caching / PWA
- **ADR-006:** احراز هویت Passwordless
- **ADR-004:** Feature Flags + Cache in-process
- **CENTRAL-STORY.md:** داستان محوری
- **USER-PERSONAS.md:** پرسونای خانم مریم ۵۲ ساله از هوراند

### کتابخانه‌ها
- **HTMX:** https://htmx.org
- **Alpine.js:** https://alpinejs.dev
- **Tailwind CSS:** https://tailwindcss.com
- **Vazirmatn Font:** https://github.com/rastikerdar/vazirmatn

### استانداردها
- **PWA Checklist (web.dev):** معیارهای Progressive Web App
- **Google Web Vitals:** TTFB, LCP, FID
- **WCAG 2.1:** Accessibility guidelines


---

## تأیید نهایی ناظر (با ۴ متمم فنی)

**تاریخ تصویب:** ۱۴۰۵/۰۵/۱۷
**Commit راستی‌آزمایی:** fb5a4d3
**Commit اصلاحات فنی:** (در انتظار ثبت)

**۴ الزام فنی اعمال‌شده:**
۱. تزریق خودکار CSRF Token جانگو در درخواست‌های HTMX (بخش ۵)
۲. سازگاری DOM بین HTMX و Alpine.js با htmx:afterSettle + Alpine.initTree (بخش ۵)
۳. میزبانی محلی تمام کتابخانه‌ها در /static/vendor/ طبق اصل ۹ (بخش ۷)
۴. ذخیره CSS کامپایل‌شده در /static/css/dist/styles.css (بخش ۷)

این سند اکنون **مصوب** است و استک فرانت‌اند برای MVP ریهان قطعی شد.
