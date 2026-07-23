"""Offline controlled-command tests for the P4A read-only verifiers."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "scripts/p4a/verify_first_launch_runtime_state.sh"
DATABASE = ROOT / "scripts/p4a/verify_first_launch_database.py"
RUNBOOK = ROOT / "docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md"


def _command(path: Path, text: str) -> None:
    path.write_text("#!/bin/sh\n" + text)
    path.chmod(0o755)


def _database_module() -> Any:
    spec = importlib.util.spec_from_file_location("p4a_database_verifier", DATABASE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def database(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "state"
    root.mkdir()
    env = tmp_path / "public.env"
    db = root / "runtime.db"
    env.write_text(f"TRADER_ASSIST_V0_DATABASE_PATH={db}\n")
    return {"module": _database_module(), "root": root, "env": env, "db": db}


@pytest.mark.parametrize(
    "phase", ["existing-before-smoke", "fresh-post-creation", "final-post-smoke"]
)
def test_database_existing_phase_json(database: dict[str, Any], phase: str) -> None:
    db = database["db"]
    sqlite3.connect(db).close()
    result = database["module"].verify(phase, database["env"], database["root"])
    assert result == {
        "status": "PASS",
        "phase": phase,
        "database_path": str(db),
        "exists": True,
        "integrity": "ok",
    }


def test_database_fresh_phase_json_and_cli_stdout(database: dict[str, Any]) -> None:
    module, env, root = database["module"], database["env"], database["root"]
    result = module.verify("fresh-pre-start", env, root)
    assert result["exists"] is False and result["integrity"] is None
    portable = env.parent / "verify_database.py"
    text = (
        DATABASE.read_text()
        .replace(
            'PUBLIC_ENV = Path("/etc/trader-assist-v0/public.env")', f'PUBLIC_ENV = Path("{env}")'
        )
        .replace('STATE_ROOT = Path("/var/lib/trader-assist-v0")', f'STATE_ROOT = Path("{root}")')
    )
    portable.write_text(text)
    process = subprocess.run(
        [sys.executable, str(portable), "fresh-pre-start"],
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert process.returncode == 0 and process.stderr == ""
    assert json.loads(process.stdout) == result


@pytest.mark.parametrize(
    "content",
    [
        "TRADER_ASSIST_V0_DATABASE_PATH=/a\nTRADER_ASSIST_V0_DATABASE_PATH=/b\n",
        "TRADER_ASSIST_V0_DATABASE_PATH value\n",
        "TRADER_ASSIST_V0_DATABASE_PATH=relative.db\n",
    ],
)
def test_database_rejects_assignment_and_path_failures(
    database: dict[str, Any], content: str
) -> None:
    env = database["env"]
    env.write_text(content)
    with pytest.raises(database["module"].VerificationError):
        database["module"].verify("fresh-pre-start", env, database["root"])


def test_database_rejects_symlink_escape_nonregular_and_bad_integrity(
    database: dict[str, Any],
) -> None:
    module, root, env, db = (database[key] for key in ("module", "root", "env", "db"))
    env.write_text("TRADER_ASSIST_V0_DATABASE_PATH=/tmp/outside.db\n")
    with pytest.raises(module.VerificationError):
        module.verify("fresh-pre-start", env, root)
    env.write_text(f"TRADER_ASSIST_V0_DATABASE_PATH={db}\n")
    target = root / "target.db"
    target.write_text("x")
    db.symlink_to(target)
    with pytest.raises(module.VerificationError):
        module.verify("existing-before-smoke", env, root)
    db.unlink()
    db.mkdir()
    with pytest.raises(module.VerificationError):
        module.verify("existing-before-smoke", env, root)
    db.rmdir()
    db.write_text("not sqlite")
    with pytest.raises(module.VerificationError):
        module.verify("existing-before-smoke", env, root)


@pytest.fixture
def runtime(tmp_path: Path) -> dict[str, Any]:
    source, installed = tmp_path / "source.service", tmp_path / "installed.service"
    source.write_text("[Service]\nUser=traderassist\n")
    installed.write_text(source.read_text())
    state_root, config_root = tmp_path / "state", tmp_path / "config"
    state_root.mkdir()
    config_root.mkdir()
    db, risk = state_root / "runtime.db", config_root / "risk.json"
    risk.write_text("{}")
    env = tmp_path / "public.env"
    env.write_text(
        "\n".join(
            (
                f"TRADER_ASSIST_V0_DATABASE_PATH={db}",
                f"TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH={risk}",
                "TRADER_ASSIST_V0_WEBHOOK_TIMEOUT_SECONDS=10",
                "TRADER_ASSIST_V0_ACKNOWLEDGEMENT_TIMEOUT_SECONDS=30",
                "TRADER_ASSIST_V0_SESSION_TIMEOUT_SECONDS=60",
            )
        )
        + "\n"
    )
    proc, cgroup, bin_dir = tmp_path / "proc", tmp_path / "cgroup", tmp_path / "bin"
    (proc / "101").mkdir(parents=True)
    group = cgroup / "system.slice" / "trader-assist-v0-public.service"
    group.mkdir(parents=True)
    (group / "cgroup.procs").write_text("")
    bin_dir.mkdir()
    python, entry = tmp_path / "python", tmp_path / "entry.py"
    python.write_text("")
    python.chmod(0o755)
    entry.write_text("")
    script = tmp_path / "verify.sh"
    text = RUNTIME.read_text()
    replacements = {
        "SOURCE_UNIT=/opt/trader-assist-v0/deploy/p4a/systemd/trader-assist-v0-public.service": (
            f"SOURCE_UNIT={source}"
        ),
        "INSTALLED_UNIT=/etc/systemd/system/trader-assist-v0-public.service": (
            f"INSTALLED_UNIT={installed}"
        ),
        "PUBLIC_ENV=/etc/trader-assist-v0/public.env": f"PUBLIC_ENV={env}",
        "PROC_ROOT=/proc": f"PROC_ROOT={proc}",
        "CGROUP_ROOT=/sys/fs/cgroup": f"CGROUP_ROOT={cgroup}",
        "PYTHON=/opt/trader-assist-v0/venv/bin/python": f"PYTHON={python}",
        "ENTRYPOINT=/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py": (
            f"ENTRYPOINT={entry}"
        ),
        "STATE_ROOT=/var/lib/trader-assist-v0 CONFIG_ROOT=/etc/trader-assist-v0": (
            f"STATE_ROOT={state_root} CONFIG_ROOT={config_root}"
        ),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace(
        'show() { systemctl show "$SERVICE" --property="$1" --value; }',
        """show() {
    local line key="$1"
    if [[ "$key" == MainPID && "${FAKE_DRIFT:-0}" == 1 ]]; then
        local count=0
        [[ -f "$FAKE_MAIN_COUNT" ]] && count="$(<"$FAKE_MAIN_COUNT")"
        ((++count)); printf '%s' "$count" > "$FAKE_MAIN_COUNT"
        [[ $count -gt 1 ]] && { printf '102\\n'; return; }
    fi
    while IFS= read -r line; do
        [[ "$line" == "$key="* ]] && { printf '%s\\n' "${line#*=}"; return; }
    done < "$FAKE_STATE"
}""",
    )
    text = text.replace(
        'metadata="$(stat -c \'%U:%G:%a\' "$INSTALLED_UNIT")" '
        "|| die 'cannot inspect installed unit metadata'",
        "metadata=root:root:644",
    )
    text = text.replace(
        'systemd-analyze verify "$INSTALLED_UNIT" >/dev/null '
        "|| die 'systemd unit verification failed'",
        ":",
    )
    text = text.replace(
        'jobs="$(systemctl list-jobs --no-legend --no-pager)" '
        "|| die 'cannot inspect lifecycle jobs'",
        'jobs="${FAKE_JOBS:-}"',
    )
    script.write_text(text)
    script.chmod(0o755)
    _command(bin_dir / "id", "echo 1001")
    _command(
        bin_dir / "readlink",
        'if [ "${FAKE_TRANSITION:-0}" = 1 ] && [ ! -e "$FAKE_STEP" ]; '
        'then echo wrapper; else echo "${FAKE_EXE:?}"; fi',
    )
    _command(bin_dir / "sleep", 'touch "$FAKE_STEP"')
    _command(
        bin_dir / "ps",
        """[ "${PS_FAIL:-0}" = 0 ] || exit 1
