from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from websockets.asyncio.server import serve

from trader_assist_v0 import hyperliquid_raw_capture as raw

STAMP = "2026-10-11T10:00:00.123456Z"
COINS = ["ETH", "builder:SKHX"]


def metadata(request: dict[str, str]) -> Any:
    if request["type"] == "perpDexs":
        return [None, {"name": "builder"}]
    return {"universe": [{"name": "ETH" if request["dex"] == "" else "builder:SKHX"}]}


def test_discovery_uses_provider_namespace_and_rejects_ambiguity() -> None:
    coins, evidence = raw.discover_coins(metadata)
    assert coins == COINS
    assert evidence[-1]["request"] == {"type": "meta", "dex": "builder"}

    def ambiguous(request: dict[str, str]) -> Any:
        result = metadata(request)
        if request.get("dex") == "builder":
            result["universe"].append({"name": "builder:SKHX"})
        return result

    with pytest.raises(ValueError, match="ambiguous"):
        raw.discover_coins(ambiguous)


@pytest.mark.parametrize("channel", raw.CHANNELS)
def test_original_object_receive_timestamp_and_reopen(tmp_path: Path, channel: str) -> None:
    payload: Any = {"coin": COINS[1], "time": 123, "levels": [[{"px": "1.2300"}], []]}
    if channel == "trades":
        payload = [{"coin": COINS[1], "px": "1.2300", "sz": "0.10", "time": 123}]
    message = {"channel": channel, "data": payload}
    with raw.RawWriter(tmp_path) as writer:
        assert raw.record_message(writer, message, STAMP, COINS) == (COINS[1], channel)
    data = [item for item in raw.read_records(writer.paths) if item["kind"] == "data"]
    assert data == [
        {
            "schema_version": 1,
            "kind": "data",
            "channel": channel,
            "venue_coin": COINS[1],
            "received_at_utc": STAMP,
            "raw_payload": message,
        }
    ]


def test_rotation_unique_sessions_and_clean_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    synced: list[int] = []
    fsync = os.fsync

    def observe(fd: int) -> None:
        synced.append(fd)
        fsync(fd)

    monkeypatch.setattr(raw.os, "fsync", observe)
    stamp = [STAMP]
    with raw.RawWriter(tmp_path, max_bytes=1024, clock=lambda: stamp[0]) as writer:
        writer.marker("large", value="x" * 800)
        writer.marker("next")
        stamp[0] = "2026-10-12T00:00:00.000000Z"
        writer.marker("next_day")
    assert len(writer.paths) >= 3
    assert len(synced) == len(writer.paths)
    before = {path: path.read_bytes() for path in writer.paths}
    with raw.RawWriter(tmp_path) as second:
        second.marker("new_session")
    assert all(path.read_bytes() == content for path, content in before.items())
    assert not set(second.paths).intersection(writer.paths)
    events = [record.get("event") for record in raw.read_records(writer.paths)]
    assert events.count("segment_start") == events.count("segment_end") == len(writer.paths)


