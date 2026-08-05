# ماتریس ردیابی ریهان (Traceability Matrix)

**نسخه:** 1.0
**تاریخ:** 2026-08-04
**وضعیت:** تأییدشده (D-061)
**هدف:** ردیابی کامل از Vision تا Acceptance Criteria

> هر تصمیم محصولی در ریهان باید به یک اصل بنیادین متصل باشد.
> این ماتریس به AIهای آینده کمک می‌کند بفهمند هر قابلیت از کجا منشأ گرفته است.

---

## ساختار ردیابی

Vision Guard (هویت)
    ↓
Product Principles (اصول محصول)
    ↓
Product Thesis (چرایی وجود)
    ↓
Selection Philosophy (فلسفه انتخاب)
    ↓
MVP Scope (محدوده محصول)
    ↓
User Stories (داستان‌های کاربر)
    ↓
Acceptance Criteria (معیارهای پذیرش)

---

## جدول نمونه ردیابی (برای قابلیت‌های کلیدی)

### ردیابی ۱: چک‌لیست اعتماد صفحه محصول

| سطح | عنصر | شناسه |
|------|------|-------|
| **Vision Guard** | اصل ۶: شفافیت قبل از فروش | VISION-GUARD.md |
| **Vision Guard** | اصل ۲: محصول بدون راستی‌آزمایی منتشر نمی‌شود | VISION-GUARD.md |
| **Product Principles** | اصل ۴: شفافیت قبل از فروش | PRODUCT-PRINCIPLES.md |
| **Product Principles** | اصل ۷: کرامت قبل از تبدیل | PRODUCT-PRINCIPLES.md |
| **Product Thesis** | مکانیسم ۲: شفافیت رادیکال | PRODUCT-THESIS.md |
| **Selection Philosophy** | ستون ۳: شفافیت (Transparency) | SELECTION-PHILOSOPHY.md |
| **MVP Scope** | ماژول M1: کاتالوگ و جستجو | MVP-SCOPE.md |
| **User Story** | US-047: چک‌لیست اعتماد صفحه محصول | USER-STORIES.md |
| **Acceptance Criteria** | ۱۱ معیار پذیرش (داستان مبدأ، شفافیت، عکس واقعی، ...) | USER-STORIES.md |

### ردیابی ۲: احراز هویت Passwordless

| سطح | عنصر | شناسه |
|------|------|-------|
| **Vision Guard** | اصل ۵: کرامت مشتری حفظ می‌شود | VISION-GUARD.md |
| **Product Principles** | اصل ۷: کرامت قبل از تبدیل | PRODUCT-PRINCIPLES.md |
| **Product Thesis** | فرضیه ۴: پرداخت کارت‌به‌کارت هنوز قابل قبول است | PRODUCT-THESIS.md |
| **MVP Scope** | ماژول M10: احراز هویت مشتری (Passwordless) | MVP-SCOPE.md |
| **User Story** | US-011: ورود / ثبت‌نام مشتری (Passwordless) | USER-STORIES.md |
| **Decision** | D-040: مدل نهایی احراز هویت | DECISIONS.md |
| **Acceptance Criteria** | ورود در کمتر از ۳۰ ثانیه، Device Remembering ۳۰ روزه | USER-STORIES.md |

### ردیابی ۳: مدیریت موجودی

| سطح | عنصر | شناسه |
|------|------|-------|
| **Vision Guard** | اصل ۱: اعتماد هرگز قربانی رشد نمی‌شود | VISION-GUARD.md |
| **Vision Guard** | اصل ۲: محصول بدون راستی‌آزمایی منتشر نمی‌شود | VISION-GUARD.md |
| **Product Principles** | اصل ۲: کیفیت قبل از تنوع | PRODUCT-PRINCIPLES.md |
| **Selection Philosophy** | ستون ۵: پایداری (Sustainability) | SELECTION-PHILOSOPHY.md |
| **MVP Scope** | ماژول M1: کاتالوگ و جستجو | MVP-SCOPE.md |
| **User Story** | US-044: مدیریت موجودی محصولات | USER-STORIES.md |
| **Decision** | D-045: جریان موجودی ریهان | DECISIONS.md |
| **Acceptance Criteria** | رزرو ۲۴ ساعته، هشدار ۲۰٪، لاگ دائمی | USER-STORIES.md |

### ردیابی ۴: پرداخت کارت‌به‌کارت

