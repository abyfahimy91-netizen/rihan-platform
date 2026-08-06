# ADR-002: معماری دیتابیس و مدل داده MVP

| شناسه | ADR-002 |
| --- | --- |
| عنوان | معماری دیتابیس و مدل داده MVP |
| وضعیت | **Proposed** — پیش‌نویس، در انتظار تأیید مشاور |
| تاریخ | ۲۰۲۶-۰۸-۰۶ |
| مرتبط | ADR-001, D-040, D-045, D-046, D-067 |

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

### ۲.۱ User

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| phone | VARCHAR(11) UNIQUE | شماره موبایل |
| password | VARCHAR(255) NULL | رمز اختیاری bcrypt |
| first_name | VARCHAR(50) | نام |
| last_name | VARCHAR(50) | نام خانوادگی |
| role | ENUM | customer/admin/family_admin/family_member/observer/supplier |
| is_active | BOOLEAN | فعال |
| created_at | TIMESTAMP | ثبت‌نام |
| updated_at | TIMESTAMP | به‌روزرسانی |
| deleted_at | TIMESTAMP NULL | Soft delete |

### ۲.۲ Supplier

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

### ۲.۳ Product

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

### ۲.۴ Inventory

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه یکتا |
| product_id | UUID FK->Product UNIQUE | محصول |
| quantity | DECIMAL(10,2) | موجود |
| unit | VARCHAR(20) | واحد |
| low_stock_threshold | DECIMAL(10,2) | آستانه هشدار |
| reserved_quantity | DECIMAL(10,2) | رزرو شده |
| available_quantity | DECIMAL(10,2) | قابل فروش |
| created_at | TIMESTAMP | ایجاد |
| updated_at | TIMESTAMP | به‌روزرسانی |

**قیود:** UNIQUE(product_id)، CHECK(available_quantity >= 0)

### ۲.۴.۱ InventoryTransaction (تاریخچه موجودی - D-045)

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

### ۲.۵ Order

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| order_number | VARCHAR(20) UNIQUE | شماره سفارش |
| user_id | UUID FK->User NULL | کاربر (NULL=مهمان) |
| guest_phone | VARCHAR(11) NULL | شماره مهمان |
| address_id | UUID FK->Address | آدرس تحویل |
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

### ۲.۶ OrderItem

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

### ۲.۷ Payment (طبق D-067)

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

### ۲.۸ Review

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

### ۲.۹ Lead

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

### ۲.۱۰ Address

| فیلد | نوع | توضیح |
| --- | --- | --- |
| id | UUID PK | شناسه |
| user_id | UUID FK->User | کاربر |
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

### ۲.۱۱ DeviceToken (D-040)

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

### ۲.۱۲ AuditLog

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

## ۳. تصمیم‌های مدل‌سازی

- **Normalization:** 3NF + Denormalization محدود
- **JSONField:** فقط images, metadata, audit values
- **Soft Delete:** User, Product, Order, Address
- **Hard Delete:** DeviceToken, Lead (پس از fulfilled)
- **تاریخچه:** InventoryTransaction + PriceHistory

## ۴. شاخص‌های ضروری

| جدول | فیلد | نوع |
| --- | --- | --- |
| User | phone | UNIQUE |
| User | role | INDEX |
| Product | slug | UNIQUE |
| Product | category, status | INDEX |
| Inventory | product_id | UNIQUE |
| Order | order_number | UNIQUE |
| Order | user_id, status, created_at | INDEX |
| OrderItem | order_id, product_id | INDEX |
| Payment | order_id, status | INDEX |
| Review | product_id, status | INDEX |
| Lead | product_id | INDEX |
| Address | user_id | INDEX |
| DeviceToken | user_id + device_fingerprint | UNIQUE |
| AuditLog | entity_type + entity_id, created_at | INDEX |

## ۵. Out of Scope صریح

- Celery / Event bus / Redis Pub/Sub
- جداول وفاداری / Loyalty
- اپ موبایل schema
- آنالیتیکس پیشرفته
- Sharding / Partitioning
- Microservice DB

## ۶. ارجاعات

ADR-001, D-040, D-045, D-046, D-067, MVP-SCOPE.md, USER-STORIES.md, ARCHITECTURE-PRINCIPLES.md
