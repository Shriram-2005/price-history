from datetime import datetime, timezone
import pytest
from src.core.models import (
    BaseUnit,
    LineItem,
    MatchStatus,
    OrderHeader,
    PriceObservation,
)
from src.core.storage import Storage


@pytest.fixture
def test_db(tmp_path):
    """Creates an isolated temporary SQLite database for testing."""
    db_file = tmp_path / "test_price_history.db"
    return Storage(db_file)


def test_order_idempotency(test_db):
    """Asserts duplicate orders are detected and prevented."""
    order = OrderHeader(
        source_name="instamart",
        source_order_id="ORD_TEST_99",
        placed_at=datetime.now(timezone.utc),
        status="DELIVERED",
        total_paise=25000,
        raw_json={"orderId": "ORD_TEST_99"},
    )

    # First insert succeeds
    order_id_1 = test_db.insert_order(order)
    assert order_id_1 > 0
    assert test_db.order_exists("ORD_TEST_99", "instamart") is True

    # Duplicate check works
    assert test_db.order_exists("ORD_NON_EXISTENT", "instamart") is False


def test_timeline_and_hike_detection(test_db):
    """Verifies that price observations form a timeline with correct percentage flags."""
    # 1. Create canonical product
    product = test_db.get_or_create_product(
        canonical_name="Fortune Sunlite Sunflower Oil",
        brand="Fortune",
        category="Oil",
        base_unit=BaseUnit.ML,
        pack_size_base=1000,
    )

    # 2. Add first order (Baseline: ₹165 / L = 16.50 paise / ml)
    order1 = OrderHeader(
        source_name="instamart",
        source_order_id="ORD_1",
        placed_at=datetime(2026, 10, 1),
        status="DELIVERED",
        total_paise=16500,
    )
    o1_id = test_db.insert_order(order1)

    li1 = LineItem(
        order_id=o1_id,
        item_index=0,
        raw_name="Fortune Sunlite Sunflower Oil 1 L",
        quantity=1,
        line_total_paise=16500,
        product_id=product.id,
        match_status=MatchStatus.CONFIRMED,
        match_confidence=1.0,
    )
    li1_id = test_db.insert_line_item(li1)

    obs1 = PriceObservation(
        product_id=product.id,
        line_item_id=li1_id,
        observed_at=datetime(2026, 10, 1),
        unit_price_paise_per_base=16.50,
        quantity=1,
        total_paise=16500,
    )
    test_db.insert_price_observation(obs1)

    # 3. Add second order (Price hike: ₹185 / L = 18.50 paise / ml -> +12.1% increase)
    order2 = OrderHeader(
        source_name="instamart",
        source_order_id="ORD_2",
        placed_at=datetime(2026, 10, 15),
        status="DELIVERED",
        total_paise=18500,
    )
    o2_id = test_db.insert_order(order2)

    li2 = LineItem(
        order_id=o2_id,
        item_index=0,
        raw_name="Fortune Sunlite Sunflower Oil 1 L",
        quantity=1,
        line_total_paise=18500,
        product_id=product.id,
        match_status=MatchStatus.CONFIRMED,
        match_confidence=1.0,
    )
    li2_id = test_db.insert_line_item(li2)

    obs2 = PriceObservation(
        product_id=product.id,
        line_item_id=li2_id,
        observed_at=datetime(2026, 10, 15),
        unit_price_paise_per_base=18.50,
        quantity=1,
        total_paise=18500,
    )
    test_db.insert_price_observation(obs2)

    # 4. Query timeline
    timeline = test_db.get_timeline_for_product(product.id)
    assert len(timeline) == 2

    # Baseline assertion
    assert timeline[0].unit_price_inr == 165.00
    assert timeline[0].change_vs_previous_pct is None
    assert timeline[0].flag_higher is False

    # Price hike assertion
    assert timeline[1].unit_price_inr == 185.00
    assert timeline[1].change_vs_previous_pct == 12.1
    assert timeline[1].flag_higher is True  # Triggered > 5% flag


def test_purge_all_data(test_db):
    """Verifies complete DPDP erasure."""
    product = test_db.get_or_create_product(
        canonical_name="Amul Milk",
        brand="Amul",
        category="Dairy",
        base_unit=BaseUnit.ML,
        pack_size_base=500,
    )
    stats = test_db.get_summary_stats()
    assert stats["products_count"] == 1

    # Purge
    assert test_db.purge_all_data() is True
    stats_after = test_db.get_summary_stats()
    assert stats_after["products_count"] == 0
    assert stats_after["orders_count"] == 0
