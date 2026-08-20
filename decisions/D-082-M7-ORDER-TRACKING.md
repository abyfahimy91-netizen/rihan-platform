# D-082: Order Tracking Implementation (M7)

**Date:** 2026-08-20
**Status:** Accepted
**Type:** Feature Implementation
**Priority:** High

---

## Background

Customer tracking (M7) was critical for building trust (CENTRAL-STORY).
US-008 required: phone + order number access WITHOUT login.

The existing tracking page used a FAKE timeline based only on current status.

---

## Decision

Implement M7 with:
1. **OrderStatusHistory model** - Real timeline with timestamps
2. **Signal auto-capture** - Automatic history on every status change
3. **Lookup by phone + order number** - No login required
4. **Tracking code field** - For postal tracking
5. **Real timeline in template** - Using OrderStatusHistory, not current status

---

## Technical Implementation

### New Model: OrderStatusHistory
- Tracks every status change with timestamp
- Stores tracking_code and description
- 9 status types (ORDER_CREATED, PENDING_PAYMENT, etc.)

### New Fields in Order
- `tracking_code` (CharField) - Postal tracking code
- `shipping_method` (CharField) - Post, Tipax, etc.
- `shipped_at` (DateTimeField) - Auto-set on SHIPPED
- `delivered_at` (DateTimeField) - Auto-set on DELIVERED

### Signal: capture_order_status_change
- Auto-creates history on every status change
- Uses QuerySet.update() to prevent recursion
- Handles edge case: order created with non-DRAFT status

### View: tracking_lookup_page
- Form for phone + order number
- Validates ownership
- Updates session_key for guest access
- Redirects to tracking page

### Template: order_tracking.html
- Real timeline from OrderStatusHistory
- Shows tracking_code prominently
- Support phone from SiteSettings
- Persian dates and labels

---

## Tests

18 comprehensive tests covering:
- Signal auto-capture (8 tests)
- Lookup validation (7 tests)
- Tracking page access (3 tests)

**Result:** 18/18 passing

---

## Files Changed

- `src/modules/order/models.py` - OrderStatusHistory + 4 fields
- `src/modules/order/signals.py` - Auto-capture signal (new)
- `src/modules/order/apps.py` - Import signals
- `src/modules/order/page_views.py` - Lookup view + history context
- `src/modules/order/page_urls.py` - /lookup/ URL
- `src/modules/order/templates/order/order_tracking.html` - Real timeline
- `src/modules/order/templates/order/tracking_lookup.html` - Lookup form (new)
- `src/modules/order/tests/test_tracking.py` - 18 tests (new)
- `src/modules/order/migrations/0005_...` - Model + fields
- `src/modules/order/migrations/0006_...` - Status labels to Persian

---

## References

- US-008 (Order Tracking)
- CENTRAL-STORY (Trust building)
- D-079 (Return to Original Vision)
