# ADR-002: معماری دیتابیس و مدل داده MVP

| شناسه | ADR-002 |
| --- | --- |
| عنوان | معماری دیتابیس و مدل داده MVP |
| وضعیت | **Proposed v3** — اصلاح‌شده بر اساس ۵ نکته مشاور + Guest Checkout |
| تاریخ | ۲۰۲۶-۰۸-۰۶ |
| مرتبط | ADR-001, D-040, D-045, D-046, D-067, D-068 |

> این سند پیش‌نویس است. تا تصویب مشاور، migration یا کد مدل تولید نشود.

## ۱. هدف و مرز

**هدف:** مدل داده MVP با ۱۴ ماژول، سازگار با PostgreSQL و سرور ۲GB.

**مرز:**
- مدل داده MVP و روابط کلیدی
- شاخص‌گذاری اولیه
- تصمیم‌های مدل‌سازی

**Out of Scope:**
- Celery / Event bus
- Loyalty / وفاداری
- Mobile app schema
- Sharding / Microservice DB
- بهینه‌سازی زودرس

## ۲. موجودیت‌ها

### ۲.۱ Role (جدید - RBAC واقعی)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| name | VARCHAR(50) UNIQUE | نام نقش |
| code | VARCHAR(50) UNIQUE | کد فنی نقش |
| description | TEXT | توضیح نقش |
| permissions | JSONB | لیست مجوزها |
| is_system | BOOLEAN | نقش سیستمی (غیرقابل حذف) |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

**نقش‌های اولیه MVP:**
- customer, admin, family_admin, family_member, observer, supplier

### ۲.۲ User

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| phone | VARCHAR(11) UNIQUE | شماره موبایل |
| password | VARCHAR(255) NULL | رمز اختیاری bcrypt |
| first_name | VARCHAR(50) | نام |
| last_name | VARCHAR(50) | نام خانوادگی |
| is_active | BOOLEAN | فعال |
| created_at | TIMESTAMP | ثبت‌نام |
| updated_at | TIMESTAMP | به‌روزرسانی |
| deleted_at | TIMESTAMP NULL | Soft delete |

**نکته مهم:** فیلد role حذف شد. نقش از طریق UserRole مشخص می‌شود.

### ۲.۳ UserRole (جدید - Many-to-Many)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| user_id | UUID FK->User | کاربر |
| role_id | UUID FK->Role | نقش |
| granted_at | TIMESTAMP | تاریخ اعطا |
| granted_by | UUID FK->User NULL | اعطاکننده |
| is_primary | BOOLEAN | نقش اصلی کاربر |
| created_at | TIMESTAMP | ایجاد |

**قیود:** UNIQUE(user_id, role_id)

**قانون MVP:** در MVP هر کاربر یک نقش اصلی دارد (is_primary = true). این معماری آماده ارتقا به چند-نقشی در آینده است.

### ۲.۴ Supplier

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| user_id | UUID FK->User | کاربر مرتبط |
| name | VARCHAR(100) | نام |
| phone | VARCHAR(11) | تماس |
| city | VARCHAR(50) | شهر |
| province | VARCHAR(50) | استان |
| notes | TEXT | یادداشت |
| is_active | BOOLEAN | فعال |
| created_at | TIMESTAMP | ثبت |
| updated_at | TIMESTAMP | به‌روزرسانی |

### ۲.۵ Product

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| slug | VARCHAR(100) UNIQUE | URL name |
| name | VARCHAR(150) | نام محصول |
| category | VARCHAR(50) | دسته‌بندی |
| supplier_id | UUID FK->Supplier | تأمین‌کننده |
| base_price | DECIMAL(10,2) | قیمت پایه |
| shipping_cost | DECIMAL(10,2) | سهم ارسال |
| margin_percent | DECIMAL(5,2) | حاشیه سود |
| final_price | DECIMAL(10,2) | قیمت نهایی |
| unit | VARCHAR(20) | واحد |
| short_description | TEXT | توضیح کوتاه |
| origin_story | TEXT | داستان مبدأ (اجباری) |
| long_description | TEXT | توضیح کامل |
| images | JSONB | لیست تصاویر |
| metadata | JSONB | اطلاعات منعطف |
| status | ENUM | draft/active/inactive/out_of_stock |
| is_featured | BOOLEAN | ویژه |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |
| deleted_at | TIMESTAMP NULL | Soft delete |

