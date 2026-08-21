# GreenBasket Grocery Tracker PRD

## Original problem statement
Create a website for a grocery store to track stock and cash flow, and include a feature to save images as proof of payment.

User clarification: “First for track product sales pueches and stock”.
Later requests: Transaction History tab, Weekly Reports tab (copy-as-text sharing), Stock top-up tab, currency in Indonesian Rupiah (IDR).

## Architecture decisions
- React dashboard frontend with a FastAPI REST backend.
- MongoDB stores products and transactions using string UUIDs, excluding Mongo `_id` from API responses.
- Transactions are the source of truth for sales, purchases, cash flow, and saved payment-proof images.
- Stock is updated atomically when a sale or purchase is recorded; a dedicated stock endpoint allows manual top-ups.
- Payment proof images are stored on the transaction as base64 image data for this version.
- All currency displayed and shared as IDR ("Rp X.XXX", id-ID locale); seed prices at rupiah scale.

## User personas
- Grocery store owner or manager who needs a quick daily view of stock and money movement.
- Store assistant recording purchases and sales at the counter.

## Core requirements (static)
- See current product stock, categories, prices, and low-stock warnings.
- Record product sales and purchases with quantity, unit price, and notes.
- Update stock automatically after each movement; manual stock top-ups.
- Show cash flow and recent activity.
- Attach and save an image as payment proof; review proofs later.
- Searchable transaction history with type and date filters.
- Weekly cash-flow and stock-movement summary, shareable as text.
- Support mobile use for quick store-floor updates.

## Key API endpoints
- GET /api/products, POST /api/products
- POST /api/products/{id}/stock  {quantity>0} → increases stock
- GET /api/transactions?type=&q=&date_from=&date_to= (YYYY-MM-DD, 400 on malformed)
- POST /api/transactions (sale/purchase, proof_image optional)
- GET /api/summary (cash flow, stock units, sales today, low stock)
- GET /api/reports/weekly?week_offset=0 (totals, per-product movement, share_text in Rp)

## What's been implemented

### 2026-08-20
- GreenBasket operations dashboard: seeded inventory, searchable table, low-stock status, cash flow, recent activity.
- Sale/purchase forms with validation, stock updates, notes, payment-proof image attachment.
- Date-filtered “Sales today” metric and live current-date header.

### 2026-08-21
- Transaction History tab: product search, sale/purchase filter, date-range filters, clear-filters, proof thumbnails with full-image modal, broken-image fallback.
- Weekly Reports tab: week navigation (prev/next), sales/purchases/cash-flow cards, per-product stock movement table, copy-as-text share summary with preview.
- Stock tab: per-product quantity input to increase stock (POST /api/products/{id}/stock).
- Currency switched to IDR everywhere (frontend formatters, report share_text, seed prices migrated in DB, old dollar-scale test transactions removed).
- Backend date validation (400 on malformed dates).
- Tested: iteration_4 — 31/31 backend pytest, 100% frontend flows passed; low-priority fixes applied and self-verified after.

## Prioritized backlog
- P0: Add product creation/editing/deletion controls in the UI.
- P1: Proof-image gallery page with download.
- P2: Supplier records and purchase invoice numbers.
- P2: Pagination on transaction history for large volumes.
- P2: Printable/PDF weekly report (user chose copy-as-text for now).

## Notes for future agents
- No auth in this app.
- Backend test suites: /app/backend/tests (pytest, -n 2). test_history_reports.py asserts IDR formatting.
- Transactions collection was emptied of test data on 2026-08-21; History/Reports show empty states until real movements are recorded.
- No delete endpoints; clean test data directly via MONGO_URL/DB_NAME.
