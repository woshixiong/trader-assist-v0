from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import inspect
import json
import os
import stat
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest

import trader_assist_v0.runtime.eth_public_capture as runtime
from scripts.run_eth_public_capture import _parser
from trader_assist_v0.contracts.events import RawCaptureModeV0, ReplayStatusV0
from trader_assist_v0.data.bronze import BronzeStore, read_manifest_entries
from trader_assist_v0.data.ingress import ingest_t2_eth_public_candle_bytes

BASE_SHA = "16963297e0ce27ed3919f52e1e536ff730f5a5b9"
ALLOWLIST = {
    "CODEX.md",
    "docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md",
    "pyproject.toml",
    "requirements-dev.lock",
    "requirements-runtime.lock",
    "scripts/run_eth_public_capture.py",
    "src/trader_assist_v0/data/ingress.py",
    "src/trader_assist_v0/runtime/__init__.py",
    "src/trader_assist_v0/runtime/eth_public_capture.py",
    "tests/test_v0_t2_eth_public_capture_runtime.py",
}
IMMUTABLE_HASHES = {
    "governance/V0_FAST_LAUNCH_PROGRAM.json": (
        "0f8a3837ffdef896f66f1cc7719f29190dd2f620a8327b641a256d6923a6f224"
    ),
    "governance/PROJECT_STATE.json": (
        "1e9d69439cb52075ea98064f98fabb6aadf0ea8d9d15cc75485f224d983f90c3"
    ),
    "schemas/governance/V0FastLaunchProgram.schema.json": (
        "aa2eca7cba7e96f63ab307b1f2fd50576a05682e47efa353bd6a89a7e557c0e1"
    ),
    "tests/test_v0_fast_launch_governance_state.py": (
        "b02f00bca6a0e200b818784fad95a02f7cef2dc407da07999725d84ace5f6659"
    ),
}


def _run(*arguments: str, cwd: Path) -> bytes:
    return subprocess.run(
        arguments,
        cwd=cwd,
        check=True,
        capture_output=True,
    ).stdout


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run("git", "init", "-q", cwd=repo)
    _run("git", "config", "user.email", "capture-test@example.invalid", cwd=repo)
    _run("git", "config", "user.name", "Capture Test", cwd=repo)
    (repo / "authority.txt").write_text("T2\n", encoding="utf-8")
    _run("git", "add", "authority.txt", cwd=repo)
    _run("git", "commit", "-q", "-m", "test authority", cwd=repo)
    return repo, _run("git", "rev-parse", "HEAD", cwd=repo).decode().strip()