### ۲.۶ Inventory (با available_quantity محاسبه‌ای)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| product_id | UUID FK->Product UNIQUE | محصول |
| quantity | DECIMAL(10,2) | موجود فیزیکی (منبع حقیقت) |
| unit | VARCHAR(20) | واحد |
| low_stock_threshold | DECIMAL(10,2) | آستانه هشدار |
| reserved_quantity | DECIMAL(10,2) | رزرو شده (منبع حقیقت) |
| available_quantity | DECIMAL GENERATED | quantity - reserved_quantity |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

**تعریف فنی (PostgreSQL 12+):**
available_quantity DECIMAL(10,2) GENERATED ALWAYS AS (quantity - reserved_quantity) STORED

**قید:** UNIQUE(product_id) → رابطه Product 1:1 Inventory (صریح)

### ۲.۷ InventoryTransaction (تاریخچه موجودی - D-045)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| inventory_id | UUID FK->Inventory | موجودی |
| change_type | ENUM | purchase/sale/return/adjustment/reservation/release |
| quantity_change | DECIMAL(10,2) | تغییر |
| reason | TEXT | دلیل |
| reference_type | VARCHAR(50) | نوع مرجع |
| reference_id | UUID | شناسه مرجع |
| created_at | TIMESTAMP | تاریخ |
| created_by | UUID FK->User | کاربر |

### ۲.۸ Cart (جدید - سبد خرید)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه سبد |
| user_id | UUID FK->User NULL | کاربر (NULL برای مهمان) |
| session_key | VARCHAR(100) NULL | کلید session برای مهمان |
| status | ENUM | active/abandoned/converted |
| expires_at | TIMESTAMP | تاریخ انقضا (۷ روز) |
| abandoned_at | TIMESTAMP NULL | تاریخ رها شدن |
| recovered_at | TIMESTAMP NULL | تاریخ بازیابی |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

**قیود:**
- اگر user_id NULL است، session_key باید پر باشد
- هر کاربر/session حداکثر یک سبد active

**بازیابی سبد مهمان (Cart Recovery - D-063):**
- session_key از cookie مرورگر گرفته می‌شود
- پس از احراز هویت، سبد مهمان به سبد کاربر منتقل می‌شود (merge)
- abandoned_at برای trigger کردن Cart Recovery Flow

### ۲.۹ CartItem (جدید - آیتم‌های سبد)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| cart_id | UUID FK->Cart | سبد |
| product_id | UUID FK->Product | محصول |
| quantity | DECIMAL(10,2) | مقدار |
| unit_price | DECIMAL(10,2) | قیمت در لحظه افزودن |
| added_at | TIMESTAMP | تاریخ افزودن |
| updated_at | TIMESTAMP | به‌روزرسانی |

**قیود:** UNIQUE(cart_id, product_id) — هر محصول یک بار در هر سبد

### ۲.۱۰ Order

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| order_number | VARCHAR(20) UNIQUE | شماره سفارش |
| user_id | UUID FK->User NULL | کاربر (NULL=مهمان) |
| guest_phone | VARCHAR(11) NULL | شماره مهمان |
| cart_id | UUID FK->Cart NULL | سبد مبدأ (برای trace) |
| address_id | UUID FK->Address NULL | آدرس تحویل (NULL برای مهمان) |
| shipping_full_name | VARCHAR(100) NULL | نام گیرنده (snapshot مهمان) |
| shipping_phone | VARCHAR(11) NULL | تلفن گیرنده (snapshot مهمان) |
| shipping_province | VARCHAR(50) NULL | استان (snapshot مهمان) |
| shipping_city | VARCHAR(50) NULL | شهر (snapshot مهمان) |
| shipping_address | TEXT NULL | آدرس کامل (snapshot مهمان) |
| shipping_postal_code | VARCHAR(10) NULL | کد پستی (snapshot مهمان) |
| status | ENUM | pending/confirmed/preparing/shipped/delivered/cancelled/returned |
| subtotal | DECIMAL(10,2) | جمع |
| shipping_cost | DECIMAL(10,2) | ارسال |
| total_amount | DECIMAL(10,2) | نهایی |
| payment_status | ENUM | pending/paid/confirmed/rejected/refunded |
| notes | TEXT | یادداشت |
| tracking_code | VARCHAR(50) | کد رهگیری |
| shipped_at | TIMESTAMP NULL | ارسال |
| delivered_at | TIMESTAMP NULL | تحویل |
| cancelled_at | TIMESTAMP NULL | لغو |
| cancelled_reason | TEXT NULL | دلیل لغو |
| created_at | TIMESTAMP | ثبت |
| updated_at | TIMESTAMP | به‌روزرسانی |
| deleted_at | TIMESTAMP NULL | Soft delete |

