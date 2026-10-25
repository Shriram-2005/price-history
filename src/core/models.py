"""Core domain models for Price History.

Uses integer paise everywhere to eliminate IEEE 754 floating-point errors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class BaseUnit(str, Enum):
    """Normalized base units of measurement."""
    ML = "ml"       # Base unit for liquids (millilitres)
    G = "g"         # Base unit for solids (grams)
    PIECE = "pc"    # Base unit for discrete items (pieces/units)
    UNKNOWN = "unk" # When pack size cannot be reliably determined


class MatchStatus(str, Enum):
    """Confidence level of matching a line item to a canonical product."""
    CONFIRMED = "confirmed"   # Exact match (1.0) or user confirmed
    PROPOSED = "proposed"     # Automatically proposed by matching engine (>= 0.90)
    NEEDS_REVIEW = "review"   # Uncertain match (0.50 - 0.89), needs user review
    UNMATCHED = "unmatched"   # New product, no match found (< 0.50)


class PackInfo(BaseModel):
    """Parsed pack size information from raw product title."""
    base_unit: BaseUnit
    pack_size_base: int = Field(gt=0, description="Size in base units (ml, g, pieces)")
    display_unit: str = Field(description="Original unit from title (e.g. L, kg, ml)")
    display_quantity: float = Field(description="Quantity in display unit (e.g. 1.0, 500)")
    multiplier: int = Field(default=1, ge=1, description="For multi-packs like 2 x 500ml")
    free_quantity_base: int = Field(default=0, ge=0, description="Bonus quantity e.g. + 100g free")
    is_pack_of_n: bool = Field(default=False)
    raw_match: str = Field(default="", description="The matched text snippet")

    @property
    def total_base_units(self) -> int:
        """Total volume/weight/count in base unit including multipliers and bonus."""
        return (self.pack_size_base * self.multiplier) + self.free_quantity_base


class Product(BaseModel):
    """Canonical product in the system."""
    id: Optional[int] = None
    canonical_name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    base_unit: BaseUnit
    pack_size_base: int = Field(gt=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderHeader(BaseModel):
    """Order metadata from Swiggy Instamart."""
    id: Optional[int] = None
    source_name: str = "instamart"
    source_order_id: str
    placed_at: datetime
    status: str
    total_paise: int = Field(ge=0)
    raw_json: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LineItem(BaseModel):
    """Extracted line item from an invoice."""
    id: Optional[int] = None
    order_id: Optional[int] = None
    item_index: int = Field(ge=0)
    raw_name: str
    quantity: int = Field(gt=0)
    line_total_paise: int = Field(ge=0, description="Total amount paid for this item in paise")
    product_id: Optional[int] = None
    match_status: MatchStatus = MatchStatus.UNMATCHED
    match_confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class PriceObservation(BaseModel):
    """Normalized price observation point."""
    id: Optional[int] = None
    product_id: int
    line_item_id: int
    observed_at: datetime
    unit_price_paise_per_base: float = Field(
        ge=0.0,
        description="Paise per base unit (paise/ml, paise/g, or paise/piece)"
    )
    quantity: int = Field(gt=0)
    total_paise: int = Field(ge=0)
    is_promo: bool = False
    is_substitute: bool = False

    @property
    def price_per_standard_unit_inr(self) -> float:
        """Returns readable INR per Litre, per Kg, or per piece.
        
        Example:
        - 18.00 paise/ml -> 18.00 * 1000 / 100 = 180.00 INR/Litre
        - 5.00 paise/g  -> 5.00 * 1000 / 100  = 50.00 INR/Kg
        - 800 paise/pc  -> 800 / 100          = 8.00 INR/piece
        """
        # If product base is ml, standard unit is 1 L (1000 ml)
        # If product base is g, standard unit is 1 kg (1000 g)
        # If piece, standard unit is 1 pc
        return (self.unit_price_paise_per_base * 1000.0) / 100.0


class TimelinePoint(BaseModel):
    """Point in a product's price timeline for display."""
    order_id: str
    date: datetime
    raw_name: str
    quantity: int
    total_paid_inr: float
    unit_price_inr: float
    standard_unit_label: str  # "INR / L", "INR / kg", "INR / pc"
    change_vs_previous_pct: Optional[float] = None
    is_promo: bool = False
    flag_higher: bool = False


# Utility conversion functions with exact mathematical rounding
def rupees_to_paise(rupees: float | int) -> int:
    """Converts Rupees (float/int) to exact integer paise."""
    return int(round(rupees * 100))


def paise_to_rupees(paise: int) -> float:
    """Converts integer paise to Rupees (float rounded to 2 decimals)."""
    return round(paise / 100.0, 2)