if [ "${FAKE_TRANSITION:-0}" = 1 ] && [ ! -e "$FAKE_STEP" ]; then
  printf '101 1001 /scripts/p4a/run_restricted_public_runtime.sh\\n'
else
  printf '%s\\n' "${FAKE_PS:-}"
fi""",
    )
    state = tmp_path / "state.txt"
    state.write_text(
        "\n".join(
            (
                f"FragmentPath={installed}",
                "DropInPaths=",
                "User=traderassist",
                "Group=traderassist",
                "Id=trader-assist-v0-public.service",
                "ActiveState=inactive",
                "SubState=dead",
                "MainPID=0",
                "UnitFileState=disabled",
                "ControlGroup=/system.slice/trader-assist-v0-public.service",
            )
        )
        + "\n"
    )
    return {
        "script": script,
        "bin": bin_dir,
        "state": state,
        "proc": proc,
        "group": group,
        "python": python,
        "entry": entry,
        "env": env,
        "tmp": tmp_path,
    }


def _argv(runtime: dict[str, Any], credential: str | None = None) -> bytes:
    credential = credential or str(runtime["tmp"] / "credentials")
    return (
        "\0".join(
            (
                str(runtime["python"]),
                str(runtime["entry"]),
                "--enable-restricted-public-runtime",
                "--mode",
                "RESTRICTED_PUBLIC_LIVE_SHADOW",
                "--database-path",
                str(runtime["tmp"] / "state/runtime.db"),
                "--risk-configuration-path",
                str(runtime["tmp"] / "config/risk.json"),
                "--notification-credential-file",
                f"{credential}/notification.json",
                "--webhook-timeout-seconds",
                "10",
                "--acknowledgement-timeout-seconds",
                "30",
                "--session-timeout-seconds",
                "60",
            )
        )
        + "\0"
    ).encode()


def _run(runtime: dict[str, Any], mode: str, **values: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        **values,
        "PATH": f"{runtime['bin']}:{os.environ['PATH']}",
        "FAKE_STATE": str(runtime["state"]),
        "FAKE_MAIN_COUNT": str(runtime["tmp"] / "main.count"),
        "FAKE_STEP": str(runtime["tmp"] / "step"),
        "FAKE_EXE": str(runtime["python"]),
    }
    return subprocess.run(
        ["bash", str(runtime["script"]), mode], text=True, capture_output=True, env=env, timeout=5
    )


@pytest.mark.parametrize("mode", ["installed", "pre-start", "final-state"])
def test_runtime_legal_empty_state(runtime: dict[str, Any], mode: str) -> None:
    result = _run(runtime, mode)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "control_group", ["", "/absent", "/system.slice/trader-assist-v0-public.service"]
)
def test_runtime_empty_control_group_is_legal_before_and_after(
    runtime: dict[str, Any], control_group: str
) -> None:
    text = (
        runtime["state"]
        .read_text()
        .replace(
            "ControlGroup=/system.slice/trader-assist-v0-public.service",
            f"ControlGroup={control_group}",
        )
    )
    runtime["state"].write_text(text)
    if control_group == "/absent":
        assert _run(runtime, "pre-start").returncode == 0
    elif control_group:
        assert _run(runtime, "final-state").returncode == 0
    else:
        assert _run(runtime, "pre-start").returncode == 0


@pytest.mark.parametrize(
    "mode,values",
    [
        ("pre-start", {"PS_FAIL": "1"}),
        ("pre-start", {"FAKE_PS": "7 1001 unwanted"}),
        ("pre-start", {"FAKE_JOBS": "1 trader-assist-v0-public.service start running"}),
    ],
)
def test_runtime_command_failure_and_unexpected_processes_fail(
    runtime: dict[str, Any], mode: str, values: dict[str, str]
) -> None:
    result = _run(runtime, mode, **values)
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


def test_runtime_post_start_contract_and_stabilization(runtime: dict[str, Any]) -> None:
    runtime["state"].write_text(
        runtime["state"]
        .read_text()
        .replace("ActiveState=inactive", "ActiveState=active")
        .replace("SubState=dead", "SubState=running")
        .replace("MainPID=0", "MainPID=101")
    )
    proc, group = runtime["proc"] / "101", runtime["group"]
    credential = runtime["tmp"] / "credentials"
    credential.mkdir()
    (proc / "cmdline").write_bytes(_argv(runtime, str(credential)))
    (proc / "environ").write_bytes(f"CREDENTIALS_DIRECTORY={credential}\0".encode())
    (group / "cgroup.procs").write_text("101\n")
    result = _run(runtime, "post-start", FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}")
    assert result.returncode == 0, result.stderr


def test_runtime_post_start_waits_for_wrapper_transition(runtime: dict[str, Any]) -> None:
    runtime["state"].write_text(
        runtime["state"]
        .read_text()
        .replace("ActiveState=inactive", "ActiveState=active")
        .replace("SubState=dead", "SubState=running")
        .replace("MainPID=0", "MainPID=101")
    )
    proc = runtime["proc"] / "101"
    credential = runtime["tmp"] / "credentials"
    credential.mkdir()
    (proc / "cmdline").write_bytes(_argv(runtime, str(credential)))
    (proc / "environ").write_bytes(f"CREDENTIALS_DIRECTORY={credential}\0".encode())
    (runtime["group"] / "cgroup.procs").write_text("101\n")
    result = _run(
        runtime,
        "post-start",
        FAKE_TRANSITION="1",
        FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}",
    )
    assert result.returncode == 0, result.stderr


def test_runtime_post_start_rejects_identity_drift(runtime: dict[str, Any]) -> None:
    runtime["state"].write_text(
        runtime["state"]
        .read_text()
        .replace("ActiveState=inactive", "ActiveState=active")
        .replace("SubState=dead", "SubState=running")
        .replace("MainPID=0", "MainPID=101")
    )
    proc = runtime["proc"] / "101"
    credential = runtime["tmp"] / "credentials"
    credential.mkdir()
    (proc / "cmdline").write_bytes(_argv(runtime, str(credential)))
    (proc / "environ").write_bytes(f"CREDENTIALS_DIRECTORY={credential}\0".encode())
    (runtime["group"] / "cgroup.procs").write_text("101\n")
    result = _run(
        runtime,
        "post-start",
        FAKE_DRIFT="1",
        FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}",
    )
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


@pytest.mark.parametrize(
    "environment,argv_suffix",
    [
        (b"", None),
        (b"CREDENTIALS_DIRECTORY=/a\0CREDENTIALS_DIRECTORY=/b\0", None),
        (b"CREDENTIALS_DIRECTORY=relative\0", None),
        (b"CREDENTIALS_DIRECTORY=/a/../b\0", None),
        (b"CREDENTIALS_DIRECTORY=/credentials\0", "/credentials/nested/notification.json"),
    ],
)
def test_runtime_post_start_rejects_credential_contract(
    runtime: dict[str, Any], environment: bytes, argv_suffix: str | None
) -> None:
    runtime["state"].write_text(
        runtime["state"]
        .read_text()
        .replace("ActiveState=inactive", "ActiveState=active")
        .replace("SubState=dead", "SubState=running")
        .replace("MainPID=0", "MainPID=101")
    )
    proc = runtime["proc"] / "101"
    (runtime["group"] / "cgroup.procs").write_text("101\n")
    argv = _argv(runtime, "/credentials")
    if argv_suffix:
        argv = argv.replace(b"/credentials/notification.json", argv_suffix.encode())
    (proc / "cmdline").write_bytes(argv)
    (proc / "environ").write_bytes(environment)
    result = _run(runtime, "post-start", FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


def _block(title: str) -> str:
    section = RUNBOOK.read_text().split(f"## {title}", 1)[1].split("```bash", 1)[1]
    return section.split("```", 1)[0]


@pytest.mark.parametrize(
    "title,fail",
    [
        ("24. Rollback", "runtime_state"),
        ("24. Rollback", "database"),
        ("25. Uninstall", "runtime_state"),
    ],
)
def test_destructive_blocks_stop_after_failed_proof(tmp_path: Path, title: str, fail: str) -> None:
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    bin_dir.mkdir()
    _command(
        bin_dir / "sudo",
        """
