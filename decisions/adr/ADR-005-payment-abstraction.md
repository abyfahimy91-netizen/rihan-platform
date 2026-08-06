# ADR-005: لایه انتزاع پرداخت (Payment Abstraction)

| شناسه | ADR-005 |
| --- | --- |
| عنوان | لایه انتزاع پرداخت (Payment Abstraction) |
| وضعیت | **Proposed v2** — اصلاح‌شده بر اساس ۲ نکته اجباری + ۴ نکته توصیه‌ای مشاور |
| تاریخ | ۲۰۲۶-۰۸-۰۶ |
| تصمیم‌گیرنده | عبدالحسین فهیمی (بنیان‌گذار) + تحلیلگر فنی |
| مرتبط | ADR-001, ADR-002, ADR-003, D-003, D-067, M11 |

> این سند پیش‌نویس است. تا تصویب مشاور، کد Gateway یا Service پرداخت تولید نشود.

## ۱. هدف و مرز

**هدف:** طراحی لایه انتزاع پرداخت برای ریهان که:
- در MVP از کارت‌به‌کارت (D-067) پشتیبانی کند
- برای درگاه‌های آنلاین آینده آماده باشد (بدون بازنویسی)
- منطق پرداخت از Order و User جدا باشد (Single Responsibility)
- امکان تست و mock ساده در لایه Service فراهم شود

**مرز:**
- Interface مشترک PaymentGateway (Strategy Pattern)
- پیاده‌سازی CardToCardGateway برای MVP
- وضعیت‌های Payment و اتصال به Order
- نقش ادمین در تأیید/رد پرداخت
- حساب مقصد پرداخت از تنظیمات سیستم (نه تکرار در هر Payment)

**Out of Scope صریح:**
- اتصال واقعی به درگاه‌های آنلاین (زرین‌پال، آیدی‌پی، و...)
- کیف پول (Wallet)
- پرداخت اقساطی (Installment)
- پرداخت ارزی (Multi-currency)
- سیستم تسهیم خودکار با تأمین‌کننده
- Refund خودکار

## ۲. اصل انتزاع (Strategy Pattern)

### الگوی طراحی
**Strategy Pattern** برای انتخاب Gateway در runtime:
- یک Interface مشترک (PaymentGatewayProtocol)
- چند پیاده‌سازی مستقل (CardToCard, ZarinPal, IDPay, ...)
- Factory یا Dependency Injection برای انتخاب Gateway
- Service Layer فقط با Interface کار می‌کند، نه پیاده‌سازی خاص

### مزایا
- افزودن Gateway جدید بدون تغییر OrderService یا UserService
- تست آسان با mock gateway
- جداسازی کامل منطق پرداخت از منطق کسب‌وکار
- آماده برای feature flag: هر Gateway می‌تواند با Flag جدا فعال/غیرفعال شود (هم‌راستا با ADR-004)

### ساختار کلی
- core/payments/gateways.py — Interface + Base class
- core/payments/card_to_card.py — پیاده‌سازی MVP
- core/payments/factory.py — انتخاب Gateway بر اساس تنظیمات
- core/payments/service.py — PaymentService (منطق مشترک)


## ۳. Interface مشترک PaymentGateway

### PaymentGatewayProtocol (قرارداد)

هر Gateway باید این متدها را پیاده‌سازی کند:

**۱. initiate_payment(order, amount, context)**
- ورودی: سفارش، مبلغ، context (مثل session یا device)
- خروجی: PaymentAttempt با وضعیت pending و جزئیات برای مشتری
- برای CardToCard: برمی‌گرداند شماره کارت مقصد، مبلغ، نام دارنده
- برای درگاه آنلاین (آینده): برمی‌گرداند URL redirect

**۲. verify_payment(payment_attempt, evidence)**
- ورودی: تلاش پرداخت، evidence (مثل ۴ رقم + زمان + رسید)
- خروجی: وضعیت verified/rejected + دلیل
- **برای CardToCard در MVP:** این متد «ثبت evidence + انتظار تأیید ادمین» است، نه verify خودکار بانکی. verify واقعی توسط ادمین در پنل انجام می‌شود (manual review).
- برای درگاه آنلاین (آینده): بررسی خودکار callback از درگاه

**۳. refund_payment(payment, reason)**
- ورودی: پرداخت، دلیل
- خروجی: وضعیت refund_requested/completed
- برای CardToCard: ثبت درخواست مرجوعی دستی
- برای درگاه آنلاین: فراخوانی API refund

**۴. get_status(payment)**
- ورودی: پرداخت
- خروجی: وضعیت فعلی از منبع حقیقت
- برای CardToCard: از دیتابیس (منبع حقیقت خود سیستم است)
- برای درگاه آنلاین: فراخوانی API درگاه

## ۴. پیاده‌سازی MVP: CardToCardGateway

### ویژگی‌های کلیدی
- حساب مقصد از تنظیمات: شماره کارت، نام دارنده، بانک از settings یا SiteConfig خوانده می‌شود
- evidence طبق D-067: sender_card_last4، transfer_time، amount، receipt_image (اختیاری)
- بدون اتصال خارجی: تمام منطق در سرور ریهان است

