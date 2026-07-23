"""Offline controlled-command tests for the P4A read-only verifiers."""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "scripts/p4a/verify_first_launch_runtime_state.sh"
DATABASE = ROOT / "scripts/p4a/verify_first_launch_database.py"
RUNBOOK = ROOT / "docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md"
VERIFIER_STABILIZATION_CONTRACT_SECONDS = 30.0
PROCESS_AND_FIXTURE_OVERHEAD_SECONDS = 5.0
LAUNCH_TIMEOUT_SECONDS = (
    VERIFIER_STABILIZATION_CONTRACT_SECONDS + PROCESS_AND_FIXTURE_OVERHEAD_SECONDS
)
LAUNCH_GRACE_SECONDS = 0.5
WAIT_POLL_SECONDS = 0.01
TIMEOUT_RETURN_CODE = 124


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


def _portable_database_verifier(env: Path, root: Path) -> Path:
    portable = env.parent / "verify_database.py"
    portable.write_text(
        DATABASE.read_text()
        .replace(
            'PUBLIC_ENV = Path("/etc/trader-assist-v0/public.env")', f'PUBLIC_ENV = Path("{env}")'
        )
        .replace('STATE_ROOT = Path("/var/lib/trader-assist-v0")', f'STATE_ROOT = Path("{root}")')
    )
    return portable


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
    portable = _portable_database_verifier(env, root)
    process = subprocess.run(
        [sys.executable, str(portable), "fresh-pre-start"],
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert process.returncode == 0 and process.stderr == ""
    assert json.loads(process.stdout) == result


def test_database_cli_success_stdout_is_exact_single_json_line(
    database: dict[str, Any],
) -> None:
    module, env, root, db = (database[key] for key in ("module", "env", "root", "db"))
    sqlite3.connect(db).close()
    expected = module.verify("existing-before-smoke", env, root)
    process = subprocess.run(
        [sys.executable, str(_portable_database_verifier(env, root)), "existing-before-smoke"],
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert process.returncode == 0 and process.stderr == ""
    assert process.stdout.endswith("\n") and process.stdout.count("\n") == 1
    payload = json.loads(process.stdout.removesuffix("\n"))
    assert set(payload) == {"status", "phase", "database_path", "exists", "integrity"}
    assert payload["status"] == "PASS"
    assert payload["phase"] == "existing-before-smoke"
    assert payload == expected
    assert process.stdout == json.dumps(payload, separators=(",", ":")) + "\n"


@pytest.mark.parametrize(
    "phase,create", [("existing-before-smoke", False), ("fresh-pre-start", True)]
)
def test_database_phase_existence_mismatch_fails(
    database: dict[str, Any], phase: str, create: bool
) -> None:
    if create:
        sqlite3.connect(database["db"]).close()
    with pytest.raises(database["module"].VerificationError):
        database["module"].verify(phase, database["env"], database["root"])


def test_database_cli_failure_has_no_pass_evidence(database: dict[str, Any]) -> None:
    env, root = database["env"], database["root"]
    portable = _portable_database_verifier(env, root)
    process = subprocess.run(
        [sys.executable, str(portable), "existing-before-smoke"],
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert process.returncode == 1 and process.stdout == ""
    assert process.stderr.startswith("SAFE_STOP:")


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


@pytest.mark.parametrize(
    "rows",
    [(), (("not ok",),), (("ok",), ("ok",))],
    ids=["zero-rows", "non-ok", "multiple-rows"],
)
def test_database_integrity_requires_exactly_one_ok_result(
    database: dict[str, Any], monkeypatch: pytest.MonkeyPatch, rows: tuple[tuple[str], ...]
) -> None:
    module, db = database["module"], database["db"]
    closed = False

    class Connection:
        def execute(self, query: str) -> Any:
            assert query == "PRAGMA integrity_check"
            return type("Cursor", (), {"fetchall": lambda self: list(rows)})()

        def close(self) -> None:
            nonlocal closed
            closed = True

    def connect(*_args: Any, **_kwargs: Any) -> Connection:
        return Connection()

    monkeypatch.setattr(module.sqlite3, "connect", connect)
    with pytest.raises(module.VerificationError, match="exactly one ok"):
        module.integrity(db)
    assert closed


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
    script.write_text(text)
    script.chmod(0o755)
    _command(
        bin_dir / "stat",
        '''if [ "${FAKE_HANG_STAT:-0}" = 1 ]; then
  while :; do :; done
fi
printf "%s\\n" "${FAKE_STAT:-root:root:644}"''',
    )
    _command(bin_dir / "systemd-analyze", '[ "${FAKE_ANALYZE_FAIL:-0}" = 0 ]')
    _command(bin_dir / "id", '[ "$1" = -u ] && printf "1001\\n"')
    _command(
        bin_dir / "systemctl",
        """if [ "$1" = list-jobs ]; then
  printf '%s\\n' "${FAKE_JOBS:-}"
  exit 0
fi
[ "$1" = show ] || exit 2
key=
for argument in "$@"; do
  case "$argument" in --property=*) key=${argument#--property=} ;; esac
done
[ -n "$key" ] || exit 2
if [ "$key" = MainPID ] && [ "${FAKE_DRIFT:-0}" = 1 ]; then
  count=0
  [ -f "$FAKE_MAIN_COUNT" ] && IFS= read -r count < "$FAKE_MAIN_COUNT"
  count=$((count + 1)); printf '%s' "$count" > "$FAKE_MAIN_COUNT"
  [ "$count" -gt 1 ] && { printf '102\\n'; exit 0; }
fi
while IFS= read -r line; do
  case "$line" in "$key="*) printf '%s\\n' "${line#*=}"; exit 0 ;; esac
done < "$FAKE_STATE"
exit 1""",
    )
    _command(
        bin_dir / "readlink",
        """step=0
[ -f "$FAKE_STEP" ] && IFS= read -r step < "$FAKE_STEP"
if [ "${FAKE_TRANSITION_ROUNDS:-0}" -gt "$step" ]; then
  printf 'wrapper\\n'
else
  printf '%s\\n' "${FAKE_EXE:?}"
fi""",
    )
    _command(
        bin_dir / "sleep",
        '''count=0
[ -f "$FAKE_SLEEP_COUNT" ] && IFS= read -r count < "$FAKE_SLEEP_COUNT"
printf '%s\\n' "$((count + 1))" > "$FAKE_SLEEP_COUNT"
step=0
[ -f "$FAKE_STEP" ] && IFS= read -r step < "$FAKE_STEP"
printf '%s\\n' "$((step + 1))" > "$FAKE_STEP"''',
    )
    _command(
        bin_dir / "ps",
        """[ "${FAKE_PS_FAIL:-0}" = 0 ] || exit 1
step=0
[ -f "$FAKE_STEP" ] && IFS= read -r step < "$FAKE_STEP"
if [ "${FAKE_TRANSITION_ROUNDS:-0}" -gt "$step" ]; then
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
        "source": source,
        "installed": installed,
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


def _wait_for_child(child_pid: int, deadline: float) -> int | None:
    while True:
        try:
            observed_pid, status = os.waitpid(child_pid, os.WNOHANG)
        except InterruptedError:
            continue
        if observed_pid:
            return status
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(WAIT_POLL_SECONDS, remaining))


def _signal_child_group(child_pid: int, signal_number: int) -> None:
    try:
        os.killpg(child_pid, signal_number)
    except ProcessLookupError:
        pass


def _terminate_and_reap(child_pid: int) -> int:
    _signal_child_group(child_pid, signal.SIGTERM)
    status = _wait_for_child(child_pid, time.monotonic() + LAUNCH_GRACE_SECONDS)
    if status is not None:
        return status
    _signal_child_group(child_pid, signal.SIGKILL)
    status = _wait_for_child(child_pid, time.monotonic() + LAUNCH_GRACE_SECONDS)
    if status is None:
        raise AssertionError("timed-out child process could not be reaped")
    return status


def _run(runtime: dict[str, Any], mode: str, **values: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        **values,
        "PATH": f"{runtime['bin']}:{os.environ['PATH']}",
        "FAKE_STATE": str(runtime["state"]),
        "FAKE_MAIN_COUNT": str(runtime["tmp"] / "main.count"),
        "FAKE_STEP": str(runtime["tmp"] / "step"),
        "FAKE_SLEEP_COUNT": str(runtime["tmp"] / "sleep.count"),
        "FAKE_EXE": str(runtime["python"]),
    }
    stdout_path = runtime["tmp"] / "runtime.stdout"
    stderr_path = runtime["tmp"] / "runtime.stderr"
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        file_actions = [
            (os.POSIX_SPAWN_DUP2, stdout.fileno(), 1),
            (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2),
        ]
        for descriptor in range(3, 256):
            try:
                os.fstat(descriptor)
            except OSError:
                continue
            file_actions.append((os.POSIX_SPAWN_CLOSE, descriptor))
        child_pid = os.posix_spawn(
            "/bin/bash",
            ["/bin/bash", str(runtime["script"]), mode],
            env,
            file_actions=file_actions,
            setpgroup=0,
        )
        runtime["last_child_pid"] = child_pid
        status = _wait_for_child(child_pid, time.monotonic() + LAUNCH_TIMEOUT_SECONDS)
        timed_out = status is None
        if timed_out:
            status = _terminate_and_reap(child_pid)
    stderr_text = stderr_path.read_text()
    if timed_out:
        stderr_text += "" if not stderr_text or stderr_text.endswith("\n") else "\n"
        stderr_text += "TEST_TIMEOUT: controlled verifier child exceeded launcher deadline\n"
    return subprocess.CompletedProcess(
        ["/bin/bash", str(runtime["script"]), mode],
        TIMEOUT_RETURN_CODE if timed_out else os.waitstatus_to_exitcode(status),
        stdout_path.read_text(),
        stderr_text,
    )


def test_runtime_launcher_timeout_terminates_group_and_reaps(
    runtime: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.modules[__name__], "LAUNCH_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(sys.modules[__name__], "LAUNCH_GRACE_SECONDS", 0.05)
    result = _run(runtime, "installed", FAKE_HANG_STAT="1")
    child_pid = runtime["last_child_pid"]
    assert result.returncode == TIMEOUT_RETURN_CODE
    assert "TEST_TIMEOUT:" in result.stderr
    with pytest.raises(ProcessLookupError):
        os.killpg(child_pid, 0)
    with pytest.raises(ChildProcessError):
        os.waitpid(child_pid, os.WNOHANG)


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
        ("pre-start", {"FAKE_PS_FAIL": "1"}),
        ("pre-start", {"FAKE_PS": "7 1001 unwanted"}),
        ("pre-start", {"FAKE_JOBS": "1 trader-assist-v0-public.service start running"}),
    ],
)
def test_runtime_command_failure_and_unexpected_processes_fail(
    runtime: dict[str, Any], mode: str, values: dict[str, str]
) -> None:
    result = _run(runtime, mode, **values)
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


@pytest.mark.parametrize("control_group", ["relative", "/", "/broken/../group"])
def test_runtime_rejects_malformed_control_group(
    runtime: dict[str, Any], control_group: str
) -> None:
    runtime["state"].write_text(
        runtime["state"]
        .read_text()
        .replace(
            "ControlGroup=/system.slice/trader-assist-v0-public.service",
            f"ControlGroup={control_group}",
        )
    )
    result = _run(runtime, "pre-start")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


def test_runtime_rejects_populated_pre_start_cgroup(runtime: dict[str, Any]) -> None:
    (runtime["group"] / "cgroup.procs").write_text("101\n")
    result = _run(runtime, "pre-start")
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
        FAKE_TRANSITION_ROUNDS="1",
        FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}",
    )
    assert result.returncode == 0, result.stderr
    assert (runtime["tmp"] / "sleep.count").read_text() == "1\n"


def test_runtime_post_start_waits_for_multiple_wrapper_polls(runtime: dict[str, Any]) -> None:
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
        FAKE_TRANSITION_ROUNDS="2",
        FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}",
    )
    assert result.returncode == 0, result.stderr
    assert (runtime["tmp"] / "sleep.count").read_text() == "2\n"


def test_runtime_post_start_transition_timeout_is_deterministic(runtime: dict[str, Any]) -> None:
    runtime["script"].write_text(runtime["script"].read_text().replace("SECONDS + 30", "SECONDS"))
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
        FAKE_TRANSITION_ROUNDS="1",
        FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}",
    )
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


@pytest.mark.parametrize(
    "active,substate",
    [("failed", "failed"), ("inactive", "dead"), ("active", "dead")],
)
def test_runtime_post_start_rejects_terminal_unit_states(
    runtime: dict[str, Any], active: str, substate: str
) -> None:
    runtime["state"].write_text(
        runtime["state"]
        .read_text()
        .replace("ActiveState=inactive", f"ActiveState={active}")
        .replace("SubState=dead", f"SubState={substate}")
        .replace("MainPID=0", "MainPID=101")
    )
    result = _run(runtime, "post-start")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


@pytest.mark.parametrize(
    "replacement",
    [
        ("FragmentPath=", "FragmentPath=/wrong.service"),
        ("DropInPaths=", "DropInPaths=/etc/systemd/system/unexpected.conf"),
        ("User=traderassist", "User=root"),
        ("Group=traderassist", "Group=root"),
    ],
)
def test_runtime_post_start_rejects_unit_authority_drift(
    runtime: dict[str, Any], replacement: tuple[str, str]
) -> None:
    needle, value = replacement
    text = runtime["state"].read_text()
    if needle == "FragmentPath=":
        text = text.replace(
            next(line for line in text.splitlines() if line.startswith(needle)), value
        )
    else:
        text = text.replace(needle, value, 1)
    runtime["state"].write_text(text)
    result = _run(runtime, "post-start")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


def test_runtime_post_start_rejects_installed_unit_hash_drift(runtime: dict[str, Any]) -> None:
    runtime["source"].write_text("[Service]\nUser=root\n")
    result = _run(runtime, "post-start")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


def test_runtime_post_start_rejects_missing_main_pid_directory(runtime: dict[str, Any]) -> None:
    runtime["state"].write_text(
        runtime["state"]
        .read_text()
        .replace("ActiveState=inactive", "ActiveState=active")
        .replace("SubState=dead", "SubState=running")
        .replace("MainPID=0", "MainPID=101")
    )
    (runtime["proc"] / "101").rmdir()
    result = _run(runtime, "post-start")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


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
        (b"CREDENTIALS_DIRECTORY=/credentials\0", "/credentials/other.json"),
        (b"CREDENTIALS_DIRECTORY=/credentials\0", "/credentials/nested/notification.json"),
        (b"CREDENTIALS_DIRECTORY=/credentials\0", "/credentials/*.json"),
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


@pytest.mark.parametrize("mutation", ["missing", "extra", "reordered"])
def test_runtime_post_start_rejects_critical_argv_mutation(
    runtime: dict[str, Any], mutation: str
) -> None:
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
    arguments = _argv(runtime, str(credential)).split(b"\0")[:-1]
    if mutation == "missing":
        arguments.remove(b"--session-timeout-seconds")
    elif mutation == "extra":
        arguments.insert(3, b"--unexpected-security-critical-option")
    else:
        arguments[5], arguments[7] = arguments[7], arguments[5]
    (proc / "cmdline").write_bytes(b"\0".join(arguments) + b"\0")
    (proc / "environ").write_bytes(f"CREDENTIALS_DIRECTORY={credential}\0".encode())
    (runtime["group"] / "cgroup.procs").write_text("101\n")
    result = _run(runtime, "post-start", FAKE_PS=f"101 1001 {runtime['python']} {runtime['entry']}")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


@pytest.mark.parametrize(
    "kind",
    [
        "database-traversal",
        "database-parent",
        "database-escape",
        "risk-symlink",
        "risk-directory",
        "risk-escape",
    ],
)
def test_runtime_rejects_unapproved_database_and_risk_paths(
    runtime: dict[str, Any], kind: str
) -> None:
    env = runtime["env"]
    text = env.read_text()
    database = runtime["tmp"] / "state" / "runtime.db"
    risk = runtime["tmp"] / "config" / "risk.json"
    if kind == "database-traversal":
        text = text.replace(str(database), str(runtime["tmp"] / "state" / "../outside.db"))
    elif kind == "database-parent":
        text = text.replace(str(database), str(runtime["tmp"] / "state" / "missing" / "runtime.db"))
    elif kind == "database-escape":
        outside = runtime["tmp"] / "outside"
        outside.mkdir()
        text = text.replace(str(database), str(outside / "runtime.db"))
    elif kind == "risk-symlink":
        target = runtime["tmp"] / "risk-target.json"
        target.write_text("{}")
        link = runtime["tmp"] / "config" / "risk-link.json"
        link.symlink_to(target)
        text = text.replace(str(risk), str(link))
    elif kind == "risk-directory":
        directory = runtime["tmp"] / "config" / "risk-directory"
        directory.mkdir()
        text = text.replace(str(risk), str(directory))
    else:
        outside = runtime["tmp"] / "outside-risk"
        outside.mkdir()
        target = outside / "risk.json"
        target.write_text("{}")
        text = text.replace(str(risk), str(target))
    env.write_text(text)
    result = _run(runtime, "post-start")
    assert result.returncode == 1 and "SAFE_STOP:" in result.stderr


def _block(title: str) -> str:
    section = RUNBOOK.read_text().split(f"## {title}", 1)[1].split("```bash", 1)[1]
    return section.split("```", 1)[0]


def _optional_cleanup_block() -> str:
    section = RUNBOOK.read_text().split("Only after the proof-bearing block above completes", 1)[1]
    return section.split("```bash", 1)[1].split("```", 1)[0]


@pytest.mark.parametrize(
    "title,fail",
    [
        ("24. Rollback", "runtime_state"),
        ("24. Rollback", "database"),
        ("25. Uninstall", "runtime_state"),
        ("25. Uninstall", "database"),
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
        ["bash", "-c", _block(title) + _optional_cleanup_block()],
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


@pytest.mark.parametrize("title", ["24. Rollback", "25. Uninstall"])
def test_destructive_blocks_execute_successful_proof_sequence(tmp_path: Path, title: str) -> None:
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    bin_dir.mkdir()
    _command(bin_dir / "sudo", 'printf "%s\\n" "$*" >> "$FAKE_LOG"')
    result = subprocess.run(
        ["bash", "-c", _block(title)],
        text=True,
        capture_output=True,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_LOG": str(log)},
    )
    observed = log.read_text().splitlines()
    assert result.returncode == 0, result.stderr
    labels = [
        "systemctl stop",
        "systemctl disable",
        "verify_first_launch_runtime_state.sh",
        "verify_first_launch_database.py",
        "rm ",
        "daemon-reload",
    ]
    positions = [
        next(index for index, line in enumerate(observed) if label in line) for label in labels
    ]
    assert positions == sorted(positions)
    assert all("userdel" not in line and "groupdel" not in line for line in observed)


@pytest.mark.parametrize("title", ["24. Rollback", "25. Uninstall"])
def test_optional_cleanup_failure_warns_after_successful_proof_sequence(
    tmp_path: Path, title: str
) -> None:
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    bin_dir.mkdir()
    _command(
        bin_dir / "sudo",
        r'''printf '%s\n' "$*" >> "$FAKE_LOG"
case "$*" in
  userdel\ *|groupdel\ *)
    printf 'WARNING: optional cleanup failed: %s\n' "$*" >&2
    exit 1
    ;;
esac''',
    )
    result = subprocess.run(
        ["bash", "-c", _block(title) + _optional_cleanup_block()],
        text=True,
        capture_output=True,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_LOG": str(log)},
    )
    observed = log.read_text().splitlines()
    proof_commands = [
        line.removeprefix("sudo ")
        for line in _block(title).splitlines()
        if line.startswith("sudo ")
    ]
    assert result.returncode == 0
    assert observed[: len(proof_commands)] == proof_commands
    assert observed[len(proof_commands) :] == ["userdel traderassist", "groupdel traderassist"]
    assert proof_commands.index("systemctl daemon-reload") < len(proof_commands)
    assert result.stderr.splitlines() == [
        "WARNING: optional cleanup failed: userdel traderassist",
        "WARNING: optional cleanup failed: groupdel traderassist",
    ]


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
