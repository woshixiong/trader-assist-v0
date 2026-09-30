from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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