### وضعیت‌های Payment (یکدست با ADR-002)

**۴ وضعیت قطعی در MVP:**
- pending → confirmed
- pending → rejected
- confirmed → refunded

| وضعیت | توضیح | مجاز توسط |
| --- | --- | --- |
| pending | مشتری evidence ثبت کرده، در انتظار تأیید ادمین | سیستم (خودکار) |
| confirmed | ادمین تأیید کرده، پرداخت موفق | ادمین (admin/family_admin) |
| rejected | ادمین رد کرده، نیاز به تلاش مجدد | ادمین |
| refunded | پرداخت تأییدشده برگشت داده شده | ادمین |

**نکته:** وضعیت completed حذف شد (مبهم بود). Payment تأییدشده = confirmed (نیاز به وضعیت جداگانه ندارد).

### جریان کامل در MVP

**۱. ثبت سفارش:** Order ایجاد می‌شود با status=pending، هیچ Payment ایجاد نمی‌شود

**۲. ثبت اطلاعات کارت‌به‌کارت:**
- مشتری به صفحه پرداخت هدایت می‌شود
- شماره کارت مقصد از CardToCardGateway.initiate_payment() خوانده می‌شود
- مشتری کارت‌به‌کارت می‌زند
- فرم را با evidence (۴ رقم + زمان + رسید اختیاری) submit می‌کند
- POST /api/v1/orders/{id}/payments/ فراخوانی می‌شود
- Payment جدید با status=pending ایجاد می‌شود

**۳. تأیید توسط ادمین:**
- ادمین به /api/v1/admin/payments/?status=pending می‌رود (مسیر یکدست با ADR-003)
- لیست پرداخت‌های در انتظار + evidence نمایش داده می‌شود
- ادمین با SMS بانکی خودش چک می‌کند
- اگر OK: کلیک روی تأیید → Payment.status = confirmed
  - Order.payment_status = confirmed
  - Order.status = confirmed
  - InventoryTransaction با change_type=sale ایجاد می‌شود
- اگر Not OK: کلیک روی رد + دلیل → Payment.status = rejected
  - مشتری notification می‌گیرد
  - می‌تواند تلاش مجدد کند (چند تلاش مجاز طبق D-067)

## ۵. تنظیمات سیستمی حساب مقصد

### ساختار تنظیمات
در settings.py یا SiteConfig (جدول مجزا در آینده):

PAYMENT_CONFIG = {
    "card_to_card": {
        "destination_card_number": "6037-9911-xxxx-xxxx",
        "destination_card_holder": "عبدالحسین فهیمی",
        "destination_bank": "بانک ملی",
        "min_amount": 10000,
        "max_amount": 50000000,
        "receipt_required_above": 5000000,
    }
}

### منطق dynamic (هم‌راستا با D-067)
- **پیش‌فرض (D-067):** receipt_image اختیاری است (NULL مجاز)
- **آستانه receipt_required_above:** اگر تنظیم شده و مبلغ سفارش بیشتر باشد، receipt_image اجباری می‌شود (override برای مبالغ بالا)
- این منطق در آینده از طریق پنل ادمین قابل تغییر است
- مثال: اگر receipt_required_above = ۵,۰۰۰,۰۰۰ تومان، سفارش‌های بالای این مبلغ رسید اجباری دارند

### مزیت
- شماره کارت مقصد در کد hardcode نمی‌شود
- تغییر حساب بدون redeploy ممکن است
- امنیت بهتر (حساب در environment variable یا encrypted config)

## ۶. اتصال Payment با Order

### هم‌راستایی با ADR-002
- هر Order می‌تواند چندین Payment داشته باشد (چند تلاش طبق D-067)
- Order.payment_status از آخرین Payment محاسبه می‌شود
- اگر آخرین Payment = confirmed → payment_status = confirmed
- اگر آخرین Payment = rejected → payment_status = pending (آماده تلاش مجدد)
- اگر هیچ Payment نباشد → payment_status = pending

### قوانین وضعیت سفارش
- Order.status فقط پس از payment_status = confirmed به confirmed تغییر می‌کند
- اگر payment_status = rejected باشد، Order.status در pending می‌ماند
- اگر Order.cancelled شود، تمام Paymentهای pending به rejected تغییر می‌کنند

### قوانین موجودی (سه‌مرحله‌ای - هم‌راستا با ADR-002)

**مرحله ۱: ثبت سفارش (Reservation)**
- هنگام ایجاد Order با status=pending، reserved_quantity افزایش می‌یابد
- InventoryTransaction با change_type=reservation ایجاد می‌شود
- available_quantity = quantity - reserved_quantity کاهش می‌یابد
- این کار از oversell جلوگیری می‌کند

**مرحله ۲: تأیید پرداخت (Finalize)**
- هنگام Payment.status = confirmed، Order.status = confirmed می‌شود
- InventoryTransaction با change_type=sale ایجاد می‌شود
- quantity کاهش می‌یابد و reserved_quantity آزاد می‌شود
- موجودی فیزیکی به‌روز می‌شود

