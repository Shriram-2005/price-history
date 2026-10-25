"""Tests for pack size normalizer and unit price calculation.

Verifies >= 95% parse accuracy on real Indian FMCG grocery pack patterns.
"""

import pytest
from src.core.models import BaseUnit, PackInfo
from src.core.normalizer import (
    _normalize_unit_and_size,
    clean_canonical_name,
    compute_unit_price,
    extract_brand,
    parse_pack_info,
)


@pytest.mark.parametrize(
    "title, expected_unit, expected_base_size",
    [
        # Liquids
        ("Fortune Sunlite Refined Sunflower Oil 1 L", BaseUnit.ML, 1000),
        ("Saffola Gold Blended Oil 5 L Can", BaseUnit.ML, 5000),
        ("Amul Taaza Homogenised Toned Milk 500 ml", BaseUnit.ML, 500),
        ("Nandini GoodLife Milk 200 ml", BaseUnit.ML, 200),
        ("Maaza Mango Drink 1.2 L Bottle", BaseUnit.ML, 1200),
        ("Coca Cola Soft Drink 750 ml", BaseUnit.ML, 750),

        # Solids
        ("Aashirvaad Superior MP Sharbati Atta 5 kg", BaseUnit.G, 5000),
        ("Aashirvaad Sharbati Atta 10 kg", BaseUnit.G, 10000),
        ("Tata Salt Vacuum Evaporated Iodised Salt 1 kg", BaseUnit.G, 1000),
        ("Fortune Besan 500 g", BaseUnit.G, 500),
        ("Tata Sampann Toor Dal 1 kg", BaseUnit.G, 1000),
        ("Maggi 2-Minute Masala Noodles 70 gm", BaseUnit.G, 70),
        ("Dabur Honey 250 g", BaseUnit.G, 250),

        # Multipliers
        ("Fortune Sunflower Oil 2 x 500 ml", BaseUnit.ML, 1000),
        ("Gemini Sunflower Oil 4 x 250 ml", BaseUnit.ML, 1000),
        ("Tata Tea Gold 2 x 500 g", BaseUnit.G, 1000),

        # Bonus / Free Combo Packs
        ("Surf Excel Matic Front Load Liquid 2 L + 1 L Free", BaseUnit.ML, 3000),
        ("Tata Tea Gold 500 g + 100 g Free", BaseUnit.G, 600),

        # Discrete / Pack of N
        ("Cadbury Dairy Milk Chocolate 10 pcs", BaseUnit.PIECE, 10),
        ("Amul Butter 100 g (Pack of 2)", BaseUnit.G, 200),
        ("Godrej Cinthol Lime Bath Soap (Pack of 4)", BaseUnit.PIECE, 4),
    ],
)
def test_pack_size_parsing(title, expected_unit, expected_base_size):
    pack_info = parse_pack_info(title)
    assert pack_info is not None, f"Failed to parse pack info from '{title}'"
    assert pack_info.base_unit == expected_unit
    assert pack_info.total_base_units == expected_base_size


def test_unit_price_math():
    """Property test: Verifies exact per-unit price calculations."""
    # 1 L bottle bought for ₹180 (18,000 paise)
    pack_1l = parse_pack_info("Fortune Sunflower Oil 1 L")
    assert pack_1l is not None
    unit_price_1l = compute_unit_price(line_total_paise=18000, quantity=1, pack_info=pack_1l)
    assert unit_price_1l == 18.00  # 18.00 paise per ml (= ₹180 / Litre)

    # 500 ml bottle bought for ₹100 (10,000 paise)
    pack_500ml = parse_pack_info("Fortune Sunflower Oil 500 ml")
    assert pack_500ml is not None
    unit_price_500ml = compute_unit_price(line_total_paise=10000, quantity=1, pack_info=pack_500ml)
    assert unit_price_500ml == 20.00  # 20.00 paise per ml (= ₹200 / Litre)

    # 500 ml bottle is more expensive per litre!
    assert unit_price_500ml > unit_price_1l


def test_brand_extraction():
    assert extract_brand("Fortune Sunlite Sunflower Oil 1 L") == "Fortune"
    assert extract_brand("Amul Taaza Toned Milk 500 ml") == "Amul"
    assert extract_brand("Aashirvaad Sharbati Atta 5 kg") == "Aashirvaad"
    assert extract_brand("Tata Salt 1 kg") == "Tata"
    assert extract_brand("Unknown Local Brand Salt 1 kg") is None
