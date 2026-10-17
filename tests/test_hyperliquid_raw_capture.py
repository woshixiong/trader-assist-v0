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


@pytest.fixture(autouse=True)
def direct_local_websocket(monkeypatch: pytest.MonkeyPatch) -> None:
    original = raw.connect

    def local_connect(url: str, **kwargs: Any) -> Any:
        if url.startswith("ws://127.0.0.1:"):
            kwargs["proxy"] = None  # Synthetic loopback never uses the host's HTTP proxy.
        return original(url, **kwargs)

    monkeypatch.setattr(raw, "connect", local_connect)


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
original_connect = raw.connect
raw.connect = lambda *a, **kw: original_connect(*a, proxy=None, **kw)
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
    if (record.get('kind') == 'data' and record.get('channel') == 'l2Book'
        and record.get('venue_coin') == 'ETH'
        and (mode != 'reconnect' or connections == 2)):
        print('READY', flush=True)
raw.RawWriter._line = line

def fsync(fd):
    if mode == 'fsync-fault':
        raise OSError('fixture fsync failure')
    original_fsync(fd)
    print('FSYNC', flush=True)
raw.os.fsync = fsync

async def receive(writer, coins, *, health_policy=None):
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
                    payload = {'coin': coin, 'time': int(time.time() * 1000) + connections,
                               'bbo': [{'px': '1', 'sz': '2', 'n': 1},
                                       {'px': '2', 'sz': '3', 'n': 1}],
                               'levels': [[{'px': '1', 'sz': '2', 'n': 1}],
                                          [{'px': '2', 'sz': '3', 'n': 1}]]}
                    if channel == 'trades':
                        payload = [{'coin': coin, 'px': '1.2300', 'time': 123}]
                    await ws.send(json.dumps({'channel': channel, 'data': payload}))
            if mode == 'reconnect' and connections == 1:
                await ws.close()
            else:
                await ws.wait_closed()
    async with serve(provider, '127.0.0.1', 0) as server:
        raw.WS_URL = 'ws://127.0.0.1:' + str(server.sockets[0].getsockname()[1])
        await original_receive(writer, coins, health_policy=health_policy)
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

                deadline = time.monotonic() + 20  # Startup allowance; signal-stop budget stays 25s.
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
    assert service["Restart"] == "on-failure" and service["TimeoutStopSec"] == "30"
    assert service["RestartSec"] == "30"
    assert service["RestartPreventExitStatus"] == "74 78"
    assert unit["Unit"]["StartLimitIntervalSec"] == "120"
    assert unit["Unit"]["StartLimitBurst"] == "5"
    assert service["KillSignal"] == "SIGTERM"
    import shlex

    assert shlex.split(service["ExecStart"]) == [
        "/opt/trader-assist-v0/venv/bin/python",
        "/opt/trader-assist-v0/scripts/hyperliquid_raw_capture.py",
        "--continuous",
        "--output",
        "/var/lib/trader-assist-v0-hyperliquid-raw-capture",
    ]
    assert service["StateDirectory"] == "trader-assist-v0-hyperliquid-raw-capture"
    assert service["StateDirectoryMode"] == "0700"
    assert service["ProtectSystem"] == "strict" and service["NoNewPrivileges"] == "yes"
    assert unit["Install"]["WantedBy"] == "multi-user.target"
    assert "WatchdogSec" not in service
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
            "/opt/trader-assist-v0/venv/bin/python is not executable: No such file or directory"
        )
        assert result.returncode == 1 and result.stderr.strip() == diagnostic, result.stderr
    assert not result.stdout.strip(), result.stdout


