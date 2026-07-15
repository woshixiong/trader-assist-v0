from __future__ import annotations

import json
from pathlib import Path


def test_first_launch_governance_preserves_historical_capture_and_false_runtime_gates() -> None:
    state_path = (
        Path(__file__).resolve().parents[1] / "governance" / "FIRST_LAUNCH_ACTIVE_STATE.json"
    )
    state = json.loads(
        state_path.read_text(encoding="utf-8")
    )
    assert state["product_baseline_id"] == "TA-PRODUCT-BASELINE-2026-07-14-R1"
    assert state["active_product"] == "FIRST_LAUNCH"
    assert state["capture_history"] == "PRESERVED_AS_HISTORY"
    assert state["paused_products"] == ["FULL_V0", "TRADEROS"]
    assert all(value is False for value in state["authorizations"].values())
