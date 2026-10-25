"""Abstract OrderSource adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class OrderSource(ABC):
    """Abstract interface isolating platform-specific APIs from core price intelligence."""

    @abstractmethod
    def list_recent_orders(self, count: int = 20) -> List[Dict[str, Any]]:
        """Fetches the latest orders available from the platform."""
        pass

    @abstractmethod
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Fetches itemized invoice details for a specific order."""
        pass

    @abstractmethod
    def search_products(self, query: str, address_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches live store catalogue for current pricing."""
        pass