def test_startup_write_failure_is_not_masked_by_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = raw.RawWriter._release

    def write_failure(self: raw.RawWriter, record: dict[str, Any]) -> None:
        raise OSError("primary startup write failure")

    def cleanup_failure(self: raw.RawWriter) -> None:
        release(self)
        raise OSError("secondary startup cleanup failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(raw.RawWriter, "_line", write_failure)
        scoped.setattr(raw.RawWriter, "_release", cleanup_failure)
        with pytest.raises(OSError, match="primary startup write failure") as exc:
            with raw.RawWriter(tmp_path):
                pass
        assert any("secondary startup cleanup failure" in note for note in exc.value.__notes__)
    with raw.RawWriter(tmp_path):
        pass


def test_rotation_fsync_failure_releases_lock_without_new_segment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(fd: int) -> None:
        raise OSError("rotation fsync failure")

    with monkeypatch.context() as scoped, pytest.raises(OSError, match="rotation fsync"):
        with raw.RawWriter(tmp_path, max_bytes=4096) as writer:
            writer.marker("large", value="x" * 1600)
            writer.max_bytes = writer._size  # Next append must rotate the first segment.
            prefix = writer.paths[0].read_bytes()
            scoped.setattr(raw.os, "fsync", fail)
            writer.marker("rotate")
    assert writer.segment_count == 1 and writer._lock is None
    assert len(list(tmp_path.glob("*.ndjson"))) == 1
    assert writer.paths[0].read_bytes().startswith(prefix)
    assert not any(r.get("event") == "rotate" for r in raw.read_records(writer.paths))
    with raw.RawWriter(tmp_path):
        pass


def eth_frame(channel: str = "l2Book", *, milliseconds: int | None = None) -> dict[str, Any]:
    import time

    sides = [{"px": "2505.5", "sz": "4.4661", "n": 3}, {"px": "2505.6", "sz": "117.3743", "n": 27}]
    return {
        "channel": channel,
        "data": {
            "coin": "ETH",
            "time": int(time.time() * 1000) if milliseconds is None else milliseconds,
            "bbo" if channel == "bbo" else "levels": sides
            if channel == "bbo"
            else [[s] for s in sides],
        },
    }


@pytest.mark.parametrize("channel", ["bbo", "l2Book"])
def test_health_uses_sample_confirmed_epoch_ms_without_mutation(channel: str) -> None:
    # Genuine sample's timestamp/shape; full raw bytes remain in canonical Issue332 evidence.
    frame = eth_frame(channel, milliseconds=1791961752972)
    before = json.dumps(frame)
    assert raw.healthy_eth_time(frame, "2026-10-14T07:09:13.184000Z", 60) == 1791961752972
    assert json.dumps(frame) == before


@pytest.mark.parametrize(
    "fault",
    [
        "null",
        "empty",
        "nan",
        "negative",
        "crossed",
        "count",
        "boolean",
        "seconds",
        "old",
        "future",
        "missing",
    ],
)
def test_invalid_or_implausible_books_never_prove_health(fault: str) -> None:
    frame = eth_frame()
    data = frame["data"]
    if fault == "null":
        frame = eth_frame("bbo")
        frame["data"]["bbo"][0] = None
    elif fault == "empty":
        data["levels"][0] = []
    elif fault == "nan":
        data["levels"][0][0]["px"] = "NaN"
    elif fault == "negative":
        data["levels"][0][0]["sz"] = "-1"
    elif fault == "crossed":
        data["levels"][0][0]["px"] = "9999"
    elif fault == "count":
        data["levels"][0][0]["n"] = True
    elif fault == "boolean":
        data["time"] = True
    elif fault == "seconds":
        data["time"] //= 1000
    elif fault == "old":
        data["time"] -= 61000
    elif fault == "future":
        data["time"] += 6000
    else:
        del data["time"]
    assert raw.healthy_eth_time(frame, raw.utc_now(), 60) is None


def test_progress_requires_advancement_and_bounds_positive_skew(tmp_path: Path) -> None:
    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            state = raw.MarketProgress(writer, raw.HealthPolicy())
            state.connected()
            frame = eth_frame()
            stamp = raw.utc_now()
            assert state.observe(frame, stamp)
            previous = state.last_depth
            assert not state.observe(frame, stamp)
            frame["data"]["time"] -= 1
            assert not state.observe(frame, stamp)
            assert state.last_depth == previous
            state.connected()
            assert not state.observe(frame, stamp)  # reconnect cannot reset watermark
            frame["data"]["time"] += 3000
            assert state.observe(frame, stamp)  # bounded positive skew; no future watermark runaway

    asyncio.run(scenario())


def test_checkpoints_are_atomic_data_only_and_connection_bound(tmp_path: Path) -> None:
    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            state = raw.MarketProgress(writer, raw.HealthPolicy())
            state.connected()
            frame, stamp = eth_frame(), raw.utc_now()
            raw.record_message(writer, frame, stamp, COINS)
            assert state.observe(frame, stamp)
            state.publish()
            path = state.path("l2Book")
            saved = path.read_bytes()
            saved_time = path.stat().st_mtime_ns
            record = json.loads(saved)
            assert record["session_id"] == writer.session and record["connection_epoch"] == 1
            assert record["execution_eligible"] is False
            writer.marker("pong")
            state.publish()
            assert path.read_bytes() == saved and path.stat().st_mtime_ns == saved_time
            assert not list(tmp_path.glob("*.tmp"))
            state.connected()
            assert not path.exists()
            assert not state.observe(frame, stamp)

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["acks", "pongs", "duplicates", "bbo", "backoff", "send"])
def test_depth_stalls_despite_control_or_other_market_activity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    class Socket:
        def __init__(self) -> None:
            self.index = 0
            self.fixed = eth_frame()

        async def send(self, message: str) -> None:
            if mode == "send":
                await asyncio.sleep(1)

        async def recv(self) -> str:
            await asyncio.sleep(0.002)
            self.index += 1
            if self.index <= 6:
                coin, channel = sorted((c, h) for c in COINS for h in raw.CHANNELS)[self.index - 1]
                return json.dumps(
                    {
                        "channel": "subscriptionResponse",
                        "data": {
                            "method": "subscribe",
                            "subscription": {"coin": coin, "type": channel},
                        },
                    }
                )
            if mode == "duplicates":
                return json.dumps(self.fixed)
            if mode == "bbo":
                return json.dumps(eth_frame("bbo"))
            if mode == "acks":
                return json.dumps(
                    {
                        "channel": "subscriptionResponse",
                        "data": {
                            "method": "subscribe",
                            "subscription": {"coin": "ETH", "type": "bbo"},
                        },
                    }
                )
            return json.dumps({"channel": "pong"})

    async def connections() -> Any:
        if mode == "backoff":
            await asyncio.sleep(1)
        yield Socket()

    monkeypatch.setattr(raw, "connect", lambda *a, **kw: connections())

    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            # Internal seam accelerates timer tests; public config still enforces [30,300].
            with pytest.raises(raw.DataStall) as caught:
                await raw.receive_public(writer, COINS, health_policy=raw.HealthPolicy(0.05, 1))
            assert raw.failure_exit_status(caught.value) == 75

    asyncio.run(scenario())
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert any(r.get("event") == "data_stall" for r in records)
    assert any(r.get("event") == "gap_open" and r["missing"] == "UNKNOWN" for r in records)
    assert not list(tmp_path.glob(".eth-*-progress.json"))


