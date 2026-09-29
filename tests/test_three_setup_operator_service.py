from __future__ import annotations

import sqlite3
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from test_three_setup_operator_contracts import make_config, make_source

from trader_assist_v0.multi_asset_shadow.l1_approval import (
    ApprovalMode,
    AuthorityMode,
    HumanApprovalLedger,
    L1ContractError,
    StrategyOrderPackage,
)
from trader_assist_v0.multi_asset_shadow.shadow_records.records import MarketEvent
from trader_assist_v0.multi_asset_shadow.shadow_records.store import ReadOnlyEvidenceSnapshot
from trader_assist_v0.nautilus_e4.contracts import GuardInputs
from trader_assist_v0.operator.approval import CurrentGuardEvidence, OperatorBlocked, OperatorEngine
from trader_assist_v0.operator.projection import project_post_activation


def _now() -> int:
    return time.time_ns() // 1_000_000


def test_post_activation_approval_guard_fail_retry_and_replay(tmp_path: Path) -> None:
    now = _now()
    shadow_id = make_source(tmp_path / "runtime.sqlite", created_ms=now)
    engine = OperatorEngine(make_config(tmp_path))
    projection, _ = engine.latest(now_ms=now)
    args = {
        "shadow_id": shadow_id,
        "package_id": projection.package.package_id,
        "package_hash": projection.package.package_hash,
        "action_key": "post-action-key-123456789",
        "action": "APPROVE",
        "session_id": "s1",
    }
    assert engine.human_action(**args, now_ms=now + 1) == "NO_SUBMIT"
    assert engine.human_action(**args, now_ms=now + 2) == "NO_SUBMIT"
    assert OperatorEngine(make_config(tmp_path)).latest(now_ms=now + 3)[1] == "NO_SUBMIT"
    with pytest.raises(OperatorBlocked, match="altered payload"):
        engine.human_action(**{**args, "session_id": "different"}, now_ms=now + 4)
    with pytest.raises(OperatorBlocked, match="stale or altered"):
        engine.human_action(**{**args, "package_hash": "0" * 64}, now_ms=now + 5)
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM ts8_transitions").fetchone()[0] == 2
        row = connection.execute(
            "SELECT evidence_role, snapshot_digest FROM ts8_actions"
        ).fetchone()
        assert row[0] == "OBSERVED" and len(row[1]) == 64


def _preauthorized_package(tmp_path: Path, now: int) -> StrategyOrderPackage:
    config = make_config(tmp_path)
    with ReadOnlyEvidenceSnapshot(config.runtime_evidence_path) as source:
        post = project_post_activation(source, config, observed_ms=now)
    original = post.package
    details = dict(original.ts8_details or {})
    details["approval_mode"] = ApprovalMode.PREAUTHORIZED_ARMED.value
    details["armed_ts_ms"] = now - 2000
    details["source_ids"] = {"strategy_evaluation": details["source_ids"]["strategy_evaluation"]}
    details["source_hashes"] = {
        "strategy_evaluation": details["source_hashes"]["strategy_evaluation"]
    }
    return StrategyOrderPackage.create(
        parent_strategy_order_id=original.parent_strategy_order_id,
        strategy_version=original.strategy_version,
        parameter_version=original.parameter_version,
        created_server_ms=now - 1000,
        expires_server_ms=now + 100_000,
        activation_opportunity_id="kernel-opportunity-1",
        authority_mode=AuthorityMode.ZERO_WRITE,
        legs=(),
        ts8_details=details,
    )


