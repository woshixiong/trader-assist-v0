from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import re
import secrets
import signal
import stat
import subprocess
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Protocol, cast
from uuid import uuid4

from websockets.asyncio.client import connect

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.contracts.events import ReplayStatusV0
from trader_assist_v0.data.bronze import BronzeStore, ManifestWriter
from trader_assist_v0.data.ingress import (
    _issue_t2_consumed_permit_proof,
    _T2ConsumedPermitProof,
    ingest_t2_eth_public_candle_bytes,
)
from trader_assist_v0.data.replay import replay_segment

TASK_ID: Final[Literal["V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME"]] = (
    "V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME"
)
WEBSOCKET_URL = "wss://api.hyperliquid.xyz/ws"
ACKNOWLEDGEMENT_DEADLINE_SECONDS = 30.0
HEARTBEAT_INTERVAL_SECONDS = 30.0
SUBSCRIBE_5M = (
    '{"method":"subscribe","subscription":{"type":"candle","coin":"ETH",'
    '"interval":"5m"}}'
)
SUBSCRIBE_15M = (
    '{"method":"subscribe","subscription":{"type":"candle","coin":"ETH",'
    '"interval":"15m"}}'
)
APPLICATION_PING = '{"method":"ping"}'
SERVER_GREETING = "Websocket connection established."
RECEIPT_VERSION = "1.0.0"
SUBSCRIPTION_IDS: dict[str, str] = {
    "5m": "eth-candle-5m",
    "15m": "eth-candle-15m",
}
_PERMIT_FIELDS = {"task_id", "permit_id", "expected_git_sha"}
_PERMIT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_RECEIPT_DOMAIN = b"trader-assist-v0/t2-permit-receipt/v1"
_RECEIPT_AUTHORITY_DIRECTORY = "trader-assist-v0"
_RECEIPT_DIRECTORY = "t2-permit-receipts"
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_STOP = object()


class CaptureRuntimeError(RuntimeError):
    pass


class PermitError(CaptureRuntimeError):
    pass


class AcknowledgementError(CaptureRuntimeError):
    pass


class AcknowledgementTimeout(CaptureRuntimeError):
    pass


class HeartbeatError(CaptureRuntimeError):
    pass


class HeartbeatTimeout(CaptureRuntimeError):
    pass


class FrameValidationError(CaptureRuntimeError):
    pass


class ReplayIntegrityError(CaptureRuntimeError):
    pass


class _DeadlineExpired(TimeoutError):
    pass


class WebSocketConnection(Protocol):
    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


@dataclass(frozen=True)
class ConsumedStartPermit:
    task_id: Literal["V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME"]
    permit_id: str
    expected_git_sha: str
    consumed_path: Path
    receipt_path: Path
    receipt_sha256: str
    ingress_proof: _T2ConsumedPermitProof


@dataclass(frozen=True)
class CaptureRunResult:
    permit_id: str
    consumed_permit_path: Path
    connection_id: str
    manifest_date: str
    segment_id: str
    replay_report_hash: str
    entries_checked: int


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON value is prohibited: {value}")


def _strict_json(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_non_finite,
    )