def test_quiet_bbo_with_advancing_depth_does_not_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time
    from itertools import pairwise

    milestone = asyncio.Event()
    depth_times: list[int] = []
    original_observe = raw.MarketProgress.observe
    original_warn = raw.MarketProgress.warn_bbo

    def observe(
        state: raw.MarketProgress,
        frame: Any,
        stamp: str,
        received_monotonic: float | None = None,
    ) -> bool:
        advanced = original_observe(state, frame, stamp, received_monotonic)
        if advanced:
            depth_times.append(frame["data"]["time"])
        return advanced

    def warn(state: raw.MarketProgress) -> None:
        if len(depth_times) >= 3:
            # Simulate a quiet BBO interval only; leave the real Depth timer untouched.
            state.last_bbo = min(
                state.last_bbo,
                asyncio.get_running_loop().time() - state.policy.bbo_warning_seconds - 1,
            )
        original_warn(state)
        if len(depth_times) >= 3 and state.bbo_warned:
            milestone.set()

    monkeypatch.setattr(raw.MarketProgress, "observe", observe)
    monkeypatch.setattr(raw.MarketProgress, "warn_bbo", warn)

    class Socket:
        def __init__(self) -> None:
            self.index = 0
            self.last_ms = int(time.time() * 1000)

        async def send(self, message: str) -> None:
            pass

        async def recv(self) -> str:
            await asyncio.sleep(0)
            self.index += 1
            if self.index <= 6:
                coin, channel = sorted((c, h) for c in COINS for h in raw.CHANNELS)[self.index - 1]
                return json.dumps(
                    {
                        "channel": "subscriptionResponse",
                        "data": {
                            "method": "subscribe",
                            "subscription": {"coin": coin, "type": channel},
                        },
                    }
                )
            self.last_ms = max(int(time.time() * 1000), self.last_ms + 1)
            return json.dumps(eth_frame(milliseconds=self.last_ms))

    async def connections() -> Any:
        yield Socket()

    monkeypatch.setattr(raw, "connect", lambda *a, **kw: connections())

    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            task = asyncio.create_task(
                raw.receive_public(writer, COINS, health_policy=raw.HealthPolicy())
            )
            try:
                # Milestone follows successful raw append, real progress validation and warning.
                await asyncio.wait_for(milestone.wait(), timeout=20)
                assert len(depth_times) >= 3
                assert all(later > earlier for earlier, later in pairwise(depth_times))
                assert not task.done()
            finally:
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task

    asyncio.run(scenario())
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert sum(r.get("kind") == "data" and r.get("channel") == "l2Book" for r in records) >= 3
    assert not any(r.get("kind") == "data" and r.get("channel") == "bbo" for r in records)
    assert any(r.get("event") == "bbo_quiet_or_unproven" for r in records)
    assert not any(r.get("event") == "data_stall" for r in records)