def _permit(
    tmp_path: Path,
    sha: str,
    *,
    document: dict[str, object] | None = None,
    raw: str | None = None,
) -> Path:
    permit_dir = tmp_path / "permits"
    permit_dir.mkdir(exist_ok=True)
    path = permit_dir / "start.json"
    values = document or {
        "task_id": runtime.TASK_ID,
        "permit_id": "manual-start-1",
        "expected_git_sha": sha,
    }
    path.write_text(
        raw if raw is not None else json.dumps(values, separators=(",", ":")),
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def _storage(tmp_path: Path) -> Path:
    anchor = tmp_path / "bronze-authority"
    anchor.mkdir()
    root = anchor / "bronze"
    root.mkdir()
    lock = anchor / ".bronze-global-observation-authority.lock"
    lock.touch()
    lock.chmod(0o600)
    anchor.chmod(0o555)
    return root


@pytest.fixture(autouse=True)
def _restore_directory_permissions(tmp_path: Path):
    yield
    for path in sorted(
        (item for item in tmp_path.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        with contextlib.suppress(FileNotFoundError):
            path.chmod(0o700)


def _ack(interval: str) -> str:
    return json.dumps(
        {
            "channel": "subscriptionResponse",
            "data": {
                "method": "subscribe",
                "subscription": {"type": "candle", "coin": "ETH", "interval": interval},
            },
        },
        separators=(",", ":"),
    )


class FakeWebSocket:
    def __init__(
        self,
        frames: list[object],
        stop_event: asyncio.Event,
        *,
        stop_on_empty: bool = True,
    ) -> None:
        self.frames = frames
        self.stop_event = stop_event
        self.stop_on_empty = stop_on_empty
        self.sent: list[str] = []
        self.close_count = 0

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str | bytes:
        if self.frames:
            frame = self.frames.pop(0)
            if isinstance(frame, BaseException):
                raise frame
            return cast(str | bytes, frame)
        if self.stop_on_empty:
            self.stop_event.set()
        await asyncio.Future()
        raise AssertionError("unreachable")

    async def close(self) -> None:
        self.close_count += 1


class FakeConnector:
    def __init__(self, websocket: FakeWebSocket, *, enter_error: BaseException | None = None):
        self.websocket = websocket
        self.enter_error = enter_error
        self.attempts = 0
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def __call__(self, *args: object, **kwargs: object) -> FakeConnector:
        self.attempts += 1
        self.calls.append((args, kwargs))
        return self

    async def __aenter__(self) -> FakeWebSocket:
        if self.enter_error is not None:
            raise self.enter_error
        return self.websocket

    async def __aexit__(self, *_args: object) -> None:
        await self.websocket.close()


def _capture(
    tmp_path: Path,
    frames: list[object],
    *,
    connector: FakeConnector | None = None,
    stop_event: asyncio.Event | None = None,
    wait_for: Callable[[Awaitable[Any], float], Awaitable[Any]] | None = None,
    monotonic: Callable[[], float] | None = None,
) -> tuple[runtime.CaptureRunResult, FakeConnector, Path, Path]:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    storage = _storage(tmp_path)
    stop = stop_event or asyncio.Event()
    websocket = connector.websocket if connector is not None else FakeWebSocket(frames, stop)
    active_connector = connector or FakeConnector(websocket)
    kwargs: dict[str, Any] = {}
    if wait_for is not None:
        kwargs["_wait_for"] = wait_for
    if monotonic is not None:
        kwargs["_monotonic"] = monotonic
    result = asyncio.run(
        runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=active_connector,
            _stop_event=stop,
            **kwargs,
        )
    )
    return result, active_connector, storage, permit


@pytest.mark.parametrize(
    "case",
    (
        "missing",
        "malformed",
        "duplicate",
        "extra",
        "wrong_task",
        "wrong_sha",
        "dirty",
        "symlink",
        "permissions",
    ),
)
def test_permit_rejections_happen_before_connect(tmp_path: Path, case: str) -> None:
    repo, sha = _repo(tmp_path)
    permit = tmp_path / "permits" / "start.json"
    if case != "missing":
        if case == "malformed":
            permit = _permit(tmp_path, sha, raw="{bad")
        elif case == "duplicate":
            permit = _permit(
                tmp_path,
                sha,
                raw=(
                    '{"task_id":"x","task_id":"y","permit_id":"p",'
                    f'"expected_git_sha":"{sha}"}}'
                ),
            )
        elif case == "extra":
            permit = _permit(tmp_path, sha, document={
                "task_id": runtime.TASK_ID,
                "permit_id": "p",
                "expected_git_sha": sha,
                "extra": False,
            })
        elif case == "wrong_task":
            permit = _permit(tmp_path, sha, document={
                "task_id": "OTHER",
                "permit_id": "p",
                "expected_git_sha": sha,
            })
        elif case == "wrong_sha":
            permit = _permit(tmp_path, sha, document={
                "task_id": runtime.TASK_ID,
                "permit_id": "p",
                "expected_git_sha": "0" * 40,
            })
        elif case == "dirty":
            permit = _permit(tmp_path, sha)
            (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
        elif case == "symlink":
            target = _permit(tmp_path, sha)
            target.rename(target.with_name("target.json"))
            permit.symlink_to(target.with_name("target.json"))
        else:
            permit = _permit(tmp_path, sha)
            permit.chmod(0o640)

    attempts = 0

    def forbidden_connect(*_args: object, **_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        raise AssertionError("connect must not be called")

    with pytest.raises(runtime.PermitError):
        asyncio.run(
            runtime.run_eth_public_capture(
                storage_root=tmp_path / "unused",
                permit_path=permit,
                _repo_root=repo,
                _connect_factory=forbidden_connect,
                _stop_event=asyncio.Event(),
            )
        )
    assert attempts == 0
    if case in {"wrong_task", "wrong_sha", "dirty"}:
        assert not permit.exists()
        assert tuple(permit.parent.glob("start.json.consumed-*"))


def test_permit_wrong_owner_is_rejected_where_safely_testable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    effective_uid = os.geteuid()
    monkeypatch.setattr(runtime.os, "geteuid", lambda: effective_uid + 1)
    with pytest.raises(runtime.PermitError, match="owned"):
        runtime.consume_start_permit(permit, repo_root=repo)


def test_permit_is_atomically_consumed_and_parent_is_fsynced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    real_fsync = os.fsync
    fsynced_directory = False

    def record_fsync(fd: int) -> None:
        nonlocal fsynced_directory
        fsynced_directory |= stat.S_ISDIR(os.fstat(fd).st_mode)
        real_fsync(fd)

    monkeypatch.setattr(runtime.os, "fsync", record_fsync)
    consumed = runtime.consume_start_permit(permit, repo_root=repo)
    assert not permit.exists()
    assert consumed.consumed_path.parent == permit.parent
    assert consumed.consumed_path.is_file()
    assert fsynced_directory


def test_one_attempt_consumes_permit_before_failed_connect_and_cannot_reuse(
    tmp_path: Path,
) -> None:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    storage = _storage(tmp_path)
    stop = asyncio.Event()
    websocket = FakeWebSocket([], stop)
    connector = FakeConnector(websocket, enter_error=OSError("offline"))
    with pytest.raises(OSError, match="offline"):
        asyncio.run(runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=connector,
            _stop_event=stop,
        ))
    assert connector.attempts == 1
    assert not permit.exists()
    with pytest.raises(runtime.PermitError):
        asyncio.run(runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=connector,
            _stop_event=stop,
        ))
    assert connector.attempts == 1


def test_fixed_single_connection_flow_persists_original_object_and_array_bytes(
    tmp_path: Path,
) -> None:
    object_frame = '{ "channel": "candle", "data": { "s": "ETH", "i": "5m" } }'
    array_frame = '{"channel":"candle","data":[{"s":"ETH","i":"15m"}]}'
    result, connector, storage, permit = _capture(
        tmp_path,
        [_ack("5m"), _ack("15m"), object_frame, array_frame],
    )
    assert connector.attempts == 1
    assert connector.calls == [
        ((runtime.WEBSOCKET_URL,), {"proxy": None, "ping_interval": None})
    ]
    assert connector.websocket.sent[:2] == [runtime.SUBSCRIBE_5M, runtime.SUBSCRIBE_15M]
    assert connector.websocket.close_count >= 1
    assert result.entries_checked == 2
    assert not permit.exists()
    with pytest.raises(runtime.PermitError):
        runtime.consume_start_permit(permit, repo_root=tmp_path / "repo")

    store = BronzeStore(storage)
    entries = read_manifest_entries(
        store,
        date.fromisoformat(result.manifest_date),
        result.segment_id,
    )
    assert [entry.raw_event.receive_sequence for entry in entries] == [1, 2]
    assert [entry.raw_event.subscription_id for entry in entries] == [
        "eth-candle-5m",
        "eth-candle-15m",
    ]
    assert all(entry.raw_event.connection_id == result.connection_id for entry in entries)
    assert all(entry.raw_event.operation_type == "candle" for entry in entries)
    assert all(entry.raw_event.coin == "ETH" for entry in entries)
    assert all(
        entry.raw_event.capture_mode is RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD
        for entry in entries
    )
    assert store.read_bytes(entries[0].raw_event.payload_ref) == object_frame.encode()
    assert store.read_bytes(entries[1].raw_event.payload_ref) == array_frame.encode()
    replay = runtime.replay_segment(
        store,
        manifest_date=entries[0].raw_event.collector_receive_time.date(),
        segment_id=result.segment_id,
    )
    assert replay.status is ReplayStatusV0.PASS


@pytest.mark.parametrize(
    "frames,error",
    (
        ([_ack("5m"), _ack("5m")], runtime.AcknowledgementError),
        ([_ack("5m"), _ack("1m")], runtime.AcknowledgementError),
        ([b"binary"], runtime.FrameValidationError),
        (["{bad"], runtime.AcknowledgementError),
        ([json.dumps({"channel": "candle", "data": {"s": "ETH", "i": "5m"}})],
         runtime.AcknowledgementError),
        ([_ack("5m"), ConnectionError("disconnect")], ConnectionError),
    ),
)
def test_acknowledgement_failures_close_without_reconnect(
    tmp_path: Path,
    frames: list[object],
    error: type[BaseException],
) -> None:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    storage = _storage(tmp_path)
    stop = asyncio.Event()
    websocket = FakeWebSocket(frames, stop, stop_on_empty=False)
    connector = FakeConnector(websocket)
    with pytest.raises(error):
        asyncio.run(runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=connector,
            _stop_event=stop,
        ))
    assert connector.attempts == 1
    assert websocket.close_count >= 1


async def _immediate_timeout(awaitable: Awaitable[Any], _timeout: float) -> Any:
    cast(Any, awaitable).close()
    raise TimeoutError


def test_acknowledgement_timeout_closes_without_reconnect(tmp_path: Path) -> None:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    storage = _storage(tmp_path)
    stop = asyncio.Event()
    websocket = FakeWebSocket([], stop, stop_on_empty=False)
    connector = FakeConnector(websocket)
    with pytest.raises(runtime.AcknowledgementTimeout):
        asyncio.run(runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=connector,
            _stop_event=stop,
            _wait_for=_immediate_timeout,
        ))
    assert connector.attempts == 1
    assert websocket.close_count >= 1


