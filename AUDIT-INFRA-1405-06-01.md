# 📋 AUDIT-INFRA-1405-06-01: ممیزی زیرساخت، رفع باگ‌های بحرانی و امنیت

**تاریخ:** 2026-08-23 (یکشنبه ۱ شهریور ۱۴۰۵)
**اجرا:** عامل هوشمند Minis (اتصال SSH کلیدمحور از دستگاه موبایل کاربر)
**دامنه:** سلامت سرویس، شبکه Docker، تنظیمات امنیتی Django/nginx، صفحات عمومی، API، استاتیک/مدیا
**وضعیت نهایی:** ✅ تمام تست‌ها سبز — سرویس پایدار روی rihan360.ir

---

## ۱. خلاصه اجرایی

سایت از حدود میانه مرداد ۱۴۰۵ عملاً غیرقابل استفاده بود؛ کانتینر `rihan_web` در حلقه کرش (۱۰۲۴+ ری‌استارت) بود و صفحه اصلی فقط به لطف یک `runserver` سرگردان روی هاست پاسخ می‌داد. ریشه مشکل یک **زنجیره ۵ مرحله‌ای خرابی** بود که هر لایه آن، لایه بعدی را پنهان می‌کرد. همگی شناسایی و رفع شدند و در ادامه سخت‌سازی امنیتی (DEBUG، SECRET_KEY، ALLOWED_HOSTS، CSRF، سرو استاتیک/مدیا) نیز انجام گرفت. **هیچ داده‌ای از دست نرفت** و قبل از تغییرات از دیتابیس پشتیبان تهیه شد.

## ۲. باگ‌های شناسایی و رفع‌شده

| # | شدت | مشکل | علت ریشه‌ای | راهکار اعمال‌شده |
|---|---|---|---|---|
| 1 | 🔴 بحرانی | کانتینر وب به PostgreSQL نمی‌رسید (`name resolution failure`)، restarts=1024 | اتصال کانتینر به شبکه `rihan-platform_default` عملاً قطع شده بود (state مخدوش daemon) | `docker compose up -d --force-recreate web` + در صورت نیاز `docker network connect` دستی |
| 2 | 🔴 بحرانی | `env file .env not found` هنگام recreate | فایل `.env` حذف شده بود | بازسازی از env کانتینر قدیمی (۱۴ کلید) با `docker exec printenv`؛ chmod 600 |
| 3 | 🟠 بالا | bind پورت 8000 ممکن نبود (`address already in use`) | یک `manage.py runserver` سرگردان از 22 اوت روی هاست اجرا بود (pid 292698) | kill فرایند سرگردان |
| 4 | 🔴 بحرانی | `ModuleNotFoundError: jdatetime / psycopg2` | `requirements.txt` فقط ۲ پکیج داشت (Django, openpyxl)! | بازنویسی کامل با ۱۶ پکیج pinned شناخته‌شده-سالم (psycopg2-binary, gunicorn, DRF, jdatetime, pillow, django-redis, whitenoise, ...) + rebuild تصویر |
| 5 | 🔴 بحرانی | gunicorn: `No module named 'rihan.wsgi'` | مسیر WSGI در `deploy/entrypoint.sh` غلط بود | اصلاح به `src.config.wsgi:application` |
| 6 | 🟠 بالا | کلیک سبد خرید → 404 روی `/cart/` | لینک هاردکد غلط در `base.html:338` | `{% url 'order_pages:cart_page' %}` (نام‌فضای `order_pages`) |
| 7 | 🟠 بالا (امنیت) | `DEBUG = True` هاردکد در settings | توسعه‌ای ماندن تنظیمات | خواندن از env با default امن `False`؛ مقدار پروداکشن `DEBUG=False` در `.env` |
| 8 | 🟠 بالا (امنیت) | اجرا با کلید ناامن dev | settings کلید `DJANGO_SECRET_KEY` را می‌خواند ولی `.env` دارای `SECRET_KEY` بود | پذیرش هر دو نام؛ اولویت `SECRET_KEY` (کلید واقعی اکنون فعال است) |
| 9 | 🟡 متوسط (امنیت) | `ALLOWED_HOSTS=['*']` | - | لیست محدود: rihan360.ir, www, IP سرور, localhost |
| 10 | 🟡 متوسط | CSRF/proxy آماده نبود | نبود `CSRF_TRUSTED_ORIGINS` و `SECURE_PROXY_SSL_HEADER` | هر دو اضافه شد؛ nginx از قبل `X-Forwarded-Proto` می‌فرستد |
| 11 | 🟡 متوسط | استاتیک (از جمله پنل ادمین) روی gunicorn سرو نمی‌شد | whitenoise نصب بود اما در MIDDLEWARE نبود | افزودن `whitenoise.middleware.WhiteNoiseMiddleware` بعد از SecurityMiddleware |
| 12 | 🟡 متوسط | مدیا فقط وقتی DEBUG=True سرو می‌شد | بلوک `if settings.DEBUG` در urls.py + نبود location در nginx | سرو مستقیم `/media/` در nginx (alias به volume) + مسیر fallback همیشگی Django |
| 13 | 🟢 کم | مهاجرت‌های معوق مدل‌ها | تغییرات index در core/rihan_auth | `makemigrations core rihan_auth` + `migrate` → OK |