@pytest.mark.parametrize("primary", [ValueError("protocol"), raw.DataStall("stale")])
def test_secondary_fsync_storage_wins_preserving_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    primary: Exception,
) -> None:
    def fail(fd: int) -> None:
        raise OSError(28, "fixture full disk")

    with monkeypatch.context() as scoped:
        scoped.setattr(raw.os, "fsync", fail)
        with pytest.raises(type(primary)) as caught:
            with raw.RawWriter(tmp_path):
                raise primary
    assert caught.value is primary
    assert raw.failure_exit_status(primary) == 74
    assert any("finalization" in n for n in primary.__notes__)
    with raw.RawWriter(tmp_path):
        pass


def test_checkpoint_failure_is_storage_not_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any) -> None:
        raise OSError(28, "checkpoint disk full")

    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            state = raw.MarketProgress(writer, raw.HealthPolicy())
            state.connected()
            frame, stamp = eth_frame(), raw.utc_now()
            raw.record_message(writer, frame, stamp, COINS)
            assert state.observe(frame, stamp)
            with monkeypatch.context() as scoped:
                scoped.setattr(raw.os, "replace", fail)
                with pytest.raises(OSError) as caught:
                    state.publish()
                assert raw.failure_exit_status(caught.value) == 74
            assert not state.path("l2Book").exists()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "policy",
    [
        raw.HealthPolicy(29, 300),
        raw.HealthPolicy(301, 300),
        raw.HealthPolicy(60, 59),
        raw.HealthPolicy(60, 901),
        raw.HealthPolicy(float("nan"), 300),
    ],
)
def test_public_policy_bounds_fail_before_writer(tmp_path: Path, policy: raw.HealthPolicy) -> None:
    async def scenario() -> None:
        with pytest.raises(ValueError):
            await raw.capture_continuous(tmp_path, stop=raw.StopIntent(), policy=policy)

    asyncio.run(scenario())
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("restore", [False, True])
def test_continuous_reconnect_requires_acks_and_new_depth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore: bool,
) -> None:
    from websockets.exceptions import ConnectionClosedOK
    from websockets.frames import Close

    first_time = eth_frame()["data"]["time"]
    restored = asyncio.Event()

    class Socket:
        def __init__(self, epoch: int) -> None:
            self.epoch, self.index = epoch, 0

        async def send(self, message: str) -> None:
            pass

        async def recv(self) -> str:
            await asyncio.sleep(0.002)
            self.index += 1
            if self.index <= 6:
                coin, channel = sorted((c, h) for c in COINS for h in raw.CHANNELS)[self.index - 1]
                return json.dumps(
                    {
                        "channel": "subscriptionResponse",
                        "data": {
                            "method": "subscribe",
                            "subscription": {"coin": coin, "type": channel},
                        },
                    }
                )
            if self.index == 7 and (self.epoch == 1 or restore):
                if self.epoch == 2:
                    restored.set()
                return json.dumps(eth_frame(milliseconds=first_time + self.epoch))
            if self.epoch == 1:
                raise ConnectionClosedOK(Close(1000, "fixture"), Close(1000, "fixture"), True)
            return json.dumps({"channel": "pong"})

    async def connections() -> Any:
        yield Socket(1)
        yield Socket(2)

    monkeypatch.setattr(raw, "connect", lambda *a, **kw: connections())

    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            task = asyncio.create_task(
                raw.receive_public(writer, COINS, health_policy=raw.HealthPolicy(0.2, 1))
            )
            if restore:
                await asyncio.wait_for(restored.wait(), timeout=1)
                await asyncio.sleep(0.01)
                assert not task.done()
                checkpoint = json.loads((tmp_path / ".eth-l2Book-progress.json").read_text())
                assert checkpoint["connection_epoch"] == 2
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                with pytest.raises(raw.DataStall):
                    await task

    asyncio.run(scenario())
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert sum(r.get("event") == "ack" for r in records) == 12
    gaps = [r for r in records if r.get("event") == "gap"]
    assert bool(gaps) is restore
    if restore:
        assert gaps[0]["coverage"] == "ETH_DEPTH_ONLY" and gaps[0]["missing"] == "UNKNOWN"


