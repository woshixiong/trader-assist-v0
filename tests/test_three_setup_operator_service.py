from __future__ import annotations

import sqlite3
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_three_setup_operator_contracts import make_config, make_credential, make_source

from trader_assist_v0.multi_asset_shadow.l1_approval import (
    ApprovalMode,
    AuthorityMode,
    HumanApprovalLedger,
    L1ContractError,
    StrategyOrderPackage,
)
from trader_assist_v0.multi_asset_shadow.shadow_records.records import (
    MarketEvent,
    StrategyEvaluation,
)
from trader_assist_v0.multi_asset_shadow.shadow_records.store import ReadOnlyEvidenceSnapshot
from trader_assist_v0.nautilus_e4.contracts import GuardInputs
from trader_assist_v0.operator.approval import CurrentGuardEvidence, OperatorBlocked, OperatorEngine
from trader_assist_v0.operator.projection import project_post_activation
from trader_assist_v0.operator.security import OperatorSecurity
from trader_assist_v0.operator.service import create_app


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
    assert OperatorEngine(make_config(tmp_path)).latest(now_ms=now + 3)[1] == (
        "WAITING_FRESH_TRIGGER"
    )
    with pytest.raises(OperatorBlocked, match="altered payload"):
        engine.human_action(**{**args, "session_id": "different"}, now_ms=now + 4)
    with pytest.raises(OperatorBlocked, match="altered payload"):
        engine.human_action(**{**args, "package_hash": "0" * 64}, now_ms=now + 5)
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM ts8_transitions").fetchone()[0] == 3
        row = connection.execute(
            "SELECT evidence_role, snapshot_digest FROM ts8_actions"
        ).fetchone()
        assert row[0] == "OBSERVED" and len(row[1]) == 64


def _preauthorized_package(tmp_path: Path, now: int) -> StrategyOrderPackage:
    config = make_config(tmp_path, mode="PREAUTHORIZED_ARMED")
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
    config = make_config(tmp_path, mode="PREAUTHORIZED_ARMED")
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
            == "WAITING_FRESH_TRIGGER"
        )
        rows = connection.execute(
            "SELECT state, submission_status FROM ts8_transitions WHERE package_id = ?",
            (package.package_id,),
        ).fetchall()
        assert [row[0] for row in rows] == [
            "APPROVED_WAITING_ACTIVATION",
            "ACTIVATED_REVALIDATING",
            "NO_SUBMIT",
            "WAITING_FRESH_TRIGGER",
        ]
        assert all(row[1] == "NOT_SUBMITTED" for row in rows)


def test_wrong_activation_and_expiry_fail_closed(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path, mode="PREAUTHORIZED_ARMED")
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
    config = make_config(tmp_path, mode="PREAUTHORIZED_ARMED")
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
    config = make_config(tmp_path, mode="PREAUTHORIZED_ARMED")
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


def _post_args(engine: OperatorEngine, now: int, key: str) -> dict[str, str]:
    projection, _ = engine.latest(now_ms=now)
    return {
        "shadow_id": projection.package.parent_strategy_order_id,
        "package_id": projection.package.package_id,
        "package_hash": projection.package.package_hash,
        "action_key": key,
        "action": "APPROVE",
        "session_id": "operator-session",
    }


def test_post_expired_view_and_browserless_durable_terminal(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now - 400_000)
    config = make_config(tmp_path)
    engine = OperatorEngine(config)
    projection, state = engine.latest(now_ms=now)
    assert state == "EXPIRED"
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_state").fetchone()[0] == 0
    # The one server owner persists expiry even with no browser/SSE clients.
    assert engine.reconcile_once(now_ms=now) == 1
    app = create_app(config, make_credential(), engine=engine)
    _, cookie = OperatorSecurity(config, make_credential()).issue(authenticated=True)
    with TestClient(app, base_url="https://operator.test") as client:
        client.cookies.set("__Host-ts8-session", cookie, domain="operator.test", path="/")
        page = client.get("/")
        assert page.status_code == 200
        assert "BLOCKED · EXPIRED" in page.text
        assert 'data-action="APPROVE" disabled' in page.text
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert connection.execute(
            "SELECT state, submission_status FROM ts8_state WHERE package_id = ?",
            (projection.package.package_id,),
        ).fetchone() == ("EXPIRED", "NOT_SUBMITTED")
        assert connection.execute(
            "SELECT reason_codes_json FROM ts8_transitions WHERE state = 'EXPIRED'"
        ).fetchone()[0] == '["PACKAGE_EXPIRED"]'


