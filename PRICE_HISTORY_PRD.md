# Price History: Personal Price-Intelligence for Quick-Commerce Orders

**Product Requirements Document, Technical Design & Delivery Plan**  
*Version:* 1.2 (Baseline for Build — Verified against Swiggy Builders Club MCP)  
*Date:* 25 October 2026  
*Status:* Approved for v1 Build  
*Primary Data Source:* Swiggy Builders Club MCP (`swiggy-instamart`; Food in v2)  

---

## 1. Executive Summary

**Price History** is a local-first price intelligence tool that reads a shopper's own Swiggy Instamart order history and tracks price changes for repeat grocery purchases over time.

It normalizes every purchase into a standardized price per unit (e.g., INR per litre for cooking oil, INR per kg for atta/rice, INR per piece for eggs), flags when current prices are higher than past purchases, and surfaces clear timeline insights in under 10 seconds.

### The Problem It Solves
Repeat buyers of staple groceries face deceptive pack sizes (e.g., 1 L bottle at ₹180 vs. 500 ml at ₹100), faulty memory of past prices, and hidden price creep (fees, discounts, substitutions).

### The 15-Day History Solution: The Local Price Vault
Swiggy MCP's `get_orders` endpoint returns a rolling window of the **last 15 days** of order history. Price History acts as an **idempotent local accumulator**: by regularly snapshotting orders into local SQLite, it builds a permanent, multi-month and multi-year price vault that outlasts Swiggy's 15-day API retention window.

### Version 1 Scope
- **Sources**: Swiggy Instamart orders (single user).
- **Architecture**: Local-first SQLite database, read-only MCP access.
- **Interfaces**: Rich Typer CLI (v1.0) and read-only local web view (v1.1).
- **Safety**: No order placement, no cart mutations, no payment handling, zero data leaves the user's laptop.

---

## 2. Problem Statement

Repeat buyers of staple groceries (cooking oil, atta, rice, milk, pulses) cannot easily answer a simple question:
> *"Is the price I am about to pay higher than what I paid last time?"*

The answer exists in order history, but manually retrieving it requires scrolling through past orders, opening invoices, finding line items, and comparing by memory.

### Three Failures of the Manual Process:
1. **Pack Sizes Differ**: A 1 L bottle at ₹180 and a 500 ml bottle at ₹100 make the larger pack look expensive, when per litre the smaller one is actually ₹200/L.
2. **Memory is Weak**: Shoppers compare against rounded or outdated figures from months ago.
3. **Context is Missing**: Higher totals often come from delivery fees, taxes, or pack changes, not actual commodity price increases.

---

## 3. Goals and Non-Goals

### Goals (v1)
* **G1. Standardized Purchase History**: Show timeline of repeated products with date, quantity, total paid, and normalized per-unit price.
* **G2. Unit Price Comparison**: Compare the latest purchase with previous purchases and all-time lowest price in per-unit terms.
* **G3. Idempotent Sync & Local Accumulation**: Sync order history safely without creating duplicates, accumulating a permanent historical record beyond Swiggy's 15-day API window.
* **G4. 100% Local-First Privacy**: Keep all order data on the user's own machine in SQLite. Zero external servers or telemetry.
* **G5. Transparent Accuracy**: Every derived number links to its source order ID, showing whether product matching was exact, aliased, or user-confirmed.
* **G6. Live Store Check (v1 Bridge)**: Query live prices via MCP `search_products` to compare current store prices against past purchase prices on Day 1.

### Non-Goals (v1)
* **NG1. Buying Advice / Timing Recommendations**: No predictive advice on whether to wait or buy now.
* **NG2. Machine Learning Predictions**: No predictive time-series models in v1 (insufficient local data).
* **NG3. Macroeconomic Explanations**: No inflation news commentary.
* **NG4. Order Placement / Cart Modification**: Strictly read-only; no checkout or payment tools.
* **NG5. Multi-User Sync / Cloud Sharing**: No central accounts or cross-user aggregation.
* **NG6. Dineout / Scenes Booking**: Table bookings and event tickets have no repeat grocery price trends.

---

## 4. User Personas & Jobs to be Done

| Persona | Context | Job to be Done | Success Criteria |
| :--- | :--- | :--- | :--- |
| **P1: Monthly Stocker** *(Primary)* | Orders staples 2–4 times a month on Instamart | Check whether today's price of a staple is inflated before ordering | Opens product timeline in $<10$ seconds; immediately knows if price is up |
| **P2: Budget Owner** *(Secondary)* | Manages household spend; reviews monthly | Understand which staples inflated the most over 3–12 months | Views ranked list of per-unit price changes for staples |
| **P3: The Author / Builder** | Builds and verifies the system | Validate correctness of pack-size normalization and idempotent sync | Golden test suite passes with zero price calculation errors |

