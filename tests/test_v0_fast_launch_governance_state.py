from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_PATH = ROOT / "governance" / "V0_FAST_LAUNCH_PROGRAM.json"
STATE_PATH = ROOT / "governance" / "PROJECT_STATE.json"
SCHEMA_PATH = ROOT / "schemas" / "governance" / "V0FastLaunchProgram.schema.json"

TASK_ID = "V0-FLP1B0B-CAPTURE-NOW-AUTHORITY-AMENDMENT"
BASE_SHA = "78d2d37bfe5a4f3f1d382a2a96e57896ae9676ae"
NEXT_GATE = "V0-FLP1B0B-EXTERNAL-INDEPENDENT-REVIEW"
AUTHORITY_HASH = "0e327e566589d8030ff00d4d009eb4b6827679ab508133d66840b2c245dc53df"
SOURCE_CATALOG_HASH = "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")

EXPECTED_CHANGED_FILES = {
    ".github/workflows/ci.yml",
    "README.md",
    "docs/V0_01_SCOPE.md",
    "docs/V0_FAST_LAUNCH_PROGRAM.md",
    "docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md",
    "docs/architecture/V0_01_DATA_PLANE.md",
    "docs/architecture/AUTHORITY_BOUNDARY.md",
    "docs/architecture/STRATEGY_AND_DATA_LIFECYCLE.md",
    "docs/architecture/PILOT_LEARNING_LOOP.md",
    "governance/V0_FAST_LAUNCH_PROGRAM.json",
    "governance/PROJECT_STATE.json",
    "schemas/governance/V0FastLaunchProgram.schema.json",
    "src/trader_assist_v0/contracts/capture.py",
    "src/trader_assist_v0/contracts/__init__.py",
    "scripts/export_schemas.py",
    "schemas/v0/CaptureRecordV0.schema.json",
    "tests/test_v0_flp1b0b_capture_now_authority.py",
    "tests/test_v0_fast_launch_governance_state.py",
}

EXPECTED_COMMITTED_STATUS_MAP = {
    ".github/workflows/ci.yml": "M",
    "README.md": "M",
    "docs/V0_01_SCOPE.md": "M",
    "docs/V0_FAST_LAUNCH_PROGRAM.md": "M",
    "docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md": "A",
    "docs/architecture/V0_01_DATA_PLANE.md": "M",
    "docs/architecture/AUTHORITY_BOUNDARY.md": "M",
    "docs/architecture/STRATEGY_AND_DATA_LIFECYCLE.md": "M",
    "docs/architecture/PILOT_LEARNING_LOOP.md": "M",
    "governance/V0_FAST_LAUNCH_PROGRAM.json": "M",
    "governance/PROJECT_STATE.json": "M",
    "schemas/governance/V0FastLaunchProgram.schema.json": "M",
    "src/trader_assist_v0/contracts/capture.py": "A",
    "src/trader_assist_v0/contracts/__init__.py": "M",
    "scripts/export_schemas.py": "M",
    "schemas/v0/CaptureRecordV0.schema.json": "A",
    "tests/test_v0_flp1b0b_capture_now_authority.py": "A",
    "tests/test_v0_fast_launch_governance_state.py": "M",
}

FORBIDDEN_FILES = {
    "CODEX.md",
    "docs/PROJECT_CONTROL_WORKFLOW.md",
    "docs/V0_01_OFFICIAL_SOURCE_CATALOG.md",
    "src/trader_assist_v0/contracts/common.py",
    "src/trader_assist_v0/contracts/events.py",
    "src/trader_assist_v0/contracts/source_catalog.py",
    "src/trader_assist_v0/contracts/rate_limits.py",
    "pyproject.toml",
    "requirements-dev.lock",
    "requirements-runtime.lock",
}

DOC_PATHS = (
    ROOT / "README.md",
    ROOT / "docs" / "V0_01_SCOPE.md",
    ROOT / "docs" / "V0_FAST_LAUNCH_PROGRAM.md",
    ROOT / "docs" / "V0_FLP0_CAPTURE_NOW_AUTHORITY.md",
    ROOT / "docs" / "architecture" / "V0_01_DATA_PLANE.md",
    ROOT / "docs" / "architecture" / "AUTHORITY_BOUNDARY.md",
    ROOT / "docs" / "architecture" / "STRATEGY_AND_DATA_LIFECYCLE.md",
    ROOT / "docs" / "architecture" / "PILOT_LEARNING_LOOP.md",
)


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_schema_self_validation_and_instances() -> None:
    schema = _load_json(SCHEMA_PATH)
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(program)
    state_schema = schema["$defs"]["ProjectState"]
    assert isinstance(state_schema, dict)
    Draft202012Validator.check_schema(state_schema)
    Draft202012Validator(state_schema).validate(state)


