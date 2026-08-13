# ADR-008: استقرار، کانتینرسازی و پشتیبان‌گیری (Deployment, Docker & Backup)

| شناسه | ADR-008 |
| --- | --- |
| عنوان | استقرار، کانتینرسازی و پشتیبان‌گیری (Deployment, Docker & Backup) |
| وضعیت | **Approved ✅** — مصوب شده توسط ناظر پروژه (۱۴۰۵/۰۵/۱۷) |
| تاریخ | ۲۰۲۶-۰۸-۰۷ (آخرین بازنویسی: ۲۰۲۶-۰۸-۱۳ بر اساس D-079) |
| تصمیم‌گیرنده | عبدالحسین فهیمی (بنیان‌گذار) + تحلیلگر فنی |
| مرتبط | ADR-001, ADR-002, ADR-003, ADR-007, اصل ۹, اصل ۱۰, D-022 (خودمیزبانی), **D-079** |

> **✅ این سند مصوب است.** هر تغییر اساسی نیاز به ADR جدید دارد.
> **تاریخ تصویب:** ۱۴۰۵/۰۵/۱۷
> **تأییدکننده:** ناظر پروژه
> **الزام:** پیاده‌سازی زیرساخت در فاز ۵ باید کاملاً مطابق این ADR باشد.
>
> ⚠️ **یادداشت بازنویسی (D-079):** در تاریخ ۲۰۲۶-۰۸-۱۳، سه تغییر اساسی بر اساس D-079 اعمال شد:
> - افزودن **sitemap.xml و robots.txt** به‌صورت خودکار در استقرار
> - افزودن **cron job** برای بازسازی sitemap
> - افزودن **CI/CD تست برند مستقل** قبل از deploy
> **ارجاع:** [decisions/D-079-RETURN-TO-ORIGINAL-VISION.md](../D-079-RETURN-TO-ORIGINAL-VISION.md)

## ۱. زمینه و ارجاعات

### چرا این ADR حیاتی است؟
این سند **آخرین مغایرت باز** از گزارش ممیزی ناظر (مغایرت شماره ۱: خلاء ADR مربوط به استقرار و زیرساخت) را می‌بندد. بدون این ADR، فاز ۴ ناقص است و ورود به فاز ۵ (کدنویسی) غیرممکن خواهد بود.

### الزامات کلیدی
- **اپراتور غیربرنامه‌نویس:** بنیان‌گذار از ترمینال Termius استفاده می‌کند و دانش فنی عمیق DevOps ندارد. استقرار باید با یک دستور ساده انجام شود.
- **اصل ۹ (مستقل از خارج):** خودمیزبانی کامل (D-022). استفاده از VPS ایرانی، بدون AWS/Azure/GCP.
- **اصل ۱۰ (کنترل کامل ادمین):** لاگ‌ها و بکاپ‌ها باید قابل دسترسی و مدیریت باشند.
- **قابلیت تکرار (Reproducibility):** هر استقرار باید دقیقاً یکسان با استقرار قبلی باشد.

#
## ارجاعات
- **ADR-001:** Django 5.2 LTS
- **ADR-002:** PostgreSQL (دیتابیس)
- **ADR-003:** API Strategy
- **ADR-007:** Frontend Stack (HTML+HTMX+Alpine+Tailwind، بدون Node.js در production)
- **D-022:** خودمیزبانی کامل
- **CENTRAL-STORY.md:** داستان محوری

## ۲. معماری کلی استقرار (3-Tier Architecture)

### نمای کلی
- **Nginx Container:** Reverse Proxy + SSL + serve استاتیک
- **Django App Container:** Gunicorn + Uvicorn برای پردازش درخواست‌ها
- **PostgreSQL Container:** دیتابیس اصلی
- **سه کانتینر با Docker-Compose** روی یک VPS ایرانی

### سه کانتینر اصلی

| کانتینر | نقش | Image پایه | پورت |
| --- | --- | --- | --- |
| **web** | Django App (Gunicorn + Uvicorn) | python:3.12-slim | 8000 (داخلی) |
| **nginx** | Reverse Proxy + SSL + Static Files | nginx:alpine | 80, 443 |
| **db** | PostgreSQL Database | postgres:16-alpine | 5432 (داخلی) |

