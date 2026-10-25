"""Tests for idempotent sync orchestrator and multi-run stability."""

import pytest
from src.adapters.swiggy.adapter import SwiggyInstamartAdapter
from src.core.storage import Storage
from src.core.sync import SyncOrchestrator


@pytest.fixture
def sync_env(tmp_path):
    """Sets up an isolated database and mock adapter."""
    db_file = tmp_path / "sync_test.db"
    storage = Storage(db_file)
    adapter = SwiggyInstamartAdapter(use_demo_data=True)
    orchestrator = SyncOrchestrator(storage, adapter)
    return storage, orchestrator


def test_sync_first_run_and_idempotency(sync_env):
    storage, orchestrator = sync_env

    # 1. First run should process all 4 demo orders
    res1 = orchestrator.run_sync()
    assert res1["status"] == "success"
    assert res1["orders_seen"] == 4
    assert res1["orders_new"] == 4
    assert res1["observations_created"] > 0

    stats1 = storage.get_summary_stats()
    assert stats1["orders_count"] == 4
    assert stats1["observations_count"] > 0

    # 2. Second run immediately after should detect all orders as existing
    res2 = orchestrator.run_sync()
    assert res2["status"] == "success"
    assert res2["orders_seen"] == 4
    assert res2["orders_new"] == 0  # Zero new orders!
    assert res2["observations_created"] == 0  # Zero duplicates created!

    stats2 = storage.get_summary_stats()
    assert stats2["orders_count"] == 4  # Unchanged
    assert stats2["observations_count"] == stats1["observations_count"]  # Unchanged
