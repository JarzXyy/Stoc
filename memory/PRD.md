# GreenBasket Grocery Tracker PRD

## Original problem statement
Create a website for a grocery store to track stock and cash flow, and include a feature to save images as proof of payment.

User clarification: “First for track product sales pueches and stock”.

## Architecture decisions
- React dashboard frontend with a FastAPI REST backend.
- MongoDB stores products and transactions using string UUIDs, excluding Mongo `_id` from API responses.
- Transactions are the source of truth for sales, purchases, cash flow, and saved payment-proof images.
- Stock is updated atomically when a sale or purchase is recorded.
- Payment proof images are stored on the transaction as image data for this first version.

## User personas
- Grocery store owner or manager who needs a quick daily view of stock and money movement.
- Store assistant recording purchases and sales at the counter.

## Core requirements (static)
- See current product stock, categories, prices, and low-stock warnings.
- Record product sales and purchases with quantity, unit price, and notes.
- Update stock automatically after each movement.
- Show cash flow and recent activity.
- Attach and save an image as payment proof.
- Support mobile use for quick store-floor updates.

## What's been implemented

### 2026-08-20
- Replaced starter screen with GreenBasket operations dashboard.
- Added seeded grocery inventory, searchable inventory table, low-stock status, live stock totals, cash flow, and recent activity.
- Added sale and purchase forms with validation, stock updates, notes, and payment-proof image attachment.
- Added FastAPI endpoints for products, transactions, and summary metrics.
- Added date-filtered “Sales today” metric and live current-date header.
- Verified desktop and mobile flows, API persistence, image proof persistence, and validation with regression testing.

## Prioritized backlog
- P0: Add product editing and product deletion controls.
- P1: Add a dedicated transaction history page with date and type filters.
- P1: Add an image-proof gallery with preview and download.
- P2: Add supplier records and purchase invoice numbers.
- P2: Add exportable weekly cash-flow reports.

## Remaining next tasks
- P0: Product management controls.
- P1: Transaction history and proof gallery.
- P2: Reporting and supplier workflows.