def test_program_state_and_release_authority_parity() -> None:
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)

    assert program["task_id"] == state["active_task_id"] == TASK_ID
    assert program["state_base_sha"] == state["state_base_sha"] == BASE_SHA
    assert state["active_write_lease"]["status"] == "NONE"
    assert state["active_write_lease"]["final_status"] == (
        "CONSUMED_PENDING_PROJECT_CONTROL_ACCEPTANCE"
    )
    assert state["next_gate"] == NEXT_GATE
    assert program["recursive_rotation"]["post_merge_next_gate"] == NEXT_GATE

    release_authority = program["release_authority"]
    assert release_authority == {
        "R0": "CAPTURE_ONLY",
        "R1": "ETH_OPERATOR_ASSIST",
        "FIRST_LAUNCH_PRIMARY_ASSET": "ETH",
        "BTC_FIRST_LAUNCH_REQUIREMENT": "NONE",
        "BTC_FIRST_LAUNCH_BLOCKER": "NO",
        "T1": "CONTRACT_SCHEMA_GOVERNANCE_ONLY",
        "T2": "SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME",
    }


def test_r0_r1_and_deferred_g4_migration() -> None:
    program = _load_json(PROGRAM_PATH)
    r0 = program["first_release"]
    r1 = program["releases"]["R1"]
    deferred = program["future_human_confirmed_execution"]

    assert r0["release_id"] == "V0-R0"
    assert r0["release_authority"] == "CAPTURE_ONLY"
    assert r0["primary_asset"] == "ETH"
    assert r0["active_strategy_count"] == 0
    assert r0["capture_contracts_authorized"] is True
    for gate in (
        "network_runtime_authorized",
        "strategy_runtime_authorized",
        "signal_recommendation_authorized",
        "risk_sizing_authorized",
        "trade_plan_authorized",
        "account_runtime_authorized",
        "exchange_execution_authorized",
    ):
        assert r0[gate] is False

    assert r1["release_id"] == "V0-R1"
    assert r1["scope"] == "ETH_OPERATOR_ASSIST"
    assert r1["status"] == "FUTURE_NOT_IMPLEMENTED_NOT_AUTHORIZED"
    assert r1["primary_asset"] == "ETH"
    assert r1["signal_outputs"] == ["LONG", "SHORT", "WAIT"]
    assert r1["deterministic_risk"] is True
    assert r1["trade_plan"] is True
    assert r1["presentation"] == ["FAST", "STANDARD"]
    assert r1["manual_execution"] is True
    assert r1["readonly_account_order_fill_observation"] is True
    assert r1["implementation_authorized"] is False
    assert r1["exchange_execution_authorized"] is False

    assert deferred["assigned_release_id"] is None
    assert deferred["release_id_authorized"] is False
    assert deferred["status"] == "DEFERRED_SEPARATE_G4_GATE"
    assert deferred["autonomous_entry"] == "PROHIBITED"
    assert deferred["human_confirmation_required"] is True
    assert deferred["implementation_authorized"] is False
    assert deferred["testnet_execution_authorized"] is False
    assert deferred["mainnet_execution_authorized"] is False
    assert "OFFICIAL_SDK_SIGNING" in deferred["required_controls"]
    assert "SEPARATE_MAINNET_AUTHORIZATION" in deferred["required_controls"]
    assert "required_controls" not in r1


def test_rate_limit_authority_immutability_and_false_gates() -> None:
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)
    authority = program["authority"]

    for document in (authority, state):
        assert document["rate_limit_status"] == "UNRESOLVED_OFFICIAL_LIMIT"
        assert document["conflict_state"] == "OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED"
        assert document["supersession_state"] == "EFFECTIVE_VARIANT_UNDETERMINED"
        assert document["authority_hash"] == AUTHORITY_HASH
        assert document["source_catalog_hash"] == SOURCE_CATALOG_HASH
        assert document["source_count"] == 2
        assert document["fact_count"] == 25
        assert document["unknown_count"] == 14
        for gate in (
            "transition_eligible",
            "live_transport_authorized",
            "account_readonly_runtime_authorized",
            "testnet_execution_authorized",
            "mainnet_execution_authorized",
            "flp1_implementation_authorized",
        ):
            assert document[gate] is False


