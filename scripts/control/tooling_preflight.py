#!/usr/bin/env python3
"""Create a deterministic, read-only Execution Launch Packet."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from urllib.parse import urlsplit

PACKET_VERSION = "1.0.0"
ROLES = ("WRITER", "REVIEWER", "FINALIZER", "PROJECT_CONTROL")
ROUTES = ("DETERMINISTIC_SCRIPT", "CHATGPT", "CODEX", "DEEPSEEK_CLAUDE_CODE", "TRAE", "NONE")
QUOTAS = ("GE_30", "LT_30_GE_10", "LT_10", "UNKNOWN")
TEXT_FIELDS = (
    "EXECUTION_CAPABILITY_REQUIRED",
    "CANDIDATE_ROUTES",
    "SELECTED_ROUTE",
    "SELECTION_REASON",
    "CODEX_QUOTA_STATE",
    "ENVIRONMENT_REUSE",
    "SETUP_REQUIRED",
    "USER_ACTION",
)
SAFE_COMMANDS: dict[str, tuple[str, ...]] = {
    "python": ("--version",),
    "pytest": ("-m", "pytest", "--version"),
    "git": ("--version",),
    "gh": ("--version",),
}
TOKEN_PATTERN = re.compile(r"(?i)(gh[pousr]_[a-z0-9_]+|(?:token|secret|password)=\S+)")
ACTIONS_URL = re.compile(r"^/([^/]+)/([^/]+)/actions/runs/([0-9]+)$")


def sanitize_stderr(value: str, limit: int = 1000) -> str:
    return TOKEN_PATTERN.sub("[REDACTED]", value)[:limit]


def run_readonly(
    argv: Sequence[str], *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
) -> tuple[int, str]:
    """Run a fixed argv-only probe; callers never supply a shell command."""
    try:
        result = runner(
            list(argv), shell=False, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, sanitize_stderr(str(exc))
    return result.returncode, sanitize_stderr(result.stderr)


def read_git(
    repo: Path, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
) -> tuple[str, str, str, bool]:
    commands = (
        ("git", "-C", str(repo), "config", "--get", "remote.origin.url"),
        ("git", "-C", str(repo), "branch", "--show-current"),
        ("git", "-C", str(repo), "rev-parse", "HEAD"),
        ("git", "-C", str(repo), "status", "--porcelain"),
    )
    values: list[str] = []
    for argv in commands:
        try:
            result = runner(
                list(argv), shell=False, capture_output=True, text=True, timeout=10, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            values.append("")
            continue
        values.append(result.stdout.strip() if result.returncode == 0 else "")
    return values[0], values[1], values[2], not values[3]


def select_python(explicit: str | None, repo: Path) -> tuple[str, str]:
    if explicit:
        return explicit, "EXPLICIT_EXECUTABLE:" + explicit
    for candidate in (repo / ".venv" / "bin" / "python", repo / "venv" / "bin" / "python"):
        if candidate.is_file() and candidate.stat().st_mode & 0o111:
            return str(candidate), "REPOSITORY_VENV:" + str(candidate)
    return sys.executable, "CURRENT_INTERPRETER:" + sys.executable


def tooling_preflight(
    required_tools: Sequence[str],
    python_path: str | None,
    repo: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[list[str], list[dict[str, object]]]:
    python, reuse = select_python(python_path, repo)
    reuse_items = [reuse]
    failures: list[dict[str, object]] = []
    effective_tools = tuple(dict.fromkeys(("git", *required_tools)))
    for tool in effective_tools:
        executable = python if tool in {"python", "pytest"} else tool
        argv = [executable, *SAFE_COMMANDS[tool]]
        code, stderr = run_readonly(argv, runner=runner)
        if code != 0:
            failures.append({"COMMAND_ARGV": argv, "EXIT_CODE": code, "STDERR": stderr})
        else:
            reuse_items.append("AVAILABLE:" + tool)
    return reuse_items, failures


def action_evidence(
    owner: str,
    repo: str,
    run_id: str | None,
    run_url: str | None,
    connector_sufficient: bool,
    gh_available: bool,
) -> tuple[str, str | None]:
    if run_id and run_id.isdecimal():
        return "CONNECTOR_KNOWN_RUN_ID", run_id
    if run_url:
        parsed = urlsplit(run_url)
        match = ACTIONS_URL.fullmatch(parsed.path)
        if (
            parsed.scheme == "https"
            and parsed.netloc == "github.com"
            and not parsed.query
            and not parsed.fragment
            and match
        ):
            if match.group(1) == owner and match.group(2) == repo:
                return "CONNECTOR_RUN_URL", match.group(3)
        return "UNAVAILABLE", None
    if connector_sufficient:
        return "UNAVAILABLE", None
    if gh_available:
        return "GH_FALLBACK", None
    return "UNAVAILABLE", None


def execution_route(
    role: str, quota: str, available: set[str], critical_blocker: bool
) -> tuple[str, str]:
    if quota == "UNKNOWN":
        return "NONE", "Execution Agent selection is prohibited while Codex quota is UNKNOWN."
    if quota == "GE_30":
        preference: tuple[str, ...] = ("CODEX", "DEEPSEEK_CLAUDE_CODE")
    else:
        preference = ("DEEPSEEK_CLAUDE_CODE",)
    for route in preference:
        if route in available:
            return route, f"{role} local execution uses available {route} under quota {quota}."
    if quota == "LT_10" and critical_blocker and "CODEX" in available:
        return (
            "CODEX",
            "LT_10 critical blocker permits CODEX only because alternatives are unavailable.",
        )
    if quota == "LT_30_GE_10" and "CODEX" in available:
        return (
            "CODEX",
            "DEEPSEEK_CLAUDE_CODE is unavailable; CODEX is the available execution fallback.",
        )
    return "NONE", "No available execution Agent satisfies the required local capability."


def select_route(
    role: str,
    quota: str,
    available_routes: Sequence[str],
    deterministic_complete: bool,
    connector_sufficient: bool,
    checkout_required: bool,
    attack_tests_required: bool,
    reproduction_required: bool,
    complex_environment_failure: bool,
    critical_blocker: bool,
) -> tuple[list[str], str, str]:
    available = set(available_routes)
    if deterministic_complete:
        return (
            ["DETERMINISTIC_SCRIPT"],
            "DETERMINISTIC_SCRIPT",
            "A deterministic script fully satisfies the capability.",
        )
    review_requires_execution = checkout_required or attack_tests_required or reproduction_required
    if role == "PROJECT_CONTROL" and connector_sufficient and "CHATGPT" in available:
        return (
            ["CHATGPT"],
            "CHATGPT",
            "Connector-sufficient read-only Project Control judgment is available.",
        )
    if role == "REVIEWER" and connector_sufficient and not review_requires_execution:
        if "CHATGPT" in available:
            return (
                ["CHATGPT"],
                "CHATGPT",
                "Connector, exact diff, CI, and evidence are sufficient for the full "
                "Review contract.",
            )
    if complex_environment_failure and "TRAE" in available:
        return ["TRAE"], "TRAE", "An explicitly declared complex environment failure requires TRAE."
    candidate_routes = [route for route in ROUTES if route in available and route != "NONE"]
    selected, reason = execution_route(role, quota, available, critical_blocker)
    if selected == "NONE":
        candidate_routes.append("NONE")
    return candidate_routes or ["NONE"], selected, reason


def build_packet(
    args: argparse.Namespace,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    repository = Path(args.repository).resolve()
    actual_origin, actual_branch, actual_head, clean = read_git(repository, runner=runner)
    object_preflight: dict[str, object] = {
        "ORIGIN": {
            "EXPECTED": args.expected_origin,
            "ACTUAL": actual_origin,
            "MATCH": args.expected_origin == actual_origin,
        },
        "BRANCH": {
            "EXPECTED": args.expected_branch,
            "ACTUAL": actual_branch,
            "MATCH": args.expected_branch == actual_branch,
        },
        "HEAD": {
            "EXPECTED": args.expected_head,
            "ACTUAL": actual_head,
            "MATCH": args.expected_head == actual_head,
        },
        "WORKTREE_CLEAN": clean,
    }
    environment_reuse, tooling_failures = tooling_preflight(
        args.required_tool, args.python_path, repository, runner=runner
    )
    evidence_route, run_id = action_evidence(
        args.github_owner,
        args.github_repository,
        args.actions_run_id,
        args.actions_run_url,
        args.actions_connector_sufficient,
        args.gh_available,
    )
    if run_id:
        object_preflight["ACTIONS_RUN_ID"] = run_id
    candidates, selected, selection_reason = select_route(
        args.target_role,
        args.codex_quota_state,
        args.available_route,
        args.deterministic_complete,
        args.connector_sufficient,
        args.checkout_required,
        args.attack_tests_required,
        args.reproduction_required,
        args.complex_environment_failure,
        args.critical_blocker,
    )
    object_drift = not (
        args.expected_origin == actual_origin
        and args.expected_branch == actual_branch
        and args.expected_head == actual_head
        and clean
    )
    status = "PASS"
    if tooling_failures:
        status = "TOOLING_UNAVAILABLE"
    elif object_drift:
        status = "OBJECT_DRIFT"
    elif selected == "NONE":
        status = "ROUTE_UNAVAILABLE"
    return {
        "PACKET_VERSION": PACKET_VERSION,
        "TARGET_ROLE": args.target_role,
        "PREFLIGHT_STATUS": status,
        "EXECUTION_CAPABILITY_REQUIRED": args.capability,
        "CANDIDATE_ROUTES": candidates,
        "SELECTED_ROUTE": selected,
        "SELECTION_REASON": selection_reason,
        "CODEX_QUOTA_STATE": args.codex_quota_state,
        "ENVIRONMENT_REUSE": environment_reuse,
        "SETUP_REQUIRED": "YES" if tooling_failures else "NO",
        "USER_ACTION": (
            "Resolve reported preflight failures before action."
            if status != "PASS"
            else "Proceed only under the selected role's existing authorization."
        ),
        "OBJECT_PREFLIGHT": object_preflight,
        "TOOLING_FAILURES": tooling_failures,
        "GITHUB_ACTIONS_EVIDENCE_ROUTE": evidence_route,
        "REVIEWER_ISOLATION": (
            "REQUIRED_NEW_READ_ONLY_CONTEXT" if args.target_role == "REVIEWER" else "NOT_APPLICABLE"
        ),
        "SIDE_EFFECTS": "NONE",
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repository", required=True)
    value.add_argument("--expected-origin", required=True)
    value.add_argument("--expected-branch", required=True)
    value.add_argument("--expected-head", required=True)
    value.add_argument("--target-role", required=True, choices=ROLES)
    value.add_argument("--capability", required=True, action="append")
    value.add_argument("--codex-quota-state", required=True, choices=QUOTAS)
    value.add_argument("--available-route", action="append", choices=ROUTES, default=[])
    value.add_argument("--required-tool", action="append", choices=tuple(SAFE_COMMANDS), default=[])
    value.add_argument("--python-path")
    value.add_argument("--deterministic-complete", action="store_true")
    value.add_argument("--connector-sufficient", action="store_true")
    value.add_argument("--checkout-required", action="store_true")
    value.add_argument("--attack-tests-required", action="store_true")
    value.add_argument("--reproduction-required", action="store_true")
    value.add_argument("--complex-environment-failure", action="store_true")
    value.add_argument("--critical-blocker", action="store_true")
    value.add_argument("--github-owner", default="woshixiong")
    value.add_argument("--github-repository", default="trader-assist-v0")
    value.add_argument("--actions-run-id")
    value.add_argument("--actions-run-url")
    value.add_argument("--actions-connector-sufficient", action="store_true")
    value.add_argument("--gh-available", action="store_true")
    value.add_argument("--output", choices=("text", "json"), default="text")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    packet = build_packet(args)
    if args.output == "json":
        print(json.dumps(packet, sort_keys=False, separators=(",", ":")))
    else:
        for field in TEXT_FIELDS:
            print(f"{field}: {json.dumps(packet[field], separators=(',', ':'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
