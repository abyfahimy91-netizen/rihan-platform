# D-083: Reviews Module Implementation (M8)

**Date:** 2026-08-20
**Status:** Accepted
**Type:** Feature Implementation
**Priority:** High

---

## Background

Customer reviews are critical for building trust (CENTRAL-STORY).
US-009 required reviews with:
- Only delivered order customers can review
- Guest reviews via SMS token (one-time, 7 days)
- Admin approval before display
- Max 500 characters

---

## Decision

Implement M8 as a separate module with:
1. Review model with approval workflow
2. Guest token system (one-time, 7 days validity)
3. Registered user review from product page
4. Guest review via SMS link
5. Admin panel with bulk approve/unapprove
6. API endpoint for product reviews

---

## Technical Implementation

### Review Model
- `product` - FK to Product
- `order` - FK to Order (proof of purchase)
- `user` / `guest_name` / `guest_phone` - reviewer identity
- `rating` (1-5), `title`, `text` (max 500)
- `is_approved`, `approved_by`, `approved_at`
- `guest_token`, `token_expires_at`, `token_used`
- UniqueConstraint: one review per order

### Key Methods
- `can_review(order)` - validates DELIVERED + no existing review
- `is_token_valid()` - checks expiration and usage
- `use_token()` - marks token as used
- `approve(admin)` - sets approval fields
- `create_guest_review_token(order)` - creates placeholder with token

### Views
- `submit_review` - registered user (login required)
- `guest_review_form` - guest via token
- `product_reviews_api` - JSON API for approved reviews

### Privacy
- Reviewer names are masked in API
- Phone numbers partially hidden (0912***5678)
- Guest names masked (A***Z)

---

## Tests

23 comprehensive tests covering:
- Model validation (9 tests)
- Guest token workflow (5 tests)
- Registered user flow (5 tests)
- Reviews API (4 tests)

**Result:** 23/23 passing

---

## Files Changed

- `src/modules/reviews/` - New module (11 files)
- `src/config/settings.py` - Added to INSTALLED_APPS
- `src/config/urls.py` - Added reviews URL
- `decisions/D-083-M8-REVIEWS.md` - This document
- `CONTINUITY.md` - Updated

---

## References

- US-009 (Customer Reviews)
- CENTRAL-STORY (Trust building)
- Trust Checklist (D-048)
