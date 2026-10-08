from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from test_three_setup_operator_contracts import make_source

ROOT = Path(__file__).resolve().parents[1]


def test_operator_lock_is_complete_hashed_and_isolated() -> None:
    subprocess.run(
        (shutil.which("python") or "python", str(ROOT / "scripts/check_dependency_lock.py")),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    lock = (ROOT / "requirements-operator.lock").read_text(encoding="utf-8")
    entries = [line for line in lock.splitlines() if line and not line.startswith("#")]
    assert len(entries) == 16
    assert all(" --hash=sha256:" in entry for entry in entries)
    assert not any("python-multipart" in entry for entry in entries)


def test_linux_python312_isolated_operator_https_qualification(tmp_path: Path) -> None:
    """Qualify the isolated lock and real HTTPS process on standard Linux CI."""
    if sys.platform != "linux":
        pytest.skip("authoritative operator qualification runs on GitHub Linux CI")
    assert sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 12), (
        "Linux qualification requires CPython 3.12"
    )
    openssl = shutil.which("openssl")
    assert openssl is not None, "Linux qualification requires system OpenSSL"

    def run(*argv: str, timeout: int = 240) -> None:
        completed = subprocess.run(
            argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
        assert completed.returncode == 0, (
            f"{' '.join(argv)} failed ({completed.returncode}):\n"
            f"{(completed.stdout + completed.stderr)[-4000:]}"
        )

    venv = tmp_path / "operator-venv"
    run(sys.executable, "-m", "venv", "--without-pip", str(venv))
    isolated_python = venv / "bin" / "python"
    assert isolated_python.is_file()
    run(
        sys.executable, "-m", "pip", "--python", str(isolated_python),
        "install", "--require-hashes", "-r", str(ROOT / "requirements-operator.lock"),
    )
    run(
        str(isolated_python), str(ROOT / "scripts/check_dependency_lock.py"),
        "--verify-operator-installed",
    )
    run(sys.executable, "-m", "pip", "--python", str(isolated_python), "check")

    runtime_db = tmp_path / "runtime.sqlite"
    make_source(runtime_db, created_ms=time.time_ns() // 1_000_000)
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    run(
        openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-subj", "/CN=127.0.0.1", "-keyout", str(key), "-out", str(cert),
        "-days", "1", timeout=30,
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    credential = tmp_path / "credential.json"
    credential.write_text(
        json.dumps(
            {
                "access_token": secrets.token_urlsafe(48),
                "session_signing_secret": secrets.token_urlsafe(48),
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "runtime_evidence_path": str(runtime_db),
                "operator_ledger_path": str(tmp_path / "operator.sqlite"),
                "credential_path": str(credential),
                "allowed_hosts": ["127.0.0.1"],
                "allowed_origin": f"https://127.0.0.1:{port}",
                "bind_host": "127.0.0.1",
                "bind_port": port,
                "reference_scenario": "1pct",
                "tls_cert_path": str(cert),
                "tls_key_path": str(key),
            }
        ),
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    process = subprocess.Popen(
        (str(isolated_python), str(ROOT / "scripts/run_three_setup_operator.py"),
         "--config", str(config)),
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
    )
    success = False
    last_error = "operator did not become ready"
    try:
        context = ssl._create_unverified_context()
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context)
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                last_error = f"operator exited with status {process.returncode}"
                break
            try:
                with opener.open(f"https://127.0.0.1:{port}/login", timeout=1) as response:
                    body = response.read()
                    if (
                        response.status == 200
                        and response.headers["Cache-Control"] == "no-store"
                        and b"Operator access" in body
                    ):
                        success = True
                        break
                    last_error = f"unexpected HTTPS response: {response.status}"
            except (OSError, TimeoutError, urllib.error.URLError) as exc:
                last_error = repr(exc)
                time.sleep(0.2)
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)
    assert process.returncode is not None, f"operator did not terminate: {output[-4000:]}"
    assert success, f"operator HTTPS qualification failed: {last_error}\n{output[-4000:]}"


def test_target_pip_check_uses_explicit_provider_not_system_python(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from scripts import check_dependency_lock as checker

    provider = tmp_path / "pip-provider/bin/python"
    observed: list[tuple[str, ...]] = []

    def capture(args: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.append(args)
        assert kwargs == {"check": False, "capture_output": True, "text": True}
        return subprocess.CompletedProcess(args, 0, "No broken requirements found.\n", "")

    monkeypatch.setattr(checker.subprocess, "run", capture)
    checker._pip_check(provider)
    assert observed == [(str(provider), "-m", "pip", "--python", sys.executable, "check")]


@pytest.mark.parametrize(
    "returncode,stdout,stderr",
    [(1, "", "No module named pip"), (1, "", "requires incompatible-package"),
     (2, "broken requirement", "provider failure")],
)
def test_target_pip_check_fails_with_provider_and_target_diagnostics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    returncode: int, stdout: str, stderr: str,
) -> None:
    from scripts import check_dependency_lock as checker

    provider = tmp_path / "provider/bin/python"
    monkeypatch.setattr(
        checker.subprocess, "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, returncode, stdout, stderr),
    )
    with pytest.raises(SystemExit) as failure:
        checker._pip_check(provider)
    message = str(failure.value)
    assert str(provider) in message and sys.executable in message
    assert str(returncode) in message and (stdout or stderr) in message


def test_target_pip_check_missing_provider_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from scripts import check_dependency_lock as checker

    provider = tmp_path / "no-provider/bin/python"

    def unavailable(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("missing isolated pip provider")

    monkeypatch.setattr(checker.subprocess, "run", unavailable)
    with pytest.raises(SystemExit, match="provider unavailable") as failure:
        checker._pip_check(provider)
    assert str(provider) in str(failure.value)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux CPython 3.12 is authoritative")
def test_real_python312_pipless_base_provider_checks_pipless_target(tmp_path: Path) -> None:
    """No runner/global -m pip call: one official provider, one pip-less target."""
    assert sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 12)
    provider = tmp_path / "provider"
    target = tmp_path / "target"
    python = sys.executable

    # This wrapper records/rejects any attempted base '-m pip', even on pip-rich CI.
    shim = tmp_path / "python3.12"
    shim.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = -m ] && [ \"$2\" = pip ]; then "
        "echo 'base pip invocation forbidden' >&2; exit 97; fi\n"
        f"exec '{python}' \"$@\"\n"
    )
    shim.chmod(0o700)

    def must_succeed(*args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(args, text=True, capture_output=True, check=False, timeout=180)
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    must_succeed(str(shim), "-I", "-B", "-m", "venv", str(provider))
    must_succeed(str(shim), "-I", "-B", "-m", "venv", "--without-pip", str(target))
    provider_python = provider / "bin/python"
    target_python = target / "bin/python"
    assert must_succeed(str(provider_python), "-I", "-m", "pip", "--version").returncode == 0
    absence = must_succeed(
        str(target_python), "-I", "-c",
        "import importlib.util,sys;"
        "assert importlib.util.find_spec('pip') is None;"
        "assert sys.prefix != sys.base_prefix",
    )
    assert absence.returncode == 0
    from scripts import check_dependency_lock as checker

    # This is exactly the final verifier seam, with sys.executable bound to the target.
    must_succeed(
        str(provider_python), "-m", "pip", "--python", str(target_python), "check",
    )
    assert "base pip invocation forbidden" in subprocess.run(
        [str(shim), "-m", "pip", "--version"], capture_output=True, text=True
    ).stderr
    assert checker.PILOT_REQUIREMENT == "nautilus-trader==2.0.0rc5"