def test_browser_absent_reconciler_restart_and_exact_once(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    package = _preauthorized_package(tmp_path, now)
    with sqlite3.connect(config.operator_ledger_path) as connection:
        ledger = HumanApprovalLedger(connection)
        assert (
            ledger.ts8_display(package, mode=ApprovalMode.PREAUTHORIZED_ARMED) == "ARMED_REVIEWABLE"
        )
        assert (
            ledger.ts8_action(
                package,
                action_key="armed-human-action-1234",
                request_digest="d" * 64,
                action="APPROVE",
                approval_mode=ApprovalMode.PREAUTHORIZED_ARMED,
                server_ms=now - 500,
                snapshot_digest="s" * 64,
                source_refs={"strategy_evaluation": "e" * 64},
            )
            == "APPROVED_WAITING_ACTIVATION"
        )
    engine = OperatorEngine(config)
    assert engine.reconcile_once(now_ms=now + 1) == 1
    assert engine.reconcile_once(now_ms=now + 2) == 0
    assert OperatorEngine(config).reconcile_once(now_ms=now + 3) == 0
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert (
            connection.execute(
                "SELECT state FROM ts8_state WHERE package_id = ?", (package.package_id,)
            ).fetchone()[0]
            == "NO_SUBMIT"
        )
        rows = connection.execute(
            "SELECT state, submission_status FROM ts8_transitions WHERE package_id = ?",
            (package.package_id,),
        ).fetchall()
        assert [row[0] for row in rows] == [
            "APPROVED_WAITING_ACTIVATION",
            "ACTIVATED_REVALIDATING",
            "NO_SUBMIT",
        ]
        assert all(row[1] == "NOT_SUBMITTED" for row in rows)


def test_wrong_activation_and_expiry_fail_closed(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    package = _preauthorized_package(tmp_path, now)
    details = dict(package.ts8_details or {})
    details["activation_trigger_id"] = "different-trigger"
    wrong = StrategyOrderPackage.create(
        parent_strategy_order_id=package.parent_strategy_order_id,
        strategy_version=package.strategy_version,
        parameter_version=package.parameter_version,
        created_server_ms=package.created_server_ms,
        expires_server_ms=package.expires_server_ms,
        activation_opportunity_id="different-trigger",
        legs=(),
        ts8_details=details,
    )
    with sqlite3.connect(config.operator_ledger_path) as connection:
        ledger = HumanApprovalLedger(connection)
        ledger.ts8_display(wrong, mode=ApprovalMode.PREAUTHORIZED_ARMED)
        ledger.ts8_action(
            wrong,
            action_key="wrong-armed-action-1234",
            request_digest="x" * 64,
            action="APPROVE",
            approval_mode=ApprovalMode.PREAUTHORIZED_ARMED,
            server_ms=now - 500,
            snapshot_digest="s" * 64,
            source_refs={},
        )
    engine = OperatorEngine(config)
    assert engine.reconcile_once(now_ms=now + 1) == 0
    assert engine.reconcile_once(now_ms=wrong.expires_server_ms) == 1
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert (
            connection.execute(
                "SELECT state FROM ts8_state WHERE package_id = ?", (wrong.package_id,)
            ).fetchone()[0]
            == "EXPIRED"
        )


def test_ambiguous_activation_never_advances_pending_approval(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    package = _preauthorized_package(tmp_path, now)
    stamp = datetime.fromtimestamp(now / 1000, tz=UTC).isoformat()
    conflicting = MarketEvent.create(
        identity={"sample": "conflicting-activation"},
        market_id="market-1",
        event_kind="BREAKOUT_RETEST",
        event_time=stamp,
        kernel_market_event_id="kernel-opportunity-1",
        side="LONG",
        setup_family="BREAKOUT_RETEST",
    )
    with sqlite3.connect(config.runtime_evidence_path) as connection:
        connection.execute(
            "INSERT INTO immutable_records VALUES (?, ?, ?, ?, ?)",
            (
                conflicting.record_id,
                conflicting.record_type,
                conflicting.canonical_hash,
                conflicting._identity_json,
                conflicting._payload_json,
            ),
        )
    with sqlite3.connect(config.operator_ledger_path) as connection:
        ledger = HumanApprovalLedger(connection)
        ledger.ts8_action(
            package,
            action_key="ambiguous-armed-action-1234",
            request_digest="d" * 64,
            action="APPROVE",
            approval_mode=ApprovalMode.PREAUTHORIZED_ARMED,
            server_ms=now - 500,
            snapshot_digest="s" * 64,
            source_refs={},
        )
    engine = OperatorEngine(config)
    assert engine.reconcile_once(now_ms=now + 1) == 0
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert connection.execute("SELECT state FROM ts8_state").fetchone()[0] == (
            "APPROVED_WAITING_ACTIVATION"
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM ts8_transitions WHERE state = 'WOULD_SUBMIT'"
        ).fetchone()[0] == 0
    assert engine.reconcile_once(now_ms=package.expires_server_ms) == 1


def test_ledger_rejects_second_human_action(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    package = _preauthorized_package(tmp_path, now)
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        ledger = HumanApprovalLedger(connection)
        ledger.ts8_display(package, mode=ApprovalMode.PREAUTHORIZED_ARMED)
        ledger.ts8_action(
            package,
            action_key="first-action-12345678",
            request_digest="d" * 64,
            action="APPROVE",
            approval_mode=ApprovalMode.PREAUTHORIZED_ARMED,
            server_ms=now - 500,
            snapshot_digest="s" * 64,
            source_refs={},
        )
        with pytest.raises(L1ContractError, match="no longer reviewable"):
            ledger.ts8_action(
                package,
                action_key="second-action-12345678",
                request_digest="d" * 64,
                action="APPROVE",
                approval_mode=ApprovalMode.PREAUTHORIZED_ARMED,
                server_ms=now - 400,
                snapshot_digest="s" * 64,
                source_refs={},
            )


def test_restart_before_activation_then_retained_exact_activation(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    package = _preauthorized_package(tmp_path, now)
    with sqlite3.connect(config.operator_ledger_path) as connection:
        ledger = HumanApprovalLedger(connection)
        ledger.ts8_display(package, mode=ApprovalMode.PREAUTHORIZED_ARMED)
        ledger.ts8_action(
            package, action_key="pre-restart-action-1234", request_digest="d" * 64,
            action="APPROVE", approval_mode=ApprovalMode.PREAUTHORIZED_ARMED,
            server_ms=now - 500, snapshot_digest="s" * 64, source_refs={},
        )
    with sqlite3.connect(config.runtime_evidence_path) as connection:
        rows = connection.execute(
            "SELECT * FROM immutable_records WHERE record_type IN ('market_event', 'shadow_order')"
        ).fetchall()
        for (name,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            "AND tbl_name = 'immutable_records'"
        ).fetchall():
            connection.execute(f'DROP TRIGGER "{name}"')
        connection.execute(
            "DELETE FROM immutable_records WHERE record_type IN ('market_event', 'shadow_order')"
        )
    assert OperatorEngine(config).reconcile_once(now_ms=now + 1) == 0
    with sqlite3.connect(config.runtime_evidence_path) as connection:
        connection.executemany("INSERT INTO immutable_records VALUES (?, ?, ?, ?, ?)", rows)
    assert OperatorEngine(config).reconcile_once(now_ms=now + 2) == 1
    assert OperatorEngine(config).reconcile_once(now_ms=now + 3) == 0


def test_post_action_rechecks_source_after_get(tmp_path: Path) -> None:
    now = _now()
    shadow_id = make_source(tmp_path / "runtime.sqlite", created_ms=now)
    engine = OperatorEngine(make_config(tmp_path))
    projection, _ = engine.latest(now_ms=now)
    with sqlite3.connect(tmp_path / "runtime.sqlite") as connection:
        for (name,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            "AND tbl_name = 'immutable_records'"
        ).fetchall():
            connection.execute(f'DROP TRIGGER "{name}"')
        connection.execute("DELETE FROM immutable_records WHERE record_id = ?", (shadow_id,))
    with pytest.raises(OperatorBlocked):
        engine.human_action(
            shadow_id=shadow_id, package_id=projection.package.package_id,
            package_hash=projection.package.package_hash,
            action_key="stale-browser-action-1234", action="APPROVE",
            session_id="s", now_ms=now + 1,
        )
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 0


def test_exact_frozen_guard_can_record_zero_write_would_submit(tmp_path: Path) -> None:
    now = _now()
    shadow_id = make_source(
        tmp_path / "runtime.sqlite", created_ms=now, policy_version="guard-v1"
    )
    def guard_reader(
        _source: ReadOnlyEvidenceSnapshot, _projection: object
    ) -> CurrentGuardEvidence:
        return CurrentGuardEvidence(
            inputs=GuardInputs(
                spread_bps=Decimal("1"), all_in_friction_bps=Decimal("2"),
                remaining_room_bps=Decimal("100"), minimum_room_to_cost=Decimal("1"),
                bbo_state_valid=True, data_evaluable=True,
                intended_notional=Decimal("2"), top_level_notional=Decimal("10"),
                guard_config_version="guard-v1",
            ),
            executable_price=Decimal("100.5"), source_ref="synthetic-bbo-ref",
        )
    engine = OperatorEngine(make_config(tmp_path), guard_reader=guard_reader)
    projection, _ = engine.latest(now_ms=now)
    assert engine.human_action(
        shadow_id=shadow_id, package_id=projection.package.package_id,
        package_hash=projection.package.package_hash,
        action_key="would-submit-action-1234", action="APPROVE",
        session_id="s", now_ms=now + 1,
    ) == "WOULD_SUBMIT"
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        assert connection.execute(
            "SELECT submission_status FROM ts8_transitions WHERE state = 'WOULD_SUBMIT'"
        ).fetchone()[0] == "NOT_SUBMITTED"
        assert connection.execute("SELECT COUNT(*) FROM ts8_transitions").fetchone()[0] == 2