### چرا Docker-Compose؟
- **سادگی:** یک فایل docker-compose.yml برای تعریف تمام سرویس‌ها
- **یک دستور:** docker-compose up -d --build برای استقرار کامل
- **تکرارپذیری:** هر بار دقیقاً همان محیط
- **ایزوله:** هر سرویس در کانتینر جداگانه
- **مناسب برای non-devops:** نیازی به دانش عمیق Kubernetes نیست

### چرا نه Kubernetes؟
- **پیچیدگی بالا:** برای یک VPS تک‌سروره overkill است
- **هزینه:** نیاز به کنترل‌پنل (Rancher, k3s) دارد
- **یادگیری سخت:** برای اپراتور غیربرنامه‌نویس مناسب نیست
- **فاز آینده:** در صورت رشد به چند سرور، می‌توان مهاجرت کرد

## ۳. Dockerfile برای Django App

### ساختار Multi-stage Build

**مرحله ۱: Builder (برای نصب وابستگی‌ها)**
- Image: python:3.12-slim
- نصب system dependencies (gcc, postgresql-client)
- کپی requirements.txt و نصب با pip
- کپی کد پروژه

**مرحله ۲: Runtime (تصویر نهایی سبک)**
- Image: python:3.12-slim (بدون build tools)
- کپی virtualenv از builder stage
- کپی کد پروژه
- ایجاد user غیر-root (security)
- EXPOSE 8000
- CMD: gunicorn با workers

### ویژگی‌های کلیدی Dockerfile
- **Multi-stage build:** کاهش حجم تصویر نهایی به کمتر از ۳۰۰ MB
- **Non-root user:** اجرای برنامه با کاربر rihan (نه root)
- **Layer caching:** ترتیب هوشمند COPY برای استفاده از cache
- **.dockerignore:** جلوگیری از کپی فایل‌های غیرضروری (.git, __pycache__, .env)
- **Health check:** بررسی سلامت اپلیکیشن با /health/ endpoint

### Environment Variables
متغیرهای مهم در فایل .env (خارج از مخزن):
- DATABASE_URL
- SECRET_KEY
- ALLOWED_HOSTS
- KAVENEGAR_API_KEY
- DEBUG=False
- SENTRY_DSN (اختیاری)

## ۴. docker-compose.yml (تعریف سرویس‌ها)

### سرویس db (PostgreSQL)
- Image: postgres:16-alpine (سبک، امن)
- Volume: postgres_data:/var/lib/postgresql/data (persist)
- Environment: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- Health check: pg_isready
- Restart policy: always

### سرویس web (Django App)
- Build: از Dockerfile محلی
- Volumes:
  - static_volume:/app/staticfiles (برای Nginx)
  - media_volume:/app/media (آپلود کاربران)
- Depends on: db (با شرط healthy)
- Environment: از فایل .env خوانده می‌شود
- Command: gunicorn rihan.wsgi:application --bind 0.0.0.0:8000 --workers 3
- Health check: curl -f http://localhost:8000/health/
- Restart policy: always

### سرویس nginx (Reverse Proxy)
- Image: nginx:alpine
- Ports: 80:80, 443:443
- Volumes:
  - ./nginx/conf.d:/etc/nginx/conf.d (config)
  - ./nginx/ssl:/etc/nginx/ssl (certificates)
  - static_volume:/app/staticfiles:ro (read-only)
  - media_volume:/app/media:ro (read-only)
- Depends on: web
- Restart policy: always

### Named Volumes (برای persistence)
- postgres_data: داده‌های دیتابیس
- static_volume: فایل‌های استاتیک جمع‌آوری‌شده (collectstatic)
- media_volume: آپلودهای کاربران (تصاویر محصولات، رسید پرداخت)

## ۵. پیکربندی Nginx

### Reverse Proxy Configuration
**مسیرهای اصلی:**
- / → proxy_pass به Django (web:8000)
- /static/ → serve مستقیم از static_volume
- /media/ → serve مستقیم از media_volume
- /health/ → بررسی سلامت

### SSL/TLS (Let's Encrypt)
**گواهی SSL رایگان:**
- استفاده از Certbot با Let's Encrypt
- Auto-renewal با cron job (هفته‌ای یک‌بار)
- Redirect خودکار HTTP به HTTPS

**Security Headers:**
- Strict-Transport-Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Content-Security-Policy (CSP)

### Performance Settings
- Gzip compression: سطح ۶ برای text/html, text/css, application/json, application/javascript
- Client-side caching: ۱ سال برای /static/ (با hash در نام فایل، هم‌راستا با ADR-007)
- Buffer sizes: مناسب برای Django responses
- Timeouts: ۶۰ ثانیه برای backend

