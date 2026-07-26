"""Static, offline checks for the First Launch supported-host packet."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

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
EXPECTED_MANIFEST_KEYS = {
    "manifest_version",
    "task_id",
    "authorized_deployment_sha",
    "os_version",
    "architecture",
    "kernel_version",
    "python_version",
    "systemd_version",
    "unit_verify_result",
    "deployed_head",
    "clean_tree_result",
    "service_unit_sha256",
    "ta_status_sha256",
    "ownership_and_modes_result",
    "credential_ingress_result",
    "default_off_result",
    "initial_ready_output",
    "initial_window_start",
    "initial_window_end",
    "controlled_restart_result",
    "post_restart_ready_output",
    "post_restart_window_start",
    "post_restart_window_end",
    "sqlite_integrity_result",
    "bounded_journal_sha256",
    "evidence_secret_scan_result",
    "final_service_state",
    "final_runtime_process_result",
    "qualification_result",
    "unresolved_limitations",
    "manifest_sha256",
}
FIXED_MANIFEST_VALUES = {
    "manifest_version": "v1",
    "task_id": "FIRST_LAUNCH_SUPPORTED_HOST_DEPLOYMENT_AND_QUALIFICATION_PACKET_V1",
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


def _manifest() -> dict[str, str]:
    parsed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def test_all_four_authorized_files_exist() -> None:
    assert len(AUTHORIZED_FILES) == 4
    assert all(path.is_file() for path in AUTHORIZED_FILES)


def test_manifest_has_exact_keys_fixed_values_and_placeholders() -> None:
    manifest = _manifest()
    assert set(manifest) == EXPECTED_MANIFEST_KEYS
    for key, value in FIXED_MANIFEST_VALUES.items():
        assert manifest[key] == value
    for key, value in manifest.items():
        if key not in FIXED_MANIFEST_VALUES:
            assert isinstance(value, str)
            assert value == "PLACEHOLDER"


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


def test_packet_has_four_separately_authorized_phases() -> None:
    packet = _packet()
    required_phases = (
        "PHASE 0 — READ_ONLY_HOST_PREFLIGHT",
        "PHASE 1 — DEPLOYMENT",
        "PHASE 2 — RUNTIME_AND_QUALIFICATION",
        "PHASE 3 — ACCEPTED_REAL_OPERATION",
        "Separate host-access authorization",
        "Separate deployment authorization",
        "Separate runtime and supervised-smoke authorization",
        "Separate final user acceptance",
    )
    for required in required_phases:
        assert required in packet
    assert "never activates a later phase" in packet


def test_packet_uses_installed_systemd_control_utility_for_version() -> None:
    packet = _packet()
    assert "systemctl --version" in packet
    assert "systemd --version" not in packet
    assert "systemd-analyze --version" in packet


def test_packet_and_runbook_bind_one_validated_python_interpreter() -> None:
    packet = _packet()
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    for content in (packet, runbook):
        assert "PYTHON_BIN" in content
        assert "sys.version_info >= (3, 12)" in content
    assert 'sudo "$PYTHON_BIN" -m venv venv' in runbook
    assert "sudo python3.12 -m venv venv" not in runbook
    assert "PYTHON_BIN=%s" in packet
    assert "PYTHON_VERSION=" in packet
    normalized_packet = " ".join(packet.split())
    assert "same separately approved interpreter path" in normalized_packet
    assert "requires revalidation" in normalized_packet


def test_runbook_requires_systemd_analyze_and_fails_closed() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    assert "`systemd-analyze` is required for unit validation" in runbook
    assert "optional but recommended" not in runbook
    assert "absence fails the supported-host preflight closed" in " ".join(runbook.split())


def test_packet_has_status_meanings_recovery_and_bounded_journal() -> None:
    packet = _packet()
    assert "sudo /opt/trader-assist-v0/bin/ta-status" in packet
    for classification, exit_code, meaning in (
        ("READY", "0", "Signals may be considered"),
        ("NOT_READY", "1", "Ignore system signals"),
        ("STATUS_UNKNOWN", "2", "investigate if persistent"),
    ):
        assert classification in packet
        assert f"{exit_code} |" in packet
        assert meaning in packet
    assert "sudo systemctl stop trader-assist-v0-public.service" in packet
    assert "sudo systemctl start trader-assist-v0-public.service" in packet
    assert (
        'sudo journalctl -u trader-assist-v0-public.service --since "30 minutes ago" '
        "--no-pager"
    ) in packet


def test_packet_has_bounded_qualification_and_final_closeout() -> None:
    packet = " ".join(_packet().split())
    for required in (
        "at least 30 minutes after initial `READY`",
        "at least 30 minutes after post-restart `READY`",
        "Target a total observation time of 60 minutes",
        "maximum bounded extension is 90 minutes",
        "start, midpoint, and end",
        "service stopped, disabled, and with no runtime process remaining",
        "QUALIFICATION_PASS",
        "QUALIFICATION_FAIL",
        "QUALIFICATION_INCOMPLETE",
    ):
        assert required in packet
    assert "not a pass" in packet


def test_packet_keeps_current_task_authority_closed() -> None:
    packet = _packet()
    for required in (
        "HOST_ACCESS_NOT_AUTHORIZED",
        "DEPLOYMENT_NOT_AUTHORIZED",
        "RUNTIME_AND_SMOKE_NOT_AUTHORIZED",
        "does not authorize any command in this document to be run against a real host",
    ):
        assert required in packet


def test_runbook_uses_ta_status_as_primary_ready_proof() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    status_section = runbook.split("## 16. Status Procedure", maxsplit=1)[1].split(
        "## 17.", maxsplit=1
    )[0]
    ready_section = runbook.split("## 20. READY Verification", maxsplit=1)[1].split(
        "## 21.", maxsplit=1
    )[0]
    assert "sudo /opt/trader-assist-v0/bin/ta-status" in status_section
    assert "sudo /opt/trader-assist-v0/bin/ta-status" in ready_section
    assert "Do not use a journal session message as primary READY proof." in ready_section
    assert "session=<uuid>" not in ready_section


def test_existing_assets_are_unchanged() -> None:
    for relative_path, expected_hash in UNCHANGED_ASSET_HASHES.items():
        actual_hash = hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, relative_path


def test_this_test_is_static_and_offline() -> None:
    source = TEST_PATH.read_text(encoding="utf-8")
    forbidden_imports = (
        "import " + "sub" + "process",
        "import " + "requests",
        "import " + "socket",
    )
    for forbidden_import in forbidden_imports:
        assert forbidden_import not in source