**مرحله ۳: لغو/رد نهایی (Release)**
- هنگام لغو Order یا رد نهایی پرداخت، reserved_quantity آزاد می‌شود
- InventoryTransaction با change_type=release ایجاد می‌شود
- available_quantity افزایش می‌یابد (موجودی برای فروش مجدد آماده می‌شود)

**قانون کلیدی:** Payment به تنهایی موجودی را تغییر نمی‌دهد — فقط وضعیت Order است که InventoryTransaction را trigger می‌کند. این هم‌راستایی کامل با ADR-002 است.

## ۷. نقش ادمین در تأیید/رد

### مجوزها (هم‌راستا با ADR-002 و ADR-004)
- admin: تأیید/رد هر پرداخت
- family_admin: تأیید/رد هر پرداخت
- family_member: فقط مشاهده پرداخت‌های تأییدشده
- observer: فقط مشاهده
- supplier: فقط مشاهده پرداخت‌های مرتبط با محصولات خودش
- customer: فقط مشاهده پرداخت‌های خودش

### عملیات‌های حساس
- تأیید پرداخت بالای ۵ میلیون تومان: تأیید دو مرحله‌ای
- رد پرداخت: باید دلیل (rejection_reason) ثبت شود
- refund: تأیید دو مرحله‌ای + ثبت در AuditLog

### UI ادمین
- لیست پرداخت‌های در انتظار با evidence
- فیلتر بر اساس: وضعیت، مبلغ، تاریخ، تأمین‌کننده
- نمایش thumbnail رسید (اگر آپلود شده)
- دکمه‌های سریع: تأیید، رد (با modal دلیل)، مشاهده جزئیات

## ۸. توسعه آینده (درگاه‌های آنلاین)

### مسیر افزودن درگاه جدید
وقتی در آینده نیاز به درگاه آنلاین شد:

۱. ساخت Gateway جدید:
- core/payments/zarinpal.py پیاده‌سازی ZarinPalGateway
- پیاده‌سازی تمام متدهای PaymentGatewayProtocol

۲. افزودن به تنظیمات:
- merchant_id, callback_url, sandbox در PAYMENT_CONFIG

۳. افزودن به GatewayFactory:
- Factory بر اساس setting.active_gateways انتخاب می‌کند

۴. افزودن به UI:
- مشتری گزینه‌های مختلف پرداخت را می‌بیند

### سازگاری با مدل داده فعلی
- جدول Payment فیلد payment_method دارد (ENUM)
- افزودن درگاه جدید = افزودن مقدار جدید به ENUM
- فیلدهای D-067 برای درگاه آنلاین NULL خواهند بود
- فیلدهای جدید (authority, ref_id) در future migration

### اصل کلیدی
- Service Layer دست نمی‌خورد
- فقط Gateway جدید + Factory update
- Order و User هیچ تغییری نمی‌کنند

## ۹. تست‌پذیری

### Mock Gateway برای تست
- MockGateway: همیشه confirmed برمی‌گرداند
- RejectingGateway: برای تست سناریوهای خطا
- تست‌های unit روی PaymentService بدون دیتابیس واقعی

### Coverage مورد انتظار (هدف آرمانی، نه تعهد سخت فاز ۴)
- PaymentService: هدف ۱۰۰٪ coverage
- CardToCardGateway: هدف ۹۰٪ coverage
- GatewayFactory: هدف ۱۰۰٪ coverage
- **نکته:** این اهداف در فاز ۵ (توسعه) پیگیری می‌شوند، نه در فاز ۴ (برنامه‌ریزی). کیفیت تست مهم‌تر از درصد coverage است.

## ۱۰. Out of Scope صریح

### در MVP انجام نمی‌شود
- اتصال واقعی به درگاه‌های آنلاین (زرین‌پال، آیدی‌پی)
- کیف پول (Wallet)
- پرداخت اقساطی (Installment)
- پرداخت ارزی (Multi-currency)
- تسهیم خودکار با تأمین‌کننده
- Refund خودکار
- Subscription و پرداخت تکرارشونده
- Crypto payment
- Buy Now Pay Later (BNPL)

### مرز دقیق MVP
- فقط کارت‌به‌کارت به یک حساب مقصد
- تأیید دستی توسط ادمین
- بدون هیچ integration خارجی

## ۱۱. هم‌راستایی با سایر اسناد

- ADR-002: موجودیت Payment با فیلدهای D-067
- ADR-003: Payment endpoints تعریف‌شده
- ADR-004: payment ماژول سیستمی (M11)
- D-003: شروع با کارت‌به‌کارت
- D-067: سه evidence اجباری + رسید اختیاری + چند تلاش
- D-047: مدیریت خطا و بازیابی
- MVP-SCOPE.md: M11 (پرداخت)

## ۱۲. ارجاعات

- ADR-001, ADR-002, ADR-003, ADR-004
- D-003, D-067, D-047
- MVP-SCOPE.md
- ARCHITECTURE-PRINCIPLES.md: Strategy Pattern