### ۲.۱۱ OrderItem

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| order_id | UUID FK->Order | سفارش |
| product_id | UUID FK->Product | محصول |
| supplier_id | UUID FK->Supplier | تأمین‌کننده |
| product_name | VARCHAR(150) | نام در لحظه سفارش |
| quantity | DECIMAL(10,2) | مقدار |
| unit | VARCHAR(20) | واحد |
| unit_price | DECIMAL(10,2) | قیمت واحد |
| supplier_cost | DECIMAL(10,2) | هزینه تأمین |
| subtotal | DECIMAL(10,2) | جمع آیتم |
| status | ENUM | pending/confirmed/preparing/shipped/delivered/cancelled |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

### ۲.۱۲ Payment (طبق D-067)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| order_id | UUID FK->Order | سفارش |
| amount | DECIMAL(10,2) | مبلغ |
| sender_card_last4 | CHAR(4) | ۴ رقم آخر کارت مبدأ |
| transfer_time | TIMESTAMP | زمان تقریبی واریز |
| payment_method | ENUM | card_to_card |
| card_number | VARCHAR(20) | شماره کارت مقصد |
| card_holder | VARCHAR(100) | نام دارنده مقصد |
| receipt_image | VARCHAR(255) NULL | رسید (اختیاری) |
| status | ENUM | pending/confirmed/rejected |
| rejection_reason | TEXT NULL | دلیل رد |
| confirmed_by | UUID FK->User NULL | تأییدکننده |
| confirmed_at | TIMESTAMP NULL | تأیید |
| rejected_at | TIMESTAMP NULL | رد |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

**قیود:** CHECK(amount > 0)، بدون UNIQUE(order_id) — چند تلاش مجاز

### ۲.۱۳ Review

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| product_id | UUID FK->Product | محصول |
| user_id | UUID FK->User NULL | کاربر |
| guest_token | VARCHAR(100) NULL | توکن مهمان |
| rating | INTEGER | امتیاز ۱-۵ |
| title | VARCHAR(200) | عنوان |
| content | TEXT | متن |
| status | ENUM | pending/approved/rejected |
| admin_response | TEXT NULL | پاسخ ادمین |
| approved_at | TIMESTAMP NULL | تأیید |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

### ۲.۱۴ Lead

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| product_id | UUID FK->Product NULL | محصول |
| product_name | VARCHAR(150) | نام درخواستی |
| customer_name | VARCHAR(100) NULL | نام |
| customer_phone | VARCHAR(11) | تماس |
| description | TEXT | توضیح |
| status | ENUM | new/following/fulfilled/rejected |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

### ۲.۱۵ Address

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| user_id | UUID FK->User NULL | کاربر (NULL برای مهمان) |
| label | VARCHAR(50) | برچسب |
| province | VARCHAR(50) | استان |
| city | VARCHAR(50) | شهر |
| street_address | TEXT | آدرس |
| postal_code | VARCHAR(10) | کد پستی |
| phone | VARCHAR(11) | تماس |
| is_default | BOOLEAN | پیش‌فرض |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |
| deleted_at | TIMESTAMP NULL | Soft delete |

### ۲.۱۶ DeviceToken (D-040)

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| user_id | UUID FK->User | کاربر |
| device_fingerprint | VARCHAR(255) | اثر انگشت |
| token | VARCHAR(500) | JWT |
| expires_at | TIMESTAMP | انقضا ۳۰ روز |
| is_active | BOOLEAN | فعال |
| created_at | TIMESTAMP | ایجاد |
| last_used_at | TIMESTAMP | آخرین استفاده |

**قیود:** UNIQUE(user_id, device_fingerprint)

### ۲.۱۷ AuditLog

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| user_id | UUID FK->User NULL | کاربر |
| action | VARCHAR(50) | عمل |
| entity_type | VARCHAR(50) | موجودیت |
| entity_id | UUID | شناسه |
| old_values | JSONB NULL | قبلی |
| new_values | JSONB NULL | جدید |
| ip_address | VARCHAR(50) | IP |
| created_at | TIMESTAMP | تاریخ |

