"""Fixture-controlled tests for the dedicated-host operational verifiers."""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_SOURCE = REPO_ROOT / "scripts/p4a/verify_first_launch_runtime_state.sh"
DATABASE_SOURCE = REPO_ROOT / "scripts/p4a/verify_first_launch_database.py"


def _command(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


@pytest.fixture
def runtime(tmp_path: Path) -> dict[str, object]:
    source = tmp_path / "source.service"
    installed = tmp_path / "installed.service"
    source.write_text("[Service]\nUser=traderassist\n")
    installed.write_text(source.read_text())
    public_env = tmp_path / "public.env"
    public_env.write_text(
        "TRADER_ASSIST_V0_DATABASE_PATH=/var/lib/trader-assist-v0/runtime.db\n"
        "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH=/etc/trader-assist-v0/risk.json\n"
        "TRADER_ASSIST_V0_WEBHOOK_TIMEOUT_SECONDS=10\n"
        "TRADER_ASSIST_V0_ACKNOWLEDGEMENT_TIMEOUT_SECONDS=30\n"
        "TRADER_ASSIST_V0_SESSION_TIMEOUT_SECONDS=60\n"
    )
    proc = tmp_path / "proc" / "101"
    proc.mkdir(parents=True)
    cgroup = tmp_path / "cgroup" / "system.slice" / "trader-assist-v0-public.service"
    cgroup.mkdir(parents=True)
    (cgroup / "cgroup.procs").write_text("")
    script = tmp_path / "verify.sh"
    text = RUNTIME_SOURCE.read_text()
    replacements = {
        "/opt/trader-assist-v0/deploy/p4a/systemd/trader-assist-v0-public.service": str(source),
        "/etc/systemd/system/trader-assist-v0-public.service": str(installed),
        "/etc/trader-assist-v0/public.env": str(public_env),
        "/sys/fs/cgroup": str(tmp_path / "cgroup"),
        'PROC_ROOT="/proc"': f'PROC_ROOT="{tmp_path / "proc"}"',
        "WAIT_SECONDS=30": "WAIT_SECONDS=0",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace(
        "metadata=\"$(stat -c '%U:%G:%a' \"$INSTALLED_UNIT\")\" || die \"cannot inspect installed unit metadata\"",
        "metadata=\"${STAT_VALUE:-root:root:644}\"",
    )
    text = text.replace(
        "source_hash=\"$(sha256sum \"$SOURCE_UNIT\" | awk '{print $1}')\" || die \"cannot hash reviewed source unit\"",
        "source_hash=good",
    )
    text = text.replace(
        "installed_hash=\"$(sha256sum \"$INSTALLED_UNIT\" | awk '{print $1}')\" || die \"cannot hash installed unit\"",
        "installed_hash=\"${INSTALLED_HASH:-good}\"",
    )
    text = text.replace(
        'value() { systemctl show "$SERVICE" --property="$1" --value; }',
        '''value() {
    case "$1" in
        FragmentPath) printf '%s\\n' "${SHOW_FRAGMENT:-$INSTALLED_UNIT}" ;;
        DropInPaths) printf '%s\\n' "${SHOW_DROPINS:-}" ;;
        User) printf '%s\\n' "${SHOW_USER:-traderassist}" ;;
        Group) printf '%s\\n' "${SHOW_GROUP:-traderassist}" ;;
        Id) printf '%s\\n' "${SHOW_ID:-trader-assist-v0-public.service}" ;;
        ActiveState) printf '%s\\n' "${SHOW_ACTIVE:-inactive}" ;;
        MainPID) printf '%s\\n' "${SHOW_PID:-0}" ;;
        SubState) printf '%s\\n' "${SHOW_SUB:-running}" ;;
        UnitFileState) printf '%s\\n' "${SHOW_UNIT_FILE:-disabled}" ;;
        ControlGroup) printf '%s\\n' /system.slice/trader-assist-v0-public.service ;;
    esac
}''',
    )
    text = text.replace(
        'systemd-analyze verify "$INSTALLED_UNIT" >/dev/null || die "systemd unit verification failed"',
        '[[ "${VERIFY_FAIL:-0}" == 0 ]] || die "systemd unit verification failed"',
    )
    text = text.replace(
        'jobs="$(systemctl list-jobs --no-legend --no-pager)" || die "cannot inspect authorized unit jobs"',
        'jobs="${SHOW_JOBS:-}"',
    )
    text = text.replace(
        'done < <(ps -eo pid=,user=,args=)',
        'done <<< "${PS_LINES:-}"',
    )
    text = text.replace(
        'users="$(ps -u "$APPROVED_USER" -o pid=)" || die "cannot inspect dedicated user processes"',
        'users="${PS_USER_PIDS:-}"',
    )
    text = text.replace(
        'executable="$(readlink -f "$PROC_ROOT/$pid/exe")" || die "cannot inspect authorized process executable"',
        'executable="${FAKE_EXE:-$APPROVED_PYTHON}"',
    )
    script.write_text(text)
    script.chmod(0o755)
    return {
        "script": script,
        "source": source,
        "installed": installed,
        "env": public_env,
        "proc": proc,
        "cgroup": cgroup,
    }


def _run_runtime(runtime: dict[str, object], mode: str, **overrides: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(
        {
        }
    )
    env.update(overrides)
    return subprocess.run(
        ["bash", str(runtime["script"]), mode],
        text=True,
        capture_output=True,
        env=env,
        timeout=5,
    )


def _post_argv() -> bytes:
    values = [
        "/opt/trader-assist-v0/venv/bin/python",
        "/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py",
        "--enable-restricted-public-runtime",
        "--mode",
        "RESTRICTED_PUBLIC_LIVE_SHADOW",
        "--database-path",
        "/var/lib/trader-assist-v0/runtime.db",
        "--risk-configuration-path",
        "/etc/trader-assist-v0/risk.json",
        "--notification-credential-file",
        "/run/credentials/unit/notification.json",
        "--webhook-timeout-seconds",
        "10",
        "--acknowledgement-timeout-seconds",
        "30",
        "--session-timeout-seconds",
        "60",
    ]
    return "\0".join(values).encode() + b"\0"


@pytest.mark.parametrize("mode", ["installed", "pre-start", "final-state"])
def test_runtime_positive_nonrunning_modes(runtime: dict[str, object], mode: str) -> None:
    result = _run_runtime(runtime, mode)
    assert result.returncode == 0, result.stderr


def test_runtime_post_start_positive(runtime: dict[str, object]) -> None:
    proc = runtime["proc"]
    cgroup = runtime["cgroup"]
    assert isinstance(proc, Path) and isinstance(cgroup, Path)
    (proc / "cmdline").write_bytes(_post_argv())
    (cgroup / "cgroup.procs").write_text("101\n")
    result = _run_runtime(
        runtime, "post-start", SHOW_ACTIVE="active", SHOW_PID="101", SHOW_SUB="running",
        PS_USER_PIDS="101",
        PS_LINES=(
            "101 traderassist /opt/trader-assist-v0/venv/bin/python "
            "/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"
        ),
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("mode", "overrides"),
    [
        ("installed", {"INSTALLED_HASH": "bad"}),
        ("installed", {"STAT_VALUE": "root:root:600"}),
        ("installed", {"SHOW_FRAGMENT": "/wrong.service"}),
        ("installed", {"SHOW_USER": "root"}), ("installed", {"SHOW_GROUP": "root"}),
        ("installed", {"SHOW_DROPINS": "/etc/systemd/system/x.conf"}),
        ("installed", {"SHOW_ID": "other.service"}),
        ("installed", {"VERIFY_FAIL": "1"}), ("pre-start", {"SHOW_ACTIVE": "active"}),
        ("pre-start", {"SHOW_JOBS": "1 trader-assist-v0-public.service start running"}),
        ("pre-start", {"PS_USER_PIDS": "77"}),
        ("pre-start", {"PS_LINES": "7 root /scripts/p4a/run_restricted_public_runtime.sh"}),
        (
            "pre-start",
            {"PS_LINES": "7 root /opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"},
        ),
        ("final-state", {"SHOW_UNIT_FILE": "enabled"}), ("final-state", {"PS_USER_PIDS": "77"}),
    ],
)
def test_runtime_negative_matrix(runtime: dict[str, object], mode: str, overrides: dict[str, str]) -> None:
    result = _run_runtime(runtime, mode, **overrides)
    assert result.returncode == 1
    assert "SAFE_STOP:" in result.stderr


def test_runtime_missing_unit_and_cgroup_fail(runtime: dict[str, object]) -> None:
    installed = runtime["installed"]
    assert isinstance(installed, Path)
    installed.unlink()
    assert _run_runtime(runtime, "installed").returncode == 1
    installed.write_text("[Service]\n")
    cgroup = runtime["cgroup"]
    assert isinstance(cgroup, Path)
    (cgroup / "cgroup.procs").write_text("9\n")
    assert _run_runtime(runtime, "pre-start").returncode == 1


@pytest.mark.parametrize(
    ("overrides", "argv"),
    [
        ({"SHOW_ACTIVE": "inactive", "SHOW_PID": "0"}, _post_argv()),
        ({"SHOW_ACTIVE": "active", "SHOW_PID": "bad"}, _post_argv()),
        (
            {"SHOW_ACTIVE": "active", "SHOW_PID": "101", "FAKE_EXE": "/wrong/python"},
            _post_argv(),
        ),
        ({"SHOW_ACTIVE": "active", "SHOW_PID": "101"}, b"bad\0"),
        (
            {"SHOW_ACTIVE": "active", "SHOW_PID": "101", "PS_USER_PIDS": "101 102"},
            _post_argv(),
        ),
        (
            {
                "SHOW_ACTIVE": "active",
                "SHOW_PID": "101",
                "PS_USER_PIDS": "101",
                "PS_LINES": "101 traderassist wrapper /scripts/p4a/run_restricted_public_runtime.sh",
            },
            _post_argv(),
        ),
    ],
)
def test_runtime_post_start_negative_matrix(runtime: dict[str, object], overrides: dict[str, str], argv: bytes) -> None:
    proc = runtime["proc"]
    assert isinstance(proc, Path)
    (proc / "cmdline").write_bytes(argv)
    overrides.setdefault("PS_USER_PIDS", "101")
    overrides.setdefault(
        "PS_LINES",
        "101 traderassist /opt/trader-assist-v0/venv/bin/python "
        "/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py",
    )
    result = _run_runtime(runtime, "post-start", **overrides)
    assert result.returncode == 1


def test_runtime_post_start_rejects_wrong_cgroup(runtime: dict[str, object]) -> None:
    proc = runtime["proc"]
    cgroup = runtime["cgroup"]
    assert isinstance(proc, Path) and isinstance(cgroup, Path)
    (proc / "cmdline").write_bytes(_post_argv())
    (cgroup / "cgroup.procs").write_text("101\n102\n")
    result = _run_runtime(
        runtime, "post-start", SHOW_ACTIVE="active", SHOW_PID="101", PS_USER_PIDS="101",
        PS_LINES=(
            "101 traderassist /opt/trader-assist-v0/venv/bin/python "
            "/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"
        ),
    )
    assert result.returncode == 1


def _database_module() -> object:
    spec = importlib.util.spec_from_file_location("database_verifier", DATABASE_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def database(tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "state"
    root.mkdir()
    env_file = tmp_path / "public.env"
    db = root / "runtime.db"
    env_file.write_text(f"TRADER_ASSIST_V0_DATABASE_PATH={db}\n")
    return {"module": _database_module(), "root": root, "env": env_file, "db": db}


@pytest.mark.parametrize("phase", ["existing-before-smoke", "fresh-post-creation", "final-post-smoke"])
def test_database_existing_phases(database: dict[str, object], phase: str) -> None:
    db = database["db"]
    assert isinstance(db, Path)
    sqlite3.connect(db).close()
    database["module"].verify(phase, database["env"], database["root"])


def test_database_fresh_pre_start(database: dict[str, object]) -> None:
    database["module"].verify("fresh-pre-start", database["env"], database["root"])


@pytest.mark.parametrize(
    "content",
    [
        "TRADER_ASSIST_V0_DATABASE_PATH=/a\nTRADER_ASSIST_V0_DATABASE_PATH=/b\n",
        "TRADER_ASSIST_V0_DATABASE_PATH nope\n",
        "TRADER_ASSIST_V0_DATABASE_PATH=/a=x\n",
    ],
)
def test_database_rejects_bad_assignment(database: dict[str, object], content: str) -> None:
    env_file = database["env"]
    assert isinstance(env_file, Path)
    env_file.write_text(content)
    with pytest.raises(database["module"].VerificationError):
        database["module"].verify("fresh-pre-start", env_file, database["root"])


def test_database_rejects_escape_symlink_nonregular_and_integrity(database: dict[str, object]) -> None:
    module = database["module"]
    root = database["root"]
    env_file = database["env"]
    db = database["db"]
    assert isinstance(root, Path) and isinstance(env_file, Path) and isinstance(db, Path)
    env_file.write_text("TRADER_ASSIST_V0_DATABASE_PATH=/tmp/outside.db\n")
    with pytest.raises(module.VerificationError):
        module.verify("fresh-pre-start", env_file, root)
    env_file.write_text(f"TRADER_ASSIST_V0_DATABASE_PATH={db}\n")
    target = root / "target.db"
    target.write_text("x")
    db.symlink_to(target)
    with pytest.raises(module.VerificationError):
        module.verify("existing-before-smoke", env_file, root)
    db.unlink()
    db.mkdir()
    with pytest.raises(module.VerificationError):
        module.verify("existing-before-smoke", env_file, root)
    db.rmdir()
    db.write_text("not sqlite")
    with pytest.raises(module.VerificationError):
        module.verify("existing-before-smoke", env_file, root)
