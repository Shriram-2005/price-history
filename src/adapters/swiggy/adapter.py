"""Swiggy Instamart MCP adapter.

Follows Swiggy Builders Club MCP specifications over Streamable HTTP.
Strictly read-only: Excludes checkout, payment, or cart modification tools by design.
Handles token auto-refresh on 401 / -32001 and HTTP 429 gateway backoff.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional
import httpx

from src.adapters.base import OrderSource
from src.adapters.swiggy.fixtures import DEMO_ORDERS
from src.adapters.swiggy.auth import (
    get_valid_access_token,
    load_token_payload,
    refresh_access_token,
)

logger = logging.getLogger(__name__)

SWIGGY_INSTAMART_ENDPOINT = "https://mcp.swiggy.com/im"

# Strictly permitted read-only tools
ALLOWED_TOOLS = {
    "get_orders",
    "get_order_details",
    "search_products",
    "get_addresses",
}

# Forbidden tools (Safety Assertions - FR-20)
FORBIDDEN_TOOLS = {
    "checkout",
    "confirm_order",
    "update_cart",
    "clear_cart",
    "apply_coupon",
    "check_payment_status",
}


class SwiggyInstamartAdapter(OrderSource):
    """Adapter connecting to Swiggy Instamart MCP server."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        use_demo_data: bool = False,
    ):
        if use_demo_data:
            self.access_token = access_token or "demo_token"
            self.use_demo_data = True
        else:
            self.access_token = access_token or get_valid_access_token()
            self.use_demo_data = not self.access_token

        # Security check: Ensure no forbidden tools are ever registered
        for tool in FORBIDDEN_TOOLS:
            assert tool not in ALLOWED_TOOLS, f"Security Violation: Forbidden tool {tool} in ALLOWED_TOOLS"

    def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Sends a JSON-RPC tool call to Swiggy MCP with 401 token refresh and 429 backoff."""
        if tool_name not in ALLOWED_TOOLS:
            raise PermissionError(f"Tool {tool_name} is not permitted in read-only adapter")

        if self.use_demo_data:
            return self._mock_call(tool_name, arguments)

        # Ensure we have a fresh token
        token = self.access_token or get_valid_access_token()
        if not token:
            raise PermissionError("No valid Swiggy MCP token found. Please run 'price-history login'.")

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": int(time.time()),
        }

        max_retries = 3
        for attempt in range(max_retries):
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            try:
                response = httpx.post(
                    SWIGGY_INSTAMART_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=20.0,
                )

                # Handle 401 Unauthorized / Token Expired
                if response.status_code == 401:
                    logger.warning("Received 401 from Swiggy MCP. Attempting token refresh...")
                    token_data = load_token_payload()
                    if token_data and "refresh_token" in token_data:
                        refreshed = refresh_access_token(token_data["refresh_token"])
                        if refreshed:
                            token = refreshed["access_token"]
                            self.access_token = token
                            continue
                    raise PermissionError("Swiggy session expired. Please re-authenticate using 'price-history login'.")

                # Handle HTTP 429 rate limit
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    logger.warning(f"Swiggy Gateway 429 received. Backing off for {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    err_code = data["error"].get("code")
                    err_msg = data["error"].get("message", "Unknown Swiggy MCP error")

                    # Handle JSON-RPC -32001 (Session / auth error)
                    if err_code == -32001:
                        logger.warning("Received JSON-RPC -32001 auth error. Attempting refresh...")
                        token_data = load_token_payload()
                        if token_data and "refresh_token" in token_data:
                            refreshed = refresh_access_token(token_data["refresh_token"])
                            if refreshed:
                                token = refreshed["access_token"]
                                self.access_token = token
                                continue
                        raise PermissionError("Swiggy MCP session invalid. Please run 'price-history login'.")

                    raise RuntimeError(f"Swiggy MCP error ({err_code}): {err_msg}")

                return data.get("result", {})

            except httpx.HTTPError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Network error communicating with Swiggy MCP: {e}")
                time.sleep(2 ** attempt)

        raise RuntimeError("Exceeded maximum retries for Swiggy MCP call")

    def _mock_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Provides realistic mock responses for testing and offline demo."""
        if tool_name == "get_orders":
            orders_summary = [
                {
                    "orderId": o["orderId"],
                    "status": o["status"],
                    "createdAt": o["createdAt"],
                    "totalAmount": o["totalAmount"],
                    "itemCount": len(o["items"]),
                    "items": [{"name": it["name"], "quantity": it["quantity"]} for it in o["items"]],
                }
                for o in DEMO_ORDERS
            ]
            return {"data": {"orders": orders_summary, "hasMore": False}, "success": True}

        elif tool_name == "get_order_details":
            order_id = arguments.get("orderId")
            for o in DEMO_ORDERS:
                if o["orderId"] == order_id:
                    return {
                        "data": {
                            "orderId": o["orderId"],
                            "status": o["status"],
                            "totalBill": o["totalAmount"],
                            "hasRefunds": False,
                            "items": o["items"],
                            "bill": o.get("bill", {}),
                        },
                        "success": True,
                    }
            return {"success": False, "error": {"message": f"Order {order_id} not found"}}

        elif tool_name == "search_products":
            query_tokens = set(arguments.get("query", "").lower().split())
            results = []
            seen_names = set()
            for o in DEMO_ORDERS:
                for it in o["items"]:
                    it_tokens = set(it["name"].lower().split())
                    if (query_tokens and query_tokens.issubset(it_tokens)) or arguments.get("query", "").lower() in it["name"].lower():
                        if it["name"] not in seen_names:
                            seen_names.add(it["name"])
                            results.append({
                                "name": it["name"],
                                "price": it["finalPrice"],
                                "storeAvailable": True,
                            })
            return {"data": {"products": results}, "success": True}

        return {"success": False, "error": {"message": f"Unhandled tool {tool_name}"}}

    def list_recent_orders(self, count: int = 20) -> List[Dict[str, Any]]:
        """Fetches the list of orders from the 15-day rolling window."""
        res = self._call_mcp_tool("get_orders", {"count": count, "orderType": "DASH"})
        return res.get("data", {}).get("orders", [])

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Fetches itemized details for an order."""
        res = self._call_mcp_tool("get_order_details", {"orderId": order_id})
        return res.get("data", {})

    def search_products(self, query: str, address_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches live store catalogue for current pricing."""
        args: Dict[str, Any] = {"query": query}
        if address_id:
            args["addressId"] = address_id
        res = self._call_mcp_tool("search_products", args)
        return res.get("data", {}).get("products", [])