@dataclass
class FakeClock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value


class HeartbeatDriver:
    def __init__(
        self,
        websocket: FakeWebSocket,
        stop_event: asyncio.Event,
        clock: FakeClock,
        *,
        pong: str | None,
        late: bool = False,
        graceful_after_two_pings: bool = False,
    ) -> None:
        self.websocket = websocket
        self.stop_event = stop_event
        self.clock = clock
        self.pong = pong
        self.late = late
        self.graceful_after_two_pings = graceful_after_two_pings
        self.timeouts = 0

    async def __call__(self, awaitable: Awaitable[Any], timeout: float) -> Any:
        if self.websocket.frames:
            result = await awaitable
            if self.late and self.timeouts:
                self.clock.value += timeout
            return result
        if self.graceful_after_two_pings and self.timeouts >= 2:
            self.stop_event.set()
            return await awaitable
        self.timeouts += 1
        self.clock.value += timeout
        cast(Any, awaitable).close()
        if self.timeouts == 1 and self.pong is not None:
            self.websocket.frames.append(self.pong)
        raise TimeoutError


def _heartbeat_case(
    tmp_path: Path,
    *,
    pong: str | None,
    late: bool = False,
    graceful: bool = False,
) -> tuple[FakeConnector, HeartbeatDriver, Callable[[], runtime.CaptureRunResult]]:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    storage = _storage(tmp_path)
    stop = asyncio.Event()
    websocket = FakeWebSocket([_ack("5m"), _ack("15m")], stop, stop_on_empty=False)
    connector = FakeConnector(websocket)
    clock = FakeClock()
    driver = HeartbeatDriver(
        websocket,
        stop,
        clock,
        pong=pong,
        late=late,
        graceful_after_two_pings=graceful,
    )

    def invoke() -> runtime.CaptureRunResult:
        return asyncio.run(runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=connector,
            _stop_event=stop,
            _monotonic=clock,
            _wait_for=driver,
        ))

    return connector, driver, invoke


