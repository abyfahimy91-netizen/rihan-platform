# D-084: Leads Module Implementation (M9)

**Date:** 2026-08-21
**Status:** Accepted
**Type:** Feature Implementation
**Priority:** High

---

## Background

Product availability notifications are critical for customer retention.
US-010 required:
- Simple form: phone (required) + name (optional) + product (optional)
- Confirmation message: "ثبت شد. اطلاع می‌دهیم."
- Admin panel with Jalali dates

---

## Decision

Implement M9 as a separate module with:
1. Lead model with status workflow (PENDING -> NOTIFIED -> CONVERTED/CANCELLED)
2. Auto-notification signal when product becomes available
3. Conversion tracking when lead becomes a purchase
4. Admin panel with Jalali dates and bulk actions
5. Integration with product page (out-of-stock CTA)

---

## Technical Implementation

### Lead Model
- `phone` (validated: 09XXXXXXXXX)
- `name` (optional)
- `product` (optional - general leads supported)
- `status` (PENDING, NOTIFIED, CONVERTED, CANCELLED)
- `notified_at`, `notification_method`
- `converted_at`, `order` (FK)
- UniqueConstraint: one pending lead per phone+product

### Key Methods
- `notify(method)` - mark as notified
- `convert(order)` - mark as converted
- `cancel()` - cancel the lead
- `can_create_lead(phone, product)` - validation
- `get_pending_leads_for_product(product)` - query helper

### Signals
1. **notify_leads_when_product_available** (on Inventory save)
   - Triggers when available_quantity > 0
   - Bulk updates all PENDING leads to NOTIFIED
   - Uses QuerySet.update() for efficiency

2. **track_lead_conversion_on_order** (on Order save)
   - Matches phone + products
   - Converts PENDING/NOTIFIED leads to CONVERTED

3. **track_lead_conversion_on_item** (on OrderItem save)
   - Handles case where items added after order creation

### Views
- `lead_form_page` - GET/POST form (with or without product)
- `submit_lead_api` - AJAX endpoint

### Templates
- `lead_form.html` - clean form with privacy note
- `lead_success.html` - confirmation page

### Admin Panel
- Jalali date display (jdatetime)
- Bulk actions: notify, cancel, mark_as_converted
- Filters by status, product
- Search by phone, name, product

### Product Page Integration
- Modified `product_detail.html`
- Shows "🔔 اطلاع از موجودی" button when out of stock
- Shows "افزودن به سبد خرید" when in stock

---

## Tests

27 comprehensive tests covering:
- Model validation (9 tests)
- Auto-notification signal (4 tests)
- Conversion tracking (3 tests)
- Form views (7 tests)
- API views (4 tests)

**Result:** 27/27 passing

---

## Files Changed

- `src/modules/leads/` - New module (11 files)
- `src/modules/catalog/templates/catalog/product_detail.html` - Stock condition
- `src/config/settings.py` - Added to INSTALLED_APPS
- `src/config/urls.py` - Added leads URL
- `decisions/D-084-M9-LEADS.md` - This document
- `CONTINUITY.md` - Updated

---

## References

- US-010 (Product Availability Notification)
- CENTRAL-STORY (Customer trust and retention)
- D-079 (Modular architecture)
