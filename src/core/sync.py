"""Sync orchestrator engine for accumulating Swiggy orders into local SQLite.

Implements idempotent sync with per-order commits and automatic resumption.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.adapters.base import OrderSource
from src.core.models import (
    BaseUnit,
    LineItem,
    MatchStatus,
    OrderHeader,
    PriceObservation,
    rupees_to_paise,
)
from src.core.normalizer import (
    clean_canonical_name,
    compute_unit_price,
    extract_brand,
    parse_pack_info,
)
from src.core.matcher import ProductMatcher
from src.core.storage import Storage

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Manages idempotent synchronization from an OrderSource into local Storage."""

    def __init__(self, storage: Storage, order_source: OrderSource):
        self.storage = storage
        self.source = order_source

    def run_sync(self) -> Dict[str, Any]:
        """Executes an incremental sync run."""
        started_at = datetime.now(timezone.utc)
        source_id = self.storage.get_source_id("instamart")

        # Create sync_run record
        with self.storage.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO sync_runs (source_id, started_at, status) VALUES (?, ?, ?);",
                (source_id, started_at.isoformat(), "running"),
            )
            conn.commit()
            sync_run_id = cur.lastrowid

        orders_seen = 0
        orders_new = 0
        observations_created = 0
        errors = []

        try:
            # 1. Fetch recent orders from the 15-day window
            recent_orders = self.source.list_recent_orders(count=20)
            orders_seen = len(recent_orders)

            # Pre-load existing products for the matcher
            existing_products = self.storage.get_all_products()
            matcher = ProductMatcher(existing_products)

            for order_summary in recent_orders:
                order_id = order_summary["orderId"]

                # 2. Idempotency check: Skip if order already stored
                if self.storage.order_exists(order_id, "instamart"):
                    continue

                # 3. Fetch full invoice line items
                details = self.source.get_order_details(order_id)
                items = details.get("items", [])

                placed_at_str = order_summary.get("createdAt") or datetime.now(timezone.utc).isoformat()
                placed_at = datetime.fromisoformat(placed_at_str.replace("Z", "+00:00"))
                total_paise = rupees_to_paise(order_summary.get("totalAmount", 0.0))

                # 4. Atomic transaction per order
                with self.storage.transaction() as conn:
                    # Insert order header
                    order_header = OrderHeader(
                        source_name="instamart",
                        source_order_id=order_id,
                        placed_at=placed_at,
                        status=order_summary.get("status", "DELIVERED"),
                        total_paise=total_paise,
                        raw_json=details,
                    )
                    db_order_id = self.storage.insert_order(order_header, conn=conn)

                    # Process line items
                    for idx, it in enumerate(items):
                        raw_name = it["name"]
                        quantity = int(it.get("quantity", 1))
                        final_price_rupees = float(it.get("finalPrice", 0.0))
                        line_total_paise = rupees_to_paise(final_price_rupees)
                        is_removed = bool(it.get("removed", False))

                        if is_removed or line_total_paise <= 0:
                            continue

                        # Parse pack size
                        pack_info = parse_pack_info(raw_name)
                        if not pack_info:
                            # Item with unparseable pack size - store line item without observation
                            line_item = LineItem(
                                order_id=db_order_id,
                                item_index=idx,
                                raw_name=raw_name,
                                quantity=quantity,
                                line_total_paise=line_total_paise,
                                match_status=MatchStatus.UNMATCHED,
                                match_confidence=0.0,
                            )
                            self.storage.insert_line_item(line_item, conn=conn)
                            continue

                        brand = extract_brand(raw_name)
                        canonical_name = clean_canonical_name(raw_name, pack_info)

                        # Match with canonical products
                        matched_product, match_status, confidence = matcher.match(
                            raw_name=raw_name,
                            cleaned_canonical_name=canonical_name,
                            brand=brand,
                            pack_info=pack_info,
                        )

                        if not matched_product:
                            # Create new canonical product
                            matched_product = self.storage.get_or_create_product(
                                canonical_name=canonical_name,
                                brand=brand,
                                category=None,
                                base_unit=pack_info.base_unit,
                                pack_size_base=pack_info.total_base_units,
                                conn=conn,
                            )
                            matcher.products.append(matched_product)
                            match_status = MatchStatus.PROPOSED
                            confidence = 1.0

                        # Insert line item
                        line_item = LineItem(
                            order_id=db_order_id,
                            item_index=idx,
                            raw_name=raw_name,
                            quantity=quantity,
                            line_total_paise=line_total_paise,
                            product_id=matched_product.id,
                            match_status=match_status,
                            match_confidence=confidence,
                        )
                        db_line_id = self.storage.insert_line_item(line_item, conn=conn)

                        # Compute per-unit price in paise/base_unit
                        unit_price_paise = compute_unit_price(
                            line_total_paise=line_total_paise,
                            quantity=quantity,
                            pack_info=pack_info,
                        )

                        # Insert price observation
                        obs = PriceObservation(
                            product_id=matched_product.id,
                            line_item_id=db_line_id,
                            observed_at=placed_at,
                            unit_price_paise_per_base=unit_price_paise,
                            quantity=quantity,
                            total_paise=line_total_paise,
                            is_promo=False,
                            is_substitute=False,
                        )
                        self.storage.insert_price_observation(obs, conn=conn)
                        observations_created += 1

                orders_new += 1

            # Update sync_run as success
            finished_at = datetime.now(timezone.utc)
            with self.storage.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE sync_runs 
                    SET finished_at = ?, orders_seen = ?, orders_new = ?, status = ?
                    WHERE id = ?;
                    """,
                    (finished_at.isoformat(), orders_seen, orders_new, "success", sync_run_id),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            finished_at = datetime.now(timezone.utc)
            with self.storage.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE sync_runs 
                    SET finished_at = ?, orders_seen = ?, orders_new = ?, status = ?, error_message = ?
                    WHERE id = ?;
                    """,
                    (finished_at.isoformat(), orders_seen, orders_new, "failed", str(e), sync_run_id),
                )
                conn.commit()
            raise

        return {
            "status": "success",
            "orders_seen": orders_seen,
            "orders_new": orders_new,
            "observations_created": observations_created,
            "duration_seconds": round((datetime.now(timezone.utc) - started_at).total_seconds(), 2),
        }