def test_post_action_racing_expiry_persists_expired_without_human_action(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    engine = OperatorEngine(make_config(tmp_path))
    args = _post_args(engine, now, "expiry-race-action-1234")
    package, _ = engine.latest(now_ms=now)
    with pytest.raises(OperatorBlocked, match="expired"):
        engine.human_action(**args, now_ms=package.package.expires_server_ms)
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        assert connection.execute("SELECT state FROM ts8_state").fetchone()[0] == "EXPIRED"
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 0


def test_post_supersession_and_fresh_causal_package(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    engine = OperatorEngine(config)
    old_args = _post_args(engine, now, "old-package-action-1234")
    assert engine.reconcile_once(now_ms=now + 1) == 0
    make_source(
        tmp_path / "runtime.sqlite", created_ms=now + 1000,
        opportunity_suffix="-next",
    )
    assert engine.reconcile_once(now_ms=now + 1001) == 1
    new_args = _post_args(engine, now + 1001, "new-package-action-1234")
    assert old_args["package_id"] != new_args["package_id"]
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert connection.execute(
            "SELECT state FROM ts8_state WHERE package_id = ?",
            (old_args["package_id"],),
        ).fetchone()[0] == "SUPERSEDED"
        assert connection.execute(
            "SELECT state FROM ts8_state WHERE package_id = ?",
            (new_args["package_id"],),
        ).fetchone()[0] == "AWAITING_HUMAN_APPROVAL"
    assert engine.reconcile_once(now_ms=now + 1002) == 0
    assert engine.recent_terminal() == ("SUPERSEDED", old_args["package_id"])
    with pytest.raises(OperatorBlocked):
        engine.human_action(**old_args, now_ms=now + 1002)
    assert engine.human_action(**new_args, now_ms=now + 1002) == "NO_SUBMIT"


def test_definitive_thesis_conflict_terminal_but_source_unavailable_retries(
    tmp_path: Path,
) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    engine = OperatorEngine(config)
    assert engine.reconcile_once(now_ms=now + 1) == 0
    duplicate = StrategyEvaluation.create(
        identity={"sample": "conflicting-evaluation"},
        evaluation_id="evaluation-1",
        market_id="market-1",
        latest_closed_5m_hash="f" * 64,
        evaluation_boundary_ms=now + 1,
        registry_version="registry-v1",
        registry_hash="r" * 64,
        strategy_version="strategy-v1",
        parameter_version="params-v1",
        input_ledger_hash="c" * 64,
        output_ledger_hash="d" * 64,
        output_ledger={},
        decisions=[],
    )
    with sqlite3.connect(config.runtime_evidence_path) as connection:
        connection.execute(
            "INSERT INTO immutable_records VALUES (?, ?, ?, ?, ?)",
            (
                duplicate.record_id, duplicate.record_type, duplicate.canonical_hash,
                duplicate._identity_json, duplicate._payload_json,
            ),
        )
    assert engine.reconcile_once(now_ms=now + 2) == 1
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert connection.execute("SELECT state FROM ts8_state").fetchone()[0] == "THESIS_INVALID"
        assert connection.execute(
            "SELECT reason_codes_json FROM ts8_transitions WHERE state = 'THESIS_INVALID'"
        ).fetchone()[0] == '["RETAINED_THESIS_CONTRADICTION"]'
    assert engine.recent_terminal() is not None
    app = create_app(config, make_credential(), engine=engine)
    _, cookie = OperatorSecurity(config, make_credential()).issue(authenticated=True)
    with TestClient(app, base_url="https://operator.test") as client:
        client.cookies.set("__Host-ts8-session", cookie, domain="operator.test", path="/")
        page = client.get("/")
        assert page.status_code == 200
        assert "Latest terminal evidence: THESIS_INVALID" in page.text

    other = tmp_path / "unavailable"
    other.mkdir()
    make_source(other / "runtime.sqlite", created_ms=now)
    second = OperatorEngine(make_config(other))
    assert second.reconcile_once(now_ms=now + 1) == 0
    (other / "runtime.sqlite").rename(other / "source-held-away.sqlite")
    assert second.reconcile_once(now_ms=now + 2) == 0
    with sqlite3.connect(other / "operator.sqlite") as connection:
        assert connection.execute("SELECT state FROM ts8_state").fetchone()[0] == (
            "AWAITING_HUMAN_APPROVAL"
        )


def test_no_submit_waits_fresh_trigger_and_old_package_is_single_use(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    engine = OperatorEngine(make_config(tmp_path))
    old = _post_args(engine, now, "first-trigger-action-1234")
    assert engine.human_action(**old, now_ms=now + 1) == "NO_SUBMIT"
    assert engine.latest(now_ms=now + 2)[1] == "WAITING_FRESH_TRIGGER"
    with pytest.raises(OperatorBlocked, match="no longer reviewable"):
        engine.human_action(
            **{**old, "action_key": "second-old-action-1234"}, now_ms=now + 2
        )
    make_source(
        tmp_path / "runtime.sqlite", created_ms=now + 1000,
        opportunity_suffix="-fresh",
    )
    new = _post_args(engine, now + 1000, "fresh-trigger-action-1234")
    assert new["package_id"] != old["package_id"]
    assert engine.latest(now_ms=now + 1001)[1] == "AWAITING_HUMAN_APPROVAL"
    assert engine.human_action(**new, now_ms=now + 1001) == "NO_SUBMIT"
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM ts8_transitions WHERE state = 'WAITING_FRESH_TRIGGER'"
        ).fetchone()[0] == 2


def test_exact_action_replay_survives_source_removal_and_rejects_altered_payload(
    tmp_path: Path,
) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    engine = OperatorEngine(make_config(tmp_path))
    args = _post_args(engine, now, "durable-replay-action-1234")
    first = engine.human_action_record(**args, now_ms=now + 1)
    assert first.state == "NO_SUBMIT" and first.observed_server_ms == now + 1
    (tmp_path / "runtime.sqlite").rename(tmp_path / "runtime-removed.sqlite")
    assert engine.human_action_record(**args, now_ms=now + 200) == first
    with pytest.raises(OperatorBlocked, match="altered payload"):
        engine.human_action_record(
            **{**args, "package_hash": "0" * 64}, now_ms=now + 201
        )
    with pytest.raises(OperatorBlocked, match="altered payload"):
        engine.human_action_record(
            **{**args, "shadow_id": "0" * 64}, now_ms=now + 201
        )
    with pytest.raises(OperatorBlocked):
        engine.human_action_record(
            **{**args, "action_key": "new-action-after-removal-1234"}, now_ms=now + 202
        )
    with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 1


def test_exact_action_replay_after_source_supersession_and_http_time(tmp_path: Path) -> None:
    now = _now()
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    engine = OperatorEngine(config)
    args = _post_args(engine, now, "superseded-replay-action-1234")
    app = create_app(config, make_credential(), engine=engine)
    session, cookie = OperatorSecurity(config, make_credential()).issue(authenticated=True)
    body = {key: args[key] for key in (
        "shadow_id", "package_id", "package_hash", "action_key", "action"
    )}
    headers = {"Origin": "https://operator.test", "X-CSRF-Token": session.csrf}
    with TestClient(app, base_url="https://operator.test") as client:
        client.cookies.set("__Host-ts8-session", cookie, domain="operator.test", path="/")
        first = client.post("/api/action", json=body, headers=headers)
        assert first.status_code == 200
        assert first.json()["state"] == "NO_SUBMIT"
        observed = first.json()["observed_server_ms"]
        make_source(
            tmp_path / "runtime.sqlite", created_ms=now + 1000,
            opportunity_suffix="-replay-replacement",
        )
        replay = client.post("/api/action", json=body, headers=headers)
        assert replay.status_code == 200
        assert replay.json()["observed_server_ms"] == observed
        assert replay.json()["state"] == first.json()["state"]
