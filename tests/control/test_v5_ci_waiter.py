from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "v5_ci_waiter", ROOT / "scripts/control/v5_ci_waiter.py"
)
assert SPEC and SPEC.loader
waiter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = waiter
SPEC.loader.exec_module(waiter)

HEAD = "a" * 40
OTHER = "b" * 40
REQUIRED = ["contracts", "e4-capture"]


def gh_fixture(*, heads=None, checks=None, failures=0):
    heads = list(heads or [HEAD, HEAD])
    checks = list(
        checks
        or [
            {
                "id": 10,
                "name": "contracts",
                "status": "completed",
                "conclusion": "success",
                "details_url": "https://example/contracts",
            },
            {
                "id": 11,
                "name": "e4-capture",
                "status": "completed",
                "conclusion": "success",
                "details_url": "https://example/e4",
            },
        ]
    )
    state = {"failures": failures}

    def fake(args):
        if state["failures"]:
            state["failures"] -= 1
            raise waiter.RetryableTransportError("TLS EOF")
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": heads.pop(0)}
        return {"check_runs": checks}

    return fake


def call(fake, **overrides):
    values = dict(
        repo="woshixiong/trader-assist-v0",
        pr_number=999,
        expected_head=HEAD,
        required_checks=REQUIRED,
        poll_seconds=0,
        max_transport_failures=20,
        max_wait_seconds=100,
        result_file=None,
        gh_json=fake,
        sleep=lambda _: None,
        monotonic=lambda: 0,
    )
    values.update(overrides)
    return waiter.wait_for_ci(**values)


def test_success_and_exact_terminal_head_readback(capsys):
    result = call(gh_fixture())
    assert result.result == "SUCCESS"
    assert result.observed_head == HEAD
    assert result.failed_checks == []
    assert '"result": "SUCCESS"' in capsys.readouterr().out


def test_terminal_failure_names_only_failed_required_check():
    checks = [
        {
            "id": 10,
            "name": "contracts",
            "status": "completed",
            "conclusion": "failure",
            "details_url": "x",
        },
        {
            "id": 11,
            "name": "e4-capture",
            "status": "completed",
            "conclusion": "success",
            "details_url": "y",
        },
    ]
    result = call(gh_fixture(checks=checks))
    assert result.result == "FAILURE"
    assert result.failed_checks == ["contracts"]


def test_stale_head_before_wait_and_at_terminal():
    assert call(gh_fixture(heads=[OTHER])).result == "STALE_HEAD"
    assert call(gh_fixture(heads=[HEAD, OTHER])).result == "STALE_HEAD"


def test_transport_failures_are_retried_locally_then_recover():
    result = call(gh_fixture(failures=2))
    assert result.result == "SUCCESS"


def test_transport_failure_budget_pauses_without_semantic_action():
    result = call(
        gh_fixture(failures=5),
        max_transport_failures=2,
    )
    assert result.result == "PAUSED_TRANSPORT"
    assert result.consecutive_transport_failures == 2


def test_latest_duplicate_check_run_wins():
    checks = [
        {
            "id": 1,
            "name": "contracts",
            "status": "completed",
            "conclusion": "failure",
            "details_url": "old",
        },
        {
            "id": 2,
            "name": "contracts",
            "status": "completed",
            "conclusion": "success",
            "details_url": "new",
        },
        {
            "id": 3,
            "name": "e4-capture",
            "status": "completed",
            "conclusion": "success",
            "details_url": "e4",
        },
    ]
    result = call(gh_fixture(checks=checks))
    assert result.result == "SUCCESS"
    by_name = {item.name: item for item in result.checks}
    assert by_name["contracts"].check_run_id == 2


# P1A negative matrix: no weakened/removed baseline test above.


def _check_rows(*, status="completed", conclusion="success"):
    return {
        "check_runs": [
            {"id": 10, "name": "contracts", "status": status,
             "conclusion": conclusion, "details_url": "test/contracts"},
            {"id": 11, "name": "e4-capture", "status": status,
             "conclusion": conclusion, "details_url": "test/e4"},
        ]
    }


def test_independent_normal_and_transient_retry_timers():
    sleeps = []
    state = {"checks": 0}

    def fake(args):
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": HEAD}
        state["checks"] += 1
        if state["checks"] == 1:
            return _check_rows(status="in_progress", conclusion=None)
        if state["checks"] == 2:
            raise waiter.RetryableTransportError("TLS EOF")
        return _check_rows()

    result = call(fake, poll_seconds=60, transport_retry_seconds=10,
                  sleep=sleeps.append)
    assert result.result == "SUCCESS"
    assert sleeps == [60, 10]
    assert state["checks"] == 3


def test_exact_20_transient_failures_produce_19_ten_second_sleeps():
    sleeps = []
    state = {"check_reads": 0}

    def fake(args):
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": HEAD}
        state["check_reads"] += 1
        raise waiter.RetryableTransportError("TLS EOF")

    result = call(fake, poll_seconds=60, transport_retry_seconds=10,
                  sleep=sleeps.append)
    assert result.result == "PAUSED_TRANSPORT"
    assert result.consecutive_transport_failures == 20
    assert state["check_reads"] == 20
    assert sleeps == [10] * 19


def test_successful_full_pending_checks_read_resets_consecutive_failure_count():
    state = {"check_reads": 0}
    sleeps = []

    def fake(args):
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": HEAD}
        state["check_reads"] += 1
        n = state["check_reads"]
        if n <= 19 or 21 <= n <= 39:
            raise waiter.RetryableTransportError("connection reset")
        if n == 20:
            return _check_rows(status="in_progress", conclusion=None)
        return _check_rows()

    result = call(fake, poll_seconds=60, transport_retry_seconds=10,
                  sleep=sleeps.append)
    assert result.result == "SUCCESS"
    assert state["check_reads"] == 40
    assert sleeps.count(10) == 38
    assert sleeps.count(60) == 1