def test_application_ping_every_30_seconds_and_valid_pong(tmp_path: Path) -> None:
    connector, driver, invoke = _heartbeat_case(
        tmp_path,
        pong='{"channel":"pong"}',
        graceful=True,
    )
    invoke()
    assert driver.timeouts == 2
    assert connector.websocket.sent == [
        runtime.SUBSCRIBE_5M,
        runtime.SUBSCRIBE_15M,
        runtime.APPLICATION_PING,
        runtime.APPLICATION_PING,
    ]
    assert connector.calls[0][1]["ping_interval"] is None


@pytest.mark.parametrize(
    "pong,late,error",
    (
        (None, False, runtime.HeartbeatTimeout),
        ('{"channel":"pong","extra":true}', False, runtime.HeartbeatError),
        ('{"channel":"pong"}', True, runtime.HeartbeatTimeout),
    ),
)
def test_missing_malformed_or_late_pong_fails_closed(
    tmp_path: Path,
    pong: str | None,
    late: bool,
    error: type[BaseException],
) -> None:
    connector, _driver, invoke = _heartbeat_case(tmp_path, pong=pong, late=late)
    with pytest.raises(error):
        invoke()
    assert connector.attempts == 1
    assert connector.websocket.close_count >= 1


@pytest.mark.parametrize(
    "frame",
    (
        '{"channel":"candle","data":{"s":"BTC","i":"5m"}}',
        '{"channel":"candle","data":{"s":"ETH","i":"1m"}}',
        '{"channel":"trades","data":[]}',
        '{"channel":"candle","data":[]}',
        '{"channel":"candle","data":{"s":"ETH","i":"5m","x":NaN}}',
        '{"channel":"candle","channel":"candle","data":{"s":"ETH","i":"5m"}}',
        "\ud800",
        b"binary",
    ),
)
def test_invalid_candle_frames_fail_closed(tmp_path: Path, frame: object) -> None:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    storage = _storage(tmp_path)
    stop = asyncio.Event()
    websocket = FakeWebSocket([_ack("5m"), _ack("15m"), frame], stop)
    connector = FakeConnector(websocket)
    with pytest.raises(runtime.FrameValidationError):
        asyncio.run(runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=connector,
            _stop_event=stop,
        ))
    assert connector.attempts == 1
    assert not tuple(storage.rglob("*.checkpoint.json"))