def test_docs_share_capture_now_semantics() -> None:
    required_tokens = (
        "CAPTURE_ONLY",
        "ETH_OPERATOR_ASSIST",
        "CONTRACT_SCHEMA_GOVERNANCE_ONLY",
        "SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME",
    )
    for path in DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        for token in required_tokens:
            assert token in text, path

    capture_doc = (ROOT / "docs" / "V0_FLP0_CAPTURE_NOW_AUTHORITY.md").read_text(
        encoding="utf-8"
    )
    assert "RAW_PUBLIC_EVIDENCE_PLANE" in capture_doc
    assert "CAPTURE_AUTHORITY_PLANE" in capture_doc
    assert AUTHORITY_HASH in capture_doc
    assert SOURCE_CATALOG_HASH in capture_doc


def test_exact_changed_file_scope_and_forbidden_boundaries() -> None:
    changed = EXPECTED_CHANGED_FILES
    assert len(changed) == 18
    assert changed == {
        ".github/workflows/ci.yml",
        "README.md",
        "docs/V0_01_SCOPE.md",
        "docs/V0_FAST_LAUNCH_PROGRAM.md",
        "docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md",
        "docs/architecture/V0_01_DATA_PLANE.md",
        "docs/architecture/AUTHORITY_BOUNDARY.md",
        "docs/architecture/STRATEGY_AND_DATA_LIFECYCLE.md",
        "docs/architecture/PILOT_LEARNING_LOOP.md",
        "governance/V0_FAST_LAUNCH_PROGRAM.json",
        "governance/PROJECT_STATE.json",
        "schemas/governance/V0FastLaunchProgram.schema.json",
        "schemas/v0/CaptureRecordV0.schema.json",
        "scripts/export_schemas.py",
        "src/trader_assist_v0/contracts/__init__.py",
        "src/trader_assist_v0/contracts/capture.py",
        "tests/test_v0_fast_launch_governance_state.py",
        "tests/test_v0_flp1b0b_capture_now_authority.py",
    }
    assert set(EXPECTED_COMMITTED_STATUS_MAP) == changed
    assert tuple(EXPECTED_COMMITTED_STATUS_MAP.values()).count("A") == 4
    assert tuple(EXPECTED_COMMITTED_STATUS_MAP.values()).count("M") == 14
    assert not _scope_boundary_errors(changed)


def _synthetic_scope_snapshot(
    *,
    committed: dict[str, str] | None = None,
    staged: dict[str, str] | None = None,
    unstaged: dict[str, str] | None = None,
    untracked: tuple[str, ...] = (),
    malformed_records: tuple[str, ...] = (),
) -> _ScopeSnapshot:
    return _ScopeSnapshot(
        committed=dict(EXPECTED_COMMITTED_STATUS_MAP if committed is None else committed),
        staged={} if staged is None else staged,
        unstaged={} if unstaged is None else unstaged,
        untracked=untracked,
        malformed_records=malformed_records,
    )


def test_scope_parser_is_nul_safe_and_preserves_tab_and_newline_paths() -> None:
    parsed = _parse_stable_status_stream(
        b"M\0tab\tpath.py\0A\0line\nbreak.py\0",
        "attack",
    )
    assert parsed == {"tab\tpath.py": "M", "line\nbreak.py": "A"}
    assert _parse_untracked_stream(b"tab\tpath.py\0line\nbreak.py\0", "attack") == (
        "tab\tpath.py",
        "line\nbreak.py",
    )


@pytest.mark.parametrize(
    "raw, message",
    (
        (b"M\0truncated", "truncated"),
        (b"M\0", "malformed"),
        (b"Q\0path.py\0", "unknown status"),
        (b"M\0bad-\xff.py\0", "non-UTF-8"),
    ),
)
def test_scope_parser_rejects_malformed_unknown_and_non_utf8_streams(
    raw: bytes,
    message: str,
) -> None:
    with pytest.raises(_ScopeParseError, match=message):
        _parse_stable_status_stream(raw, "attack")


