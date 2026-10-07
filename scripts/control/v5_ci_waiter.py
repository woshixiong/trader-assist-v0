#!/usr/bin/env python3
"""Deterministic exact-head GitHub CI waiter for V5.

This is an execution transport helper, not an engineering authority. It waits
locally so Remote Desktop Commander does not need repeated status polling.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

RETRYABLE_MARKERS = (
    "eof",
    "tls",
    "ssl",
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "could not resolve",
    "temporary failure",
    "network is unreachable",
    "connection aborted",
)
NON_RETRYABLE_MARKERS = (
    "rate limit",
    "rate-limit",
    "secondary rate",
    "retry-after",
    "too many requests",
    "quota",
    "permission",
    "forbidden",
    "unauthorized",
    "authentication",
    "bad credentials",
    "oauth",
    "resource not accessible",
    "abuse detection",
)
# The 401/403/429 family is intentionally excluded even if the response also
# contains retryable words such as "timeout", "503" or "connection reset".
REJECT_HTTP = re.compile(r"(?<!\\d)(?:401|403|429)(?!\\d)")
TRANSIENT_HTTP = re.compile(r"(?<!\\d)(?:408|500|502|503|504)(?!\\d)")


class WaiterError(RuntimeError):
    """Base waiter error."""


class RetryableTransportError(WaiterError):
    """A transient GitHub/network failure that may be retried locally."""


class QueryError(WaiterError):
    """A non-transient GitHub/CLI failure that must fail closed."""


@dataclass(frozen=True)
class CheckState:
    name: str
    status: str
    conclusion: str | None
    check_run_id: int
    details_url: str


@dataclass(frozen=True)
class WaitResult:
    result: str
    expected_head: str
    observed_head: str | None
    checks: list[CheckState]
    failed_checks: list[str]
    consecutive_transport_failures: int
    reason: str = ""


def _run_gh_json(args: list[str]) -> Any:
    try:
        proc = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RetryableTransportError(str(exc)) from exc
    except OSError as exc:
        # Failure to spawn gh (including local permission errors) is not a
        # network read failure; repeated fast retries cannot repair it.
        raise QueryError(f"gh invocation failed: {exc}") from exc
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout).strip()
        lowered = message.lower()
        if REJECT_HTTP.search(lowered) or any(
            marker in lowered for marker in NON_RETRYABLE_MARKERS
        ):
            raise QueryError(message[:500] or f"gh exited {proc.returncode}")
        if TRANSIENT_HTTP.search(lowered) or any(
            marker in lowered for marker in RETRYABLE_MARKERS
        ):
            raise RetryableTransportError(message[:500])
        raise QueryError(message[:500] or f"gh exited {proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise QueryError("gh returned invalid JSON") from exc


def read_pr_head(repo: str, pr_number: int, gh_json: Callable[[list[str]], Any]) -> str:
    value = gh_json(["pr", "view", str(pr_number), "--repo", repo, "--json", "headRefOid"])
    head = value.get("headRefOid") if isinstance(value, dict) else None
    if not isinstance(head, str) or len(head) != 40:
        raise QueryError("PR head is missing or invalid")
    return head


def read_check_runs(
    repo: str,
    expected_head: str,
    required_checks: Iterable[str],
    gh_json: Callable[[list[str]], Any],
) -> list[CheckState]:
    value = gh_json(
        [
            "api",
            f"repos/{repo}/commits/{expected_head}/check-runs?per_page=100",
            "-H",
            "Accept: application/vnd.github+json",
        ]
    )
    runs = value.get("check_runs") if isinstance(value, dict) else None
    if not isinstance(runs, list):
        raise QueryError("check-runs response is malformed")

    required = set(required_checks)
    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        if not isinstance(run, dict) or run.get("name") not in required:
            continue
        name = str(run["name"])
        run_id = int(run.get("id") or 0)
        if name not in latest or run_id > int(latest[name].get("id") or 0):
            latest[name] = run

    return [
        CheckState(
            name=name,
            status=str(latest[name].get("status") or ""),
            conclusion=(
                str(latest[name]["conclusion"])
                if latest[name].get("conclusion") is not None
                else None
            ),
            check_run_id=int(latest[name].get("id") or 0),
            details_url=str(latest[name].get("details_url") or ""),
        )
        for name in sorted(latest)
    ]


def _check_terminal(
    checks: list[CheckState], required_checks: list[str]
) -> tuple[bool, list[str]]:
    by_name = {check.name: check for check in checks}
    if any(name not in by_name for name in required_checks):
        return False, []
    if any(by_name[name].status != "completed" for name in required_checks):
        return False, []
    failed = [
        name for name in required_checks if by_name[name].conclusion != "success"
    ]
    return True, failed


def _write_result(result: WaitResult, result_file: Path | None) -> None:
    payload = json.dumps(asdict(result), sort_keys=True)
    if result_file is not None:
        result_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = result_file.with_name(result_file.name + ".tmp")
        tmp.write_text(payload + "\n", encoding="utf-8")
        tmp.replace(result_file)
    print(payload, flush=True)


def wait_for_ci(
    *,
    repo: str,
    pr_number: int,
    expected_head: str,
    required_checks: list[str],
    poll_seconds: float,
    max_transport_failures: int,
    max_wait_seconds: float,
    result_file: Path | None,
    gh_json: Callable[[list[str]], Any] = _run_gh_json,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    retry_seconds: float = 10.0,
) -> WaitResult:
    if not required_checks:
        raise ValueError("at least one required check is required")
    if (
        poll_seconds < 0
        or retry_seconds <= 0
        or max_transport_failures < 1
        or max_wait_seconds <= 0
    ):
        raise ValueError("invalid CI poll/retry/timeout bounds")
    start = monotonic()
    transport_failures = 0
    checks: list[CheckState] = []

    while True:
        if monotonic() - start > max_wait_seconds:
            result = WaitResult(
                "TIMEOUT",
                expected_head,
                None,
                checks,
                [],
                transport_failures,
                "CI wait exceeded max_wait_seconds",
            )
            _write_result(result, result_file)
            return result

        try:
            if not checks:
                observed_head = read_pr_head(repo, pr_number, gh_json)
                if observed_head != expected_head:
                    result = WaitResult(
                        "STALE_HEAD",
                        expected_head,
                        observed_head,
                        checks,
                        [],
                        transport_failures,
                        "PR head differs before CI wait",
                    )
                    _write_result(result, result_file)
                    return result

            checks = read_check_runs(repo, expected_head, required_checks, gh_json)
            # A complete successful poll clears the *consecutive* transport
            # failure counter, even while required CI remains pending.
            transport_failures = 0
            terminal, failed = _check_terminal(checks, required_checks)
            if terminal:
                terminal_head = read_pr_head(repo, pr_number, gh_json)
                transport_failures = 0
                if terminal_head != expected_head:
                    result = WaitResult(
                        "STALE_HEAD",
                        expected_head,
                        terminal_head,
                        checks,
                        failed,
                        0,
                        "PR head changed before terminal readback",
                    )
                else:
                    result = WaitResult(
                        "SUCCESS" if not failed else "FAILURE",
                        expected_head,
                        terminal_head,
                        checks,
                        failed,
                        0,
                    )
                _write_result(result, result_file)
                return result
        except RetryableTransportError as exc:
            transport_failures += 1
            if transport_failures >= max_transport_failures:
                result = WaitResult(
                    "PAUSED_TRANSPORT",
                    expected_head,
                    None,
                    checks,
                    [],
                    transport_failures,
                    str(exc),
                )
                _write_result(result, result_file)
                return result
            sleep(retry_seconds)
            continue
        except QueryError as exc:
            result = WaitResult(
                "QUERY_ERROR",
                expected_head,
                None,
                checks,
                [],
                transport_failures,
                str(exc),
            )
            _write_result(result, result_file)
            return result

        sleep(poll_seconds)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True)
    p.add_argument("--pr", required=True, type=int)
    p.add_argument("--expected-head", required=True)
    p.add_argument("--required-check", action="append", required=True, dest="required_checks")
    p.add_argument("--poll-seconds", type=float, default=60.0)
    p.add_argument("--retry-seconds", type=float, default=10.0)
    p.add_argument("--max-transport-failures", type=int, default=20)
    p.add_argument("--max-wait-seconds", type=float, default=10800.0)
    p.add_argument("--result-file", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = wait_for_ci(
        repo=args.repo,
        pr_number=args.pr,
        expected_head=args.expected_head,
        required_checks=args.required_checks,
        poll_seconds=args.poll_seconds,
        max_transport_failures=args.max_transport_failures,
        max_wait_seconds=args.max_wait_seconds,
        result_file=args.result_file,
        retry_seconds=args.retry_seconds,
    )
    return {
        "SUCCESS": 0,
        "FAILURE": 1,
        "STALE_HEAD": 2,
        "PAUSED_TRANSPORT": 3,
        "QUERY_ERROR": 4,
        "TIMEOUT": 5,
    }[result.result]


if __name__ == "__main__":
    raise SystemExit(main())
