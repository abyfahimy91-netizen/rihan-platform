# راهنمای طراحی راست‌به‌چپ ریهان (RTL Guide)

**نسخه:** 1.0
**تاریخ:** 2026-08-05
**وضعیت:** تأییدشده (D-064)

> ریهان از روز اول برای RTL طراحی می‌شود.
> هر AI یا توسعه‌دهنده MUST این را رعایت کند.

---

## ۱. اصول پایه

### چه چیزی mirror می‌شود؟

| عنصر | Mirror؟ |
|------|---------|
| متن | ✅ |
| Layout کلی | ✅ |
| Progress bar | ✅ |
| Breadcrumbs | ✅ |
| آیکون directional | ✅ |
| Icons جهانی | ❌ |
| اعداد | ❌ |
| فرمول | ❌ |
| کد | ❌ |

---

## ۲. Typography

### فونت
**وزیرمتن** (D-042)
- Regular: متن عادی
- Medium: عناوین کوچک
- Bold: عناوین اصلی، دکمه‌ها
- Black: عناوین بزرگ

### Line Height
| نوع | Line Height |
|-----|-------------|
| متن عادی | ۱.۸ |
| عناوین | ۱.۴ |
| دکمه‌ها | ۱.۲ |

### اعداد
| حالت | استفاده | مثال |
|------|---------|------|
| فارسی | UI، متن، قیمت | ۲۵۰,۰۰۰ تومان |
| انگلیسی | URL، کد، فرمول | /product/500g |

**قوانین:**
- قیمت: همیشه فارسی + "تومان"
- تاریخ: شمسی فارسی (۱۴۰۵/۰۵/۱۴)
- شماره تلفن: ۰۹۱۲۳۴۵۶۷۸۹ (LTR)
- کد پستی: ۱۲۳۴۵۶۷۸۹۰ (LTR)

---

## ۳. Navigation

### Breadcrumbs
خانه > کاتالوگ > خشکبار > گردو
- از راست شروع
- جداکننده: >
- در موبایل: فقط ۲ سطح آخر

### Progress Bar
[✓ موبایل] ─── [● آدرس] ─── [○ ارسال]
- از راست به چپ پیشرفت

### آیکون‌ها

| نوع | Mirror؟ |
|-----|---------|
| Arrow | ✅ |
| Play/Pause | ❌ |
| Check | ❌ |
| Search | ❌ |
| Cart | ❌ |
| User | ❌ |
| Home | ❌ |

---

## ۴. Forms

### جهت Label و Input
[نام]  [________________]
- Label در راست
- Input از راست پر شود

### شماره موبایل
[۰۹۱۲۳۴۵۶۷۸۹]  [شماره موبایل]
LTR حتی در RTL

### Checkbox و Radio
[✓] قوانین را می‌پذیرم
Checkbox در راست

### دکمه‌های فرم
[انصراف]  [ثبت]
  (چپ)     (راست)
دکمه اصلی در راست

---

## ۵. Modal و Popup

### Modal
- Close button: بالا-چپ
- دکمه‌ها: انصراف (چپ)، تأیید (راست)

### Drawer
- Mini cart: از سمت راست
- Filter: از سمت راست

---

## ۶. CSS Guidelines

### Logical Properties

| غلط | درست |
|-----|------|
| margin-left | margin-inline-start |
| margin-right | margin-inline-end |
| padding-left | padding-inline-start |
| text-align: left | text-align: start |

### Flexbox و Grid
خودکار با RTL کار می‌کنند.

---

## ۷. Accessibility

- Tab order: از راست به چپ
- lang="fa" dir="rtl"
- Focus indicator واضح

---

## ۸. چک‌لیست RTL

- [ ] direction: rtl؟
- [ ] فونت وزیرمتن؟
- [ ] Line height ۱.۸؟
- [ ] آیکون directional mirror؟
- [ ] آیکون جهانی بدون تغییر؟
- [ ] Progress bar از راست؟
- [ ] Breadcrumbs از راست؟
- [ ] Labels در راست؟
- [ ] دکمه اصلی در راست؟
- [ ] Modal close بالا-چپ؟
- [ ] Logical properties؟
- [ ] Keyboard navigation؟
- [ ] lang="fa" dir="rtl"؟

---

## ارجاعات

- docs/VISION-GUARD.md
- docs/UX-DETAILS.md
- Smashing Magazine - RTL Mobile
- Muz.li - RTL Web Design
- Arabic-First UX Research 2026