def _read_permit_json(fd: int) -> dict[str, str]:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 64 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
        if sum(map(len, chunks)) > 16 * 1024:
            raise PermitError("start permit exceeds the bounded JSON size")
    try:
        decoded = b"".join(chunks).decode("utf-8", errors="strict")
        document = _strict_json(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PermitError("start permit is not strict UTF-8 JSON") from exc
    if type(document) is not dict or set(document) != _PERMIT_FIELDS:
        raise PermitError("start permit must contain exactly the three authorized fields")
    if any(type(document[field]) is not str for field in _PERMIT_FIELDS):
        raise PermitError("start permit fields must be exact strings")
    return cast(dict[str, str], document)


def _git_output(repo_root: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PermitError("repository authority validation failed") from exc
    return completed.stdout


def _validate_permit_document(document: dict[str, str]) -> None:
    if document["task_id"] != TASK_ID:
        raise PermitError("start permit task_id does not match the T2 runtime")
    if _PERMIT_ID_RE.fullmatch(document["permit_id"]) is None:
        raise PermitError("start permit permit_id is not a bounded identifier")
    expected_sha = document["expected_git_sha"]
    if _SHA_RE.fullmatch(expected_sha) is None:
        raise PermitError("start permit expected_git_sha is not a lowercase commit SHA")


def _validate_repository_state(document: dict[str, str], repo_root: Path) -> None:
    expected_sha = document["expected_git_sha"]
    head = _git_output(repo_root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if head != expected_sha:
        raise PermitError("start permit expected_git_sha does not match repository HEAD")
    if _git_output(repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise PermitError("repository worktree must be clean before T2 Capture")


def _git_common_directory(repo_root: Path) -> Path:
    try:
        raw = _git_output(repo_root, "rev-parse", "--git-common-dir").decode(
            "utf-8", errors="strict"
        ).strip()
    except UnicodeDecodeError as exc:
        raise PermitError("Git common-directory authority is not UTF-8") from exc
    if not raw or "\x00" in raw:
        raise PermitError("Git common-directory authority is empty or malformed")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        metadata = candidate.lstat()
    except FileNotFoundError as exc:
        raise PermitError("Git common directory is missing") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise PermitError("Git common directory must be an exact directory")
    return candidate.resolve(strict=True)


def _open_private_directory(parent_fd: int, name: str) -> int:
    created = False
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
    except FileExistsError:
        pass
    except OSError as exc:
        raise PermitError("durable permit-receipt directory could not be created") from exc

    try:
        path_metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise PermitError("durable permit-receipt directory cannot be inspected") from exc
    if stat.S_ISLNK(path_metadata.st_mode) or not stat.S_ISDIR(path_metadata.st_mode):
        raise PermitError("durable permit-receipt authority must be an exact directory")
    try:
        directory_fd = os.open(name, os.O_RDONLY | _DIRECTORY | _NOFOLLOW, dir_fd=parent_fd)
    except OSError as exc:
        raise PermitError("durable permit-receipt directory cannot be opened safely") from exc
    try:
        if created:
            os.fchmod(directory_fd, 0o700)
        opened = os.fstat(directory_fd)
        if (opened.st_dev, opened.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise PermitError("durable permit-receipt directory identity changed")
        if opened.st_uid != os.geteuid():
            raise PermitError("durable permit-receipt directory has the wrong owner")
        if stat.S_IMODE(opened.st_mode) != 0o700:
            raise PermitError("durable permit-receipt directory mode must be exactly 0700")
        if created:
            os.fsync(parent_fd)
        return directory_fd
    except BaseException:
        os.close(directory_fd)
        raise


def _receipt_filename(permit_id: str) -> str:
    digest = hashlib.sha256(
        _RECEIPT_DOMAIN + b"\0" + TASK_ID.encode("utf-8") + b"\0" + permit_id.encode("utf-8")
    ).hexdigest()
    return f"{digest}.json"


def _canonical_receipt_bytes(document: dict[str, str]) -> bytes:
    return canonical_json_bytes(
        {
            "receipt_version": RECEIPT_VERSION,
            "task_id": TASK_ID,
            "permit_id": document["permit_id"],
            "expected_git_sha": document["expected_git_sha"],
        }
    )


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short durable receipt write")
        view = view[written:]


def _read_bounded_file(fd: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > 16 * 1024:
            raise PermitError("durable permit receipt exceeds its bounded size")
        chunks.append(chunk)


def _reject_existing_receipt(
    receipt_directory_fd: int,
    filename: str,
    expected_bytes: bytes,
) -> None:
    try:
        receipt_fd = os.open(filename, os.O_RDONLY | _NOFOLLOW, dir_fd=receipt_directory_fd)
    except OSError as exc:
        raise PermitError("existing durable permit receipt is not a regular file") from exc
    try:
        metadata = os.fstat(receipt_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise PermitError("existing durable permit receipt is not a regular file")
        if metadata.st_uid != os.geteuid():
            raise PermitError("existing durable permit receipt has the wrong owner")
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            raise PermitError("existing durable permit receipt mode must be exactly 0600")
        existing_bytes = _read_bounded_file(receipt_fd)
    finally:
        os.close(receipt_fd)
    if existing_bytes != expected_bytes:
        raise PermitError("existing durable permit receipt is malformed or conflicting")
    raise PermitError("start permit_id has already been consumed in this Git repository family")


def _create_durable_receipt(
    document: dict[str, str],
    *,
    repo_root: Path,
) -> tuple[Path, bytes]:
    common_directory = _git_common_directory(repo_root)
    try:
        common_fd = os.open(common_directory, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)
    except OSError as exc:
        raise PermitError("Git common directory cannot be opened safely") from exc
    authority_fd = -1
    receipts_fd = -1
    try:
        authority_fd = _open_private_directory(common_fd, _RECEIPT_AUTHORITY_DIRECTORY)
        receipts_fd = _open_private_directory(authority_fd, _RECEIPT_DIRECTORY)
        filename = _receipt_filename(document["permit_id"])
        receipt_bytes = _canonical_receipt_bytes(document)
        try:
            receipt_fd = os.open(
                filename,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                0o600,
                dir_fd=receipts_fd,
            )
        except FileExistsError:
            _reject_existing_receipt(receipts_fd, filename, receipt_bytes)
            raise AssertionError("existing receipt rejection must raise") from None
        except OSError as exc:
            raise PermitError("durable permit receipt could not be created atomically") from exc
        receipt_error: BaseException | None = None
        try:
            os.fchmod(receipt_fd, 0o600)
            metadata = os.fstat(receipt_fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise PermitError("new durable permit receipt is not a regular file")
            if metadata.st_uid != os.geteuid():
                raise PermitError("new durable permit receipt has the wrong owner")
            if stat.S_IMODE(metadata.st_mode) != 0o600:
                raise PermitError("new durable permit receipt mode must be exactly 0600")
            _write_all(receipt_fd, receipt_bytes)
            os.fsync(receipt_fd)
        except BaseException as exc:
            receipt_error = exc
        finally:
            try:
                os.close(receipt_fd)
            except OSError as exc:
                if receipt_error is None:
                    receipt_error = exc
        try:
            os.fsync(receipts_fd)
        except OSError as exc:
            raise PermitError("durable permit receipt directory could not be fsynced") from exc
        if receipt_error is not None:
            if isinstance(receipt_error, PermitError):
                raise receipt_error
            if isinstance(receipt_error, OSError):
                raise PermitError(
                    "durable permit receipt could not be written durably"
                ) from receipt_error
            raise receipt_error
        receipt_path = (
            common_directory
            / _RECEIPT_AUTHORITY_DIRECTORY
            / _RECEIPT_DIRECTORY
            / filename
        )
        return receipt_path, receipt_bytes
    finally:
        if receipts_fd >= 0:
            os.close(receipts_fd)
        if authority_fd >= 0:
            os.close(authority_fd)
        os.close(common_fd)


def consume_start_permit(permit_path: Path, *, repo_root: Path) -> ConsumedStartPermit:
    if _NOFOLLOW == 0 or _DIRECTORY == 0:
        raise PermitError("start permits require O_NOFOLLOW and O_DIRECTORY support")
    try:
        parent = permit_path.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PermitError("start permit parent directory is missing") from exc
    name = permit_path.name
    if not name or name in {".", ".."}:
        raise PermitError("start permit path must name one file")
    try:
        parent_fd = os.open(parent, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)
    except OSError as exc:
        raise PermitError("start permit parent directory is not authoritative") from exc
    permit_fd = -1
    try:
        try:
            path_metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if stat.S_ISLNK(path_metadata.st_mode) or not stat.S_ISREG(
                path_metadata.st_mode
            ):
                raise PermitError("start permit must be an exact regular file, not a symlink")
            permit_fd = os.open(name, os.O_RDONLY | _NOFOLLOW, dir_fd=parent_fd)
            opened = os.fstat(permit_fd)
        except PermitError:
            raise
        except FileNotFoundError as exc:
            raise PermitError("start permit is missing") from exc
        except OSError as exc:
            raise PermitError("start permit cannot be opened without following links") from exc
        if not stat.S_ISREG(opened.st_mode):
            raise PermitError("start permit must remain a regular file")
        if (opened.st_dev, opened.st_ino) != (path_metadata.st_dev, path_metadata.st_ino):
            raise PermitError("start permit identity changed during validation")
        if stat.S_IMODE(opened.st_mode) != 0o600:
            raise PermitError("start permit mode must be exactly 0600")
        if opened.st_uid != os.geteuid():
            raise PermitError("start permit must be owned by the effective user")
        document = _read_permit_json(permit_fd)
        _validate_permit_document(document)
        receipt_path, receipt_bytes = _create_durable_receipt(document, repo_root=repo_root)

        consumed_name = f"{name}.consumed-{secrets.token_hex(16)}"
        try:
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                raise PermitError("start permit identity changed before consumption")
            os.rename(name, consumed_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            consumed_metadata = os.stat(
                consumed_name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
            if (consumed_metadata.st_dev, consumed_metadata.st_ino) != (
                opened.st_dev,
                opened.st_ino,
            ):
                raise PermitError("consumed start permit identity does not match")
            os.fsync(parent_fd)
        except PermitError:
            raise
        except OSError as exc:
            raise PermitError("start permit could not be atomically consumed") from exc
    finally:
        if permit_fd >= 0:
            os.close(permit_fd)
        os.close(parent_fd)

    consumed_path = parent / consumed_name
    _validate_repository_state(document, repo_root)
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
    proof = _issue_t2_consumed_permit_proof(
        consumed_path=consumed_path,
        receipt_path=receipt_path,
        receipt_sha256=receipt_sha256,
        permit_id=document["permit_id"],
    )
    return ConsumedStartPermit(
        task_id=TASK_ID,
        permit_id=document["permit_id"],
        expected_git_sha=document["expected_git_sha"],
        consumed_path=consumed_path,
        receipt_path=receipt_path,
        receipt_sha256=receipt_sha256,
        ingress_proof=proof,
    )


def _validate_acknowledgement(message: Any) -> str:
    if type(message) is not dict or message.get("channel") != "subscriptionResponse":
        raise AcknowledgementError("expected only subscriptionResponse during acknowledgement")
    data = message.get("data")
    if type(data) is not dict or data.get("method") != "subscribe":
        raise AcknowledgementError("subscriptionResponse does not bind the subscribe method")
    subscription = data.get("subscription")
    if type(subscription) is not dict:
        raise AcknowledgementError("subscriptionResponse is missing the subscription identity")
    if subscription.get("type") != "candle" or subscription.get("coin") != "ETH":
        raise AcknowledgementError("subscriptionResponse is outside the ETH candle allowlist")
    interval = subscription.get("interval")
    if interval not in {"5m", "15m"}:
        raise AcknowledgementError("subscriptionResponse contains an unexpected interval")
    return cast(str, interval)


def _validate_candle_message(message: Any) -> Literal["5m", "15m"]:
    if type(message) is not dict or message.get("channel") != "candle":
        raise FrameValidationError(
            "only candle and pong channels are allowed after acknowledgement"
        )
    data = message.get("data")
    if type(data) is dict:
        candles = (data,)
    elif type(data) is list and data:
        candles = tuple(data)
    else:
        raise FrameValidationError(
            "candle data must use the frozen object or non-empty array envelope"
        )
    intervals: set[str] = set()
    for candle in candles:
        if type(candle) is not dict:
            raise FrameValidationError("every candle array element must be an object")
        coin = candle.get("s")
        interval = candle.get("i")
        if type(coin) is not str or not coin or coin != "ETH":
            raise FrameValidationError("every candle must identify ETH")
        if type(interval) is not str or not interval or interval not in {"5m", "15m"}:
            raise FrameValidationError("every candle must identify interval 5m or 15m")
        intervals.add(interval)
    if len(intervals) != 1:
        raise FrameValidationError("one candle application message must bind one interval")
    return cast(Literal["5m", "15m"], intervals.pop())


async def _receive_or_stop(
    websocket: WebSocketConnection,
    stop_event: asyncio.Event,
) -> str | bytes | object:
    if stop_event.is_set():
        return _STOP
    receive_task = asyncio.create_task(websocket.recv())
    stop_task = asyncio.create_task(stop_event.wait())
    try:
        done, _pending = await asyncio.wait(
            {receive_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_task in done:
            return _STOP
        return receive_task.result()
    finally:
        for task in (receive_task, stop_task):
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def _receive_before(
    websocket: WebSocketConnection,
    stop_event: asyncio.Event,
    *,
    deadline: float,
    monotonic: Callable[[], float],
    wait_for: Callable[[Awaitable[Any], float], Awaitable[Any]],
) -> str | bytes | object:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise _DeadlineExpired
    try:
        result = await wait_for(_receive_or_stop(websocket, stop_event), remaining)
    except TimeoutError as exc:
        raise _DeadlineExpired from exc
    if result is not _STOP and monotonic() >= deadline:
        raise _DeadlineExpired
    return cast(str | bytes | object, result)


async def _run_connected(
    websocket: WebSocketConnection,
    *,
    stop_event: asyncio.Event,
    store: BronzeStore,
    writer: ManifestWriter,
    permit: ConsumedStartPermit,
    connection_id: str,
    monotonic: Callable[[], float],
    monotonic_ns: Callable[[], int],
    utcnow: Callable[[], datetime],
    wait_for: Callable[[Awaitable[Any], float], Awaitable[Any]],
    status: Callable[[str], None],
) -> None:
    await websocket.send(SUBSCRIBE_5M)
    await websocket.send(SUBSCRIBE_15M)
    acknowledgement_deadline = monotonic() + ACKNOWLEDGEMENT_DEADLINE_SECONDS
    acknowledged: set[str] = set()
    greeting_seen = False
    while len(acknowledged) != 2:
        try:
            frame = await _receive_before(
                websocket,
                stop_event,
                deadline=acknowledgement_deadline,
                monotonic=monotonic,
                wait_for=wait_for,
            )
        except _DeadlineExpired as exc:
            raise AcknowledgementTimeout(
                "both subscriptions were not acknowledged in 30 seconds"
            ) from exc
        if frame is _STOP:
            status("graceful shutdown requested")
            return
        if type(frame) is bytes:
            raise FrameValidationError("binary WebSocket frames are prohibited")
        if type(frame) is not str:
            raise FrameValidationError("WebSocket recv returned an unsupported frame type")
        if frame == SERVER_GREETING:
            if greeting_seen:
                raise AcknowledgementError("duplicate server greeting")
            greeting_seen = True
            continue
        try:
            message = _strict_json(frame)
        except (json.JSONDecodeError, ValueError) as exc:
            raise AcknowledgementError("acknowledgement frame is not strict JSON") from exc
        if type(message) is dict and message.get("channel") == "candle":
            candle_interval = _validate_candle_message(message)
            if candle_interval not in acknowledged:
                raise AcknowledgementError(
                    "candle arrived before its subscription was acknowledged"
                )
            continue
        interval = _validate_acknowledgement(message)
        if interval in acknowledged:
            raise AcknowledgementError("duplicate subscription acknowledgement")
        acknowledged.add(interval)
    status("both subscriptions acknowledged")

    receive_sequence = 0
    awaiting_pong = False
    heartbeat_deadline = monotonic() + HEARTBEAT_INTERVAL_SECONDS
    while True:
        try:
            frame = await _receive_before(
                websocket,
                stop_event,
                deadline=heartbeat_deadline,
                monotonic=monotonic,
                wait_for=wait_for,
            )
        except _DeadlineExpired as exc:
            if awaiting_pong:
                raise HeartbeatTimeout(
                    "application pong was not received before the next deadline"
                ) from exc
            if stop_event.is_set():
                status("graceful shutdown requested")
                return
            await websocket.send(APPLICATION_PING)
            awaiting_pong = True
            heartbeat_deadline += HEARTBEAT_INTERVAL_SECONDS
            continue
        if frame is _STOP or stop_event.is_set():
            status("graceful shutdown requested")
            return
        if type(frame) is bytes:
            raise FrameValidationError("binary WebSocket frames are prohibited")
        if type(frame) is not str:
            raise FrameValidationError("WebSocket recv returned an unsupported frame type")
        try:
            payload = frame.encode("utf-8", errors="strict")
            message = _strict_json(frame)
        except (UnicodeEncodeError, json.JSONDecodeError, ValueError) as exc:
            raise FrameValidationError("market-data frame is not strict UTF-8 JSON") from exc
        if type(message) is not dict:
            raise FrameValidationError("WebSocket application message must be an object")
        channel = message.get("channel")
        if channel == "pong":
            if message != {"channel": "pong"} or not awaiting_pong:
                raise HeartbeatError("pong is malformed or does not answer an application ping")
            awaiting_pong = False
            continue
        interval = _validate_candle_message(message)
        receive_sequence += 1
        observed_at = utcnow()
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise CaptureRuntimeError("UTC clock returned a naive timestamp")
        ingest_t2_eth_public_candle_bytes(
            payload=payload,
            consumed_permit=permit.ingress_proof,
            candle_interval=interval,
            connection_id=connection_id,
            subscription_id=SUBSCRIPTION_IDS[interval],
            receive_sequence=receive_sequence,
            first_observed_time=observed_at,
            collector_receive_time=observed_at,
            collector_monotonic_ns=monotonic_ns(),
            store=store,
            writer=writer,
        )


def _install_signal_handlers(stop_event: asyncio.Event) -> Callable[[], None]:
    loop = asyncio.get_running_loop()
    installed: list[signal.Signals] = []
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop_event.set)
        except (NotImplementedError, RuntimeError):
            continue
        installed.append(signum)

    def remove() -> None:
        for signum in installed:
            loop.remove_signal_handler(signum)

    return remove


async def run_eth_public_capture(
    *,
    storage_root: Path,
    permit_path: Path,
    _repo_root: Path | None = None,
    _connect_factory: Callable[..., Any] | None = None,
    _stop_event: asyncio.Event | None = None,
    _monotonic: Callable[[], float] = time.monotonic,
    _monotonic_ns: Callable[[], int] = time.monotonic_ns,
    _utcnow: Callable[[], datetime] | None = None,
    _wait_for: Callable[[Awaitable[Any], float], Awaitable[Any]] | None = None,
    _status: Callable[[str], None] | None = None,
) -> CaptureRunResult:
    repo_root = _repo_root or Path(__file__).resolve().parents[3]
    status_sink = _status or (lambda _message: None)
    permit = consume_start_permit(permit_path, repo_root=repo_root)
    status_sink("permit consumed")

    store = BronzeStore(storage_root)
    authority_fd = os.open(
        store.authority_anchor,
        os.O_RDONLY | _DIRECTORY | _NOFOLLOW,
    )
    connection_id = f"eth-capture-{uuid4().hex}"
    started_at = (_utcnow or (lambda: datetime.now(UTC)))()
    manifest_date = started_at.date()
    segment_id = connection_id
    writer: ManifestWriter | None = None
    stop_event = _stop_event or asyncio.Event()
    remove_signal_handlers = (
        _install_signal_handlers(stop_event) if _stop_event is None else lambda: None
    )
    wait_for = _wait_for or asyncio.wait_for
    connector = _connect_factory or connect
    try:
        writer = ManifestWriter(
            store,
            manifest_date=manifest_date,
            segment_id=segment_id,
            authority_anchor_fd=authority_fd,
        )
        async with connector(
            WEBSOCKET_URL,
            proxy=None,
            ping_interval=None,
        ) as raw_websocket:
            websocket = cast(WebSocketConnection, raw_websocket)
            status_sink("connection opened")
            await _run_connected(
                websocket,
                stop_event=stop_event,
                store=store,
                writer=writer,
                permit=permit,
                connection_id=connection_id,
                monotonic=_monotonic,
                monotonic_ns=_monotonic_ns,
                utcnow=_utcnow or (lambda: datetime.now(UTC)),
                wait_for=wait_for,
                status=status_sink,
            )
            await websocket.close()

        checkpoint = writer.finalize()
        status_sink("checkpoint finalized")
        replay = replay_segment(
            store,
            manifest_date=manifest_date,
            segment_id=segment_id,
            expected_terminal_hash=checkpoint.terminal_entry_hash,
        )
        if replay.status is not ReplayStatusV0.PASS:
            status_sink("replay failure")
            raise ReplayIntegrityError("deterministic Bronze replay did not PASS")
        status_sink("replay PASS")
        return CaptureRunResult(
            permit_id=permit.permit_id,
            consumed_permit_path=permit.consumed_path,
            connection_id=connection_id,
            manifest_date=manifest_date.isoformat(),
            segment_id=segment_id,
            replay_report_hash=replay.report_hash,
            entries_checked=replay.entries_checked,
        )
    except BaseException:
        if writer is not None and not writer.finalized:
            with contextlib.suppress(Exception):
                writer.close()
        raise
    finally:
        remove_signal_handlers()
        os.close(authority_fd)
