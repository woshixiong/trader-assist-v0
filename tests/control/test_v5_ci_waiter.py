from __future__ import annotations

import importlib.util
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


def test_separate_default_ci_poll_and_transient_retry_timers():
    parsed = waiter.parser().parse_args([
        "--repo", "owner/repo", "--pr", "12",
        "--expected-head", HEAD, "--required-check", "contracts",
    ])
    assert parsed.poll_seconds == 60.0
    assert parsed.retry_seconds == 10.0
    assert parsed.max_transport_failures == 20
    sleeps = []
    assert call(
        gh_fixture(failures=2),
        poll_seconds=60,
        retry_seconds=10,
        sleep=sleeps.append,
    ).result == "SUCCESS"
    assert sleeps == [10, 10]


def test_transport_counter_resets_only_after_successful_poll():
    calls = {"checks": 0}
    sleeps = []

    def fake(args):
        if args[:2] == ["pr", "view"]:
            return {"headRefOid": HEAD}
        calls["checks"] += 1
        if calls["checks"] in {1, 3}:
            raise waiter.RetryableTransportError("TLS EOF")
        if calls["checks"] == 2:
            return {"check_runs": [{
                "id": 10, "name": "contracts",
                "status": "in_progress", "conclusion": None,
            }]}
        return {"check_runs": [{
            "id": 11, "name": "contracts",
            "status": "completed", "conclusion": "success",
        }]}

    result = call(
        fake, required_checks=["contracts"], max_transport_failures=2,
        poll_seconds=60, retry_seconds=10, sleep=sleeps.append,
    )
    assert result.result == "SUCCESS"
    assert sleeps == [10, 60, 10]


def test_exact_twenty_consecutive_transient_failures_pause():
    sleeps = []
    result = call(
        gh_fixture(failures=21),
        max_transport_failures=20,
        retry_seconds=10,
        sleep=sleeps.append,
    )
    assert result.result == "PAUSED_TRANSPORT"
    assert result.consecutive_transport_failures == 20
    assert sleeps == [10] * 19


@pytest.mark.parametrize("message", [
    "HTTP 401: bad credentials and timeout",
    "HTTP 403: API rate limit exceeded, 503 retry later",
    "HTTP 429: Too Many Requests",
    "resource not accessible by integration",
    "permission denied: TLS error",
    "quota exhausted; connection reset",
    "secondary rate limit retry-after: 10",
    "fatal: authentication failed",
])
def test_nonretryable_auth_quota_semantic_errors_never_fast_retry(
    monkeypatch, message
):
    monkeypatch.setattr(
        waiter.subprocess,
        "run",
        lambda argv, **kw: subprocess.CompletedProcess(
            argv, 1, stdout="", stderr=message
        ),
    )
    with pytest.raises(waiter.QueryError):
        waiter._run_gh_json(["api", "test"])


@pytest.mark.parametrize("message", [
    "TLS EOF", "connection reset by peer", "HTTP 408 Request Timeout",
    "HTTP 500 Internal Server Error", "HTTP 502 Bad Gateway",
    "HTTP 503 Service Unavailable", "HTTP 504 Gateway Timeout",
])
def test_classified_network_failures_have_bounded_retry(monkeypatch, message):
    monkeypatch.setattr(
        waiter.subprocess,
        "run",
        lambda argv, **kw: subprocess.CompletedProcess(
            argv, 1, stdout="", stderr=message
        ),
    )
    with pytest.raises(waiter.RetryableTransportError):
        waiter._run_gh_json(["api", "test"])


def test_gh_executable_failure_not_retried_as_network(monkeypatch):
    def no_gh(argv, **kw):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(waiter.subprocess, "run", no_gh)
    with pytest.raises(waiter.QueryError, match="invocation failed"):
        waiter._run_gh_json(["api", "test"])


def test_terminal_skipped_required_check_is_not_success():
    checks = [
        {"id": 10, "name": "contracts", "status": "completed", "conclusion": "success"},
        {"id": 11, "name": "e4-capture", "status": "completed", "conclusion": "skipped"},
    ]
    result = call(gh_fixture(checks=checks))
    assert result.result == "FAILURE"
    assert result.failed_checks == ["e4-capture"]
