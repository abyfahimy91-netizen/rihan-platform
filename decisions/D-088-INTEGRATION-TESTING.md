# D-088: تست یکپارچه Full Purchase Flow

**تاریخ:** ۲۰۲۶-۰۸-۲۱
**وضعیت:** Approved
**فاز:** ۵ (Development)
**مرتبط با:** US-059, M1, M2, M6

## ۱. تصمیم
پیاده‌سازی تست یکپارچه cross-module در tests/test_integration.py

## ۲. Flow تست شده
محصول -> سفارش DRAFT -> آیتم -> پرداخت کارت‌به‌کارت -> تأیید ادمین -> PAID -> DELIVERED -> Signal M6 -> تراکنش مالی خودکار

## ۳. ماژول‌های validate شده
- M1 Catalog: Supplier, Product, Category
- M2 Order: Order, OrderItem, Payment
- M6 Finance: SupplierLedger, SupplierTransaction (از طریق signal)

## ۴. تست‌ها
- test_full_purchase_flow: جریان کامل ۸ مرحله‌ای
- test_cancelled_order_no_finance: ایزولاسیون سفارش لغو شده

## ۵. نتیجه
هر ۲ تست پاس شدند