## ۳. روابط و قیود کلیدی

### ۳.۱ مدل تأمین‌کننده (قفل شده - D-068)
**در MVP:** هر محصول دقیقاً یک تأمین‌کننده دارد (Product.supplier_id).
- رابطه: Product N:1 Supplier
- چندتأمین‌کننده در سطح سفارش یعنی: یک Order می‌تواند OrderItemهایی از Supplierهای مختلف داشته باشد
- این محدودیت MVP است. در آینده اگر نیاز به چندتأمین‌کننده برای یک محصول بود، ADR جدید ثبت می‌شود

### ۳.۲ رزرو موجودی و جلوگیری از Oversell
- هنگام ثبت سفارش، OrderItemها موجودی را رزرو می‌کنند
- Inventory.reserved_quantity افزایش می‌یابد
- available_quantity = quantity - reserved_quantity (محاسبه‌ای)
- اگر available_quantity < 0، سفارش رد می‌شود
- پس از تأیید سفارش، InventoryTransaction ایجاد می‌شود (change_type: sale)
- پس از لغو یا مرجوعی، InventoryTransaction ایجاد می‌شود (change_type: release یا return)

### ۳.۳ Guest Checkout و Address
- برای خریدار مهمان: Order.shipping_* فیلدها پر می‌شوند (snapshot)
- برای خریدار ثبت‌نام‌شده: Order.address_id به Address اشاره می‌کند
- Address.user_id NULL مجاز است (برای آدرس‌های موقت مهمان)
- پس از ثبت سفارش، آدرس مهمان در Order ذخیره می‌شود و نیازی به Address جداگانه نیست

### ۳.۴ وضعیت‌های سفارش
pending → confirmed → preparing → shipped → delivered
cancelled یا returned در هر مرحله ممکن است

### ۳.۵ ارتباط پرداخت با سفارش (D-067)
- هر Order می‌تواند چندین Payment داشته باشد (تلاش‌های متعدد)
- Payment.status: pending, confirmed, rejected
- Order.payment_status بر اساس آخرین Payment تنظیم می‌شود

### ۳.۶ نقش‌های خانواده/ادمین/تأمین‌کننده (RBAC)
- Role: تعریف نقش‌ها و مجوزها
- UserRole: ارتباط کاربر با نقش (Many-to-Many)
- در MVP هر کاربر یک نقش اصلی دارد (is_primary = true)
- آماده ارتقا به چند-نقشی در آینده

## ۴. تصمیم‌های مدل‌سازی

- **Normalization:** 3NF + Denormalization محدود
- **JSONField:** فقط images, metadata, audit values, Role.permissions
- **Soft Delete:** User, Product, Order, Address
- **Hard Delete:** DeviceToken, Lead (پس از fulfilled)
- **تاریخچه:** InventoryTransaction (برای موجودی)
- **Computed Fields:** available_quantity (GENERATED ALWAYS AS)

## ۵. شاخص‌های ضروری

| جدول | فیلد | نوع |
| --- | --- | --- |
| User | phone | UNIQUE |
| Role | code | UNIQUE |
| UserRole | user_id, role_id | UNIQUE |
| Product | slug | UNIQUE |
| Product | category, status | INDEX |
| Inventory | product_id | UNIQUE |
| Cart | user_id, session_key | INDEX |
| CartItem | cart_id, product_id | UNIQUE |
| Order | order_number | UNIQUE |
| Order | user_id, status, created_at | INDEX |
| OrderItem | order_id, product_id | INDEX |
| Payment | order_id, status | INDEX |
| Review | product_id, status | INDEX |
| Lead | product_id | INDEX |
| Address | user_id | INDEX |
| DeviceToken | user_id, device_fingerprint | UNIQUE |
| AuditLog | entity_type, entity_id, created_at | INDEX |

## ۶. Out of Scope صریح

- Celery / Event bus / Redis Pub/Sub
- جداول وفاداری / Loyalty
- اپ موبایل schema
- آنالیتیکس پیشرفته
- Sharding / Partitioning
- Microservice DB
- Multi-supplier per product (در MVP)

## ۷. ارجاعات

ADR-001, D-040, D-045, D-046, D-067, D-068, MVP-SCOPE.md, USER-STORIES.md, ARCHITECTURE-PRINCIPLES.md
