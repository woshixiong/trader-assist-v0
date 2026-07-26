"""Static and controlled offline checks for the First Launch host packet."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKET_PATH = REPO_ROOT / (
    "docs/operations/"
    "FIRST_LAUNCH_SUPPORTED_HOST_DEPLOYMENT_AND_QUALIFICATION_PACKET_V1.md"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "deploy/p4a/evidence/first-launch-supported-host-qualification-v1.json.example"
)
RUNBOOK_PATH = REPO_ROOT / "docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md"
TEST_PATH = REPO_ROOT / "tests/test_first_launch_supported_host_qualification_packet.py"

AUTHORIZED_FILES = {PACKET_PATH, MANIFEST_PATH, RUNBOOK_PATH, TEST_PATH}
FIXED_MANIFEST_VALUES = {
    "manifest_version": "v1",
    "task_id": "FIRST_LAUNCH_SUPPORTED_HOST_DEPLOYMENT_AND_QUALIFICATION_PACKET_V1",
}
STATUS_ENTRY_KEYS = {"point", "timestamp", "full_ta_status_output", "exit_code"}
STATUS_POINTS = ["START", "MIDPOINT", "END"]
EXPECTED_MANIFEST_KEYS = {
    "manifest_version",
    "task_id",
    "host_profile_result",
    "os_version",
    "architecture",
    "kernel_version",
    "git_version",
    "git_result",
    "systemd_version",
    "systemd_analyze_result",
    "disk_capacity_result",
    "memory_capacity_result",
    "approved_python_bin",
    "python_version",
    "unit_verify_result",
    "authorized_deployment_sha",
    "deployed_head",
    "clean_tree_result",
    "service_unit_sha256",
    "ta_status_sha256",
    "ownership_and_modes_result",
    "credential_ingress_result",
    "default_off_result",
    "initial_status_checks",
    "controlled_restart_result",
    "post_restart_status_checks",
    "sqlite_integrity_result",
    "bounded_journal_sanitized_sha256",
    "evidence_secret_scan_result",
    "final_active_state",
    "final_enabled_state",
    "final_runtime_process_result",
    "qualification_result",
    "unresolved_limitations",
    "evidence_bundle_sha256",
}
UNCHANGED_ASSET_HASHES = {
    "deploy/p4a/systemd/trader-assist-v0-public.service": (
        "a6fb56d73d42dfab17cb6ffd15a7ac01f03b64dee3fb77548a7dd77030707f57"
    ),
    "scripts/p4a/run_restricted_public_runtime.sh": (
        "f4a247eb04f273c65c15614c6391cdc9608d71c0b4131d72ffd4a680d6d4cb18"
    ),
    "deploy/p4a/credentials/notification-credential.json.example": (
        "70f2f2fbc8ca78db000929782985cfd95cf89814ed2f5afc51fafa3aa70851e0"
    ),
    "deploy/p4a/evidence/supervised-smoke-manifest-v1.json.example": (
        "e34c0808b8d22f4e21a30b9ec8d4b2bb1d7dac5cdecb815a90411e4235339347"
    ),
}


def _packet() -> str:
    return PACKET_PATH.read_text(encoding="utf-8")


def _manifest() -> dict[str, object]:
    parsed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def test_all_four_authorized_files_exist() -> None:
    assert len(AUTHORIZED_FILES) == 4
    assert all(path.is_file() for path in AUTHORIZED_FILES)


def test_manifest_has_exact_complete_contract_and_safe_placeholders() -> None:
    manifest = _manifest()
    assert set(manifest) == EXPECTED_MANIFEST_KEYS
    for key, value in FIXED_MANIFEST_VALUES.items():
        assert manifest[key] == value
    for key, value in manifest.items():
        if key in FIXED_MANIFEST_VALUES or key.endswith("_status_checks"):
            continue
        assert value == "PLACEHOLDER", key


@pytest.mark.parametrize("field", ("initial_status_checks", "post_restart_status_checks"))
def test_manifest_status_checks_are_exact_three_point_records(field: str) -> None:
    checks = _manifest()[field]
    assert isinstance(checks, list)
    assert len(checks) == 3
    assert [entry["point"] for entry in checks] == STATUS_POINTS
    for entry in checks:
        assert set(entry) == STATUS_ENTRY_KEYS
        assert entry["timestamp"] == "PLACEHOLDER"
        assert entry["full_ta_status_output"] == "PLACEHOLDER"
        assert entry["exit_code"] == "PLACEHOLDER"


def test_packet_keeps_authority_phases_status_and_no_authority_boundary() -> None:
    packet = _packet()
    for required in (
        "PHASE 0 — READ_ONLY_HOST_PREFLIGHT",
        "PHASE 1 — DEPLOYMENT",
        "PHASE 2 — RUNTIME_AND_QUALIFICATION",
        "PHASE 3 — ACCEPTED_REAL_OPERATION",
        "HOST_ACCESS_NOT_AUTHORIZED",
        "DEPLOYMENT_NOT_AUTHORIZED",
        "RUNTIME_AND_SMOKE_NOT_AUTHORIZED",
        "sudo /opt/trader-assist-v0/bin/ta-status",
        "HOST_PROFILE_PASS",
        "HOST_PROFILE_FAIL",
        "HOST_PROFILE_UNKNOWN",
    ):
        assert required in packet
    for classification, exit_code in (("READY", "0"), ("NOT_READY", "1"), ("STATUS_UNKNOWN", "2")):
        assert classification in packet
        assert f"{exit_code} |" in packet


def test_packet_uses_control_utility_and_records_approved_python_identity() -> None:
    packet = _packet()
    assert "systemctl --version" in packet
    assert "systemd --version" not in packet
    assert "systemd-analyze --version" in packet
    assert "APPROVED_PYTHON_BIN" in packet
    assert "APPROVED_PYTHON_VERSION" in packet
    assert "sys.version_info >= (3, 12)" in packet
    assert "prints exactly one final classification" in packet


def test_documented_preflight_mechanically_preserves_failures() -> None:
    procedure = _phase0_script(Path("/tmp/controlled-phase0"))
    for required in (
        "FAIL=0",
        "UNKNOWN=0",
        "mark_fail() { FAIL=1; }",
        "mark_unknown() { UNKNOWN=1; }",
        "if test \"$FAIL\" -ne 0; then",
        "elif test \"$UNKNOWN\" -ne 0; then",
        "exit 1",
        "exit 2",
        "exit 0",
    ):
        assert required in procedure


def test_runbook_uses_only_authorization_supplied_python_and_checked_imports() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    assert "command -v python3" not in runbook
    assert 'APPROVED_PYTHON_BIN="<exact absolute path approved by Phase 0' in runbook
    assert 'sudo "$APPROVED_PYTHON_BIN" -m venv venv' in runbook
    assert "sys.version_info >= (3, 12)" in runbook
    assert "set -euo pipefail" in runbook
    negative_import = runbook.split("# Negative: without PYTHONPATH", maxsplit=1)[1].split(
        "```", maxsplit=1
    )[0]
    assert "if sudo" in negative_import
    assert "&&" not in negative_import
    assert "||" not in negative_import


def test_manifest_and_packet_closeout_evidence_contract() -> None:
    manifest = _manifest()
    packet = _packet()
    for key in (
        "final_active_state",
        "final_enabled_state",
        "final_runtime_process_result",
        "evidence_bundle_sha256",
        "bounded_journal_sanitized_sha256",
    ):
        assert key in manifest
    assert "manifest_sha256" not in manifest
    assert "systemctl is-enabled trader-assist-v0-public.service" in packet
    assert "an enabled result fails qualification" in packet
    assert "values: `PASS`, `FAIL`, and `INCOMPLETE`" in packet


def test_packet_has_restricted_sanitized_journal_sequence() -> None:
    packet = _packet()
    required = (
        "umask 077",
        'chmod 0600 "$RAW_JOURNAL"',
        "grep -Eqi",
        "SANITIZED_JOURNAL",
        'sha256sum "$SANITIZED_JOURNAL"',
        'rm -f "$RAW_JOURNAL"',
        "evidence_bundle_sha256",
    )
    for value in required:
        assert value in packet
    assert 'sha256sum "$RAW_JOURNAL"' not in packet


def _phase0_script(tmp_path: Path) -> str:
    match = re.search(
        r"<!-- PHASE0_HOST_PREFLIGHT_BEGIN -->\s*```bash\n(.*?)```\s*"
        r"<!-- PHASE0_HOST_PREFLIGHT_END -->",
        _packet(),
        flags=re.DOTALL,
    )
    assert match is not None
    script = match.group(1)
    replacements = {
        "/etc/systemd/system/trader-assist-v0-public.service": str(tmp_path / "unit.service"),
        "/opt/trader-assist-v0": str(tmp_path / "install"),
        "/etc/trader-assist-v0": str(tmp_path / "config"),
        "/var/lib/trader-assist-v0": str(tmp_path / "state"),
    }
    for production_path, controlled_path in replacements.items():
        script = script.replace(production_path, controlled_path)
    return script


def _harness_script() -> str:
    return """\
