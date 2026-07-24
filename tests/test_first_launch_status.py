from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

NOW = datetime(2026, 7, 25, 3, 12, 4, tzinfo=UTC)
_STATUS_COMMAND = Path(__file__).resolve().parents[1] / "bin" / "ta-status"
_LOADER = importlib.machinery.SourceFileLoader("ta_status_test", str(_STATUS_COMMAND))
_SPEC = importlib.util.spec_from_loader(_LOADER.name, _LOADER)
assert _SPEC is not None
_STATUS = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _STATUS
_LOADER.exec_module(_STATUS)


def _systemctl(*, active_state: str = "active", main_pid: str = "4321") -> str:
    return f"MainPID={main_pid}\nActiveState={active_state}\n"


def _snapshot(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "pid": 4321,
        "session_id": "0123456789abcdef0123456789abcdef",
        "state": "READY",
        "last_active_context_at": (NOW - timedelta(seconds=4)).isoformat(),
        "mode": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "scope": "ETH_ONLY",
    }
    value.update(changes)
    return value


def _write_snapshot(path: Path, **changes: object) -> None:
    path.write_text(json.dumps(_snapshot(**changes)), encoding="utf-8")


def _classify(path: Path, *, output: str | None = None, now: datetime = NOW):
    return _STATUS.classify(
        snapshot_path=path,
        systemctl_runner=lambda: _systemctl() if output is None else output,
        now=now,
    )


def test_ready_snapshot_is_fresh_and_uses_no_database(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path)
    result = _classify(path)
    assert result.exit_code == 0
    assert result.output == "READY | CONTEXT_AGE=4s | SIGNALS_MAY_BE_CONSIDERED"
    assert "sqlite" not in _STATUS_COMMAND.read_text(encoding="utf-8").lower()


@pytest.mark.parametrize(
    ("age_seconds", "exit_code", "fragment"),
    [(15.0, 0, "CONTEXT_AGE=15s"), (15.1, 1, "DATA_STALE")],
)
def test_freshness_boundary(
    tmp_path: Path, age_seconds: float, exit_code: int, fragment: str
) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, last_active_context_at=(NOW - timedelta(seconds=age_seconds)).isoformat())
    result = _classify(path)
    assert result.exit_code == exit_code
    assert fragment in result.output


@pytest.mark.parametrize(
    "state",
    ["STARTING", "WARMING", "DEGRADED", "NOT_READY", "DISCONNECTED", "STOPPING", "STOPPED"],
)
def test_every_non_ready_runtime_state_is_not_ready(tmp_path: Path, state: str) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, state=state, last_active_context_at=None)
    result = _classify(path)
    assert result.exit_code == 1
    assert result.output == f"NOT_READY | RUNTIME_{state} | IGNORE_SYSTEM_SIGNALS"


def test_inactive_service_does_not_read_snapshot(tmp_path: Path) -> None:
    result = _classify(tmp_path / "missing.json", output=_systemctl(active_state="inactive"))
    assert result.exit_code == 1
    assert result.output == "NOT_READY | SERVICE_INACTIVE | IGNORE_SYSTEM_SIGNALS"


@pytest.mark.parametrize(
    ("output", "fragment"),
    [
        (_systemctl(main_pid="0"), "INVALID_MAIN_PID"),
        ("ActiveState=active\n", "CHECK_FAILED"),
        ("ActiveState=active\nMainPID=1\nMainPID=2\n", "CHECK_FAILED"),
    ],
)
def test_bad_systemctl_result_is_unknown(tmp_path: Path, output: str, fragment: str) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path)
    result = _classify(path, output=output)
    assert result.exit_code == 2
    assert fragment in result.output


def test_systemctl_execution_failure_is_unknown(tmp_path: Path) -> None:
    result = _STATUS.classify(
        snapshot_path=tmp_path / "status.json",
        systemctl_runner=lambda: (_ for _ in ()).throw(OSError("injected")),
        now=NOW,
    )
    assert result.exit_code == 2
    assert "CHECK_FAILED" in result.output


@pytest.mark.parametrize(
    ("changes", "fragment"),
    [
        ({"last_active_context_at": None}, "CONTEXT_TIMESTAMP_MISSING"),
        (
            {"last_active_context_at": (NOW + timedelta(seconds=5.1)).isoformat()},
            "FUTURE_TIMESTAMP",
        ),
        ({"pid": 4322}, "PID_MISMATCH"),
        ({"session_id": "ABCDEF" * 5 + "AB"}, "SESSION_INVALID"),
        ({"mode": "OTHER"}, "MODE_MISMATCH"),
        ({"scope": "BTC_ONLY"}, "SCOPE_MISMATCH"),
        ({"state": "BROKEN"}, "STATE_INVALID"),
        ({"pid": True}, "STATE_INVALID"),
        ({"last_active_context_at": "not-a-timestamp"}, "STATE_INVALID"),
    ],
)
def test_invalid_snapshot_fields_fail_closed(
    tmp_path: Path, changes: dict[str, object], fragment: str
) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, **changes)
    result = _classify(path)
    assert result.exit_code == 2
    assert fragment in result.output


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ("{", "STATE_MALFORMED"),
        (
            '{"pid":4321,"pid":4321,"session_id":"0123456789abcdef0123456789abcdef",'
            '"state":"READY","last_active_context_at":null,'
            '"mode":"RESTRICTED_PUBLIC_LIVE_SHADOW","scope":"ETH_ONLY"}',
            "STATE_MALFORMED",
        ),
        (
            json.dumps({key: value for key, value in _snapshot().items() if key != "scope"}),
            "STATE_MISSING",
        ),
        (json.dumps({**_snapshot(), "extra": 1}), "STATE_INVALID"),
    ],
)
def test_strict_snapshot_structure(tmp_path: Path, raw: str, fragment: str) -> None:
    path = tmp_path / "status.json"
    path.write_text(raw, encoding="utf-8")
    result = _classify(path)
    assert result.exit_code == 2
    assert fragment in result.output


def test_missing_and_unreadable_snapshot_are_unknown(tmp_path: Path) -> None:
    missing = _classify(tmp_path / "missing.json")
    assert missing.exit_code == 2
    assert "STATE_MISSING" in missing.output

    unreadable_path = tmp_path / "status-directory"
    unreadable_path.mkdir()
    unreadable = _classify(unreadable_path)
    assert unreadable.exit_code == 2
    assert "STATE_UNREADABLE" in unreadable.output


def test_small_future_skew_is_treated_as_zero_age(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, last_active_context_at=(NOW + timedelta(seconds=5)).isoformat())
    result = _classify(path)
    assert result.exit_code == 0
    assert "CONTEXT_AGE=0s" in result.output