---

## 5. Scope & Swiggy Platform Constraints

| Source | Status in v1 | Rationale |
| :--- | :--- | :--- |
| **Swiggy Instamart** | **In Scope (P0)** | Standard pack sizes, high repeat purchases, meaningful unit pricing (`₹/L`, `₹/kg`). |
| **Swiggy Food** | Planned for v2 (P1) | Same order structure; per-dish tracking rather than per-unit. |
| **Dineout / Scenes** | Out of Scope | Table reservations and event tickets; no commodity repeat prices. |

### Verified Platform Constraints (Swiggy Builders Club MCP)
1. **15-Day History Window**: `get_orders` returns orders from the last 15 days only. Local storage is strictly mandatory to build multi-month timelines.
2. **Read-Only Adapter**: The application excludes all write tools (`checkout`, `confirm_order`, `update_cart`, `clear_cart`, `apply_coupon`).
3. **Gateway Rate Limits**: Swiggy enforces gateway caps returning `429` (JSON-RPC code `-32000`) with `Retry-After`. The sync engine must respect backoff and keep daily syncs to $\le 2$ requests.
4. **OAuth 2.1 PKCE**: Tokens are stored securely on localhost and can be wiped instantly.

---

## 6. Functional Requirements

*Priority: P0 = Required for v1 core; P1 = Required for v1 polish; P2 = v2 Roadmap.*

| ID | Requirement | Priority | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **FR-01** | Authenticate via Swiggy MCP OAuth | **P0** | Token acquired via OAuth 2.1 PKCE; stored locally; revokable by deletion. |
| **FR-02** | Fetch Instamart order list | **P0** | Fetches recent orders via `get_orders(count=20)`; iterates until watermark reached. |
| **FR-03** | Fetch itemized invoice details | **P0** | Calls `get_order_details(orderId)` for new orders; extracts `name`, `quantity`, `finalPrice`. |
| **FR-04** | Normalize pack size and unit | **P0** | Parses `ml`, `l`, `g`, `kg`, `pc`, `pack of N`, `N x Y` with $\ge 95\%$ accuracy on fixtures. |
| **FR-05** | Compute per-unit price | **P0** | Calculates `unit_price_paise = line_total_paise / (quantity * pack_size_base)` in integer paise. |
| **FR-06** | Show per-product price timeline | **P0** | CLI outputs chronological purchases with dates, quantities, unit prices, and % change. |
| **FR-07** | Flag price increases ($>5\%$) | **P0** | Visual warning when unit price exceeds previous non-promo purchase by $\ge 5\%$. |
| **FR-08** | Live store price lookup | **P0** | `price-history check <item>` calls `search_products` to compare current store price against last paid. |
| **FR-09** | User confirmation for uncertain matches | **P1** | Fuzzy matches with confidence $<0.90$ prompt user review and store permanent alias. |
| **FR-10** | Scheduled and on-demand sync | **P1** | Sync runs on CLI invocation or daily OS task without creating duplicate orders. |
| **FR-11** | Min/Max/Median summary metrics | **P1** | Product summary shows all-time low, all-time high, and 12-month median unit price. |
| **FR-12** | Export and complete data wipe | **P1** | Export to CSV/JSON; `price-history wipe --all` removes DB, raw payloads, logs, and tokens. |
| **FR-13** | Audit trail for derived calculations | **P1** | Detail view shows exact mathematical formula, source `orderId`, and raw line text. |
| **FR-14** | Local read-only web view | **P1.1** | Lightweight local browser dashboard rendering interactive charts for each product. |
| **FR-15** | Swiggy Food adapter | **P2** | Adapter for restaurant dish price tracking. |

---

## 7. System Architecture

The system decouples the platform-specific data source from the core business logic via an `OrderSource` interface.

```
                      +-------------------+
                      |   CLI / Cron      |
                      +---------+---------+
                                |
                      +---------v---------+
                      | Sync Orchestrator |
                      +----+---------+----+
                           |         |
         +-----------------+         +-----------------+
         |                                             |
+--------v--------+                           +--------v--------+
|   OrderSource   | (Interface)               |   Normalizer    |
+--------+--------+                           | - Unit parser   |
         |                                    | - Product match |
+--------v--------+                           | - Unit price    |
| SwiggyInstamart |                           +--------+--------+
| Adapter (MCP)   |                                    |
+-----------------+                           +--------v--------+
                                              | Storage (SQLite)|
                                              | - orders        |
                                              | - line_items    |
                                              | - products      |
                                              | - observations  |
                                              +--------+--------+
                                                       |
                                              +--------v--------+
                                              |  Presentation   |
                                              | - Typer CLI     |
                                              | - Local Web UI  |
                                              +-----------------+
```

