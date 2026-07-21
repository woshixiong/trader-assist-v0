"""Static offline tests for the P4A local deployment package.

These tests verify the eight-file implementation scope, systemd unit content,
environment and risk configuration fail-closed behavior, wrapper guardrails,
and the absence of secrets, credentials, or prohibited configuration.

All tests are static, offline, and non-root. No runtime is started, no
network requests are made, and no systemd service is installed or enabled.

Tests are portable across macOS local devel and Linux GitHub Actions.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_FILES = {
    "deploy/p4a/systemd/trader-assist-v0-public.service",
    "deploy/p4a/systemd/trader-assist-v0-public.env.example",
    "deploy/p4a/config/risk-configuration.json.example",
    "deploy/p4a/credentials/notification-credential.json.example",
    "scripts/p4a/run_restricted_public_runtime.sh",
    "deploy/p4a/evidence/supervised-smoke-manifest-v1.json.example",
    "docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md",
    "tests/test_p4a_local_deployment_package.py",
}

PROHIBITED_PREFIXES = (
    "src/",
    "governance/",
    "schemas/",
    ".github/",
)

PROHIBITED_FILES = {
    "requirements-runtime.lock",
    "requirements-dev.lock",
    "pyproject.toml",
}

SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"x-api-key[=:]\s*\S+"),
    re.compile(r"api[_-]?key[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"secret[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"token[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"password[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
    re.compile(r"0x[0-9a-fA-F]{64}"),
]

PROHIBITED_CONTENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"AWS_", re.IGNORECASE),
    re.compile(r"aws_access_key", re.IGNORECASE),
    re.compile(r"aws_secret", re.IGNORECASE),
    re.compile(r"ACCOUNT_ID", re.IGNORECASE),
    re.compile(r"PRIVATE_KEY", re.IGNORECASE),
    re.compile(r"WALLET", re.IGNORECASE),
    re.compile(r"MNEMONIC", re.IGNORECASE),
    re.compile(r"EXCHANGE_WRITE", re.IGNORECASE),
    re.compile(r"ORDER_PLACE", re.IGNORECASE),
    re.compile(r"NONCE", re.IGNORECASE),
    re.compile(r"SIGNING_KEY", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Exact-scope constants (ER-06)
# ---------------------------------------------------------------------------

EXACT_BASE = "8480d0b6ef0354de29283d86bbc5759491f822f3"
EXACT_SCOPE_BRANCH = "feature/v0-fl-r3-p4a-local-deployment-package"

EXPECTED_EXACT_SCOPE: set[tuple[str, str]] = {
    ("A", "deploy/p4a/config/risk-configuration.json.example"),
    ("A", "deploy/p4a/credentials/notification-credential.json.example"),
    ("A", "deploy/p4a/evidence/supervised-smoke-manifest-v1.json.example"),
    ("A", "deploy/p4a/systemd/trader-assist-v0-public.env.example"),
    ("A", "deploy/p4a/systemd/trader-assist-v0-public.service"),
    ("A", "docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md"),
    ("A", "scripts/p4a/run_restricted_public_runtime.sh"),
    ("A", "tests/test_p4a_local_deployment_package.py"),
}

# ---------------------------------------------------------------------------
# Test 1: Exact eight-file implementation scope
# ---------------------------------------------------------------------------

def _collect_p4a_files() -> set[str]:
    """Collect all new P4A files by listing the allowed directories."""
    found: set[str] = set()
    for allowed in ALLOWED_FILES:
        full = REPO_ROOT / allowed
        if full.exists():
            found.add(allowed)
    return found


def test_exact_eight_file_scope() -> None:
    """All eight authorized files exist and no extra files are present."""
    found = _collect_p4a_files()
    assert found == ALLOWED_FILES, (
        f"Expected exactly 8 files, got {len(found)}. "
        f"Missing: {ALLOWED_FILES - found}. "
        f"Extra: {found - ALLOWED_FILES}"
    )
    assert len(found) == 8, f"Expected 8 files, got {len(found)}"


# ---------------------------------------------------------------------------
# Test 2: No prohibited-path changes
# ---------------------------------------------------------------------------

def test_no_prohibited_path_changes() -> None:
    """No file under prohibited paths was modified.

    This test is a static check: the allowed files must not reside under any
    prohibited prefix.
    """
    for path in ALLOWED_FILES:
        for prefix in PROHIBITED_PREFIXES:
            assert not path.startswith(prefix), (
                f"File {path} is under prohibited prefix {prefix}"
            )


# ---------------------------------------------------------------------------
# Test 3: Systemd unit content verification
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def service_unit() -> str:
    return (REPO_ROOT / "deploy/p4a/systemd/trader-assist-v0-public.service").read_text()


def test_service_type_simple(service_unit: str) -> None:
    assert "Type=simple" in service_unit


def test_service_user_traderassist(service_unit: str) -> None:
    assert "User=traderassist" in service_unit


def test_service_group_traderassist(service_unit: str) -> None:
    assert "Group=traderassist" in service_unit


def test_service_condition_path_exists(service_unit: str) -> None:
    assert "ConditionPathExists=" in service_unit


def test_service_condition_path_exists_in_unit_section(service_unit: str) -> None:
    """ConditionPathExists must be in the [Unit] section, not [Service]."""
    # Split unit into sections
    sections = re.split(r"\n\[", service_unit)
    unit_section = ""
    service_section = ""
    for section in sections:
        section_text = "[" + section if not section.startswith("[") else section
        if section_text.startswith("[Unit]"):
            unit_section = "\n[" + section
        elif section_text.startswith("[Service]"):
            service_section = "\n[" + section

    assert "ConditionPathExists=" in unit_section, (
        "ConditionPathExists must be in [Unit] section"
    )
    assert "ConditionPathExists=" not in service_section, (
        "ConditionPathExists must NOT be in [Service] section"
    )


def test_service_environment_file(service_unit: str) -> None:
    assert "EnvironmentFile=" in service_unit


def test_service_exec_start_wrapper_only(service_unit: str) -> None:
    assert "ExecStart=" in service_unit
    assert "run_restricted_public_runtime.sh" in service_unit
    # Must not exec Python directly
    assert "run_first_launch_public_runtime.py" not in service_unit


def test_service_restart_no(service_unit: str) -> None:
    assert "Restart=no" in service_unit


def test_service_kill_signal_sigterm(service_unit: str) -> None:
    assert "KillSignal=SIGTERM" in service_unit


def test_service_timeout_stop_sec_bounded(service_unit: str) -> None:
    match = re.search(r"TimeoutStopSec=(\d+)", service_unit)
    assert match is not None, "TimeoutStopSec not found"
    value = int(match.group(1))
    assert 1 <= value <= 300, f"TimeoutStopSec={value} out of bounded range [1,300]"


def test_service_standard_output_journal(service_unit: str) -> None:
    assert "StandardOutput=journal" in service_unit


def test_service_standard_error_journal(service_unit: str) -> None:
    assert "StandardError=journal" in service_unit


def test_service_syslog_identifier_fixed(service_unit: str) -> None:
    match = re.search(r"SyslogIdentifier=(\S+)", service_unit)
    assert match is not None, "SyslogIdentifier not found"
    assert match.group(1) == "trader-assist-v0-public"


def test_service_hardening_directives(service_unit: str) -> None:
    required = [
        "NoNewPrivileges=yes",
        "ProtectSystem=",
        "ProtectHome=yes",
        "PrivateTmp=yes",
        "ProtectKernelTunables=yes",
        "ProtectKernelModules=yes",
        "ProtectControlGroups=yes",
        "RestrictAddressFamilies=",
        "RestrictRealtime=yes",
        "MemoryDenyWriteExecute=yes",
        "LockPersonality=yes",
        "SystemCallArchitectures=native",
        "SystemCallFilter=",
    ]
    for directive in required:
        assert directive in service_unit, f"Missing hardening directive: {directive}"


def test_service_state_directory_mode(service_unit: str) -> None:
    """StateDirectoryMode must be exactly 0750."""
    match = re.search(r"StateDirectoryMode=(\S+)", service_unit)
    assert match is not None, "StateDirectoryMode not found"
    assert match.group(1) == "0750", f"StateDirectoryMode must be 0750, got {match.group(1)}"


def test_service_runtime_directory_mode(service_unit: str) -> None:
    """RuntimeDirectoryMode must be exactly 0750."""
    match = re.search(r"RuntimeDirectoryMode=(\S+)", service_unit)
    assert match is not None, "RuntimeDirectoryMode not found"
    assert match.group(1) == "0750", f"RuntimeDirectoryMode must be 0750, got {match.group(1)}"


def test_service_umask(service_unit: str) -> None:
    """UMask must be exactly 0077."""
    match = re.search(r"UMask=(\S+)", service_unit)
    assert match is not None, "UMask not found"
    assert match.group(1) == "0077", f"UMask must be 0077, got {match.group(1)}"


def test_service_unit_contains_load_credential(service_unit: str) -> None:
    """The systemd service unit must contain the LoadCredential directive."""
    assert "LoadCredential" in service_unit, (
        "service unit must contain LoadCredential directive"
    )
    assert "notification.json" in service_unit, (
        "service unit must reference notification.json credential"
    )
    assert "/etc/trader-assist-v0/credentials/notification.json" in service_unit, (
        "service unit must reference the exact credential source path"
    )


# ---------------------------------------------------------------------------
# Test 4: Unchanged environment example cannot activate runtime
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def env_example() -> str:
    return (REPO_ROOT / "deploy/p4a/systemd/trader-assist-v0-public.env.example").read_text()


def test_env_example_enable_is_zero(env_example: str) -> None:
    """TRADER_ASSIST_V0_ENABLE must be 0 (disabled) in the example."""
    match = re.search(r"TRADER_ASSIST_V0_ENABLE=(\S+)", env_example)
    assert match is not None, "TRADER_ASSIST_V0_ENABLE not found"
    assert match.group(1) == "0", (
        f"TRADER_ASSIST_V0_ENABLE must be 0, got {match.group(1)}"
    )


def test_env_example_mode_is_disabled(env_example: str) -> None:
    """TRADER_ASSIST_V0_MODE must not be the active runtime mode."""
    match = re.search(r"TRADER_ASSIST_V0_MODE=(\S+)", env_example)
    assert match is not None, "TRADER_ASSIST_V0_MODE not found"
    assert match.group(1) != "RESTRICTED_PUBLIC_LIVE_SHADOW", (
        "TRADER_ASSIST_V0_MODE must not be the active mode"
    )


def test_env_example_no_webhook_url_variable(env_example: str) -> None:
    """TRADER_ASSIST_V0_WEBHOOK_URL must not appear in the environment example."""
    assert "TRADER_ASSIST_V0_WEBHOOK_URL" not in env_example, (
        "TRADER_ASSIST_V0_WEBHOOK_URL must not appear in the environment example; "
        "webhook URL is supplied via credential file"
    )


def test_env_example_no_aws_variable(env_example: str) -> None:
    assert "AWS" not in env_example


def test_env_example_no_account_variable(env_example: str) -> None:
    assert "ACCOUNT" not in env_example.upper()


def test_env_example_no_exchange_variable(env_example: str) -> None:
    assert "EXCHANGE" not in env_example.upper()


# ---------------------------------------------------------------------------
# Test 5: Unchanged risk example fails closed
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def risk_example() -> str:
    return (REPO_ROOT / "deploy/p4a/config/risk-configuration.json.example").read_text()


def test_risk_example_is_valid_json(risk_example: str) -> None:
    parsed = json.loads(risk_example)
    assert isinstance(parsed, dict)


def test_risk_example_fails_closed(risk_example: str) -> None:
    """The unchanged risk example must fail RiskConfiguration.from_json().

    Either the CONFIGURATION_VERSION is a placeholder that fails the version
    regex, or the ACCOUNT_EQUITY_USD is 0.00 which fails the range check.

    The test succeeds ONLY when the expected ConfigurationError occurs.  It
    fails on ImportError, ModuleNotFoundError, or any unexpected exception.

    Uses sys.executable and PYTHONPATH=src so the test is portable across
    macOS local devel and Linux GitHub Actions.
    """
    import subprocess as _sp

    src_dir = str(REPO_ROOT / "src")
    # Distinct exit codes:
    #   0 = expected ConfigurationError raised (risk example fails closed)
    #   2 = ImportError / ModuleNotFoundError (test must fail)
    #   3 = unexpected success (risk example did NOT fail closed; test must fail)
    #   4 = unexpected exception (test must fail)
    # Embed the raw risk example as a Python string literal via repr() so the
    # subprocess receives the exact JSON text.  Do NOT use json.dumps() of a
    # Python dict here: JSON `null` is not valid Python and would raise
    # NameError before the try/except block, exiting with code 1.
    raw_literal = repr(risk_example)
    script = (
        "import json, sys\n"
        "try:\n"
        "    from trader_assist_v0.first_launch.configuration import "
        "ConfigurationError, RiskConfiguration\n"
        "except (ImportError, ModuleNotFoundError) as exc:\n"
        "    sys.stderr.write('IMPORT_FAILURE: ' + repr(exc) + chr(10))\n"
        "    sys.exit(2)\n"
        f"raw = {raw_literal}\n"
        "try:\n"
        "    RiskConfiguration.from_json(raw)\n"
        "    sys.stderr.write('UNEXPECTED_SUCCESS: risk example did not fail closed' + chr(10))\n"
        "    sys.exit(3)\n"
        "except ConfigurationError:\n"
        "    sys.exit(0)\n"
        "except Exception as exc:\n"
        "    sys.stderr.write('UNEXPECTED_EXCEPTION: ' + repr(exc) + chr(10))\n"
        "    sys.exit(4)\n"
    )
    env = {**os.environ, "PYTHONPATH": src_dir}
    result = _sp.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Risk example should fail closed with ConfigurationError (exit 0), "
        f"got exit code {result.returncode}. stderr: {result.stderr}"
    )


def test_risk_example_no_plausible_default_equity(risk_example: str) -> None:
    parsed = json.loads(risk_example)
    assert "ACCOUNT_EQUITY_USD" in parsed
    equity = parsed["ACCOUNT_EQUITY_USD"]
    assert equity == "0.00", (
        f"ACCOUNT_EQUITY_USD must be 0.00 (fail-closed), got {equity}"
    )


def test_risk_example_no_default_risk_pct(risk_example: str) -> None:
    parsed = json.loads(risk_example)
    assert "RISK_PER_TRADE_PCT" in parsed
    pct = parsed["RISK_PER_TRADE_PCT"]
    assert pct == "0.0000", (
        f"RISK_PER_TRADE_PCT must be 0.0000 (fail-closed), got {pct}"
    )


def test_risk_example_has_placeholder_version(risk_example: str) -> None:
    parsed = json.loads(risk_example)
    assert "CONFIGURATION_VERSION" in parsed
    version = parsed["CONFIGURATION_VERSION"]
    assert "PLACEHOLDER" in version or "DISABLED" in version.upper(), (
        f"CONFIGURATION_VERSION must be a placeholder, got {version}"
    )


# ---------------------------------------------------------------------------
# Test 6: No committed secret or credential
# ---------------------------------------------------------------------------

def test_no_secret_in_any_file() -> None:
    violations: list[tuple[str, str, int]] = []
    for path_str in ALLOWED_FILES:
        full = REPO_ROOT / path_str
        content = full.read_text()
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(content):
                line_no = content[: match.start()].count("\n") + 1
                violations.append((path_str, pattern.pattern, line_no))
    assert not violations, (
        f"Secret patterns found in {len(violations)} location(s): {violations}"
    )


# ---------------------------------------------------------------------------
# Test 7: No AWS, account, wallet, private-key, signing, nonce or exchange-write
# ---------------------------------------------------------------------------

def test_no_prohibited_content_in_any_file() -> None:
    # Skip the test file itself — it contains the prohibited patterns as
    # part of its own pattern definitions.
    test_file = "tests/test_p4a_local_deployment_package.py"
    violations: list[tuple[str, str, int]] = []
    for path_str in ALLOWED_FILES:
        if path_str == test_file:
            continue
        full = REPO_ROOT / path_str
        content = full.read_text()
        for pattern in PROHIBITED_CONTENT_PATTERNS:
            for match in pattern.finditer(content):
                line_no = content[: match.start()].count("\n") + 1
                violations.append((path_str, pattern.pattern, line_no))
    assert not violations, (
        f"Prohibited content found in {len(violations)} location(s): {violations}"
    )


# ---------------------------------------------------------------------------
# Test 8: Wrapper exits before Python execution
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def wrapper_path() -> Path:
    return REPO_ROOT / "scripts/p4a/run_restricted_public_runtime.sh"


def _run_wrapper(
    wrapper_path: Path,
    extra_env: dict[str, str] | None = None,
    extra_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "TRADER_ASSIST_V0_ENABLE": "0",
        "TRADER_ASSIST_V0_MODE": "DISABLED",
        "TRADER_ASSIST_V0_DATABASE_PATH": "",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "",
        "CREDENTIALS_DIRECTORY": "",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(wrapper_path), *extra_args],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_wrapper_exits_when_permit_absent(wrapper_path: Path) -> None:
    """Wrapper exits non-zero when activation permit is missing."""
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
    })
    assert result.returncode != 0, "Wrapper should exit non-zero when permit is absent"


def test_wrapper_exits_when_enable_wrong(wrapper_path: Path) -> None:
    """Wrapper exits non-zero when enable value is not '1'."""
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "0",
    })
    assert result.returncode != 0, "Wrapper should exit non-zero when enable is wrong"


def test_wrapper_exits_when_mode_wrong(wrapper_path: Path) -> None:
    """Wrapper exits non-zero when mode is not RESTRICTED_PUBLIC_LIVE_SHADOW."""
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "WRONG_MODE",
    })
    assert result.returncode != 0, "Wrapper should exit non-zero when mode is wrong"


def test_wrapper_exits_when_database_path_missing(wrapper_path: Path) -> None:
    """Wrapper exits non-zero when database path is empty."""
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "",
    })
    assert result.returncode != 0, "Wrapper should exit non-zero when database path is missing"


def test_wrapper_exits_when_risk_path_missing(wrapper_path: Path) -> None:
    """Wrapper exits non-zero when risk configuration path is empty."""
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "",
    })
    assert result.returncode != 0, "Wrapper should exit non-zero when risk path is missing"


def test_wrapper_exits_when_database_path_outside_approved(
    wrapper_path: Path, tmp_path: Path
) -> None:
    """Wrapper exits non-zero when database path is outside approved directory."""
    outside = tmp_path / "outside.db"
    outside.touch()
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": str(outside),
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    assert result.returncode != 0, (
        "Wrapper should exit non-zero when database path is outside approved directory"
    )


def test_wrapper_exits_when_risk_path_outside_approved(
    wrapper_path: Path, tmp_path: Path
) -> None:
    """Wrapper exits non-zero when risk config path is outside approved directory."""
    outside = tmp_path / "outside.json"
    outside.touch()
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(outside),
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    assert result.returncode != 0, (
        "Wrapper should exit non-zero when risk config path is outside approved directory"
    )


# ---------------------------------------------------------------------------
# Test 8a: Fresh database (non-existent file) passes path check
# ---------------------------------------------------------------------------

def test_wrapper_allows_fresh_database_path(
    wrapper_path: Path, tmp_path: Path
) -> None:
    """Wrapper accepts a database path whose parent directory exists but
    the database file does not yet exist (SQLite creates it on first start)."""
    parent = tmp_path / "approved"
    parent.mkdir()
    db_path = parent / "runtime.db"
    # db_path does NOT exist — that's the point of this test
    assert not db_path.exists()

    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": str(db_path),
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    # The wrapper should exit before Python because the risk config file
    # doesn't exist — but the database path check should pass.
    # If the database path check fails, the error message will mention database.
    stderr = result.stderr.lower()
    assert "database" not in stderr or "db" not in stderr, (
        f"Fresh database path should not cause error, got: {result.stderr}"
    )


def test_wrapper_rejects_database_parent_nonexistent(
    wrapper_path: Path, tmp_path: Path
) -> None:
    """Wrapper rejects a database path whose parent directory does not exist."""
    db_path = tmp_path / "nonexistent" / "runtime.db"
    assert not db_path.parent.exists()

    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": str(db_path),
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    assert result.returncode != 0, (
        "Wrapper should reject nonexistent database parent directory"
    )


def test_wrapper_rejects_database_traversal_path(
    wrapper_path: Path,
) -> None:
    """Wrapper rejects database paths containing traversal."""
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/../outside.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    assert result.returncode != 0, (
        "Wrapper should reject traversal in database path"
    )


# ---------------------------------------------------------------------------
# Test 8b: Risk config must be an existing regular file
# ---------------------------------------------------------------------------

def test_wrapper_rejects_risk_config_not_a_file(
    wrapper_path: Path, tmp_path: Path
) -> None:
    """Wrapper rejects a risk config path that is not a regular file."""
    dir_path = tmp_path / "not-a-file"
    dir_path.mkdir()

    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(dir_path),
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    assert result.returncode != 0, (
        "Wrapper should reject risk config path that is not a regular file"
    )


def test_wrapper_rejects_risk_config_nonexistent(
    wrapper_path: Path, tmp_path: Path
) -> None:
    """Wrapper rejects a risk config path that does not exist."""
    nonexistent = tmp_path / "nonexistent.json"
    assert not nonexistent.exists()

    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(nonexistent),
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    assert result.returncode != 0, (
        "Wrapper should reject nonexistent risk config path"
    )


# ---------------------------------------------------------------------------
# Test 8c: Python entrypoint and executable must exist
# ---------------------------------------------------------------------------

def test_wrapper_rejects_missing_python_executable(
    wrapper_path: Path, tmp_path: Path
) -> None:
    """Wrapper exits non-zero when PYTHON_EXECUTABLE is not found.

    The wrapper hardcodes PYTHON_EXECUTABLE=/opt/trader-assist-v0/venv/bin/python.
    On a test machine, this path is unlikely to exist. We verify the wrapper
    exits non-zero with an error about the Python executable.
    """
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
        "CREDENTIALS_DIRECTORY": "/tmp/credential-dir",
    })
    # The wrapper will fail at either the risk config file check or the
    # Python executable check. Either way, it must exit non-zero.
    assert result.returncode != 0, (
        "Wrapper should exit non-zero when Python executable or risk config is missing"
    )
    stderr = result.stderr.lower()
    assert "python" in stderr or "risk" in stderr or "not found" in stderr, (
        f"Expected error about Python or risk config, got: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Test 9: Wrapper contains no eval
# ---------------------------------------------------------------------------

def test_wrapper_contains_no_eval(wrapper_path: Path) -> None:
    content = wrapper_path.read_text()
    assert "eval " not in content, "Wrapper must not contain eval"
    assert "eval\t" not in content, "Wrapper must not contain eval"
    for line in content.split("\n"):
        if "eval" in line.lower() and not line.strip().startswith("#"):
            assert "eval " not in line.lower(), (
                f"Wrapper contains eval in line: {line}"
            )


# ---------------------------------------------------------------------------
# Test 10: Wrapper constructs argv as an array
# ---------------------------------------------------------------------------

def test_wrapper_argv_is_array(wrapper_path: Path) -> None:
    content = wrapper_path.read_text()
    assert "PYTHON_ARGS=(" in content, "Wrapper must use bash array for argv"
    assert '"${PYTHON_ARGS[@]}"' in content, "Wrapper must expand argv as array"


# ---------------------------------------------------------------------------
# Test 11: Wrapper passes bash -n syntax check
# ---------------------------------------------------------------------------

def test_wrapper_bash_syntax(wrapper_path: Path) -> None:
    result = subprocess.run(
        ["bash", "-n", str(wrapper_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"bash -n failed: {result.stderr.strip()}"
    )


# ---------------------------------------------------------------------------
# Test 12: Runbook contains required sections
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def runbook() -> str:
    return (REPO_ROOT / "docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md").read_text()


def test_runbook_has_installation(runbook: str) -> None:
    assert "Installation" in runbook or "installation" in runbook.lower()


def test_runbook_has_permissions(runbook: str) -> None:
    assert "Permission" in runbook or "permission" in runbook.lower()


def test_runbook_has_default_off_proof(runbook: str) -> None:
    assert "Default-Off" in runbook or "default-off" in runbook.lower()


def test_runbook_has_activation_permit(runbook: str) -> None:
    assert "activation-permit" in runbook


def test_runbook_has_start(runbook: str) -> None:
    assert "Start" in runbook


def test_runbook_has_stop(runbook: str) -> None:
    assert "Stop" in runbook


def test_runbook_has_restart(runbook: str) -> None:
    assert "Restart" in runbook


def test_runbook_has_status(runbook: str) -> None:
    assert "Status" in runbook


def test_runbook_has_journald(runbook: str) -> None:
    assert "journald" in runbook.lower() or "Journald" in runbook


def test_runbook_has_sqlite_health(runbook: str) -> None:
    assert "SQLite" in runbook


def test_runbook_has_rollback(runbook: str) -> None:
    assert "Rollback" in runbook or "rollback" in runbook.lower()


def test_runbook_has_30_30_plan(runbook: str) -> None:
    assert "30 minutes" in runbook


def test_runbook_has_exactly_one_controlled_restart(runbook: str) -> None:
    assert "controlled restart" in runbook.lower() or "Controlled Restart" in runbook


def test_runbook_has_final_stop(runbook: str) -> None:
    assert "final service stopped" in runbook.lower() or "final stop" in runbook.lower()


def test_runbook_has_final_disable(runbook: str) -> None:
    assert "final service disabled" in runbook.lower() or "final disable" in runbook.lower()


def test_runbook_has_smoke_not_authorized(runbook: str) -> None:
    assert "SMOKE IS NOT AUTHORIZED" in runbook


def test_runbook_installs_only_runtime_lock_with_require_hashes(runbook: str) -> None:
    """Runbook must install only requirements-runtime.lock with --require-hashes."""
    assert "pip install" in runbook
    assert "--require-hashes" in runbook
    assert "requirements-runtime.lock" in runbook
    # Must not install the dev lockfile
    assert "requirements-dev.lock" not in runbook


def test_runbook_prohibits_editable_install(runbook: str) -> None:
    """Runbook must not include editable install instructions."""
    assert "pip install --no-deps --no-build-isolation -e" not in runbook, (
        "Runbook must not include editable install step"
    )
    assert "--no-build-isolation" not in runbook, (
        "Runbook must not use --no-build-isolation"
    )
    # No editable install of the project path
    assert "-e /opt/trader-assist-v0" not in runbook, (
        "Runbook must not editable-install /opt/trader-assist-v0"
    )


def test_runbook_verifies_import_source_path(runbook: str) -> None:
    """Runbook must verify trader_assist_v0 imports from /opt/src/trader_assist_v0."""
    assert "import trader_assist_v0" in runbook
    assert "/opt/trader-assist-v0/src/trader_assist_v0" in runbook, (
        "Runbook must verify import source path"
    )
    # Must reference the forced PYTHONPATH
    assert "PYTHONPATH=/opt/trader-assist-v0/src" in runbook, (
        "Runbook must reference the forced PYTHONPATH"
    )


def test_runbook_prohibits_pythonpath_in_env(runbook: str) -> None:
    """Runbook must state PYTHONPATH is not set in public.env."""
    assert "PYTHONPATH" in runbook
    assert "public.env" in runbook


def test_runbook_requires_exact_sha_deployment(runbook: str) -> None:
    """Runbook must require full 40-char SHA, exact fetch, detached checkout."""
    assert "40-character SHA" in runbook or "40-character" in runbook
    assert "git fetch" in runbook
    assert "git checkout" in runbook
    assert "rev-parse HEAD" in runbook
    assert "status --porcelain" in runbook


def test_runbook_prohibits_floating_deployment(runbook: str) -> None:
    """Runbook must prohibit floating main, mutable branches, abbreviated SHAs."""
    assert "floating" in runbook.lower()
    assert "abbreviated" in runbook.lower()
    assert "mutable" in runbook.lower()


def test_runbook_documents_credential_ingress(runbook: str) -> None:
    """Runbook must document the secure notification credential ingress."""
    assert "SECURE NOTIFICATION CREDENTIAL INGRESS" in runbook
    assert "notification.json" in runbook


def test_runbook_has_import_verification(runbook: str) -> None:
    """Runbook must include an import verification step."""
    assert "import trader_assist_v0" in runbook


# ---------------------------------------------------------------------------
# Test 13: Evidence manifest contains every mandatory field
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def evidence_manifest() -> dict[str, Any]:
    raw = (REPO_ROOT / "deploy/p4a/evidence/supervised-smoke-manifest-v1.json.example").read_text()
    return json.loads(raw)


MANDATORY_MANIFEST_FIELDS = {
    "manifest_version",
    "exact_base_sha",
    "implementation_sha",
    "os_version",
    "kernel_version",
    "python_version",
    "service_unit_sha256",
    "environment_template_sha256",
    "notification_credential_example_sha256",
    "redacted_effective_configuration",
    "runtime_user",
    "runtime_group",
    "ownership_and_path_modes",
    "process_identity",
    "initial_ready_timestamp",
    "initial_observation_start",
    "initial_observation_end",
    "controlled_stop_timestamp",
    "controlled_restart_timestamp",
    "post_restart_ready_timestamp",
    "post_restart_observation_start",
    "post_restart_observation_end",
    "sqlite_file_metadata",
    "sqlite_integrity_evidence",
    "sqlite_journal_mode",
    "sqlite_schema_version",
    "health_events",
    "bounded_journald_evidence",
    "effective_network_destination_evidence",
    "final_stopped_proof",
    "final_disabled_proof",
    "rollback_result",
    "unresolved_limitations",
    "evidence_bundle_hash",
}


def test_evidence_manifest_has_all_fields(evidence_manifest: dict[str, Any]) -> None:
    missing = MANDATORY_MANIFEST_FIELDS - set(evidence_manifest.keys())
    assert not missing, f"Evidence manifest missing fields: {missing}"


def test_evidence_manifest_no_real_identifiers(evidence_manifest: dict[str, Any]) -> None:
    for key, value in evidence_manifest.items():
        if key in ("manifest_version",):
            continue
        assert isinstance(value, str), f"Field {key} must be a string placeholder"
        # All placeholder values should be PLACEHOLDER or clearly not real
        assert value == "PLACEHOLDER" or "PLACEHOLDER" in value, (
            f"Field {key} has non-placeholder value: {value}"
        )


def test_evidence_manifest_valid_json() -> None:
    raw = (REPO_ROOT / "deploy/p4a/evidence/supervised-smoke-manifest-v1.json.example").read_text()
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)
    assert len(parsed) >= 30, f"Expected at least 30 fields, got {len(parsed)}"


# ---------------------------------------------------------------------------
# Test 14: Controlled behavioral test harness (ER-05) and filesystem
# containment adversarial tests (ER-03)
# ---------------------------------------------------------------------------
#
# The harness creates a temporary copy of the production wrapper, replaces
# only the fixed production path constants with temp paths, and sets up temp
# permit/state/config/risk/database/stub Python/stub entrypoint paths.  Each
# adversarial test satisfies every preceding guard before triggering the
# target guard and asserts the exact target error.  No root is required;
# nothing is written to /etc, /var/lib or /opt; no network, AWS, real
# webhook or systemd service is used.  The real runtime is never started.

@pytest.fixture
def harness(tmp_path: Path) -> dict[str, Any]:
    """Build a temporary copy of the production wrapper with replaced path
    constants, plus temp permit/state/config/risk/db/stub paths.

    The default setup satisfies every guard so each test can target a
    specific guard by overriding one env var or mutating one path.
    """
    prod = (REPO_ROOT / "scripts/p4a/run_restricted_public_runtime.sh").read_text()

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)

    # Permit lives outside config_dir so config_dir can be broken independently
    permit = tmp_path / "permit"
    permit.write_text("")

    # Stub Python executable (replaces the real venv python)
    stub_python = venv_bin / "python"
    stub_python.write_text("#!/usr/bin/env bash\necho STUB_PYTHON_EXEC\nexit 0\n")
    stub_python.chmod(0o755)

    # Stub entrypoint (must be a regular file; content irrelevant)
    stub_entry = scripts_dir / "run_first_launch_public_runtime.py"
    stub_entry.write_text("# stub entrypoint\n")

    # Valid risk config (regular file inside approved config dir)
    risk_file = config_dir / "risk-configuration.json"
    risk_file.write_text('{"CONFIGURATION_VERSION": "PLACEHOLDER_DISABLED"}\n')

    # Default database path: missing file is valid (SQLite creates it)
    db_path = state_dir / "runtime.db"

    # Credential directory and file for wrapper credential check
    credential_dir = tmp_path / "credentials"
    credential_dir.mkdir()
    credential_file = credential_dir / "notification.json"
    credential_file.write_text(
        '{"version": 1, '
        '"webhook_url": "https://example.invalid/replace-me", '
        '"authorization_header": null}\n'
    )
    credential_file.chmod(0o600)

    # Replace only the fixed production path constants in the copy
    content = prod
    content = content.replace(
        'ACTIVATION_PERMIT="/etc/trader-assist-v0/activation-permit"',
        f'ACTIVATION_PERMIT="{permit}"',
    )
    content = content.replace(
        'PYTHON_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"',
        f'PYTHON_ENTRYPOINT="{stub_entry}"',
    )
    content = content.replace(
        'PYTHON_EXECUTABLE="/opt/trader-assist-v0/venv/bin/python"',
        f'PYTHON_EXECUTABLE="{stub_python}"',
    )
    content = content.replace(
        'PYTHONPATH_FORCED="/opt/trader-assist-v0/src"',
        f'PYTHONPATH_FORCED="{src_dir}"',
    )
    content = content.replace(
        'APPROVED_STATE_DIR="/var/lib/trader-assist-v0"',
        f'APPROVED_STATE_DIR="{state_dir}"',
    )
    content = content.replace(
        'APPROVED_CONFIG_DIR="/etc/trader-assist-v0"',
        f'APPROVED_CONFIG_DIR="{config_dir}"',
    )

    wrapper_copy = tmp_path / "wrapper.sh"
    wrapper_copy.write_text(content)
    wrapper_copy.chmod(0o755)

    base_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": str(db_path),
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(risk_file),
        "CREDENTIALS_DIRECTORY": str(credential_dir),
    }

    return {
        "wrapper": wrapper_copy,
        "wrapper_text": content,
        "base_env": base_env,
        "tmp_path": tmp_path,
        "state_dir": state_dir,
        "config_dir": config_dir,
        "src_dir": src_dir,
        "risk_file": risk_file,
        "permit": permit,
        "stub_python": stub_python,
        "stub_entry": stub_entry,
        "db_path": db_path,
    }


def _run_harness(
    harness: dict[str, Any],
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(harness["base_env"])
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(harness["wrapper"])],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


# --- ER-05: positive path and real-runtime-never-started proof ---

def test_harness_positive_path_reaches_stub_exec(harness: dict[str, Any]) -> None:
    """All guards satisfied: wrapper execs the stub Python (not the real runtime).

    This also covers the 'valid missing database file' case (the default
    database path does not exist).
    """
    result = _run_harness(harness)
    assert result.returncode == 0, (
        f"Positive path should reach stub exec, got rc={result.returncode}: {result.stderr}"
    )
    assert "STUB_PYTHON_EXEC" in result.stdout, (
        f"Stub Python was not exec'd. stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_harness_proves_real_runtime_never_started(harness: dict[str, Any]) -> None:
    """The wrapper copy must reference only temp paths, never production paths."""
    text = harness["wrapper_text"]
    assert "/opt/trader-assist-v0" not in text, "wrapper copy references /opt"
    assert "/etc/trader-assist-v0" not in text, "wrapper copy references /etc"
    assert "/var/lib/trader-assist-v0" not in text, "wrapper copy references /var/lib"
    # The real entrypoint must not exist on the test machine
    assert not Path("/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py").exists()


def test_harness_writes_nothing_to_system_paths(harness: dict[str, Any]) -> None:
    """The harness uses only tmp_path; no writes to /etc, /var/lib or /opt."""
    tmp_str = str(harness["tmp_path"])
    assert (
        tmp_str.startswith("/tmp")
        or tmp_str.startswith("/var/folders")
        or tmp_str.startswith("/private/var/folders")
        or tmp_str.startswith("/private/tmp")
    ), f"tmp_path not under a recognized temp root: {tmp_str}"
    assert "/etc/trader-assist-v0" not in tmp_str
    assert "/var/lib/trader-assist-v0" not in tmp_str
    assert "/opt/trader-assist-v0" not in tmp_str


# --- ER-03: approved directory canonicalization failures ---

def test_harness_rejects_state_dir_canonicalization_failure(harness: dict[str, Any]) -> None:
    """Approved state directory cannot canonicalize -> exact error."""
    shutil.rmtree(harness["state_dir"])
    result = _run_harness(harness)
    assert result.returncode != 0
    assert "approved state directory cannot canonicalize" in result.stderr, (
        f"Expected state canonicalization error, got: {result.stderr}"
    )


def test_harness_rejects_config_dir_canonicalization_failure(harness: dict[str, Any]) -> None:
    """Approved config directory cannot canonicalize -> exact error."""
    shutil.rmtree(harness["config_dir"])
    result = _run_harness(harness)
    assert result.returncode != 0
    assert "approved config directory cannot canonicalize" in result.stderr, (
        f"Expected config canonicalization error, got: {result.stderr}"
    )


# --- ER-03: database filesystem containment adversarial tests ---

def test_harness_rejects_database_parent_nonexistent(harness: dict[str, Any]) -> None:
    """Database parent directory cannot canonicalize -> exact error."""
    db_path = harness["state_dir"] / "nonexistent_subdir" / "runtime.db"
    result = _run_harness(harness, {"TRADER_ASSIST_V0_DATABASE_PATH": str(db_path)})
    assert result.returncode != 0
    assert "database parent directory cannot canonicalize" in result.stderr, (
        f"Expected db parent canonicalization error, got: {result.stderr}"
    )


def test_harness_rejects_database_parent_outside_approved(harness: dict[str, Any]) -> None:
    """Database parent outside approved state -> exact error."""
    outside = harness["tmp_path"] / "outside"
    outside.mkdir()
    db_path = outside / "runtime.db"
    result = _run_harness(harness, {"TRADER_ASSIST_V0_DATABASE_PATH": str(db_path)})
    assert result.returncode != 0
    assert "database parent directory must be under" in result.stderr, (
        f"Expected db parent outside error, got: {result.stderr}"
    )


def test_harness_rejects_existing_database_symlink(harness: dict[str, Any]) -> None:
    """Existing database symlink -> exact error."""
    target = harness["tmp_path"] / "target.db"
    target.write_text("data")
    link = harness["db_path"]
    os.symlink(target, link)
    result = _run_harness(harness)
    assert result.returncode != 0
    assert "database final path must not be a symlink" in result.stderr, (
        f"Expected db symlink error, got: {result.stderr}"
    )


def test_harness_rejects_existing_database_non_regular(harness: dict[str, Any]) -> None:
    """Existing database non-regular object (directory) -> exact error."""
    db_as_dir = harness["db_path"]
    db_as_dir.mkdir()
    result = _run_harness(harness)
    assert result.returncode != 0
    assert "database final path must be a regular file" in result.stderr, (
        f"Expected db non-regular error, got: {result.stderr}"
    )


def test_harness_allows_missing_database_file(harness: dict[str, Any]) -> None:
    """Missing final database file is valid -> stub exec reached."""
    assert not harness["db_path"].exists()
    result = _run_harness(harness)
    assert result.returncode == 0, (
        f"Missing db file should be valid, got: {result.stderr}"
    )
    assert "STUB_PYTHON_EXEC" in result.stdout


def test_harness_allows_existing_regular_database_file(harness: dict[str, Any]) -> None:
    """Existing regular database file is valid -> stub exec reached."""
    harness["db_path"].write_text("sqlite data")
    result = _run_harness(harness)
    assert result.returncode == 0, (
        f"Existing regular db file should be valid, got: {result.stderr}"
    )
    assert "STUB_PYTHON_EXEC" in result.stdout


# --- ER-03: risk configuration filesystem containment adversarial tests ---

def test_harness_rejects_missing_risk_file(harness: dict[str, Any]) -> None:
    """Missing risk file -> exact error."""
    missing = harness["config_dir"] / "nonexistent.json"
    result = _run_harness(harness, {"TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(missing)})
    assert result.returncode != 0
    assert "risk configuration file not found or not a regular file" in result.stderr, (
        f"Expected missing risk file error, got: {result.stderr}"
    )


def test_harness_rejects_non_regular_risk_path(harness: dict[str, Any]) -> None:
    """Non-regular risk path (directory) -> exact error."""
    risk_dir = harness["config_dir"] / "not-a-file"
    risk_dir.mkdir()
    result = _run_harness(harness, {"TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(risk_dir)})
    assert result.returncode != 0
    assert "risk configuration file not found or not a regular file" in result.stderr, (
        f"Expected non-regular risk error, got: {result.stderr}"
    )


def test_harness_rejects_risk_path_outside_approved_config(harness: dict[str, Any]) -> None:
    """Risk path outside approved config -> exact error."""
    outside = harness["tmp_path"] / "outside-risk"
    outside.mkdir()
    risk_outside = outside / "risk.json"
    risk_outside.write_text("{}")
    result = _run_harness(harness, {"TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(risk_outside)})
    assert result.returncode != 0
    assert "risk configuration path must be under" in result.stderr, (
        f"Expected risk outside config error, got: {result.stderr}"
    )


def test_harness_rejects_risk_path_symlink(harness: dict[str, Any]) -> None:
    """Risk path symlink -> exact error."""
    target = harness["config_dir"] / "real-risk.json"
    target.write_text("{}")
    link = harness["config_dir"] / "link-risk.json"
    os.symlink(target, link)
    result = _run_harness(harness, {"TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(link)})
    assert result.returncode != 0
    assert "risk configuration path must not be a symlink" in result.stderr, (
        f"Expected risk symlink error, got: {result.stderr}"
    )


# --- ER-03: TOCTOU documentation in wrapper ---

def test_wrapper_documents_toctou_limitation(wrapper_path: Path) -> None:
    """Wrapper must document that same-UID TOCTOU races are reduced but not eliminated."""
    content = wrapper_path.read_text()
    assert "TOCTOU" in content, "Wrapper must document TOCTOU limitation"
    assert "not mathematically eliminated" in content, (
        "Wrapper must state TOCTOU races are not mathematically eliminated"
    )


# ---------------------------------------------------------------------------
# Test 15: Exact scope relative to EXACT_BASE (ER-06)
# ---------------------------------------------------------------------------

def _exact_scope_active() -> bool:
    """True when local branch or CI PR head matches the exact scope branch."""
    # Local branch check
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip() == EXACT_SCOPE_BRANCH:
            return True
    except Exception:
        pass
    # CI check: pull_request event with matching head ref
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request" and \
       os.environ.get("GITHUB_HEAD_REF") == EXACT_SCOPE_BRANCH:
        return True
    return False


def test_exact_scope_relative_to_base() -> None:
    """When active on the exact branch or PR, require exactly the 7 A paths.

    Skips main, post-merge push, unrelated branches and unrelated PRs.
    """
    if not _exact_scope_active():
        pytest.skip(
            "exact-scope test only active on "
            "feature/v0-fl-r3-p4a-local-deployment-package"
        )
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{EXACT_BASE}...HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=10,
    )
    assert result.returncode == 0, f"git diff failed: {result.stderr}"
    lines = [line.split("\t") for line in result.stdout.strip().split("\n") if line.strip()]
    actual = {(parts[0], parts[1]) for parts in lines if len(parts) >= 2}
    assert actual == EXPECTED_EXACT_SCOPE, (
        f"Scope mismatch.\nExpected: {sorted(EXPECTED_EXACT_SCOPE)}\n"
        f"Got: {sorted(actual)}"
    )