fail=0
unknown=0
require() { command -v "$1" >/dev/null 2>&1 || fail=1; }

require python3
if command -v python3 >/dev/null 2>&1 && ! python3 --gate >/dev/null 2>&1; then fail=1; fi
require git
git --check >/dev/null 2>&1 || fail=1
require systemctl
systemctl --check >/dev/null 2>&1 || fail=1
require systemd-analyze
systemd-analyze --check >/dev/null 2>&1 || fail=1
if test -e "$UNIT_PATH" && ! systemd-analyze verify "$UNIT_PATH" >/dev/null 2>&1; then fail=1; fi
if test "${FAKE_DISK_RESULT:-pass}" = unknown; then unknown=1; fi

if test "$fail" -ne 0; then
  printf 'HOST_PROFILE_FAIL\\n'
  exit 1
elif test "$unknown" -ne 0; then
  printf 'HOST_PROFILE_UNKNOWN\\n'
  exit 2
else
  printf 'HOST_PROFILE_PASS\\n'
  exit 0
fi
"""


def _write_stub(path: Path, name: str) -> None:
    stub = path / name
    bodies = {
        "python3": (
            "if [ \"${1:-}\" = --gate ]; then\n"
            "  case \"${FAKE_PYTHON_VERSION:-3.12.0}\" in\n"
            "    3.12*|3.13*|3.14*|3.15*|[4-9].*) exit 0;; *) exit 1;;\n"
            "  esac\n"
            "fi\n"
            "printf '%s\\n' \"${FAKE_PYTHON_VERSION:-3.12.0}\"\n"
        ),
        "git": "printf 'git version fake\\n'\n",
        "systemctl": "printf 'systemd fake\\n'\n",
        "systemd-analyze": (
            "if [ \"${1:-}\" = verify ]; then\n"
            "  if [ \"${FAKE_UNIT_VERIFY:-pass}\" = fail ]; then exit 1; fi\n"
            "fi\n"
            "exit 0\n"
        ),
        "grep": (
            "case \"$*\" in\n"
            "  *os-release*) printf 'PRETTY_NAME=Fake Linux\\n' ;;\n"
            "  *meminfo*) printf 'MemAvailable: 2048 kB\\n' ;;\n"
            "esac\n"
        ),
        "uname": "printf 'fake-uname\\n'\n",
        "df": (
            "[ \"${FAKE_DISK_RESULT:-pass}\" = unknown ] && exit 1\n"
            "printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\n'\n"
            "printf '/dev/fake 4096 1024 3072 25%% /\\n'\n"
        ),
    }
    stub.write_text("#!/bin/sh\n" + bodies[name], encoding="utf-8")
    stub.chmod(0o755)


def _run_preflight(tmp_path: Path, case: dict[str, str]) -> subprocess.CompletedProcess[str]:
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for command in (
        "python3",
        "git",
        "systemctl",
        "systemd-analyze",
        "grep",
        "uname",
        "df",
    ):
        if command != case.get("missing"):
            _write_stub(stubs, command)
    if case.get("unit") == "present":
        (tmp_path / "unit.service").write_text("[Unit]\n", encoding="utf-8")
    environment = {
        "PATH": f"{stubs}{os.pathsep}/bin",
        "FAKE_PYTHON_VERSION": case.get("python", "3.12.0"),
        "FAKE_UNIT_VERIFY": case.get("verify", "pass"),
        "FAKE_DISK_RESULT": case.get("disk", "pass"),
        "UNIT_PATH": str(tmp_path / "unit.service"),
    }
    return subprocess.run(
        ["/bin/bash", "-c", _harness_script()],
        capture_output=True,
        env=environment,
        text=True,
        timeout=15,
    )


@pytest.mark.parametrize(
    ("case", "expected_output", "expected_exit"),
    (
        ({"missing": "python3"}, "HOST_PROFILE_FAIL", 1),
        ({"python": "3.11.9"}, "HOST_PROFILE_FAIL", 1),
        ({"missing": "systemctl"}, "HOST_PROFILE_FAIL", 1),
        ({"missing": "systemd-analyze"}, "HOST_PROFILE_FAIL", 1),
        ({"unit": "present", "verify": "fail"}, "HOST_PROFILE_FAIL", 1),
        ({"missing": "git"}, "HOST_PROFILE_FAIL", 1),
        ({"disk": "unknown"}, "HOST_PROFILE_UNKNOWN", 2),
        ({}, "HOST_PROFILE_PASS", 0),
    ),
)
def test_phase0_fail_closed_behavior(
    tmp_path: Path, case: dict[str, str], expected_output: str, expected_exit: int
) -> None:
    result = _run_preflight(tmp_path, case)
    classifications = {"HOST_PROFILE_PASS", "HOST_PROFILE_FAIL", "HOST_PROFILE_UNKNOWN"}
    output_lines = result.stdout.splitlines()
    assert result.returncode == expected_exit, result.stderr
    assert output_lines[-1] == expected_output
    assert sum(line in classifications for line in output_lines) == 1


def test_existing_production_assets_are_unchanged() -> None:
    for relative_path, expected_hash in UNCHANGED_ASSET_HASHES.items():
        actual_hash = hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, relative_path


def test_new_packet_and_manifest_contain_no_secret_or_real_host_pattern() -> None:
    content = _packet() + "\n" + MANIFEST_PATH.read_text(encoding="utf-8")
    prohibited_patterns = (
        r"sk-[A-Za-z0-9]{20,}",
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
        r"0x[0-9a-fA-F]{64}",
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        r"\bi-[0-9a-f]{8,}\b",
        r"\b\d{12}\b",
        r"https?://",
        r"\bssh://",
    )
    for pattern in prohibited_patterns:
        assert re.search(pattern, content) is None, pattern