### Key Architectural Decoupling:
1. **`OrderSource` Interface**: Exposes `list_recent_orders()` and `get_order_details(order_id)`. Returns plain Python data classes; zero Swiggy MCP types leak into the core.
2. **Sync Orchestrator**: Manages watermarks, fetches new orders, caches raw JSON, invokes the normalizer, and writes observations within an atomic transaction.
3. **Normalizer**: Pure mathematical and text-processing engine; no network or database dependencies.
4. **Storage (SQLite)**: Single file on the user's machine. Raw payloads are preserved so normalizer improvements can be re-applied offline without network calls.

---

## 8. Data Model & Database Schema

All monetary values are stored as **integer paise** (INR $\times 100$) to completely eliminate IEEE 754 floating-point errors. Timestamps are stored in UTC ISO-8601.

### Tables

```sql
-- Sources registry (Instamart, Food)
CREATE TABLE sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- 'instamart', 'food'
    adapter_version TEXT NOT NULL
);

-- Orders table (Stores order header and raw JSON)
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    source_order_id TEXT NOT NULL,       -- Swiggy's orderId
    placed_at TEXT NOT NULL,             -- ISO timestamp
    status TEXT NOT NULL,                -- DELIVERED, CANCELLED
    total_paise INTEGER NOT NULL,
    raw_json TEXT NOT NULL,              -- Permanent backup of Swiggy payload
    created_at TEXT NOT NULL,
    UNIQUE(source_id, source_order_id)  -- Core of sync idempotency
);

-- Canonical Products
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,        -- e.g. "Fortune Sunlite Sunflower Oil"
    brand TEXT,                          -- "Fortune"
    category TEXT,                       -- "Edible Oils"
    base_unit TEXT NOT NULL,             -- 'ml', 'g', 'piece'
    pack_size_base INTEGER NOT NULL,     -- 1000 (ml), 5000 (g)
    created_at TEXT NOT NULL
);

-- Aliases and User-Confirmed Mappings
CREATE TABLE product_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    raw_name_pattern TEXT NOT NULL UNIQUE,
    confidence REAL NOT NULL,
    created_by TEXT NOT NULL             -- 'auto' or 'user'
);

-- Line Items extracted from Invoices
CREATE TABLE line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_index INTEGER NOT NULL,         -- Position in order items array
    raw_name TEXT NOT NULL,              -- "Fortune Sunlite Refined Sunflower Oil 1 L"
    quantity INTEGER NOT NULL,
    line_total_paise INTEGER NOT NULL,   -- finalPrice in paise
    product_id INTEGER REFERENCES products(id),
    match_status TEXT NOT NULL,          -- 'confirmed', 'proposed', 'unmatched'
    match_confidence REAL NOT NULL,
    UNIQUE(order_id, item_index)         -- Handles missing line ID safely
);

-- Append-Only Time Series of Price Observations
CREATE TABLE price_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    line_item_id INTEGER NOT NULL REFERENCES line_items(id) ON DELETE CASCADE,
    observed_at TEXT NOT NULL,
    unit_price_paise_per_base REAL NOT NULL, -- paise per ml/g/piece (with precision)
    quantity INTEGER NOT NULL,
    line_total_paise INTEGER NOT NULL,
    is_promo BOOLEAN NOT NULL DEFAULT 0,
    is_substitute BOOLEAN NOT NULL DEFAULT 0
);

-- Sync Audit Trail
CREATE TABLE sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    orders_seen INTEGER NOT NULL DEFAULT 0,
    orders_new INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,                -- 'running', 'success', 'failed'
    error_message TEXT
);

-- User Settings
CREATE TABLE user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 9. Normalization & Matching Pipeline

```
Raw Invoice Name ("Fortune Sunlite Sunflower Oil 1 L")
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Stage 1: Pack Size & Unit Parser (Regex Engine)        │
│ Matches: "1 L" ──► Unit: ml, Base Pack Size: 1000      │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Unit Price Calculation                        │
│ unit_price = line_total_paise / (qty * 1000 ml)        │
│ e.g. 18000 paise / (1 * 1000) = 18.00 paise/ml (₹180/L)│
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Stage 3: Canonical Product Matcher                     │
│ 1. Exact Match (confidence 1.0) ──► Match existing     │
│ 2. Alias Match (confidence 0.95) ──► Match alias       │
│ 3. Token-Set Fuzzy Match (0.50 - 0.89) ──► Review Queue│
│ 4. No Match ──► Propose New Canonical Product          │
└────────────────────────────────────────────────────────┘
```

### Supported Pack Patterns:
* **Single Units**: `1 L`, `500 ml`, `1 kg`, `5 kg`, `250 g`, `10 pcs`, `1 pc`.
* **Multi-Packs**: `2 x 500 ml` $\rightarrow 1000\text{ ml}$, `Pack of 4` $\rightarrow 4\text{ pcs}$.
* **Free Add-ons**: `2 L + 1 L Free` $\rightarrow 3000\text{ ml}$.

---

## 10. Sync Algorithm & Idempotency

Because Swiggy MCP does not support date-range filtering, the sync uses **cursor/timestamp termination**:

```python
def sync_orders():
    # 1. Read last known order timestamp from SQLite
    watermark = get_latest_order_timestamp()
    
    # 2. Fetch recent orders from Instamart MCP
    seen_count = 0
    new_count = 0
    orders = mcp_client.call_tool("get_orders", count=20)
    
    for order_header in orders.data["orders"]:
        seen_count += 1
        
        # 3. Stop if order is older than 2-day overlap buffer before watermark
        if order_header["createdAt"] < (watermark - timedelta(days=2)):
            break
            
        # 4. Upsert order header
        if db.order_exists(order_header["orderId"]):
            continue
            
        # 5. Fetch granular line items with item prices
        details = mcp_client.call_tool("get_order_details", orderId=order_header["orderId"])
        
        # 6. Atomic transaction: Save order + line items + observations
        with db.transaction():
            db.insert_order(order_header, raw_json=details)
            for idx, item in enumerate(details.data["items"]):
                parsed = normalizer.parse(item["name"])
                product = matcher.match_or_create(parsed)
                db.insert_line_item(item, idx, product)
                db.insert_price_observation(item, parsed, product)
            new_count += 1