def test_head_only_read_does_not_reset_transport_failure_count():
    state = {"heads": 0, "checks": 0}

    def fake(args):
        if args[:2] == ["pr", "view"]:
            state["heads"] += 1
            return {"headRefOid": HEAD}
        state["checks"] += 1
        raise waiter.RetryableTransportError("TLS EOF")

    result = call(fake)
    assert result.result == "PAUSED_TRANSPORT"
    assert result.consecutive_transport_failures == 20
    assert state == {"heads": 20, "checks": 20}


@pytest.mark.parametrize(
    "message",
    [
        "HTTP 401: TLS EOF", "HTTP 403: connection reset",
        "status 429 error 503", "HTTP 502: rate limit exhausted",
        "TLS handshake failed: quota exceeded",
        "HTTP 503: OAuth authentication required",
        "HTTP 408: permission denied", "HTTP 504: bad credentials",
        "HTTP 500: unauthorized", "resource not accessible: TLS EOF",
        "HTTP 500: insufficient scope", "HTTP 503: rate-limit",
        "request id 5029999", "record 502", "query returned invalid JSON",
    ],
)
def test_nonretryable_auth_quota_and_ambiguous_errors_take_precedence(message):
    assert waiter._is_transient_read_error(message) is False


@pytest.mark.parametrize(
    "message",
    [
        "HTTP 408: Request Timeout", "HTTP 500: Internal Server Error",
        "HTTP 502: Bad Gateway", "status 503",
        "response status 504", "500 Internal Server Error",
        "502 Bad Gateway", "503 Service Unavailable", "504 Gateway Timeout",
        "TLS handshake EOF", "SSL handshake failure", "unexpected EOF",
        "connection reset by peer", "connection refused",
        "could not resolve host", "temporary failure in name resolution",
        "context deadline exceeded", "i/o timeout",
    ],
)
def test_positive_transient_read_failures(message):
    assert waiter._is_transient_read_error(message) is True


@pytest.mark.parametrize(
    "error", [FileNotFoundError("gh missing"), PermissionError("no execute"),
              OSError("OS spawn failure")]
)
def test_missing_gh_executable_and_spawn_failures_are_not_retried(
    monkeypatch, error
):
    def raise_os_error(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(waiter.subprocess, "run", raise_os_error)
    with pytest.raises(waiter.QueryError, match="gh launch failed"):
        waiter._run_gh_json(["api", "some/read"])


def test_gh_process_timeout_is_retryable_but_invalid_json_is_not(monkeypatch):
    def time_out(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=30)

    monkeypatch.setattr(waiter.subprocess, "run", time_out)
    with pytest.raises(waiter.RetryableTransportError):
        waiter._run_gh_json(["api", "read"])

    monkeypatch.setattr(
        waiter.subprocess, "run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout="{unparseable", stderr=""
        ),
    )
    with pytest.raises(waiter.QueryError, match="invalid JSON"):
        waiter._run_gh_json(["api", "read"])


def test_cli_fails_closed_on_mixed_permanent_and_transient_stderr(monkeypatch):
    monkeypatch.setattr(
        waiter.subprocess, "run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            args=["gh"], returncode=1, stdout="",
            stderr="HTTP 429 rate limit and HTTP 503 TLS EOF"
        ),
    )
    with pytest.raises(waiter.QueryError):
        waiter._run_gh_json(["api", "read"])


def test_hard_timeout_not_overridden_by_transient_retry_delays():
    now = [0.0]
    sleeps = []

    def fake(args):
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": HEAD}
        raise waiter.RetryableTransportError("TLS EOF")

    def advance(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    result = call(fake, poll_seconds=60, transport_retry_seconds=10,
                  max_wait_seconds=15, monotonic=lambda: now[0],
                  sleep=advance)
    assert result.result == "TIMEOUT"
    assert sleeps == [10, 5]


@pytest.mark.parametrize("bad", [None, {}, {"check_runs": "wrong"}, []])
def test_malformed_checks_response_fails_closed(bad):
    def fake(args):
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": HEAD}
        return bad

    assert call(fake).result == "QUERY_ERROR"


def test_required_skipped_check_is_failure_not_success():
    checks = _check_rows()
    checks["check_runs"][1]["conclusion"] = "skipped"

    def fake(args):
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": HEAD}
        return checks

    assert call(fake).result == "FAILURE"


def test_missing_required_check_is_never_treated_as_terminal_success():
    checks = _check_rows()
    checks["check_runs"].pop()
    complete, failed = waiter._check_terminal(
        waiter.read_check_runs("x/y", HEAD, REQUIRED, lambda *_: checks),
        REQUIRED,
    )
    assert complete is False
    assert failed == []


def test_checkpoint_result_file_remains_atomic_and_cli_defaults(tmp_path):
    result_file = tmp_path / "checkpoint.json"
    result = call(gh_fixture(), result_file=result_file)
    assert result.result == "SUCCESS"
    payload = json.loads(result_file.read_text(encoding="utf-8"))
    assert payload["expected_head"] == HEAD
    assert payload["result"] == "SUCCESS"
    assert payload["consecutive_transport_failures"] == 0
    assert not result_file.with_name("checkpoint.json.tmp").exists()

    args = waiter.parser().parse_args([
        "--repo", "x/y", "--pr", "2", "--expected-head", HEAD,
        "--required-check", "contracts",
    ])
    assert args.poll_seconds == 60.0
    assert args.transport_retry_seconds == 10.0
    assert args.max_transport_failures == 20