printf '%s\\n' "$*" >> "$FAKE_LOG"
case "$*" in
  *verify_first_launch_runtime_state.sh*) [ "$FAIL" = runtime_state ] && exit 1 ;;
  *verify_first_launch_database.py*) [ "$FAIL" = database ] && exit 1 ;;
esac
exit 0
""",
    )
    result = subprocess.run(
        ["bash", "-c", _block(title)],
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "FAKE_LOG": str(log),
            "FAIL": fail,
        },
    )
    observed = log.read_text()
    assert result.returncode != 0
    assert " rm " not in f" {observed}" and "daemon-reload" not in observed
    assert "userdel" not in observed and "groupdel" not in observed


def test_destructive_blocks_have_success_order_and_optional_cleanup() -> None:
    rollback, uninstall = _block("24. Rollback"), _block("25. Uninstall")
    for block in (rollback, uninstall):
        assert block.lstrip().startswith("set -euo pipefail")
        assert (
            block.index("systemctl stop")
            < block.index("systemctl disable")
            < block.index("verify_first_launch_runtime_state.sh")
            < block.index("verify_first_launch_database.py")
            < block.index("rm ")
            < block.index("daemon-reload")
        )
    assert "userdel traderassist || true" not in uninstall
    assert "userdel traderassist || true" in RUNBOOK.read_text()


def test_manifest_database_evidence_mapping() -> None:
    manifest = json.loads(
        (ROOT / "deploy/p4a/evidence/supervised-smoke-manifest-v1.json.example").read_text()
    )
    fields = {key for key in manifest if key.endswith("_database_evidence")}
    assert fields == {
        "existing_before_smoke_database_evidence",
        "fresh_pre_start_database_evidence",
        "fresh_post_creation_database_evidence",
        "final_post_smoke_database_evidence",
    }
    assert all(manifest[field] is None for field in fields)
