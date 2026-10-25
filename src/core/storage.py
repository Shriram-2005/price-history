"""SQLite storage engine with strict constraints, integer paise, and atomic transactions.

Supports local-first persistence, DPDP-compliant complete erasure, and raw payload retention.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from src.core.models import (
    BaseUnit,
    LineItem,
    MatchStatus,
    OrderHeader,
    PriceObservation,
    Product,
    TimelinePoint,
    paise_to_rupees,
)


def get_default_db_path() -> Path:
    """Returns the default secure path for the local SQLite database.
    
    Serverless (Vercel/Lambda): /tmp/price_history.db
    Windows: %LOCALAPPDATA%/price_history/price_history.db
    macOS/Linux: ~/.local/share/price_history/price_history.db
    """
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return Path("/tmp/price_history.db")

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    try:
        app_dir = base / "price_history"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "price_history.db"
    except (OSError, PermissionError):
        return Path("/tmp/price_history.db")


class Storage:
    """Database repository for local-first price history."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            pass
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys and WAL enabled."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides an atomic transaction block with automatic rollback on error."""
        conn = self.get_connection()
        try:
            conn.execute("BEGIN TRANSACTION;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes tables, indices, and constraints."""
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                adapter_version TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL REFERENCES sources(id),
                source_order_id TEXT NOT NULL,
                placed_at TEXT NOT NULL,
                status TEXT NOT NULL,
                total_paise INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_id, source_order_id)
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name TEXT NOT NULL,
                brand TEXT,
                category TEXT,
                base_unit TEXT NOT NULL,
                pack_size_base INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(canonical_name, base_unit, pack_size_base)
            );

            CREATE TABLE IF NOT EXISTS product_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id),
                raw_name_pattern TEXT NOT NULL UNIQUE,
                confidence REAL NOT NULL,
                created_by TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                item_index INTEGER NOT NULL,
                raw_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                line_total_paise INTEGER NOT NULL,
                product_id INTEGER REFERENCES products(id),
                match_status TEXT NOT NULL,
                match_confidence REAL NOT NULL,
                UNIQUE(order_id, item_index)
            );

            CREATE TABLE IF NOT EXISTS price_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id),
                line_item_id INTEGER NOT NULL REFERENCES line_items(id) ON DELETE CASCADE,
                observed_at TEXT NOT NULL,
                unit_price_paise_per_base REAL NOT NULL,
                quantity INTEGER NOT NULL,
                total_paise INTEGER NOT NULL,
                is_promo BOOLEAN NOT NULL DEFAULT 0,
                is_substitute BOOLEAN NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL REFERENCES sources(id),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                orders_seen INTEGER NOT NULL DEFAULT 0,
                orders_new INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- Indices for lightning-fast timeline queries
            CREATE INDEX IF NOT EXISTS idx_orders_placed_at ON orders(placed_at);
            CREATE INDEX IF NOT EXISTS idx_obs_product_observed ON price_observations(product_id, observed_at);
            CREATE INDEX IF NOT EXISTS idx_line_items_product ON line_items(product_id);
            """)

            # Pre-register instamart source
            conn.execute(
                "INSERT OR IGNORE INTO sources (name, adapter_version) VALUES (?, ?);",
                ("instamart", "1.0.0"),
            )
            conn.commit()

    # Source operations
    def get_source_id(self, name: str = "instamart") -> int:
        with self.get_connection() as conn:
            row = conn.execute("SELECT id FROM sources WHERE name = ?;", (name,)).fetchone()
            if row:
                return row["id"]
            cur = conn.execute("INSERT INTO sources (name, adapter_version) VALUES (?, ?);", (name, "1.0.0"))
            conn.commit()
            return cur.lastrowid

    # Order operations
    def order_exists(self, source_order_id: str, source_name: str = "instamart") -> bool:
        source_id = self.get_source_id(source_name)
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM orders WHERE source_id = ? AND source_order_id = ?;",
                (source_id, source_order_id),
            ).fetchone()
            return row is not None

    def insert_order(
        self,
        order: OrderHeader,
        conn: Optional[sqlite3.Connection] = None,
    ) -> int:
        source_id = self.get_source_id(order.source_name)
        raw_json_str = json.dumps(order.raw_json or {})

        sql = """
        INSERT INTO orders (source_id, source_order_id, placed_at, status, total_paise, raw_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            source_id,
            order.source_order_id,
            order.placed_at.isoformat(),
            order.status,
            order.total_paise,
            raw_json_str,
            order.created_at.isoformat(),
        )

        if conn is not None:
            cur = conn.execute(sql, params)
            return cur.lastrowid
        else:
            with self.get_connection() as c:
                cur = c.execute(sql, params)
                c.commit()
                return cur.lastrowid

    def get_latest_order_timestamp(self, source_name: str = "instamart") -> Optional[datetime]:
        source_id = self.get_source_id(source_name)
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT placed_at FROM orders WHERE source_id = ? ORDER BY placed_at DESC LIMIT 1;",
                (source_id,),
            ).fetchone()
            if row and row["placed_at"]:
                return datetime.fromisoformat(row["placed_at"])
            return None

    # Product operations
    def get_or_create_product(
        self,
        canonical_name: str,
        brand: Optional[str],
        category: Optional[str],
        base_unit: BaseUnit,
        pack_size_base: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Product:
        now = datetime.now(timezone.utc)
        sql_find = """
        SELECT id, canonical_name, brand, category, base_unit, pack_size_base, created_at
        FROM products
        WHERE canonical_name = ? AND base_unit = ? AND pack_size_base = ?;
        """
        params_find = (canonical_name, base_unit.value, pack_size_base)

        c = conn if conn is not None else self.get_connection()
        try:
            row = c.execute(sql_find, params_find).fetchone()
            if row:
                return Product(
                    id=row["id"],
                    canonical_name=row["canonical_name"],
                    brand=row["brand"],
                    category=row["category"],
                    base_unit=BaseUnit(row["base_unit"]),
                    pack_size_base=row["pack_size_base"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )

            sql_insert = """
            INSERT INTO products (canonical_name, brand, category, base_unit, pack_size_base, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """
            cur = c.execute(sql_insert, (canonical_name, brand, category, base_unit.value, pack_size_base, now.isoformat()))
            if conn is None:
                c.commit()
            return Product(
                id=cur.lastrowid,
                canonical_name=canonical_name,
                brand=brand,
                category=category,
                base_unit=base_unit,
                pack_size_base=pack_size_base,
                created_at=now,
            )
        finally:
            if conn is None:
                c.close()

    def get_all_products(self) -> List[Product]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, canonical_name, brand, category, base_unit, pack_size_base, created_at FROM products ORDER BY canonical_name ASC;"
            ).fetchall()
            return [
                Product(
                    id=r["id"],
                    canonical_name=r["canonical_name"],
                    brand=r["brand"],
                    category=r["category"],
                    base_unit=BaseUnit(r["base_unit"]),
                    pack_size_base=r["pack_size_base"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]

    # Line item & observation operations
    def insert_line_item(self, item: LineItem, conn: Optional[sqlite3.Connection] = None) -> int:
        sql = """
        INSERT INTO line_items (order_id, item_index, raw_name, quantity, line_total_paise, product_id, match_status, match_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            item.order_id,
            item.item_index,
            item.raw_name,
            item.quantity,
            item.line_total_paise,
            item.product_id,
            item.match_status.value,
            item.match_confidence,
        )
        if conn is not None:
            return conn.execute(sql, params).lastrowid
        with self.get_connection() as c:
            cur = c.execute(sql, params)
            c.commit()
            return cur.lastrowid

    def insert_price_observation(self, obs: PriceObservation, conn: Optional[sqlite3.Connection] = None) -> int:
        sql = """
        INSERT INTO price_observations (product_id, line_item_id, observed_at, unit_price_paise_per_base, quantity, total_paise, is_promo, is_substitute)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            obs.product_id,
            obs.line_item_id,
            obs.observed_at.isoformat(),
            obs.unit_price_paise_per_base,
            obs.quantity,
            obs.total_paise,
            int(obs.is_promo),
            int(obs.is_substitute),
        )
        if conn is not None:
            return conn.execute(sql, params).lastrowid
        with self.get_connection() as c:
            cur = c.execute(sql, params)
            c.commit()
            return cur.lastrowid

    # Timeline & Analytics Queries
    def get_timeline_for_product(self, product_id: int) -> List[TimelinePoint]:
        """Fetches chronological price observations for a product with percentage changes."""
        sql = """
        SELECT 
            o.source_order_id,
            po.observed_at,
            li.raw_name,
            po.quantity,
            po.total_paise,
            po.unit_price_paise_per_base,
            po.is_promo,
            p.base_unit,
            p.pack_size_base
        FROM price_observations po
        JOIN line_items li ON po.line_item_id = li.id
        JOIN orders o ON li.order_id = o.id
        JOIN products p ON po.product_id = p.id
        WHERE po.product_id = ?
        ORDER BY po.observed_at ASC;
        """
        with self.get_connection() as conn:
            rows = conn.execute(sql, (product_id,)).fetchall()

        timeline: List[TimelinePoint] = []
        prev_price_per_std: Optional[float] = None

        for r in rows:
            base_unit = BaseUnit(r["base_unit"])
            unit_paise_per_base = r["unit_price_paise_per_base"]

            # Calculate price per standard unit (1 L, 1 kg, or 1 pc)
            if base_unit in (BaseUnit.ML, BaseUnit.G):
                std_price_inr = round((unit_paise_per_base * 1000.0) / 100.0, 2)
                unit_label = "₹ / L" if base_unit == BaseUnit.ML else "₹ / kg"
            else:
                std_price_inr = round(unit_paise_per_base / 100.0, 2)
                unit_label = "₹ / pc"

            change_pct: Optional[float] = None
            flag_higher = False

            if prev_price_per_std is not None and prev_price_per_std > 0:
                change_pct = round(((std_price_inr - prev_price_per_std) / prev_price_per_std) * 100.0, 1)
                # Flag price increase >= 5% if previous was not promo
                if change_pct >= 5.0 and not r["is_promo"]:
                    flag_higher = True

            timeline.append(
                TimelinePoint(
                    order_id=r["source_order_id"],
                    date=datetime.fromisoformat(r["observed_at"]),
                    raw_name=r["raw_name"],
                    quantity=r["quantity"],
                    total_paid_inr=paise_to_rupees(r["total_paise"]),
                    unit_price_inr=std_price_inr,
                    standard_unit_label=unit_label,
                    change_vs_previous_pct=change_pct,
                    is_promo=bool(r["is_promo"]),
                    flag_higher=flag_higher,
                )
            )
            # Update previous non-promo baseline
            if not r["is_promo"]:
                prev_price_per_std = std_price_inr

        return timeline

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns overview counts of orders, products, and observations."""
        with self.get_connection() as conn:
            orders_count = conn.execute("SELECT COUNT(*) as c FROM orders;").fetchone()["c"]
            products_count = conn.execute("SELECT COUNT(*) as c FROM products;").fetchone()["c"]
            obs_count = conn.execute("SELECT COUNT(*) as c FROM price_observations;").fetchone()["c"]
            return {
                "orders_count": orders_count,
                "products_count": products_count,
                "observations_count": obs_count,
                "db_path": str(self.db_path),
            }

    # DPDP Complete Erasure (FR-12)
    def purge_all_data(self) -> bool:
        """Completely purges database tables and user data."""
        with self.get_connection() as conn:
            conn.executescript("""
            DELETE FROM price_observations;
            DELETE FROM line_items;
            DELETE FROM product_aliases;
            DELETE FROM products;
            DELETE FROM orders;
            DELETE FROM sync_runs;
            DELETE FROM user_settings;
            VACUUM;
            """)
            conn.commit()
        return True