@pytest.mark.parametrize("range_name", ("committed", "staged", "unstaged"))
def test_scope_gate_rejects_deletion_in_every_status_map(range_name: str) -> None:
    maps = {
        "committed": dict(EXPECTED_COMMITTED_STATUS_MAP),
        "staged": {},
        "unstaged": {},
    }
    maps[range_name]["README.md"] = "D"
    snapshot = _synthetic_scope_snapshot(
        committed=maps["committed"],
        staged=maps["staged"],
        unstaged=maps["unstaged"],
    )
    findings = _scope_snapshot_findings(snapshot)
    assert (range_name, "D", "README.md") in findings["prohibited_statuses"]


def test_scope_gate_rejects_forbidden_deletion_and_untracked_paths() -> None:
    snapshot = _synthetic_scope_snapshot(
        unstaged={"src/trader_assist_v0/contracts/common.py": "D"},
        untracked=("unexpected\nfile.py",),
    )
    findings = _scope_snapshot_findings(snapshot)
    assert findings["unexpected_paths"] == [
        "src/trader_assist_v0/contracts/common.py",
        "unexpected\nfile.py",
    ]
    assert findings["prohibited_statuses"] == [
        ("unstaged", "D", "src/trader_assist_v0/contracts/common.py")
    ]
    assert findings["boundary_errors"]


@pytest.mark.parametrize("status", ("T", "U", "X", "B"))
def test_scope_gate_rejects_type_unmerged_unknown_and_broken_statuses(status: str) -> None:
    snapshot = _synthetic_scope_snapshot(unstaged={"README.md": status})
    assert _scope_snapshot_findings(snapshot)["prohibited_statuses"] == [
        ("unstaged", status, "README.md")
    ]


def test_scope_gate_rejects_forbidden_to_allowlisted_rename_as_delete_add() -> None:
    snapshot = _synthetic_scope_snapshot(
        unstaged={
            "src/trader_assist_v0/contracts/common.py": "D",
            "README.md": "A",
        }
    )
    findings = _scope_snapshot_findings(snapshot)
    assert ("unstaged", "D", "src/trader_assist_v0/contracts/common.py") in findings[
        "prohibited_statuses"
    ]
    assert "src/trader_assist_v0/contracts/common.py" in findings["unexpected_paths"]


def test_scope_gate_rejects_allowlisted_to_forbidden_rename_as_delete_add() -> None:
    snapshot = _synthetic_scope_snapshot(
        unstaged={"README.md": "D", "forbidden-destination.md": "A"}
    )
    findings = _scope_snapshot_findings(snapshot)
    assert ("unstaged", "D", "README.md") in findings["prohibited_statuses"]
    assert findings["unexpected_paths"] == ["forbidden-destination.md"]


def test_scope_gate_rejects_unauthorized_copy_destination_path() -> None:
    snapshot = _synthetic_scope_snapshot(
        unstaged={"unauthorized-copy.py": "A"}
    )
    assert _scope_snapshot_findings(snapshot)["unexpected_paths"] == [
        "unauthorized-copy.py"
    ]


def test_scope_gate_governs_authorized_copy_target_by_exact_expected_status() -> None:
    assert not any(_scope_snapshot_findings(_synthetic_scope_snapshot()).values())
    wrong_status = dict(EXPECTED_COMMITTED_STATUS_MAP)
    wrong_status["docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md"] = "M"
    assert _scope_snapshot_findings(
        _synthetic_scope_snapshot(committed=wrong_status)
    )["status_mismatches"]