def test_exclusive_lock_across_processes_and_shutdown_readback(tmp_path: Path) -> None:
    code = """
import sys
from pathlib import Path
from trader_assist_v0.hyperliquid_raw_capture import RawWriter
with RawWriter(Path(sys.argv[1])) as writer:
    writer.marker('child_saved')
"""
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    with raw.RawWriter(tmp_path):
        child = subprocess.run(
            [sys.executable, "-c", code, str(tmp_path)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert child.returncode != 0
        assert "BlockingIOError" in child.stderr
    child = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == 0, child.stderr
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert any(record.get("event") == "child_saved" for record in records)
    assert all(record["clean"] for record in records if record.get("event") == "stop")


def test_write_failure_stops_without_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with raw.RawWriter(tmp_path) as writer:

        def disk_full(record: dict[str, Any]) -> None:
            raise OSError("disk full")

        with monkeypatch.context() as scoped:
            scoped.setattr(writer, "_line", disk_full)
            with pytest.raises(OSError, match="disk full"):
                raw.record_message(
                    writer, {"channel": "bbo", "data": {"coin": "ETH"}}, STAMP, COINS
                )
    assert not any(record.get("event") == "reconnect" for record in raw.read_records(writer.paths))


def test_ack_empty_trades_unknown_coin_and_partial_line(tmp_path: Path) -> None:
    with raw.RawWriter(tmp_path) as writer:
        raw.record_message(
            writer,
            {
                "channel": "subscriptionResponse",
                "data": {
                    "method": "subscribe",
                    "subscription": {"coin": COINS[1], "type": "trades"},
                },
            },
            STAMP,
            COINS,
        )
        assert raw.record_message(writer, {"channel": "trades", "data": []}, STAMP, COINS) is None
        with pytest.raises(ValueError, match="unexpected data coin"):
            raw.record_message(writer, {"channel": "bbo", "data": {"coin": "GUESS"}}, STAMP, COINS)
    assert not any(record["kind"] == "data" for record in raw.read_records(writer.paths))
    partial = tmp_path / "partial.ndjson"
    partial.write_text('{"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="partial line"):
        list(raw.read_records([partial]))


def test_reconnect_requires_fresh_acks_and_marks_unknown_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coins_and_evidence = raw.discover_coins(metadata)
    monkeypatch.setattr(raw, "discover_coins", lambda: coins_and_evidence)

    async def scenario() -> dict[str, Any]:
        connections = 0

        async def provider(websocket: Any) -> None:
            nonlocal connections
            connections += 1
            for _ in range(6):
                message = json.loads(await websocket.recv())
                await websocket.send(
                    json.dumps({"channel": "subscriptionResponse", "data": message})
                )
            await websocket.send(json.dumps({"channel": "bbo", "data": {"coin": "ETH", "bbo": []}}))
            if connections == 1:
                await websocket.close()
            else:
                await websocket.wait_closed()

        async with serve(provider, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            monkeypatch.setattr(raw, "WS_URL", f"ws://127.0.0.1:{port}")
            return await raw.capture(tmp_path, duration=0.5)

    result = asyncio.run(scenario())
    assert result["transport_storage"] == "PASS"
    assert result["family_coverage"]["builder:SKHX/trades"] == "INCOMPLETE"
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert sum(record.get("event") == "ack" for record in records) == 12
    assert any(
        record.get("event") == "gap" and record["missing"] == "UNKNOWN" for record in records
    )


def test_public_real_receipt_ubuntu(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    explicit = os.environ.get("HYPERLIQUID_RAW_PUBLIC_PROOF") == "1"
    issue_ci = (
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_JOB") == "contracts"
        and os.environ.get("GITHUB_HEAD_REF") == "feature/issue-322-rc5-public-raw-p0"
    )
    if not (explicit or issue_ci):
        pytest.skip("bounded public proof is opt-in or exact Issue #322 contracts job")
    assert sys.platform == "linux", "authoritative public proof requires Linux"
    result = asyncio.run(raw.capture(tmp_path, duration=60))
    # Emit only bounded proof, not public raw payloads; preserve canonical CI evidence.
    with capsys.disabled():
        print("I322_PUBLIC_PROOF=" + json.dumps(result, sort_keys=True), flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(
                "\nIssue #322 public proof\n```json\n"
                + json.dumps(result, sort_keys=True)
                + "\n```\n"
            )
    assert result["transport_storage"] == "PASS", result
    assert result["reopened_records"] > 0


@pytest.mark.parametrize("duration", [0, -1, 181, float("nan"), float("inf")])
def test_bounded_duration_rejects_invalid(tmp_path: Path, duration: float) -> None:
    with pytest.raises(ValueError, match="duration"):
        asyncio.run(raw.capture(tmp_path, duration=duration))


def test_continuous_rotation_has_bounded_path_memory(tmp_path: Path) -> None:
    with raw.RawWriter(tmp_path, max_bytes=1024, retain_paths=False) as writer:
        for _ in range(30):
            writer.marker("fixture", value="x" * 800)
    assert writer.paths == []
    assert writer.segment_count >= 30
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert sum(r.get("event") == "segment_end" for r in records) == writer.segment_count


# Test-only subprocess seams; the production CLI accepts no provider/fixture options.
CLI_FIXTURE = r"""
import asyncio, importlib.util, json, sys, threading, time
from pathlib import Path
from websockets.asyncio.server import serve
from trader_assist_v0 import hyperliquid_raw_capture as raw
spec = importlib.util.spec_from_file_location(
    'raw_cli_fixture', 'scripts/hyperliquid_raw_capture.py'
)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
mode = sys.argv[1]
out = sys.argv[2]
original_discover = raw.discover_coins
original_receive = raw.receive_public
original_line = raw.RawWriter._line
original_fsync = raw.os.fsync
connections = 0

def discover(*, stop):
    def info(request):
        print('REQUEST=' + json.dumps(request), flush=True)
        if request['type'] == 'perpDexs':
            return [None, {'name': 'builder'}, {'name': 'later'}, {'name': 'last'}]
        if request['dex'] == 'builder' and mode.startswith('discovery'):
            print('READY', flush=True)
            if mode == 'discovery-stuck':
                time.sleep(60)
            else:
                assert stop._intent.wait(10)
                time.sleep(0.05)
            if mode == 'discovery-http-error':
                raise OSError('fixture metadata HTTP failure')
            if mode == 'discovery-invalid':
                return {'universe': 'invalid'}
        coin = 'ETH' if request['dex'] == '' else request['dex'] + ':SKHX'
        if request['dex'] in ('', 'builder'):
            return {'universe': [{'name': coin}]}
        return {'universe': []}
    return original_discover(info, stop=stop)
raw.discover_coins = discover
if mode == 'discovery-stuck':
    raw.DISCOVERY_STOP_SECONDS = 0.2

def line(self, record):
    if record.get('kind') == 'data' and mode == 'write-fault':
        raise OSError('fixture disk write failure')
    original_line(self, record)
    if record.get('kind') == 'data' and (mode != 'reconnect' or connections == 2):
        print('READY', flush=True)
raw.RawWriter._line = line

def fsync(fd):
    if mode == 'fsync-fault':
        raise OSError('fixture fsync failure')
    original_fsync(fd)
    print('FSYNC', flush=True)
raw.os.fsync = fsync

async def receive(writer, coins):
    async def provider(ws):
        global connections
        connections += 1
        for _ in range(6):
            message = json.loads(await ws.recv())
            await ws.send(json.dumps({'channel': 'subscriptionResponse', 'data': message}))
        if mode == 'provider-fault':
            await ws.send(json.dumps({'channel': 'error', 'data': 'fixture fatal provider'}))
        elif mode == 'exhausted':
            await ws.close()
        else:
            for coin in coins:
                for channel in raw.CHANNELS:
                    payload = {'coin': coin, 'bbo': [], 'levels': [[], []]}
                    if channel == 'trades':
                        payload = [{'coin': coin, 'px': '1.2300', 'time': 123}]
                    await ws.send(json.dumps({'channel': channel, 'data': payload}))
            if mode == 'reconnect' and connections == 1:
                await ws.close()
            else:
                await ws.wait_closed()
    async with serve(provider, '127.0.0.1', 0) as server:
        raw.WS_URL = 'ws://127.0.0.1:' + str(server.sockets[0].getsockname()[1])
        await original_receive(writer, coins)
raw.receive_public = receive
sys.argv = ['fixture', '--continuous', '--output', out]
try:
    raise SystemExit(cli.main())
finally:
    workers = sum(t.name == 'hyperliquid-public-discovery' for t in threading.enumerate())
    print('WORKERS=' + str(workers), flush=True)
"""


def cli_fixture(tmp_path: Path, mode: str, sig: int | None = None) -> tuple[int, str, str]:
    import select

    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    with subprocess.Popen(
        [sys.executable, "-u", "-c", CLI_FIXTURE, mode, str(tmp_path)],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as child:
        prefix = ""
        try:
            if sig is not None:
                assert child.stdout is not None
                # Read at the fd level so TextIO read-ahead cannot hide readiness.
                import time

                deadline = time.monotonic() + 10
                while "READY\n" not in prefix:
                    remaining = deadline - time.monotonic()
                    assert remaining > 0, "fixture did not become ready"
                    assert select.select([child.stdout], [], [], remaining)[0]
                    chunk = os.read(child.stdout.fileno(), 4096).decode()
                    assert chunk, "fixture exited before signal readiness"
                    prefix += chunk
                started = time.monotonic()
                child.send_signal(sig)
            stdout, stderr = child.communicate(timeout=25)
            if sig is not None:
                assert time.monotonic() - started < 25
            return child.returncode, prefix + stdout, stderr
        finally:
            if child.poll() is None:
                child.kill()  # Only a failed, disposable test child; never a service.
                child.communicate(timeout=5)


@pytest.mark.parametrize("sig", [15, 2])
@pytest.mark.parametrize("mode", ["healthy", "reconnect", "discovery-stop"])
def test_actual_cli_signal_clean_stop(tmp_path: Path, mode: str, sig: int) -> None:
    status, stdout, stderr = cli_fixture(tmp_path, mode, sig)
    assert status == 0, stderr
    assert '"termination": "clean_requested_stop"' in stdout
    assert "WORKERS=0" in stdout and "FSYNC" in stdout
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert any(r.get("event") == "stop" and r["clean"] for r in records)
    assert records[-1]["event"] == "segment_end"
    if mode == "discovery-stop":
        assert '"dex": "later"' not in stdout
        assert not any(r.get("event") == "subscribe" for r in records)
    else:
        assert any(r["kind"] == "data" for r in records)
    if mode == "reconnect":
        assert sum(r.get("event") == "ack" for r in records) == 12
        assert any(r.get("event") == "gap" and r["missing"] == "UNKNOWN" for r in records)
    with raw.RawWriter(tmp_path):
        pass  # The signalled child released its flock.


@pytest.mark.parametrize(
    ("mode", "error", "sig"),
    [
        ("discovery-http-error", "metadata HTTP failure", 15),
        ("discovery-invalid", "invalid meta universe", 15),
        ("discovery-stuck", "join budget", 15),
        ("provider-fault", "unexpected public channel", None),
        ("exhausted", "ConnectionClosed", None),
        ("write-fault", "disk write failure", None),
        ("fsync-fault", "fsync failure", 15),
    ],
)
def test_cli_faults_fail_nonzero(tmp_path: Path, mode: str, error: str, sig: int | None) -> None:
    status, stdout, stderr = cli_fixture(tmp_path, mode, sig)
    assert status != 0 and error in stderr, (stdout, stderr)
    assert "clean_requested_stop" not in stdout
    if mode != "discovery-stuck":
        assert "WORKERS=0" in stdout
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert any(
        r.get("event") in {"stop", "finalization_failure"} and not r["clean"] for r in records
    )
    with raw.RawWriter(tmp_path):
        pass


def test_stop_before_discovery_and_no_archive_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_readback(paths: list[Path]) -> Any:
        raise AssertionError("continuous must not reopen or hash archive")

    monkeypatch.setattr(raw, "read_records", unexpected_readback)

    async def scenario() -> dict[str, Any]:
        stop = raw.StopIntent()
        stop.request()
        return await raw.capture_continuous(tmp_path, stop=stop)

    assert asyncio.run(scenario())["termination"] == "clean_requested_stop"


def test_receiver_failure_wins_simultaneous_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        stop = raw.StopIntent()

        async def provider_failure(writer: raw.RawWriter, coins: list[str]) -> None:
            stop.request()
            raise ValueError("simultaneous provider failure")

        monkeypatch.setattr(raw, "receive_public", provider_failure)
        with raw.RawWriter(tmp_path) as writer:
            await raw._receive_until_stop(writer, COINS, stop)

    with pytest.raises(ValueError, match="simultaneous provider failure"):
        asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["flush", "close"])
def test_finalization_fault_releases_lock(tmp_path: Path, fault: str) -> None:
    class FaultFile:
        def __init__(self, source: Any) -> None:
            self.source = source

        def __getattr__(self, name: str) -> Any:
            return getattr(self.source, name)

        def flush(self) -> None:
            if fault == "flush":
                raise OSError("fixture flush failure")
            self.source.flush()

        def close(self) -> None:
            self.source.close()
            if fault == "close":
                raise OSError("fixture close failure")

    with pytest.raises(OSError, match=fault):
        with raw.RawWriter(tmp_path) as writer:
            writer._file = FaultFile(writer._file)  # type: ignore[assignment]
    assert writer._lock is None
    with raw.RawWriter(tmp_path):
        pass


def test_primary_failure_is_not_masked_by_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(fd: int) -> None:
        raise OSError("secondary fsync failure")

    with monkeypatch.context() as scoped, pytest.raises(ValueError, match="primary provider"):
        scoped.setattr(raw.os, "fsync", fail)
        with raw.RawWriter(tmp_path):
            raise ValueError("primary provider failure")
    with raw.RawWriter(tmp_path):
        pass


def test_cli_defaults_and_exclusive_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("raw_cli", "scripts/hyperliquid_raw_capture.py")
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    durations: list[float] = []

    async def bounded(directory: Path, *, duration: float) -> dict[str, str]:
        durations.append(duration)
        return {"transport_storage": "PASS"}

    monkeypatch.setattr(cli, "capture", bounded)
    monkeypatch.setattr(sys, "argv", ["cli", "--output", str(tmp_path)])
    assert cli.main() == 0 and durations == [180]
    for flags in (
        ["--continuous", "--duration", "1"],
        ["--continuous", "--readback"],
        ["--readback", "--duration", "1"],
    ):
        monkeypatch.setattr(sys, "argv", ["cli", "--output", str(tmp_path), *flags])
        with pytest.raises(SystemExit) as exc:
            cli.main()
        assert exc.value.code == 2


def test_unit_is_dedicated_hardened_and_default_off() -> None:
    from configparser import ConfigParser

    path = Path("deploy/p4a/systemd/trader-assist-v0-hyperliquid-raw-capture.service")
    unit = ConfigParser(interpolation=None)
    unit.read(path)
    assert unit["Unit"]["ConditionPathExists"].endswith("/hyperliquid-raw-capture-permit")
    service = unit["Service"]
    assert service["User"] == service["Group"] == "traderassist"
    assert service["Restart"] == "no" and service["TimeoutStopSec"] == "30"
    assert service["KillSignal"] == "SIGTERM"
    assert "--continuous" in service["ExecStart"]
    assert service["StateDirectory"] == "trader-assist-v0-hyperliquid-raw-capture"
    assert service["StateDirectoryMode"] == "0700"
    assert service["ProtectSystem"] == "strict" and service["NoNewPrivileges"] == "yes"
    assert "Install" not in unit
    assert "LoadCredential" not in service and "EnvironmentFile" not in service
    assert "three-setup" not in path.read_text()


def test_missing_acks_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    ticks = iter([0, 31])
    monkeypatch.setattr(raw, "time", SimpleNamespace(monotonic=lambda: next(ticks)))

    class Socket:
        async def send(self, message: str) -> None:
            pass

    async def connections() -> Any:
        yield Socket()

    monkeypatch.setattr(raw, "connect", lambda *args, **kwargs: connections())

    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            await raw.receive_public(writer, COINS)

    with pytest.raises(ValueError, match="missing subscription acknowledgments"):
        asyncio.run(scenario())


def test_native_linux_unit_syntax() -> None:
    import shutil

    if sys.platform != "linux" or shutil.which("systemd-analyze") is None:
        pytest.skip("native Linux systemd syntax verification is unavailable")
    unit = "deploy/p4a/systemd/trader-assist-v0-hyperliquid-raw-capture.service"
    result = subprocess.run(
        ["systemd-analyze", "verify", "--man=no", unit],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        # CI has no staged release. Admit only its exact missing executable,
        # never a syntax/hardening diagnostic or an unknown platform failure.
        diagnostic = (
            "trader-assist-v0-hyperliquid-raw-capture.service: Command "
            "/opt/trader-assist-v0/.venv/bin/python is not executable: No such file or directory"
        )
        assert result.returncode == 1 and result.stderr.strip() == diagnostic, result.stderr
    assert not result.stdout.strip(), result.stdout