## ۳. فایل‌های تغییر یافته

| فایل | نوع تغییر | نسخه پشتیبان |
|---|---|---|
| `src/config/settings.py` | SECRET_KEY/DEBUG/HOSTS env-driven، CSRF_TRUSTED_ORIGINS، SECURE_PROXY_SSL_HEADER، whitenoise MW | `settings.py.bak_14050601` |
| `src/config/urls.py` | سرو همیشگی media (fallback) | `urls.py.bak_14050601` |
| `.env` | DEBUG=False، ALLOWED_HOSTS محدود، افزودن CSRF_TRUSTED_ORIGINS | `.env.bak_14050601` |
| `requirements.txt` | ۱۶ پکیج کامل pinned | `requirements.txt.bak` |
| `deploy/entrypoint.sh` | مسیر صحیح WSGI | (تغییر تک‌خطی) |
| `src/modules/catalog/templates/catalog/base.html` | لینک صحیح سبد خرید | (تغییر تک‌خطی) |
| `/etc/nginx/sites-available/rihan.conf` | بلوک `location /media/` | - |

> ⚠️ تغییرات فعلاً **commit نشده**اند (repo روی branch `main`)؛ پیشنهاد: پس از تایید نهایی، commit و push شود.

## ۴. نتایج تست نهایی (پس از رفع)

| مسیر | وضعیت |
|---|---|
| `/` (فهرست محصولات)، `/about/`، `/contact/`، `/return-policy/` | ✅ 200 |
| `/order/cart/` (صفحه سبد) و `/api/v1/order/cart/` | ✅ 200 |
| `/products/<slug>/` (جزئیات محصول) | ✅ 200 |
| `/admin/login/` + POST فرم با CSRF (سناریوی http واقعی) | ✅ 200 |
| `/static/admin/css/base.css` (whitenoise) | ✅ 200 |
| `/media/receipts/...` (nginx مستقیم) | ✅ 200 (پس از `chmod o+x` زنجیره `/var/lib/docker`) |
| `/sitemap.xml`، `/robots.txt` | ✅ 200 |
| `manage.py check` | ✅ بدون خطا |
| مهاجرت‌ها | ✅ کاملاً به‌روز |

**پشتیبان دیتابیس:** `/root/backups/rihan_db_20260823_0517.sql.gz`

## ۵. اقدامات پیشنهادی آینده (Backlog)

1. 🔒 **نصب TLS** (certbot/Let's Encrypt) و `listen 443` + ریدایرکت 80→443؛ سپس افزودن `http://` variants به CSRF_TRUSTED_ORIGINS و بررسی کوکی Secure.
2. 💾 **بکاپ خودکار روزانه** pg_dump + نگهداشت ۷ روزه (cron).
3. 🧹 حذف جدول یتیمی `catalog_productreview` از دیتابیس (مدل مربوطه دیگر در کد وجود ندارد؛ خطاهای تکراری لاگ 16 مرداد از همین بود).
4. 📦 ماژول `api/v1/catalog` هنوز placeholder است («اسپرینت‌های آینده»).
5. 🌱 جایگزینی داده‌های تست (۵ محصول نمونه) با اطلاعات واقعی فروشگاه.
6. 🔄 commit و push تغییرات جاری در گیت.