| سطح | عنصر | شناسه |
|------|------|-------|
| **Vision Guard** | اصل ۶: شفافیت قبل از فروش | VISION-GUARD.md |
| **Vision Guard** | اصل ۸: معماری باز برای آینده | VISION-GUARD.md |
| **Product Principles** | اصل ۴: شفافیت قبل از فروش | PRODUCT-PRINCIPLES.md |
| **Product Principles** | اصل ۶: تدریج قبل از انفجار | PRODUCT-PRINCIPLES.md |
| **Product Thesis** | فرضیه ۴: پرداخت کارت‌به‌کارت هنوز قابل قبول است | PRODUCT-THESIS.md |
| **Architecture Principles** | الگوی ۳: Payment Abstraction Layer | ARCHITECTURE-PRINCIPLES.md |
| **MVP Scope** | ماژول M11: پرداخت کارت‌به‌کارت | MVP-SCOPE.md |
| **User Story** | US-007: پرداخت کارت‌به‌کارت | USER-STORIES.md |
| **Decision** | D-003: شروع با کارت‌به‌کارت | DECISIONS.md |
| **Acceptance Criteria** | نمایش شماره کارت، آپلود رسید، تأیید ادمین | USER-STORIES.md |

### ردیابی ۵: داستان محصول (Origin Story)

| سطح | عنصر | شناسه |
|------|------|-------|
| **Vision Guard** | اصل ۳: داستان جعلی منتشر نمی‌شود | VISION-GUARD.md |
| **Product Principles** | اصل ۳: داستان قبل از مشخصات | PRODUCT-PRINCIPLES.md |
| **Product Thesis** | مکانیسم ۳: داستان واقعی (Authentic Story) | PRODUCT-THESIS.md |
| **Selection Philosophy** | ستون ۱: اصالت (Authenticity) | SELECTION-PHILOSOPHY.md |
| **MVP Scope** | ماژول M1: کاتالوگ و جستجو | MVP-SCOPE.md |
| **User Story** | US-004: مشاهده جزئیات محصول | USER-STORIES.md |
| **Decision** | D-049: سیاست حداقل محتوای اجباری محصول | DECISIONS.md |
| **Acceptance Criteria** | داستان محصول ۲-۴ جمله واقعی، بدون نام شخصی | USER-STORIES.md |

---

## قانون ردیابی (Traceability Rule)

**برای هر قابلیت جدید، قبل از کدنویسی باید این چک‌لیست طی شود:**

- [ ] حداقل یک اصل از Vision Guard به آن متصل است
- [ ] حداقل یک اصل از Product Principles آن را تأیید می‌کند
- [ ] با Product Thesis سازگار است
- [ ] با Selection Philosophy هم‌راستا است
- [ ] در MVP Scope تعریف شده است
- [ ] یک یا چند User Story برای آن نوشته شده
- [ ] Acceptance Criteria قابل اندازه‌گیری دارد

اگر هر یک از این موارد ناقص باشد، قابلیت **قبل از کدنویسی** باید بازنگری شود.

---

## استفاده توسط AIهای آینده

**اگر شما یک AI جدید هستید که وارد این پروژه می‌شوید:**

1. وقتی می‌خواهید یک قابلیت جدید اضافه کنید، ابتدا این ماتریس را بررسی کنید
2. ببینید قابلیت‌های مشابه از کدام اصول منشأ گرفته‌اند
3. برای قابلیت جدید، همان مسیر ردیابی را طی کنید
4. اگر نمی‌توانید قابلیت را به یک اصل بنیادین متصل کنید، **با بنیان‌گذار مشورت کنید**

**مثال:** اگر می‌خواهید ماژول "سیستم امتیازدهی وفاداری" اضافه کنید:
- بررسی کنید: آیا با Vision Guard سازگار است؟
- بررسی کنید: آیا با Product Thesis سازگار است؟
- اگر پاسخ منفی است → قابلیت رد می‌شود

---

## آمار فعلی پروژه

| نوع عنصر | تعداد |
|----------|-------|
| اصول Vision Guard | ۸ |
| اصول Product Principles | ۷ |
| اصول Architecture Principles | ۶ |
| سؤالات Product Thesis | ۶ |
| ستون‌های Selection Philosophy | ۵ |
| ماژول‌های MVP | ۱۴ |
| User Stories | ۴۷ |
| Decisions ثبت‌شده | ۶۱ |

---

## ارجاعات

- docs/VISION-GUARD.md — ۸ اصل هویتی
- docs/PRODUCT-PRINCIPLES.md — ۷ اصل محصول
- docs/ARCHITECTURE-PRINCIPLES.md — ۶ الگوی معماری
- docs/PRODUCT-THESIS.md — ۶ سؤال بنیادین
- docs/SELECTION-PHILOSOPHY.md — ۵ ستون انتخاب
- docs/MVP-SCOPE.md — ۱۴ ماژول MVP
- docs/USER-STORIES.md — ۴۷ داستان کاربر
- decisions/DECISIONS.md — تمام تصمیمات
