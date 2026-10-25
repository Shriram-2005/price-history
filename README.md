# Price History: Personal Price-Intelligence for Quick-Commerce

> Personal grocery staple price tracker and inflation intelligence built on top of the **Swiggy Builders Club MCP platform**.

---

## What It Does

1. **Pack Size Normalization**: Automatically converts complex Indian FMCG pack sizes (`1 L`, `500 ml`, `5 kg`, `Pack of 2`, `2 L + 1 L Free`) into standardized base units (`ml`, `g`, `pc`).
2. **Standardized Unit Pricing**: Calculates precise per-unit rates (e.g. `₹ / Litre`, `₹ / kg`) in integer paise to eliminate floating-point rounding errors.
3. **The 15-Day Local Vault**: Swiggy's API only exposes the last 15 days of order history. Price History accumulates your orders into local SQLite, building a permanent, multi-month price vault.
4. **Inflation Alerts**: Flags when you are about to pay $\ge 5\%$ more than your last non-promotional purchase.
5. **Live Deal Check**: Compares today's live Instamart store price against your last paid price.
6. **Maximum Security & DPDP Compliance**: 
   - 100% local-first data residency. Zero telemetry or external cloud storage.
   - Strictly read-only adapter: Mutating tools (`checkout`, `update_cart`, `confirm_order`) are barred at code level.
   - Complete erasure with `price-history purge --confirm`.

---

## Installation & Setup

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -e .[dev]
```

---

## Quickstart CLI Commands

### 1. Sync Orders (Demo or Live)
```bash
# Sync using offline demo fixtures
python -m src.cli.main sync --demo

# Sync with live Swiggy MCP token
python -m src.cli.main sync --token <YOUR_SWIGGY_TOKEN>
```

### 2. View Tracked Staples
```bash
python -m src.cli.main list
```

### 3. Inspect Price Timeline & Inflation Flags
```bash
python -m src.cli.main timeline oil
python -m src.cli.main timeline milk
```

### 4. Check Live Store Price vs. Past Purchases
```bash
python -m src.cli.main check "Sunflower Oil"
```

### 5. Launch the Web Dashboard & Grounded Copilot
```bash
# Launch the dashboard locally at http://127.0.0.1:8000
python -m uvicorn src.web.server:app --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to inspect your personal price intelligence vault, unit price timeline charts, live store deal radar, and interactive conversational copilot.

### 6. DPDP Full Data Erasure
```bash
python -m src.cli.main purge --confirm
```

---

## Running the Automated Test Suite

```bash
pytest -v
```
Runs all 29 automated tests covering pack parsing, unit price mathematics, SQLite idempotency, and security constraints.