```

---

## 11. Security, Privacy & DPDP Compliance

* **Local Data Residency**: All database files, configuration, and tokens remain strictly on `localhost`.
* **DPDP Act 2023 Compliance**: The user acts as their own Data Principal accessing their own data. No third-party data processor is involved.
* **Encryption at Rest**: SQLite database is stored in user application data directories with restricted file permissions (`chmod 600` / Windows User ACL).
* **Complete Erasure (FR-12)**:
  ```bash
  price-history purge --confirm
  ```
  Completely wipes `price_history.db`, cache, logs, and OAuth tokens.

---

## 12. Technology Stack

| Layer | Selection | Justification |
| :--- | :--- | :--- |
| **Language** | **Python 3.12+** | Robust string parsing, standard data libraries, cross-platform support. |
| **Storage** | **SQLite 3** | Zero-server, transactional, ACID-compliant, single portable file. |
| **ORM / Query** | **SQLAlchemy Core** | Type-safe SQL expressions without heavy ORM overhead. |
| **CLI Framework** | **Typer + Rich** | Beautiful terminal tables, colored change badges (`+8.4%`), progress bars. |
| **Testing** | **pytest + hypothesis** | Property-based testing on mathematical unit price conversions. |
| **Packaging** | **uv / pyproject.toml** | Fast dependency management and simple local installation. |

---

## 13. Resolved Questions (from v1.0 / v1.1)

| Question ID | Question | Resolution | Official Source Reference |
| :--- | :--- | :--- | :--- |
| **Q1** | Does the invoice tool return per-item quantity & price? | **RESOLVED (YES)** | `get_order_details` returns `items: [{ name, quantity, finalPrice, removed }]`. |
| **Q2** | Is order history available for 12 months? | **RESOLVED (15 Days)** | `get_orders` explicitly limits results to the last 15 days. Local accumulation is required. |
| **Q3** | Does Swiggy allow scheduled personal sync? | **RESOLVED (YES)** | Low-frequency personal sync respects rate-limit guidance; local storage is DPDP-compliant. |
| **Q4** | Are substitutions reflected on invoices? | **RESOLVED (YES)** | `removed: boolean` flags out-of-stock items; replacement items appear as line items. |
| **Q5** | Do pack sizes appear consistently in names? | **RESOLVED (YES)** | Standard Instamart catalogue uses strict unit suffixes (`1 L`, `500 g`, `1 kg`). |

---

## 14. Delivery Milestones

```
M0: Scaffolding ──► M1: MCP Adapter ──► M2: Core Engine ──► M3: Sync ──► M4: CLI v1.0
  (Repo & CI)       (OAuth & Live API)   (Parser & DB)      (Idempotent)    (Rich UX)
```

* **Milestone M0**: Repo structure, `pyproject.toml`, test configuration, SQLite schema migration.
* **Milestone M1**: Swiggy MCP client, OAuth PKCE flow, live `get_orders` & `get_order_details` fetcher.
* **Milestone M2**: Pack size regex parser, per-unit price math, golden test suite (50 real fixtures).
* **Milestone M3**: Idempotent sync orchestrator with resume capability and raw JSON backup.
* **Milestone M4**: Typer CLI with `sync`, `timeline`, `check`, `summary`, and `purge` commands.
* **Milestone v1.1**: Local HTML dashboard with Chart.js price trends.