def test_scope_gate_rejects_status_mismatch_and_cli_prints_full_maps(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    committed = dict(EXPECTED_COMMITTED_STATUS_MAP)
    committed["docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md"] = "M"
    snapshot = _synthetic_scope_snapshot(
        committed=committed,
        malformed_records=("unstaged: malformed status/path record",),
    )
    monkeypatch.setattr(sys.modules[__name__], "_collect_pr_scope_snapshot", lambda _sha: snapshot)
    assert _check_pr_scope(BASE_SHA) == 1
    stderr = capsys.readouterr().err
    for label in (
        "missing paths",
        "unexpected paths",
        "prohibited statuses",
        "malformed records",
        "actual committed map",
        "actual staged map",
        "actual unstaged map",
        "actual untracked map",
    ):
        assert label in stderr


def _scope_boundary_errors(changed: set[str]) -> list[str]:
    errors: list[str] = []
    forbidden = sorted(changed & FORBIDDEN_FILES)
    if forbidden:
        errors.append(f"forbidden files: {', '.join(forbidden)}")
    data_files = sorted(
        path for path in changed if path.startswith("src/trader_assist_v0/data/")
    )
    if data_files:
        errors.append(f"data files: {', '.join(data_files)}")
    dependency_files = sorted(
        path
        for path in changed
        if path in {"pyproject.toml", "requirements-dev.lock", "requirements-runtime.lock"}
    )
    if dependency_files:
        errors.append(f"dependency or lock files: {', '.join(dependency_files)}")
    workflow_files = {
        path for path in changed if path.startswith(".github/workflows/")
    }
    if workflow_files != {".github/workflows/ci.yml"}:
        errors.append(f"workflow files: {', '.join(sorted(workflow_files))}")
    return errors


@dataclass(frozen=True)
class _ScopeSnapshot:
    committed: dict[str, str]
    staged: dict[str, str]
    unstaged: dict[str, str]
    untracked: tuple[str, ...]
    malformed_records: tuple[str, ...]


class _ScopeParseError(ValueError):
    pass


def _nul_tokens(raw: bytes, context: str) -> list[bytes]:
    if type(raw) is not bytes:
        raise TypeError(f"{context} output must be exact bytes")
    if not raw:
        return []
    if not raw.endswith(b"\0"):
        raise _ScopeParseError(f"{context}: truncated NUL stream")
    return raw[:-1].split(b"\0")


def _decode_git_path(raw: bytes, context: str) -> str:
    if not raw:
        raise _ScopeParseError(f"{context}: empty path")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _ScopeParseError(f"{context}: non-UTF-8 path") from exc


def _parse_stable_status_stream(raw: bytes, context: str) -> dict[str, str]:
    tokens = _nul_tokens(raw, context)
    if len(tokens) % 2:
        raise _ScopeParseError(f"{context}: malformed status/path record")
    status_map: dict[str, str] = {}
    for offset in range(0, len(tokens), 2):
        try:
            status = tokens[offset].decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise _ScopeParseError(f"{context}: non-ASCII status") from exc
        if len(status) != 1 or status not in "ACDMRTUXB":
            raise _ScopeParseError(f"{context}: unknown status {status!r}")
        if status in {"R", "C"}:
            raise _ScopeParseError(f"{context}: prohibited non-path status {status!r}")
        path = _decode_git_path(tokens[offset + 1], context)
        if path in status_map:
            raise _ScopeParseError(f"{context}: duplicate path record {path!r}")
        status_map[path] = status
    return status_map


def _parse_untracked_stream(raw: bytes, context: str) -> tuple[str, ...]:
    paths = tuple(_decode_git_path(token, context) for token in _nul_tokens(raw, context))
    if len(set(paths)) != len(paths):
        raise _ScopeParseError(f"{context}: duplicate untracked path")
    return paths


def _run_git_bytes(arguments: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode:
        detail_bytes = result.stderr.strip() or result.stdout.strip()
        detail = detail_bytes.decode("utf-8", errors="backslashreplace")
        raise RuntimeError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout


def _collect_pr_scope_snapshot(base_sha: str) -> _ScopeSnapshot:
    if not COMMIT_SHA_PATTERN.fullmatch(base_sha):
        raise ValueError("--check-pr-scope requires a 40-character commit SHA")

    stable_arguments = {
        "committed": [
            "diff",
            "--name-status",
            "-z",
            "--no-renames",
            "--diff-filter=ACDMRTUXB",
            f"{base_sha}...HEAD",
            "--",
        ],
        "staged": [
            "diff",
            "--cached",
            "--name-status",
            "-z",
            "--no-renames",
            "--diff-filter=ACDMRTUXB",
            "HEAD",
            "--",
        ],
        "unstaged": [
            "diff",
            "--name-status",
            "-z",
            "--no-renames",
            "--diff-filter=ACDMRTUXB",
            "HEAD",
            "--",
        ],
    }
    status_maps: dict[str, dict[str, str]] = {}
    malformed: list[str] = []
    for range_name, arguments in stable_arguments.items():
        raw = _run_git_bytes(arguments)
        try:
            status_maps[range_name] = _parse_stable_status_stream(raw, range_name)
        except _ScopeParseError as exc:
            malformed.append(str(exc))
            status_maps[range_name] = {}
    untracked_raw = _run_git_bytes(["ls-files", "-z", "--others", "--exclude-standard"])
    try:
        untracked = _parse_untracked_stream(untracked_raw, "untracked")
    except _ScopeParseError as exc:
        malformed.append(str(exc))
        untracked = ()
    return _ScopeSnapshot(
        committed=status_maps["committed"],
        staged=status_maps["staged"],
        unstaged=status_maps["unstaged"],
        untracked=untracked,
        malformed_records=tuple(malformed),
    )


def _scope_snapshot_findings(snapshot: _ScopeSnapshot) -> dict[str, Any]:
    actual_paths = (
        set(snapshot.committed)
        | set(snapshot.staged)
        | set(snapshot.unstaged)
        | set(snapshot.untracked)
    )
    prohibited_statuses = sorted(
        (range_name, status, path)
        for range_name, status_map in (
            ("committed", snapshot.committed),
            ("staged", snapshot.staged),
            ("unstaged", snapshot.unstaged),
        )
        for path, status in status_map.items()
        if status not in {"A", "M"}
    )
    status_mismatches = sorted(
        (path, EXPECTED_COMMITTED_STATUS_MAP[path], snapshot.committed.get(path))
        for path in EXPECTED_CHANGED_FILES
        if snapshot.committed.get(path) != EXPECTED_COMMITTED_STATUS_MAP[path]
    )
    return {
        "missing_paths": sorted(EXPECTED_CHANGED_FILES - actual_paths),
        "unexpected_paths": sorted(actual_paths - EXPECTED_CHANGED_FILES),
        "prohibited_statuses": prohibited_statuses,
        "status_mismatches": status_mismatches,
        "malformed_records": list(snapshot.malformed_records),
        "boundary_errors": _scope_boundary_errors(actual_paths),
    }


def _check_pr_scope(base_sha: str) -> int:
    try:
        snapshot = _collect_pr_scope_snapshot(base_sha)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("missing paths: <unavailable>", file=sys.stderr)
        print("unexpected paths: <unavailable>", file=sys.stderr)
        print("prohibited statuses: <unavailable>", file=sys.stderr)
        print("malformed records: <unavailable>", file=sys.stderr)
        print("actual committed map: <unavailable>", file=sys.stderr)
        print("actual staged map: <unavailable>", file=sys.stderr)
        print("actual unstaged map: <unavailable>", file=sys.stderr)
        print("actual untracked map: <unavailable>", file=sys.stderr)
        return 2

    findings = _scope_snapshot_findings(snapshot)
    if any(findings.values()):
        print(f"missing paths: {findings['missing_paths']}", file=sys.stderr)
        print(f"unexpected paths: {findings['unexpected_paths']}", file=sys.stderr)
        print(f"prohibited statuses: {findings['prohibited_statuses']}", file=sys.stderr)
        print(f"status mismatches: {findings['status_mismatches']}", file=sys.stderr)
        print(f"malformed records: {findings['malformed_records']}", file=sys.stderr)
        print(f"actual committed map: {sorted(snapshot.committed.items())}", file=sys.stderr)
        print(f"actual staged map: {sorted(snapshot.staged.items())}", file=sys.stderr)
        print(f"actual unstaged map: {sorted(snapshot.unstaged.items())}", file=sys.stderr)
        print(f"actual untracked map: {sorted(snapshot.untracked)}", file=sys.stderr)
        for error in findings["boundary_errors"]:
            print(f"boundary error: {error}", file=sys.stderr)
        return 1

    print(f"PR scope check passed: {len(snapshot.committed)} files (4 A, 14 M)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-pr-scope", metavar="BASE_SHA")
    arguments = parser.parse_args()
    if arguments.check_pr_scope is None:
        parser.error("--check-pr-scope BASE_SHA is required")
    return _check_pr_scope(arguments.check_pr_scope)


if __name__ == "__main__":
    raise SystemExit(main())