### Rate Limiting (در Nginx)
- /api/v1/auth/otp/request/: ۳ درخواست در دقیقه per IP
- /api/v1/orders/: ۱۰ درخواست در دقیقه per IP
- جلوگیری از DDoS سبک

## ۶. مدیریت دیتابیس (PostgreSQL)

### Migrations
**استراتژی:**
- Migrations در مخزن commit می‌شوند
- اجرای خودکار migrations هنگام start کانتینر web (قبل از gunicorn)
- دستور: python manage.py migrate --noinput

**Zero-downtime migrations:**
- migrations باید backward-compatible باشند
- برای تغییرات بزرگ، دو مرحله‌ای (add column → backfill → add constraint)
- تست migrations در staging قبل از production

### Database Connection Pooling
- استفاده از django-db-geventpool یا pgbouncer (در آینده)
- در MVP: تنظیمات پیش‌فرض Django با CONN_MAX_AGE=60
- Max connections: ۱۰۰ (قابل تنظیم از پنل ادمین در آینده)

## ۷. استراتژی پشتیبان‌گیری (Backup Strategy)

### بکاپ دیتابیس (PostgreSQL)

**زمان‌بندی:**
- بکاپ روزانه: هر شب ساعت ۲ بامداد (cron job)
- بکاپ هفتگی: هر جمعه ساعت ۳ بامداد (full backup)
- Retention: ۳۰ روز برای بکاپ‌های روزانه، ۶ ماه برای بکاپ‌های هفتگی

**فرمت بکاپ:**
- pg_dump با فرمت custom (برای restore سریع)
- فشرده‌سازی با gzip
- رمزنگاری با AES-256 (برای امنیت)

**محل ذخیره:**
- Local: /backups/ داخل سرور (Named Volume)
- Remote: انتقال به فضای ذخیره‌سازی ابری ایرانی (مانند ArvanCloud Object Storage یا Podspace) در فاز ۶
- در MVP فقط local backup

### بکاپ فایل‌های Media

**زمان‌بندی:**
- بکاپ هفتگی: همه فایل‌های media
- Retention: ۳ ماه

**اسکریپت بکاپ:**
- scripts/backup.sh در مخزن
- اجرای خودکار با cron
- لاگ کامل در /var/log/rihan-backups.log

### تست Restore
- تست ماهیانه restore در محیط staging
- مستندسازی کامل روند restore برای بنیان‌گذار
- دستور restore: docker-compose exec db pg_restore ...

## ۸. One-Command Deployment (برای اپراتور غیربرنامه‌نویس)

### دستورات کلیدی برای بنیان‌گذار

**استقرار اولیه (فقط یک‌بار):**
- git clone https://github.com/abyfahimy91-netizen/rihan-platform.git
- cd rihan-platform
- cp .env.example .env (ویرایش مقادیر)
- docker-compose up -d --build

**به‌روزرسانی (هر بار):**
- git pull origin main
- docker-compose up -d --build
- (migrations خودکار اجرا می‌شوند)

**مشاهده لاگ‌ها:**
- docker-compose logs -f web (لاگ Django)
- docker-compose logs -f nginx (لاگ Nginx)
- docker-compose logs -f db (لاگ PostgreSQL)

**Restart سرویس‌ها:**
- docker-compose restart web
- docker-compose restart (همه)

**Stop کامل:**
- docker-compose down (حفظ داده‌ها)
- docker-compose down -v (حذف داده‌ها - خطرناک!)

### مستندسازی برای بنیان‌گذار
- فایل deploy/OPERATOR-GUIDE.md در مخزن
- راهنمای گام‌به‌گام با تصاویر
- عیب‌یابی مشکلات رایج
- دستورات ضروری برای Termius

## ۹. GitHub Actions CI/CD Pipeline

### Workflow اصلی (.github/workflows/deploy.yml)

**مرحله ۱: CI (Continuous Integration)**
- Trigger: push به main یا pull request
- مراحل:
  - Checkout کد
  - Setup Python 3.12
  - Install dependencies
  - Run tests (pytest)
  - Run linters (flake8, black)
  - Build Docker image (تست build)

**مرحله ۲: CD (Continuous Deployment)**
- Trigger: فقط push به main
- مراحل:
  - SSH به سرور VPS ایرانی (با key)
  - git pull origin main
  - docker-compose up -d --build
  - اجرای migrations
  - اجرای collectstatic
  - Health check

