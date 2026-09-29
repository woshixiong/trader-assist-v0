from __future__ import annotations

import sqlite3
import time
from decimal import Decimal
from pathlib import Path

import pytest
from test_three_setup_operator_contracts import make_config, make_source

from trader_assist_v0.multi_asset_shadow.shadow_records.records import StrategyEvaluation
from trader_assist_v0.multi_asset_shadow.shadow_records.store import ReadOnlyEvidenceSnapshot
from trader_assist_v0.operator.projection import (
    ProjectionBlocked,
    project_post_activation,
    project_preauthorized_armed,
)


def _now() -> int:
    return time.time_ns() // 1_000_000


def test_stable_package_and_explicit_reference_scenario(tmp_path: Path) -> None:
    now = _now()
    shadow_id = make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    with ReadOnlyEvidenceSnapshot(config.runtime_evidence_path) as source:
        first = project_post_activation(source, config, shadow_id=shadow_id, observed_ms=now)
    with ReadOnlyEvidenceSnapshot(config.runtime_evidence_path) as source:
        later = project_post_activation(source, config, shadow_id=shadow_id, observed_ms=now + 100)
    assert first.package.package_id == later.package.package_id
    assert first.snapshot_digest != later.snapshot_digest
    assert first.package.ts8_details["reference_quantity"] == "0.02"
    assert first.package.ts8_details["reference_notional"] == "2"
    assert Decimal(first.package.ts8_details["reference_risk_budget_usd"]) == Decimal("2")
    assert first.package.ts8_details["execution_eligible"] is False


def test_unresolved_scenario_and_unproven_armed_are_not_reviewable(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path, scenario=None)
    with ReadOnlyEvidenceSnapshot(config.runtime_evidence_path) as source:
        with pytest.raises(ProjectionBlocked, match="REFERENCE_SCENARIO_UNRESOLVED"):
            project_post_activation(source, config, observed_ms=now)
        with pytest.raises(ProjectionBlocked, match="EXACT_FIELDS_UNPROVEN"):
            project_preauthorized_armed(source, config, _observed_ms=now)


def test_tampered_retained_source_fails_closed(tmp_path: Path) -> None:
    now = _now()
    shadow_id = make_source(tmp_path / "runtime.sqlite", created_ms=now)
    with sqlite3.connect(tmp_path / "runtime.sqlite") as connection:
        triggers = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            "AND tbl_name = 'immutable_records'"
        ).fetchall()
        for (name,) in triggers:
            connection.execute(f'DROP TRIGGER "{name}"')
        connection.execute(
            "UPDATE immutable_records SET payload_json = '{}' WHERE record_id = ?", (shadow_id,)
        )
    with ReadOnlyEvidenceSnapshot(tmp_path / "runtime.sqlite") as source:
        with pytest.raises(ProjectionBlocked):
            project_post_activation(
                source, make_config(tmp_path), shadow_id=shadow_id, observed_ms=now
            )


def test_newer_strategy_evaluation_makes_browser_package_stale(tmp_path: Path) -> None:
    now = _now()
    shadow_id = make_source(tmp_path / "runtime.sqlite", created_ms=now)
    newer = StrategyEvaluation.create(
        identity={"sample": "newer-evaluation"}, evaluation_id="evaluation-2",
        market_id="market-1", latest_closed_5m_hash="b" * 64,
        evaluation_boundary_ms=now + 1, registry_version="registry-v1",
        registry_hash="r" * 64, strategy_version="strategy-v1",
        parameter_version="params-v1", input_ledger_hash="c" * 64,
        output_ledger_hash="d" * 64, output_ledger={}, decisions=[],
    )
    with sqlite3.connect(tmp_path / "runtime.sqlite") as connection:
        connection.execute(
            "INSERT INTO immutable_records VALUES (?, ?, ?, ?, ?)",
            (newer.record_id, newer.record_type, newer.canonical_hash,
             newer._identity_json, newer._payload_json),
        )
    with ReadOnlyEvidenceSnapshot(tmp_path / "runtime.sqlite") as source:
        with pytest.raises(ProjectionBlocked, match="stale or superseded"):
            project_post_activation(
                source, make_config(tmp_path), shadow_id=shadow_id, observed_ms=now + 2
            )