@pytest.mark.parametrize("operation", ["write", "checkpoint_fsync", "close"])
def test_storage_fault_classes_and_lock_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    import errno

    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            if operation == "write":

                def fail(record: dict[str, Any]) -> None:
                    raise OSError(errno.ENOSPC, "fixture bytes/inodes exhausted")

                with monkeypatch.context() as scoped:
                    scoped.setattr(writer, "_line", fail)
                    with pytest.raises(OSError) as caught:
                        writer.marker("fault")
                    assert raw.failure_exit_status(caught.value) == 74
            elif operation == "checkpoint_fsync":
                state = raw.MarketProgress(writer, raw.HealthPolicy())
                state.connected()
                frame, stamp = eth_frame(), raw.utc_now()
                raw.record_message(writer, frame, stamp, COINS)
                state.observe(frame, stamp)

                def fail(fd: int) -> None:
                    raise OSError(errno.EDQUOT, "fixture quota")

                with monkeypatch.context() as scoped:
                    scoped.setattr(raw.os, "fsync", fail)
                    with pytest.raises(OSError) as caught:
                        state.publish()
                    assert raw.failure_exit_status(caught.value) == 74
                    assert not state.path("l2Book").exists()

    if operation == "close":
        primary = ValueError("primary protocol")
        with pytest.raises(ValueError) as caught:
            with raw.RawWriter(tmp_path) as writer:
                source = writer._file

                class File:
                    def __getattr__(self, name: str) -> Any:
                        return getattr(source, name)

                    def close(self) -> None:
                        assert source is not None
                        source.close()
                        raise OSError(errno.EIO, "secondary close")

                writer._file = File()  # type: ignore[assignment]
                raise primary
        assert caught.value is primary and raw.failure_exit_status(primary) == 74
    else:
        asyncio.run(scenario())
    with raw.RawWriter(tmp_path):
        pass


def test_cancel_cleanup_storage_fault_cannot_be_clean_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        stop = raw.StopIntent()

        async def connections() -> Any:
            stop.request()
            await asyncio.sleep(1)
            yield None

        monkeypatch.setattr(raw, "connect", lambda *a, **kw: connections())
        original = raw.MarketProgress.invalidate
        calls = 0

        def invalidate(state: raw.MarketProgress) -> None:
            nonlocal calls
            calls += 1
            if calls > 1:
                with raw.storage_operation("checkpoint cancellation cleanup"):
                    raise OSError(28, "fixture cleanup disk full")
            original(state)

        monkeypatch.setattr(raw.MarketProgress, "invalidate", invalidate)
        with raw.RawWriter(tmp_path) as writer:
            with pytest.raises(OSError) as caught:
                await raw._receive_until_stop(writer, COINS, stop, raw.HealthPolicy())
            assert raw.failure_exit_status(caught.value) == 74

    asyncio.run(scenario())


def test_cli_failure_precedence_and_policy_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "raw_cli_classification", "scripts/hyperliquid_raw_capture.py"
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    for exception, status in (
        (raw.DataStall("stale"), 75),
        (ValueError("protocol"), 78),
        (RuntimeError("unexpected"), 1),
    ):

        async def failing(
            output: Path,
            policy: raw.HealthPolicy,
            error: Exception = exception,
        ) -> Any:
            raise error

        monkeypatch.setattr(cli, "continuous", failing)
        monkeypatch.setattr(sys, "argv", ["cli", "--continuous", "--output", str(tmp_path)])
        assert cli.main() == status
    primary = ValueError("protocol")
    with pytest.raises(OSError) as captured, raw.storage_operation("secondary fsync"):
        raise OSError(28, "full")
    raw.carry_storage_failure(primary, captured.value)

    async def secondary(output: Path, policy: raw.HealthPolicy) -> Any:
        raise primary

    monkeypatch.setattr(cli, "continuous", secondary)
    assert cli.main() == 74
    monkeypatch.setattr(
        sys, "argv", ["cli", "--output", str(tmp_path), "--eth-depth-seconds", "60"]
    )
    with pytest.raises(SystemExit) as caught:
        cli.main()
    assert caught.value.code == 2


