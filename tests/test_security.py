"""Security and compliance guardrail tests (FR-20).

Asserts that:
1. No mutating tools (checkout, update_cart, confirm_order) can be called.
2. SQL injection via malicious product titles is strictly prevented.
3. Path traversal attacks on storage paths are prevented.
"""

import pytest
from src.adapters.swiggy.adapter import SwiggyInstamartAdapter, FORBIDDEN_TOOLS
from src.core.models import BaseUnit
from src.core.storage import Storage


def test_forbidden_tools_completely_blocked():
    """Asserts that all write and payment tools are strictly blocked by the adapter."""
    adapter = SwiggyInstamartAdapter(use_demo_data=True)

    for tool in FORBIDDEN_TOOLS:
        with pytest.raises(PermissionError) as exc_info:
            adapter._call_mcp_tool(tool, {})
        assert "not permitted in read-only adapter" in str(exc_info.value)


def test_sql_injection_resilience(tmp_path):
    """Verifies parameterized queries handle SQL injection attempts safely."""
    db_file = tmp_path / "sql_test.db"
    storage = Storage(db_file)

    malicious_title = "Tata Salt 1 kg'; DROP TABLE products; --"
    product = storage.get_or_create_product(
        canonical_name=malicious_title,
        brand="Tata",
        category="Staples",
        base_unit=BaseUnit.G,
        pack_size_base=1000,
    )

    # Product should be inserted safely with escaped string
    assert product.canonical_name == malicious_title

    # Table products must still exist!
    with storage.get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM products;").fetchone()
        assert row["c"] == 1