### Secrets در GitHub
- VPS_HOST: آدرس IP سرور
- VPS_USER: نام کاربری SSH
- VPS_SSH_KEY: کلید خصوصی SSH
- DEPLOY_PATH: مسیر پروژه روی سرور

### Branch Strategy
- main: production (هر push = deploy خودکار)
- develop: staging (برای تست)
- feature/*: feature branches (PR به develop)

### Rollback
- اگر deploy شکست خورد، GitHub Actions به‌صورت خودکار به commit قبلی rollback می‌کند
- دستور دستی rollback: docker-compose down و git checkout commit-hash و docker-compose up -d --build

## ۱۰. Monitoring و Logging

### لاگ‌ها (Logs)

**ساختار لاگ:**
- Django: JSON format با python-json-logger
- Nginx: combined format
- PostgreSQL: پیش‌فرض

**محل ذخیره:**
- Docker logs: docker-compose logs
- File logs: /var/log/rihan/ در سرور
- Retention: ۳۰ روز (logrotate)

### Monitoring

**Health Checks:**
- /health/: بررسی سلامت Django + Database
- /health/db/: بررسی اختصاصی database
- /health/nginx/: بررسی Nginx

**Uptime Monitoring (فاز ۶):**
- UptimeRobot یا سرویس ایرانی مشابه
- Alert از طریق SMS (Kavenegar) در صورت downtime

**Application Performance Monitoring (فاز ۶):**
- Sentry برای error tracking
- Prometheus + Grafana (اگر نیاز شد)

### Alerts
- خطاهای ۵xx بالای ۱٪ در ۵ دقیقه
- Downtime بیش از ۲ دقیقه
- Disk usage بالای ۸۰٪
- Database connection pool exhaustion

## ۱۱. سئو فنی در استقرار (D-079)

### ۸.۱ تولید خودکار sitemap.xml

یک Django management command برای تولید sitemap.xml در /static/sitemap.xml ذخیره می‌شود.

### ۸.۲ فایل robots.txt

فایل robots.txt به‌صورت استاتیک در /static/robots.txt قرار می‌گیرد:

- User-agent: * - Allow: /
- Disallow: /admin/ - Disallow: /api/
- Sitemap: https://rihan.ir/sitemap.xml

### ۸.۳ Cron Job برای بازسازی sitemap

یک cron job روزانه ساعت ۲ صبح sitemap را بازسازی می‌کند.

### ۸.۴ پیکربندی Nginx برای فایل‌های سئو

Nginx فایل‌های sitemap.xml و robots.txt را از مسیر /app/static/ سرو می‌کند.

---

## ۱۲. CI/CD تست برند مستقل (D-079)

### ۹.۱ تست خودکار قبل از Deploy

قبل از هر deploy، قالب‌های HTML اسکن می‌شوند تا کلمات ممنوعه یافت نشوند:

- عبدالحسین فهیمی
- فهیمی
- بنیان‌گذار (در صفحات عمومی)
- صاحب سایت
- موسس

### ۹.۲ ادغام در GitHub Actions

یک step در GitHub Actions قبل از deploy اجرا می‌شود. اگر کلمه ممنوعه‌ای یافت شود، deploy رد می‌شود.

### ۹.۳ قوانین Deploy

- اگر تست برند مستقل fail شود، deploy رد می‌شود
- ادمین باید ابتدا مشکل را حل کند
- هیچ راه میانبری وجود ندارد

---

## ۱۳. Out of Scope صریح

### در MVP اجرا نمی‌شود
- **Kubernetes:** overkill برای VPS تک‌سروره
- **Multi-region deployment:** فقط یک VPS ایرانی
- **Blue-Green Deployment:** پیچیدگی بالا
- **Canary Releases:** نیاز به traffic splitting
- **Auto-scaling:** ترافیک پایین در MVP
- **Cloud provider (AWS/Azure/GCP):** مغایر اصل ۹
- **CDN خارجی:** مغایر اصل ۹
- **Advanced monitoring (Datadog, New Relic):** هزینه بالا
- **Load balancer:** فقط یک سرور در MVP
- **Disaster Recovery به datacenter دیگر:** در فاز ۷

## ۱۴. معیارهای پذیرش و ریسک‌ها

### معیارهای پذیرش

| معیار | هدف | روش اندازه‌گیری |
| --- | --- | --- |
| زمان استقرار | کمتر از ۵ دقیقه | از git pull تا up شدن |
| Uptime | ۹۹.۵٪ (ماهانه) | Uptime monitoring |
| زمان بکاپ روزانه | کمتر از ۱۰ دقیقه | cron log |
| زمان restore | کمتر از ۳۰ دقیقه | تست ماهیانه |
| Docker image size | کمتر از ۵۰۰ MB | docker images |
| Build time | کمتر از ۳ دقیقه | GitHub Actions |
| Health check response | کمتر از ۲۰۰ ms | curl |

### ریسک‌ها و Mitigation

| ریسک | احتمال | تأثیر | Mitigation |
| --- | --- | --- | --- |
| VPS outage | متوسط | بالا | بکاپ روزانه + disaster recovery plan |
| Docker image build failure | پایین | متوسط | CI pipeline با rollback خودکار |
| Database corruption | پایین | بحرانی | بکاپ روزانه + تست restore ماهیانه |
| SSL certificate expiration | پایین | بالا | auto-renewal با Certbot + alert |
| Disk full | متوسط | بالا | monitoring + logrotate |
| DDoS attack | پایین | بالا | Nginx rate limiting + firewall |
| SSH key compromise | پایین | بحرانی | key rotation دوره‌ای + 2FA |

## ۱۵. هم‌راستایی با سایر ADRها و اصول

### با ADR-001 (Django)
- Gunicorn برای production (نه runserver)
- collectstatic برای static files
- migrate برای migrations

### با ADR-002 (Database)
- PostgreSQL 16 (آخرین نسخه پایدار)
- Volume persistence برای داده‌ها
- بکاپ روزانه

### با ADR-007 (Frontend)
- بدون نیاز به Node.js در production
- Static files از static_volume serve می‌شوند
- Media files از media_volume serve می‌شوند

### با اصل ۹ (مستقل از خارج)
- VPS ایرانی
- بدون AWS/Azure/GCP
- Let's Encrypt برای SSL (رایگان، اما غیرایرانی - قابل قبول چون فقط گواهی است)
- جایگزین ایرانی برای Let's Encrypt در فاز ۶ ارزیابی می‌شود

### با اصل ۱۰ (کنترل کامل ادمین)
- لاگ‌های قابل دسترسی
- بکاپ‌های قابل مدیریت
- دستورات ساده برای اپراتور

### با D-022 (خودمیزبانی)
- کاملاً self-hosted
- کنترل کامل روی infrastructure
- بدون وابستگی به PaaS

## ۱۶. ارجاعات

### تصمیمات و اسناد
- **ADR-001:** Django 5.2 LTS
- **ADR-002:** PostgreSQL (دیتابیس)
- **ADR-003:** API Strategy
- **ADR-007:** Frontend Stack
- **D-022:** خودمیزبانی کامل
- **CENTRAL-STORY.md:** داستان محوری

### ابزارها و تکنولوژی‌ها
- **Docker:** https://docs.docker.com
- **Docker Compose:** https://docs.docker.com/compose
- **Nginx:** https://nginx.org
- **PostgreSQL:** https://www.postgresql.org
- **Let's Encrypt:** https://letsencrypt.org
- **GitHub Actions:** https://docs.github.com/en/actions

### پچ‌های تکمیلی
- **PHASE4-FINAL-PATCHES.md:** ۴ اصلاحیه تکمیلی (Media WebP, Cart Validation API, Log Rotation, Trust Badges Fixtures)

### استانداردها
- **12-Factor App:** https://12factor.net
- **OWASP Docker Security Cheat Sheet**
- **NIST SP 800-190:** Application Container Security Guide


---

## تأیید نهایی ناظر

**تاریخ تصویب:** ۱۴۰۵/۰۵/۱۷
**Commit راستی‌آزمایی:** f7c9e8e

با تصویب این سند، **تمام ۴ مغایرت گزارش ممیزی اولیه** رسماً بسته شدند:
۱. خلاء ADR استقرار و زیرساخت → ADR-008 ✅
۲. اینترنت ضعیف → متمم ADR-003 ✅
۳. حریم خصوصی/مالیاتی → ADR-006 v2 ✅
۴. قفل ترتیبی → رفع شد ✅

این سند اکنون **مصوب** است و زیرساخت استقرار برای MVP ریهان قطعی شد.
