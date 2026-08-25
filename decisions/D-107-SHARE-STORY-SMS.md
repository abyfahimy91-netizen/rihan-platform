# D-107 — برند واحد Rihan + استوری تولیدی + لینک کوتاه اشتراک‌گذاری

**تاریخ:** 1405/06/03 | **کامیت:** b35f3b6

## تصمیم‌ها
1. **برند لاتین:** همه متون خروجی ماشین (پیامک‌ها، دستور ارسال، کپشن، استوری) از `SiteSettings.brand_name_latin` (پیش‌فرض `Rihan`) می‌خوانند.
2. **قالب پیامک ادمین‌محور:** `sms_text_customer_shipped` / `sms_text_supplier_assign` با متغیرهای `{order_number} {carrier} {tracking_code} {link} {items} {brand}`؛ خالی=پیش‌فرض، قالب خراب=پیش‌فرض امن (render_sms_template با try/except).
3. **استوری اینستاگرام با محتوا:** مودال + Canvas 1080×1920 (گرادیان برند، قاب طلایی #C9A961، عکس محصول cover-fit، عنوان wrap شده، پیل قیمت) + چهار اکشن: ارسال مستقیم (WebShare Level2 با فایل)، ذخیره PNG، کپی کپشن/هشتگ، باز کردن اینستاگرام. محدودیت iOS: پیش‌پرکردن استوری از وب ممکن نیست → این بهترین جریان ممکن است.
4. **متن اشتراک‌گذاری:** `share_message_text` (پیش‌فرض: «✨ یه انتخاب خاص برات پیدا کردم؛ یه نگاه بنداز، ارزشش رو داره!») + `share_hashtags`؛ سرور caption کامل (متن+نام محصول+لینک کوتاه+هشتگ) می‌سازد و JS از آن استفاده می‌کند.
5. **لینک کوتاه:** مدل `catalog.ShortLink` (کد ۸ نویسه‌ای بدون حروف گنگ) + مسیر `/p/<code>/` → 302 به صفحه محصول. مثال زنده: rihan360.ir/p/2kmTyMcd
6. **پیش‌نمایش پیام‌رسان‌ها:** og:image مطلق با cache-buster `?v=<timestamp>` + twitter:card summary_large_image در product_detail.

## فایل‌ها
pages/models.py+0006, pages/admin.py, order/fulfillment.py, catalog/models.py+0009(ShortLink), catalog/views.py, urls.py, templates/catalog/product_detail.html

## دام‌ها
- scp چندفایلی دوباره ناقص نشست (cat_views/cat_urls روی سرور قدیمی ماندند و تست 404 داد) → بعد از هر پوش، md5 مقایسه شود.
- تست redirect: Location اسلاگ یونیکد percent-encoded است — با «شامل products/slug» چک شود نه مساوی.

## وضعیت
۵۴ تست زیرمجموعه سبز (۹ جدید). زنده: og tags ✓، /p/code 302 ✓، share JSON ✓.