def test_t2_ingress_requires_consumed_proof() -> None:
    with pytest.raises(ValueError, match="proof"):
        ingest_t2_eth_public_candle_bytes(
            payload=b"{}",
            consumed_permit=cast(Any, None),
            candle_interval="5m",
            connection_id="connection",
            subscription_id="eth-candle-5m",
            receive_sequence=1,
            first_observed_time=runtime.datetime.now(runtime.UTC),
            collector_receive_time=runtime.datetime.now(runtime.UTC),
            collector_monotonic_ns=1,
            store=cast(Any, None),
            writer=cast(Any, None),
        )


def test_persistence_uncertainty_prevents_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, sha = _repo(tmp_path)
    permit = _permit(tmp_path, sha)
    storage = _storage(tmp_path)
    stop = asyncio.Event()
    websocket = FakeWebSocket([
        _ack("5m"),
        _ack("15m"),
        '{"channel":"candle","data":{"s":"ETH","i":"5m"}}',
    ], stop)
    connector = FakeConnector(websocket)

    def fail_persistence(**_kwargs: object) -> None:
        raise OSError("persistence uncertain")

    monkeypatch.setattr(runtime, "ingest_t2_eth_public_candle_bytes", fail_persistence)
    with pytest.raises(OSError, match="persistence uncertain"):
        asyncio.run(runtime.run_eth_public_capture(
            storage_root=storage,
            permit_path=permit,
            _repo_root=repo,
            _connect_factory=connector,
            _stop_event=stop,
        ))
    assert not tuple(storage.rglob("*.checkpoint.json"))


def test_cli_runtime_and_repository_boundaries_are_exact() -> None:
    parser = _parser()
    options = {
        option
        for action in parser._actions
        for option in action.option_strings
        if option not in {"-h", "--help"}
    }
    assert options == {"--storage-root", "--permit"}

    root = Path(__file__).resolve().parents[1]
    source = (root / "src/trader_assist_v0/runtime/eth_public_capture.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported.isdisjoint({"requests", "httpx", "aiohttp", "boto3"})
    lowered = source.lower()
    for prohibited in (
        "candlesnapshot",
        "api_key",
        "private_key",
        "wallet",
        "signing",
        "nonce",
        "order_submission",
        "tradeplan",
        "strategy",
    ):
        assert prohibited not in lowered

    for relative, expected in IMMUTABLE_HASHES.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
    changed = set(
        _run("git", "diff", "--name-only", BASE_SHA, cwd=root).decode().splitlines()
    )
    changed.update(
        _run("git", "ls-files", "--others", "--exclude-standard", cwd=root)
        .decode()
        .splitlines()
    )
    assert changed == ALLOWLIST

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert pyproject.count('"websockets==16.1"') == 1
    assert "websockets==16.1" in (root / "requirements-runtime.lock").read_text()
    assert "websockets==16.1" in (root / "requirements-dev.lock").read_text()
    assert "connect(" not in inspect.getsource(runtime._run_connected)
