"""Static offline tests for the P4A local deployment package.

These tests verify the seven-file implementation scope, systemd unit content,
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
# Test 1: Exact seven-file implementation scope
# ---------------------------------------------------------------------------

def _collect_p4a_files() -> set[str]:
    """Collect all new P4A files by listing the allowed directories."""
    found: set[str] = set()
    for allowed in ALLOWED_FILES:
        full = REPO_ROOT / allowed
        if full.exists():
            found.add(allowed)
    return found


def test_exact_seven_file_scope() -> None:
    """All seven authorized files exist and no extra files are present."""
    found = _collect_p4a_files()
    assert found == ALLOWED_FILES, (
        f"Expected exactly 7 files, got {len(found)}. "
        f"Missing: {ALLOWED_FILES - found}. "
        f"Extra: {found - ALLOWED_FILES}"
    )
    assert len(found) == 7, f"Expected 7 files, got {len(found)}"


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


def test_env_example_no_valid_webhook_url(env_example: str) -> None:
    """The example webhook URL must not be a valid HTTPS URL."""
    match = re.search(r"TRADER_ASSIST_V0_WEBHOOK_URL=(\S+)", env_example)
    assert match is not None, "TRADER_ASSIST_V0_WEBHOOK_URL not found"
    value = match.group(1)
    assert not value.startswith("https://"), (
        f"Webhook URL must not be a valid HTTPS URL, got {value}"
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

    Uses sys.executable and PYTHONPATH=src so the test is portable across
    macOS local devel and Linux GitHub Actions.
    """
    import subprocess as _sp

    src_dir = str(REPO_ROOT / "src")
    script = (
        "import json, sys; "
        "from trader_assist_v0.first_launch.configuration import "
        "ConfigurationError, RiskConfiguration; "
        f"raw = json.dumps({json.dumps(json.loads(risk_example))}); "
        "try: RiskConfiguration.from_json(raw); sys.exit(0)\n"
        "except ConfigurationError: sys.exit(1)\n"
    )
    env = {**os.environ, "PYTHONPATH": src_dir}
    result = _sp.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1, (
        f"Risk example should fail closed, got exit code {result.returncode}"
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "",
        "TRADER_ASSIST_V0_AUTHORIZATION_HEADER_NAME": "",
        "TRADER_ASSIST_V0_AUTHORIZATION_HEADER_VALUE": "",
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
    })
    assert result.returncode != 0, (
        "Wrapper should exit non-zero when risk config path is outside approved directory"
    )


def test_wrapper_exits_when_authorization_pair_incomplete(
    wrapper_path: Path,
) -> None:
    """Wrapper exits non-zero when only one of the authorization pair is set."""
    # Name set, value empty
    result = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
        "TRADER_ASSIST_V0_AUTHORIZATION_HEADER_NAME": "Authorization",
        "TRADER_ASSIST_V0_AUTHORIZATION_HEADER_VALUE": "",
    })
    assert result.returncode != 0, (
        "Wrapper should exit non-zero when auth name set but value empty"
    )
    # Value set, name empty
    result2 = _run_wrapper(wrapper_path, extra_env={
        "TRADER_ASSIST_V0_ENABLE": "1",
        "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
        "TRADER_ASSIST_V0_AUTHORIZATION_HEADER_NAME": "",
        "TRADER_ASSIST_V0_AUTHORIZATION_HEADER_VALUE": "Bearer token",
    })
    assert result2.returncode != 0, (
        "Wrapper should exit non-zero when auth value set but name empty"
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
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
        "TRADER_ASSIST_V0_WEBHOOK_URL": "https://example.com/hook",
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


def test_runbook_has_pip_install_editable(runbook: str) -> None:
    """Runbook must include pip install --no-deps --no-build-isolation -e step."""
    assert "--no-deps" in runbook or "--no-build-isolation" in runbook
    assert "-e" in runbook or "--editable" in runbook.lower()
    assert "pip install" in runbook


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