def test_disposable_process_crash_preserves_archive_and_releases_flock(tmp_path: Path) -> None:
    code = """
import sys
from pathlib import Path
from trader_assist_v0.hyperliquid_raw_capture import RawWriter
with RawWriter(Path(sys.argv[1])) as writer:
    writer.marker('before_crash')
    print('READY', flush=True)
    sys.stdin.read()
"""
    with subprocess.Popen(
        [sys.executable, "-u", "-c", code, str(tmp_path)],
        env={**os.environ, "PYTHONPATH": str(Path.cwd() / "src")},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as child:
        try:
            import select

            assert child.stdout is not None
            assert select.select([child.stdout], [], [], 10)[0]
            assert child.stdout.readline().strip() == "READY"
            before = {p: p.read_bytes() for p in tmp_path.glob("*.ndjson")}
            child.kill()  # Only this disposable fixture, never a host service.
            child.communicate(timeout=5)
            assert child.returncode != 0
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
    with raw.RawWriter(tmp_path) as writer:
        writer.marker("after_crash", previous_coverage="UNKNOWN")
    assert all(p.read_bytes() == content for p, content in before.items())
    assert not set(writer.paths).intersection(before)
    records = list(raw.read_records(list(before)))
    assert any(r.get("event") == "before_crash" for r in records)
    assert not any(r.get("event") == "stop" for r in records)


def test_prior_session_checkpoints_removed_before_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for channel in ("bbo", "l2Book"):
        (tmp_path / f".eth-{channel}-progress.json").write_text('{"session_id":"old"}')

    async def discovery(stop: raw.StopIntent) -> None:
        assert not list(tmp_path.glob(".eth-*-progress.json"))
        stop.request()
        return None

    monkeypatch.setattr(raw, "_discover_continuous", discovery)

    async def scenario() -> None:
        result = await raw.capture_continuous(tmp_path, stop=raw.StopIntent())
        assert result["termination"] == "clean_requested_stop"

    asyncio.run(scenario())


def test_slow_raw_append_cannot_retroactively_refresh_expired_depth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    original = raw.RawWriter._line

    def delayed(writer: raw.RawWriter, record: dict[str, Any]) -> None:
        original(writer, record)
        if record.get("kind") == "data":
            time.sleep(0.05)  # Disposable fault injection; no service is involved.

    monkeypatch.setattr(raw.RawWriter, "_line", delayed)

    class Socket:
        async def send(self, message: str) -> None:
            pass

        async def recv(self) -> str:
            return json.dumps(eth_frame())

    async def connections() -> Any:
        yield Socket()

    monkeypatch.setattr(raw, "connect", lambda *a, **kw: connections())

    async def scenario() -> None:
        with raw.RawWriter(tmp_path) as writer:
            with pytest.raises(raw.DataStall):
                await raw.receive_public(writer, COINS, health_policy=raw.HealthPolicy(0.03, 1))

    asyncio.run(scenario())
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert any(r.get("kind") == "data" for r in records)  # genuine received frame retained
    assert any(r.get("event") == "data_stall" for r in records)
    assert not list(tmp_path.glob(".eth-*-progress.json"))


@pytest.mark.parametrize("data", [None, [], {"subscription": None}, {"subscription": []}])
def test_malformed_ack_is_protocol_failure(tmp_path: Path, data: Any) -> None:
    with raw.RawWriter(tmp_path) as writer:
        with pytest.raises(ValueError) as caught:
            raw.record_message(
                writer, {"channel": "subscriptionResponse", "data": data}, STAMP, COINS
            )
        assert raw.failure_exit_status(caught.value) == 78


@pytest.mark.parametrize("http_status,exit_status", [(401, 78), (408, 75), (429, 75), (503, 75)])
def test_websocket_http_failure_classification(http_status: int, exit_status: int) -> None:
    from websockets.datastructures import Headers
    from websockets.exceptions import InvalidStatus
    from websockets.http11 import Response

    failure = InvalidStatus(Response(http_status, "fixture", Headers()))
    assert raw.failure_exit_status(failure) == exit_status
