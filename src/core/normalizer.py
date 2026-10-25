"""Pack size normalization and product title parsing engine.

Converts arbitrary grocery product names (e.g. "Fortune Sunlite Sunflower Oil 1 L",
"Amul Butter 100 g (Pack of 2)", "Surf Excel Liquid 2 L + 1 L Free") into
canonical units (ml, g, pc) and calculates standardized per-unit pricing.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple
from src.core.models import BaseUnit, PackInfo


# Regex patterns for unit recognition
LIQUID_PATTERN = re.compile(
    r"\b(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>ml|millilitre|milliliter|ltr|litre|liter|l)\b",
    re.IGNORECASE,
)
SOLID_PATTERN = re.compile(
    r"\b(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>kg|kgs|kilo|kilogram|gm|gms|gram|grams|g)\b",
    re.IGNORECASE,
)
PIECE_PATTERN = re.compile(
    r"\b(?P<qty>\d+)\s*(?P<unit>pcs|pc|piece|pieces|units|unit|tablets|tabs|eggs|capsules|bars)\b",
    re.IGNORECASE,
)

# Multiplier patterns: "2 x 500 ml", "4x250g", "3 * 100 g"
MULTIPLIER_PATTERN = re.compile(
    r"\b(?P<mult>\d+)\s*(?:x|\*)\s*(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>ml|l|ltr|litre|g|gm|kg|pc|pcs)\b",
    re.IGNORECASE,
)

# Free / Bonus patterns: "500 g + 100 g Free", "2 L + 1 L Free", "1 kg + 200 gm Extra"
BONUS_PATTERN = re.compile(
    r"\b(?P<base_qty>\d+(?:\.\d+)?)\s*(?P<base_unit>ml|l|ltr|litre|g|gm|kg)\s*\+\s*(?P<free_qty>\d+(?:\.\d+)?)\s*(?P<free_unit>ml|l|ltr|litre|g|gm|kg)\s*(?:free|extra)\b",
    re.IGNORECASE,
)

# Pack of N pattern: "Pack of 4", "Pack of 2"
PACK_OF_N_PATTERN = re.compile(
    r"\bpack\s+of\s+(?P<n>\d+)\b",
    re.IGNORECASE,
)

# Top FMCG brands in India for canonical extraction
KNOWN_BRANDS = [
    "Fortune", "Amul", "Aashirvaad", "Tata", "Saffola", "Dhara", "Gemini",
    "Sundrop", "Mother Dairy", "Nandini", "Dabur", "Patanjali", "Surf Excel",
    "Ariel", "Vim", "Dettol", "Colgate", "Maggi", "Sunfeast", "Britannia",
    "Parle", "Kellogg's", "Nestle", "Brooke Bond", "Taj Mahal", "Red Label",
    "Catch", "Everest", "MDH", "Haldiram's", "Bikaji", "Lipton", "Tata Tea",
    "Pillsbury", "Chakki", "Nature Fresh", "Gowardhan", "Epigamia", "Milky Mist",
    "Pampers", "Huggies", "Comfort", "Harpic", "Lizol", "Godrej", "Cinthol"
]


def _normalize_unit_and_size(qty: float, unit_str: str) -> Tuple[BaseUnit, int]:
    """Converts a raw quantity and unit string into base units (ml, g, pc)."""
    unit_lower = unit_str.lower().strip()

    # Liquids -> Millilitres
    if unit_lower in ("l", "ltr", "litre", "liter"):
        return BaseUnit.ML, int(round(qty * 1000))
    if unit_lower in ("ml", "millilitre", "milliliter"):
        return BaseUnit.ML, int(round(qty))

    # Solids -> Grams
    if unit_lower in ("kg", "kgs", "kilo", "kilogram"):
        return BaseUnit.G, int(round(qty * 1000))
    if unit_lower in ("g", "gm", "gms", "gram", "grams"):
        return BaseUnit.G, int(round(qty))

    # Discrete items -> Pieces
    if unit_lower in ("pc", "pcs", "piece", "pieces", "units", "unit", "tablets", "tabs", "eggs", "capsules", "bars"):
        return BaseUnit.PIECE, int(round(qty))

    return BaseUnit.UNKNOWN, int(round(qty))


def parse_pack_info(title: str) -> Optional[PackInfo]:
    """Parses pack size, multipliers, and units from a product name.
    
    Examples:
    - "Fortune Sunlite Sunflower Oil 1 L" -> BaseUnit.ML, 1000 ml
    - "Tata Salt Vacuum Evaporated 1 kg" -> BaseUnit.G, 1000 g
    - "Amul Taaza Milk 500 ml (Pack of 2)" -> BaseUnit.ML, 500 ml x 2 = 1000 ml
    - "Surf Excel Front Load 2 L + 1 L Free" -> BaseUnit.ML, 2000 ml + 1000 ml = 3000 ml
    - "Cadbury Dairy Milk 12 pcs" -> BaseUnit.PIECE, 12 pcs
    """
    if not title or not title.strip():
        return None

    cleaned_title = title.strip()

    # 1. Check for bonus/free patterns: "2 L + 1 L Free" or "500 g + 100 g Free"
    bonus_match = BONUS_PATTERN.search(cleaned_title)
    if bonus_match:
        base_qty = float(bonus_match.group("base_qty"))
        base_unit_str = bonus_match.group("base_unit")
        free_qty = float(bonus_match.group("free_qty"))
        free_unit_str = bonus_match.group("free_unit")

        base_unit, pack_size_base = _normalize_unit_and_size(base_qty, base_unit_str)
        free_unit, free_size_base = _normalize_unit_and_size(free_qty, free_unit_str)

        if base_unit == free_unit and base_unit != BaseUnit.UNKNOWN:
            return PackInfo(
                base_unit=base_unit,
                pack_size_base=pack_size_base,
                display_unit=base_unit_str,
                display_quantity=base_qty,
                multiplier=1,
                free_quantity_base=free_size_base,
                raw_match=bonus_match.group(0),
            )

    # 2. Check for explicit multipliers: "2 x 500 ml" or "4 x 250 g"
    mult_match = MULTIPLIER_PATTERN.search(cleaned_title)
    if mult_match:
        mult = int(mult_match.group("mult"))
        qty = float(mult_match.group("qty"))
        unit_str = mult_match.group("unit")
        base_unit, pack_size_base = _normalize_unit_and_size(qty, unit_str)
        if base_unit != BaseUnit.UNKNOWN and pack_size_base > 0:
            return PackInfo(
                base_unit=base_unit,
                pack_size_base=pack_size_base,
                display_unit=unit_str,
                display_quantity=qty,
                multiplier=mult,
                raw_match=mult_match.group(0),
            )

    # 3. Check for Pack of N with a preceding unit (e.g. "Amul Milk 500 ml (Pack of 2)")
    pack_of_n_match = PACK_OF_N_PATTERN.search(cleaned_title)
    pack_of_n = int(pack_of_n_match.group("n")) if pack_of_n_match else 1

    # Check liquid volume
    liquid_match = LIQUID_PATTERN.search(cleaned_title)
    if liquid_match:
        qty = float(liquid_match.group("qty"))
        unit_str = liquid_match.group("unit")
        base_unit, pack_size_base = _normalize_unit_and_size(qty, unit_str)
        if pack_size_base > 0:
            return PackInfo(
                base_unit=base_unit,
                pack_size_base=pack_size_base,
                display_unit=unit_str,
                display_quantity=qty,
                multiplier=pack_of_n,
                is_pack_of_n=bool(pack_of_n_match),
                raw_match=liquid_match.group(0),
            )

    # Check solid weight
    solid_match = SOLID_PATTERN.search(cleaned_title)
    if solid_match:
        qty = float(solid_match.group("qty"))
        unit_str = solid_match.group("unit")
        base_unit, pack_size_base = _normalize_unit_and_size(qty, unit_str)
        if pack_size_base > 0:
            return PackInfo(
                base_unit=base_unit,
                pack_size_base=pack_size_base,
                display_unit=unit_str,
                display_quantity=qty,
                multiplier=pack_of_n,
                is_pack_of_n=bool(pack_of_n_match),
                raw_match=solid_match.group(0),
            )

    # Check discrete count/piece
    piece_match = PIECE_PATTERN.search(cleaned_title)
    if piece_match:
        qty = float(piece_match.group("qty"))
        unit_str = piece_match.group("unit")
        base_unit, pack_size_base = _normalize_unit_and_size(qty, unit_str)
        if pack_size_base > 0:
            return PackInfo(
                base_unit=base_unit,
                pack_size_base=pack_size_base,
                display_unit=unit_str,
                display_quantity=qty,
                multiplier=pack_of_n,
                is_pack_of_n=bool(pack_of_n_match),
                raw_match=piece_match.group(0),
            )

    # If only "Pack of N" was found without specific units (e.g., "Avocado (Pack of 2)")
    if pack_of_n_match:
        return PackInfo(
            base_unit=BaseUnit.PIECE,
            pack_size_base=1,
            display_unit="pc",
            display_quantity=1.0,
            multiplier=pack_of_n,
            is_pack_of_n=True,
            raw_match=pack_of_n_match.group(0),
        )

    return None


def extract_brand(title: str) -> Optional[str]:
    """Extracts known Indian FMCG brand name from product title."""
    title_lower = title.lower()
    for brand in KNOWN_BRANDS:
        # Match brand as full word at start or anywhere in title
        if re.search(rf"\b{re.escape(brand.lower())}\b", title_lower):
            return brand
    return None


def clean_canonical_name(title: str, pack_info: Optional[PackInfo] = None) -> str:
    """Removes pack size, promo banners, and noise to derive canonical product name.
    
    Example:
    "Fortune Sunlite Refined Sunflower Oil 1 L Pouch (Save Rs 20)"
    -> "Fortune Sunlite Refined Sunflower Oil"
    """
    cleaned = title

    # Remove matched pack text
    if pack_info and pack_info.raw_match:
        cleaned = cleaned.replace(pack_info.raw_match, " ")

    # Remove promo text like "(Save Rs 20)", "Combo Offer", "Special Price"
    cleaned = re.sub(r"\((?:Save|Off|Pack of \d+|Special)[^)]*\)", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:Save\s+Rs\.?\s*\d+|Buy\s+\d+\s+Get\s+\d+|Pouch|Bottle|Jar|Box)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def compute_unit_price(
    line_total_paise: int,
    quantity: int,
    pack_info: PackInfo,
) -> float:
    """Computes price in paise per base unit.
    
    Formula:
    unit_price = line_total_paise / (quantity * total_base_units)
    
    Example:
    - 1 bottle of 1 L oil bought for ₹180 (18000 paise):
      18000 / (1 * 1000 ml) = 18.00 paise / ml.
    - 2 pouches of 500 ml oil bought for ₹200 (20000 paise total):
      20000 / (2 * 500 ml) = 20.00 paise / ml.
    """
    total_base_units = pack_info.total_base_units
    if total_base_units <= 0 or quantity <= 0:
        raise ValueError("Total base units and quantity must be positive")

    total_units_in_line = quantity * total_base_units
    return round(line_total_paise / total_units_in_line, 4)
