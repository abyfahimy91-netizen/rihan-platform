# D-085: User-Supplier Link for M4 Supplier Panel

Date: 2026-08-21
Status: Approved
Phase: 5 (Development)
Related: D-068, US-028, US-029

## Decision

Hybrid architecture: RBAC + User-Supplier Link

1. RBAC: supplier role with order.view_own and product.view permissions
2. User-Supplier Link: OneToOneField user added to Supplier model

## Files Changed

- src/modules/catalog/models.py: Added user field to Supplier
- src/modules/catalog/migrations/0004_add_user_to_supplier.py: Migration
- src/modules/supplier_panel/: New app for M4

## Tests

5 tests written and passing.
IDOR prevention: suppliers only see their own orders.
