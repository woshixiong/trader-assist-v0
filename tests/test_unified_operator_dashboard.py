"""D1 display-only authority and centralized form transport checks."""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from test_three_setup_operator_contracts import make_config, make_credential, make_source

from trader_assist_v0.multi_asset_shadow.l1_approval import ApprovalMode, HumanApprovalLedger
from trader_assist_v0.multi_asset_shadow.shadow_records.store import EvidenceStore
from trader_assist_v0.operator.approval import OperatorEngine
from trader_assist_v0.operator.dashboard import EVENT_LIMIT, _recent_events, build_dashboard
from trader_assist_v0.operator.registry import ModuleSpec, validate_registry
from trader_assist_v0.operator.security import OperatorSecurity
from trader_assist_v0.operator.service import create_app


def _authenticated_client(tmp_path: Path) -> tuple[TestClient, dict[str, str]]:
    config = make_config(tmp_path)
    app = create_app(config, make_credential())
    client = TestClient(app, base_url="https://operator.test")
    client.__enter__()
    _, cookie = OperatorSecurity(config, make_credential()).issue(authenticated=True)
    client.cookies.set("__Host-ts8-session", cookie, domain="operator.test", path="/")
    page = client.get("/")
    assert page.status_code == 200
    fields = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', page.text))
    return client, fields


def test_one_current_reference_only_card_and_unknown_health(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    client, fields = _authenticated_client(tmp_path)
    try:
        page = client.get("/")
        assert page.text.count('id="opportunity-card"') == 1
        assert "Trade Gate: PASS" in page.text
        assert "OVERALL <strong class=\"status-unknown\">UNKNOWN" in page.text
        assert "reference only" in page.text
        assert "NOT_AVAILABLE" in page.text
        assert "Margin USD" not in page.text
        assert "Manual Close" not in page.text
        assert "Realized PnL" not in page.text
        assert fields["package_id"]
    finally:
        client.__exit__(None, None, None)


def test_missing_source_blocks_and_valid_empty_source_is_idle(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    model = build_dashboard(OperatorEngine(config), config)
    assert model.overall == "BLOCKED" and model.package_gate == "BLOCKED"
    with EvidenceStore(config.runtime_evidence_path):
        pass
    model = build_dashboard(OperatorEngine(config), config)
    assert model.state == "NO_OPPORTUNITY" and model.overall == "UNKNOWN"


def test_fixed_module_registry_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_registry((ModuleSpec("same", "A", "three_setup_nautilus", "three_setup_current"),
                           ModuleSpec("same", "B", "three_setup_nautilus", "three_setup_current")))
    with pytest.raises(ValueError, match="unknown"):
        validate_registry((ModuleSpec("other", "Other", "dynamic_plugin", "three_setup_current"),))
    with pytest.raises(ValueError, match="builder"):
        validate_registry((ModuleSpec("other", "Other", "three_setup_nautilus", "dynamic"),))


def test_no_js_form_uses_server_action_and_rejects_bad_transport(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    client, fields = _authenticated_client(tmp_path)
    try:
        origin = {"Origin": "https://operator.test"}
        action = {**fields, "action": "REJECT"}
        for headers, data, status in (
            ({}, action, 403),
            ({"Origin": "https://evil.test"}, action, 403),
            (origin, {**action, "csrf_token": "wrong"}, 403),
            (origin, {**action, "extra": "1"}, 400),
            (origin, urlencode(action) + "&csrf_token=duplicate", 400),
            (origin, urlencode(action) + "&action=APPROVE", 400),
            (origin, "csrf_token=%ZZ", 400),
            (origin, "x=" * 3000, 413),
        ):
            if isinstance(data, str):
                headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}
            response = client.post("/action", content=data if isinstance(data, str) else None,
                                   data=data if isinstance(data, dict) else None,
                                   headers=headers, follow_redirects=False)
            assert response.status_code == status
        assert client.post("/action", json=action, headers=origin).status_code == 415
        assert client.post(
            "/action", content=urlencode(action),
            headers={**origin, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        ).status_code == 415
        assert client.post(
            "/action", content=b"csrf_token=%FF",
            headers={**origin, "Content-Type": "application/x-www-form-urlencoded"},
        ).status_code == 400
        assert client.post("/action", data=action, headers={**origin, "Host": "wrong.test"}
                           ).status_code == 400
        with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
            assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 0
        accepted = client.post("/action", data=action, headers=origin, follow_redirects=False)
        assert accepted.status_code == 303
        page = client.get("/")
        assert "REJECTED" in page.text and 'data-action="APPROVE"' not in page.text
        with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
            assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 1
    finally:
        client.__exit__(None, None, None)


def test_no_js_approve_remains_zero_write_and_card_persists(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    client, fields = _authenticated_client(tmp_path)
    try:
        result = client.post(
            "/action", data={**fields, "action": "APPROVE"},
            headers={"Origin": "https://operator.test"}, follow_redirects=False,
        )
        assert result.status_code == 303
        page = client.get("/")
        assert page.text.count('id="opportunity-card"') == 1
        assert "WAITING_FRESH_TRIGGER" in page.text
        assert "NOT_SUBMITTED" in page.text
        assert 'data-action="APPROVE"' not in page.text
        with sqlite3.connect(tmp_path / "operator.sqlite") as connection:
            assert connection.execute(
                "SELECT submission_status FROM ts8_state"
            ).fetchone()[0] == "NOT_SUBMITTED"
    finally:
        client.__exit__(None, None, None)


def test_recent_events_are_bounded_and_deterministic(tmp_path: Path) -> None:
    now = time.time_ns() // 1_000_000
    make_source(tmp_path / "runtime.sqlite", created_ms=now)
    config = make_config(tmp_path)
    projection, _ = OperatorEngine(config).latest(now_ms=now)
    with sqlite3.connect(config.operator_ledger_path) as connection:
        ledger = HumanApprovalLedger(connection)
        ledger.ts8_display(projection.package, mode=ApprovalMode.POST_ACTIVATION)
        for index in range(EVENT_LIMIT + 5):
            connection.execute(
                "INSERT INTO ts8_transitions VALUES "
                "(?, ?, 'REJECTED', ?, NULL, ?, '[]', '[]', 'NOT_SUBMITTED')",
                (f"event-{index:03}", projection.package.package_id, now, "x" * 64),
            )
    events, available = _recent_events(config.operator_ledger_path)
    assert available and len(events) == EVENT_LIMIT
    assert events[0].event_key == f"event-{EVENT_LIMIT + 4:03}"
    assert events[-1].event_key == "event-005"
