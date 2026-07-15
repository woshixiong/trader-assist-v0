from __future__ import annotations

import json
from pathlib import Path


def test_first_launch_governance_preserves_historical_capture_and_false_runtime_gates() -> None:
    governance = Path(__file__).resolve().parents[1] / "governance"
    state_path = governance / "FIRST_LAUNCH_ACTIVE_STATE.json"
    state = json.loads(
        state_path.read_text(encoding="utf-8")
    )
    assert state["product_baseline_id"] == "TA-PRODUCT-BASELINE-2026-07-14-R1"
    assert state["active_product"] == "FIRST_LAUNCH"
    assert state["capture_history"] == "PRESERVED_AS_HISTORY"
    assert state["paused_products"] == ["FULL_V0", "TRADEROS"]
    assert state["task_id"] == "NONE"
    assert state["branch"] == "NONE"
    assert state["write_lease"] == "NONE"
    assert state["write_lease_status"] == "NONE"
    assert all(value is False for value in state["authorizations"].values())

    fastsafe = (governance / "FASTSAFE_V1_MASTER_CONTROL_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    engineering_track = (governance / "ENGINEERING_AUTOMATION_TRACK_V1.md").read_text(
        encoding="utf-8"
    )
    assert "FASTSAFE-V1-2026-07" in fastsafe
    assert "TA-FASTSAFE-V1-2026-07-15-R1" not in fastsafe
    assert "ENGINEERING-AUTOMATION-TRACK-V1-2026-07" in engineering_track
    assert "TA-ENGINEERING-AUTOMATION-V1-2026-07-15-R1" not in engineering_track
