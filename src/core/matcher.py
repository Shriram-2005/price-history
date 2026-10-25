"""Product matching engine across raw line items and canonical products.

Implements the 3-stage matching pipeline:
1. Exact Match (confidence 1.0): normalized brand + canonical name + pack size.
2. Alias Match (confidence 0.95): matches a stored pattern or user-confirmed alias.
3. Token-Set Fuzzy Match (confidence 0.50 - 0.89): token similarity with same pack size.
Unmatched items create a new proposed canonical product. Never merges across pack sizes!
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from src.core.models import MatchStatus, PackInfo, Product


def _tokenize(text: str) -> set[str]:
    """Lowercases, removes punctuation, and splits into unique tokens."""
    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
    # Filter common stop words in grocery titles
    stop_words = {"refined", "pure", "fresh", "premium", "pouch", "bottle", "jar", "pack"}
    return {t for t in tokens if t not in stop_words and len(t) > 1}


def token_set_similarity(str1: str, str2: str) -> float:
    """Calculates Jaccard / token-set overlap similarity (0.0 to 1.0)."""
    tokens1 = _tokenize(str1)
    tokens2 = _tokenize(str2)
    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return round(intersection / union, 2)


class ProductMatcher:
    """Matches line items to canonical products with strict guardrails."""

    def __init__(self, existing_products: Optional[List[Product]] = None, aliases: Optional[dict[str, int]] = None):
        self.products = existing_products or []
        # maps raw_name_pattern -> product_id
        self.aliases = aliases or {}

    def match(
        self,
        raw_name: str,
        cleaned_canonical_name: str,
        brand: Optional[str],
        pack_info: PackInfo,
    ) -> Tuple[Optional[Product], MatchStatus, float]:
        """Finds the best matching canonical product.
        
        Returns:
            (Matched Product or None, MatchStatus, confidence_score)
        """
        # Rule 1: Stored Alias Match (confidence 0.95)
        clean_key = raw_name.strip().lower()
        if clean_key in self.aliases:
            target_id = self.aliases[clean_key]
            for p in self.products:
                if p.id == target_id:
                    return p, MatchStatus.CONFIRMED, 0.95

        # Rule 2: Exact Match on (canonical_name, base_unit, pack_size)
        # CRITICAL GUARD: Never match across different pack sizes!
        for p in self.products:
            if p.base_unit == pack_info.base_unit and p.pack_size_base == pack_info.total_base_units:
                if p.canonical_name.strip().lower() == cleaned_canonical_name.strip().lower():
                    return p, MatchStatus.CONFIRMED, 1.0

        # Rule 3: Fuzzy Token-Set Match on products WITH THE EXACT SAME PACK SIZE
        best_match: Optional[Product] = None
        best_score = 0.0

        for p in self.products:
            # Enforce same pack size and unit
            if p.base_unit != pack_info.base_unit or p.pack_size_base != pack_info.total_base_units:
                continue

            # Brand must match if both are present
            if brand and p.brand and brand.lower() != p.brand.lower():
                continue

            similarity = token_set_similarity(cleaned_canonical_name, p.canonical_name)
            if similarity > best_score:
                best_score = similarity
                best_match = p

        if best_match and best_score >= 0.90:
            return best_match, MatchStatus.PROPOSED, best_score
        elif best_match and best_score >= 0.50:
            return best_match, MatchStatus.NEEDS_REVIEW, best_score

        return None, MatchStatus.UNMATCHED, 0.0
