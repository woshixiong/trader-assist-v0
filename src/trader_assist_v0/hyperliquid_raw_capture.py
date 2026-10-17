"""Bounded proof and opt-in continuous public raw capture; no account/execution API."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import math
import os
import threading
import time
from collections.abc import AsyncGenerator, Callable, Iterator
from contextlib import aclosing, contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, TextIO, cast
from urllib.request import Request, urlopen
from uuid import uuid4

from websockets.asyncio.client import connect, process_exception
from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidStatus, InvalidURI

INFO_URL = "https://api.hyperliquid.xyz/info"
WS_URL = "wss://api.hyperliquid.xyz/ws"
CHANNELS = ("trades", "bbo", "l2Book")
MAX_SEGMENT_BYTES = 64 * 1024 * 1024


DISCOVERY_STOP_SECONDS = 12.0


class DiscoveryStopped(Exception):
    """Only deliberate stop between successfully validated metadata requests."""


class DataStall(TimeoutError):
    """No qualifying advancing ETH Depth within the monotonic budget."""


class SubscriptionTimeout(ValueError):
    """Recoverable missing acknowledgments, distinct from invalid protocol."""


@dataclass(frozen=True)
class StorageFailureSignal:
    operation: str
    errno: int | None


@contextmanager
def storage_operation(operation: str) -> Iterator[None]:
    try:
        yield
    except OSError as exc:
        exc.raw_capture_storage_failure = StorageFailureSignal(operation, exc.errno)  # type: ignore[attr-defined]
        raise


def carry_storage_failure(primary: BaseException, secondary: BaseException) -> None:
    signal = getattr(secondary, "raw_capture_storage_failure", None)
    if isinstance(signal, StorageFailureSignal):
        primary.raw_capture_storage_failure = signal  # type: ignore[attr-defined]


def failure_exit_status(exc: Exception) -> int:
    """Storage evidence wins without parsing error strings or losing the primary."""
    if isinstance(getattr(exc, "raw_capture_storage_failure", None), StorageFailureSignal):
        return 74
    if isinstance(exc, BlockingIOError):
        return 78
    if isinstance(exc, InvalidURI):
        return 78
    if isinstance(exc, InvalidStatus):
        status = exc.response.status_code
        if 400 <= status < 500 and status not in {408, 429}:
            return 78
    if isinstance(exc, InvalidHandshake):
        return 75
    if isinstance(exc, SubscriptionTimeout | TimeoutError | ConnectionClosed | OSError):
        return 75
    if isinstance(exc, ValueError | TypeError | KeyError):
        return 78
    return 1


@dataclass(frozen=True)
class HealthPolicy:
    depth_seconds: float = 60
    bbo_warning_seconds: float = 300

    def validate(self) -> None:
        if not math.isfinite(self.depth_seconds) or not 30 <= self.depth_seconds <= 300:
            raise ValueError("ETH Depth deadline must be finite and in [30, 300]")
        if not math.isfinite(self.bbo_warning_seconds) or not 60 <= self.bbo_warning_seconds <= 900:
            raise ValueError("BBO warning age must be finite and in [60, 900]")


def healthy_eth_time(raw: Any, stamp: str, max_age: float) -> int | None:
    """Health only; preserve raw objects. Sample-confirmed ETH Unix milliseconds."""
    if not isinstance(raw, dict) or raw.get("channel") not in {"bbo", "l2Book"}:
        return None
    data = raw.get("data")
    if not isinstance(data, dict) or data.get("coin") != "ETH":
        return None
    venue_time = data.get("time")
    if type(venue_time) is not int or venue_time <= 0:
        return None
    receipt_ms = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() * 1000
    if not -5000 <= receipt_ms - venue_time <= max_age * 1000:
        return None
    sides = data.get("bbo" if raw["channel"] == "bbo" else "levels")
    if not isinstance(sides, list) or len(sides) != 2:
        return None
    if raw["channel"] == "bbo":
        sides = [[side] for side in sides]
    prices: list[list[Decimal]] = []
    for side in sides:
        if not isinstance(side, list) or not side:
            return None
        side_prices: list[Decimal] = []
        for level in side:
            if not isinstance(level, dict):
                return None
            if not isinstance(level.get("px"), str) or not isinstance(level.get("sz"), str):
                return None
            if type(level.get("n")) is not int or level["n"] <= 0:
                return None
            try:
                price, size = Decimal(level["px"]), Decimal(level["sz"])
            except InvalidOperation:
                return None
            if not price.is_finite() or not size.is_finite() or price <= 0 or size <= 0:
                return None
            side_prices.append(price)
        prices.append(side_prices)
    if max(prices[0]) > min(prices[1]):
        return None
    return venue_time


class StopIntent:
    """CLI stop notification and atomic metadata request admission."""

    def __init__(self) -> None:
        self.event = asyncio.Event()
        self._intent = threading.Event()
        self._admission = threading.Lock()
        self.requested_at: float | None = None

    def request(self) -> None:
        # Called on the event-loop thread, including asyncio signal callbacks.
        with self._admission:
            if not self._intent.is_set():
                self.requested_at = time.monotonic()
                self._intent.set()
        self.event.set()

    def check(self) -> None:
        with self._admission:
            if self._intent.is_set():
                raise DiscoveryStopped()


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def public_info(request: dict[str, str]) -> Any:
    """Only the two public metadata request types are admitted."""
    if request.get("type") not in {"perpDexs", "meta"} or set(request) - {"type", "dex"}:
        raise ValueError("only public perp metadata is allowed")
    req = Request(
        INFO_URL,
        data=json.dumps(request).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=10) as response:
        if response.url != INFO_URL:
            raise ValueError("unexpected metadata redirect")
        return json.loads(response.read())


def discover_coins(
    info: Callable[[dict[str, str]], Any] = public_info,
    *,
    stop: StopIntent | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Resolve unique active ETH and builder-deployed SKHX from venue metadata."""
    evidence: list[dict[str, Any]] = []

    def fetch(request: dict[str, str]) -> Any:
        if stop is not None:
            stop.check()  # Admission precedes I/O; the lock is never held during HTTP.
        payload = info(request)
        evidence.append({"request": request, "raw_payload": payload, "received_at_utc": utc_now()})
        return payload

    dexes = fetch({"type": "perpDexs"})
    if not isinstance(dexes, list):
        raise ValueError("invalid perpDexs response")
    names = [dex["name"] for dex in dexes if isinstance(dex, dict)]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(
        names
    ):
        raise ValueError("invalid or duplicate DEX names")
    if stop is not None:
        stop.check()
    eth: list[str] = []
    skhx: list[str] = []
    for dex in ["", *names]:
        meta = fetch({"type": "meta", "dex": dex})
        if not isinstance(meta, dict) or not isinstance(meta.get("universe"), list):
            raise ValueError("invalid meta universe")
        for item in meta["universe"]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise ValueError("invalid meta instrument")
            coin = item["name"]
            if item.get("isDelisted", False):
                continue
            if dex == "" and coin == "ETH":
                eth.append(coin)
            if dex and coin.rsplit(":", 1)[-1] == "SKHX":
                if not coin.startswith(dex + ":"):
                    raise ValueError("SKHX metadata lacks canonical DEX prefix")
                skhx.append(coin)
    if len(eth) != 1 or len(skhx) != 1:
        raise ValueError("missing or ambiguous active ETH/SKHX metadata")
    if stop is not None:
        stop.check()
    return [eth[0], skhx[0]], evidence


class RawWriter:
    """Single locked owner; one active segment, no overwrite or retention deletion."""

    def __init__(
        self,
        directory: Path,
        *,
        max_bytes: int = MAX_SEGMENT_BYTES,
        clock: Callable[[], str] = utc_now,
        retain_paths: bool = True,
    ) -> None:
        if max_bytes < 1024:
            raise ValueError("segment size must be at least 1024 bytes")
        self.directory = directory
        self.max_bytes = max_bytes
        self.clock = clock
        self.session = uuid4().hex
        self.paths: list[Path] = []
        self.retain_paths = retain_paths
        self.segment_count = 0
        self._path: Path | None = None
        self._lock: TextIO | None = None
        self._file: TextIO | None = None
        self._date = ""
        self._size = 0

    def __enter__(self) -> RawWriter:
        with storage_operation("writer startup"):
            self.directory.mkdir(parents=True, exist_ok=True)
            self._lock = (self.directory / ".capture.lock").open("a", encoding="utf-8")
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.marker("start", session_id=self.session)
        except BaseException as exc:
            try:
                self._release()
            except BaseException as release_error:
                carry_storage_failure(exc, release_error)
                exc.add_note(f"writer startup release also failed: {release_error}")
            raise
        return self

    def _release(self) -> None:
        try:
            if self._file is not None:
                try:
                    with storage_operation("file release"):
                        self._file.close()
                finally:
                    self._file = None
        finally:
            if self._lock is not None:
                try:
                    with storage_operation("lock release"):
                        self._lock.close()
                finally:
                    self._lock = None

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        failure: BaseException | None = exc
        try:
            self.marker("stop", clean=exc_type is None, reason=None if exc is None else str(exc))
            self._finish_segment()
        except BaseException as finalization_error:
            if failure is None:
                failure = finalization_error
            else:
                carry_storage_failure(failure, finalization_error)
                failure.add_note(f"writer finalization also failed: {finalization_error}")
            # A preceding clean stop marker is intent, not proof of successful fsync.
            try:
                self.marker("finalization_failure", clean=False, reason=str(finalization_error))
            except BaseException as marker_error:
                carry_storage_failure(failure, marker_error)
        finally:
            try:
                self._release()
            except BaseException as release_error:
                if failure is None:
                    failure = release_error
                else:
                    carry_storage_failure(failure, release_error)
                    failure.add_note(f"writer release also failed: {release_error}")
        if failure is not None and failure is not exc:
            raise failure

    def _line(self, record: dict[str, Any]) -> None:
        if self._file is None:
            raise RuntimeError("writer is not open")
        line = json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
        self._file.write(line)
        self._file.flush()
        self._size += len(line.encode())

    def _control(self, event: str, **fields: Any) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "marker",
            "event": event,
            "received_at_utc": self.clock(),
            **fields,
        }

    def _finish_segment(self) -> None:
        with storage_operation("segment finalization"):
            self._finish_segment_storage()

    def _finish_segment_storage(self) -> None:
        if self._file is not None:
            self._line(
                self._control(
                    "segment_end", segment=self._path.name if self._path is not None else None
                )
            )
            os.fsync(self._file.fileno())
            self._file.close()
            self._file = None

    def append(self, record: dict[str, Any]) -> None:
        with storage_operation("raw append"):
            self._append_storage(record)

    def _append_storage(self, record: dict[str, Any]) -> None:
        if self._lock is None:
            raise RuntimeError("writer has no ownership lock")
        stamp = self.clock()
        size = len(json.dumps(record, ensure_ascii=False, allow_nan=False).encode()) + 1
        if self._file is None or stamp[:10] != self._date or self._size + size > self.max_bytes:
            self._finish_segment()
            self._date = stamp[:10]
            path = self.directory / f"{self._date}-{self.session}-{self.segment_count:06d}.ndjson"
            self._file = path.open("x", encoding="utf-8")
            self._path = path
            self.segment_count += 1
            if self.retain_paths:
                self.paths.append(path)
            self._size = 0
            self._line(self._control("segment_start", segment=path.name))
        self._line(record)

    def marker(self, event: str, **fields: Any) -> None:
        self.append(self._control(event, **fields))


def read_records(paths: list[Path]) -> Iterator[dict[str, Any]]:
    """Reopen closed files; reject partial or malformed envelopes."""
    for path in paths:
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.endswith("\n"):
                    raise ValueError(f"partial line in {path.name}")
                record = json.loads(line)
                if not isinstance(record, dict) or record.get("schema_version") != 1:
                    raise ValueError("invalid raw envelope")
                datetime.fromisoformat(record["received_at_utc"].replace("Z", "+00:00"))
                yield record


def record_message(
    writer: RawWriter,
    raw: Any,
    stamp: str,
    coins: list[str],
) -> tuple[str, str] | None:
    """Preserve full parsed frames; reject unknown routes, never derive ticks."""
    if not isinstance(raw, dict) or not isinstance(raw.get("channel"), str):
        raise ValueError("invalid WS envelope")
    channel = raw["channel"]
    if channel == "subscriptionResponse":
        acknowledgment = raw.get("data")
        if not isinstance(acknowledgment, dict):
            raise ValueError("invalid subscription acknowledgment payload")
        subscription = acknowledgment.get("subscription")
        if not isinstance(subscription, dict):
            raise ValueError("invalid subscription acknowledgment route")
        pair = (subscription.get("coin"), subscription.get("type"))
        if (
            pair[0] not in coins
            or pair[1] not in CHANNELS
            or raw["data"].get("method") != "subscribe"
        ):
            raise ValueError("unexpected subscription acknowledgment")
        writer.marker(
            "ack", venue_coin=pair[0], channel=pair[1], raw_payload=raw, ack_received_at_utc=stamp
        )
        return None
    if channel == "pong":
        writer.marker("pong", raw_payload=raw, pong_received_at_utc=stamp)
        return None
    if channel not in CHANNELS:
        raise ValueError(f"unexpected public channel: {channel}")
    payload = raw.get("data")
    if channel == "trades":
        if not isinstance(payload, list):
            raise ValueError("invalid trades payload")
        if not payload:
            writer.marker("empty_trades", raw_payload=raw, frame_received_at_utc=stamp)
            return None
        coin_set = {trade["coin"] for trade in payload}
        if len(coin_set) != 1:
            raise ValueError("mixed trades coins")
        coin = coin_set.pop()
    else:
        if not isinstance(payload, dict):
            raise ValueError("invalid book/BBO payload")
        coin = payload.get("coin")
    if coin not in coins:
        raise ValueError("unexpected data coin")
    writer.append(
        {
            "schema_version": 1,
            "kind": "data",
            "channel": channel,
            "venue_coin": coin,
            "received_at_utc": stamp,
            "raw_payload": raw,
        }
    )
    return str(coin), channel


class MarketProgress:
    """Constant-size, connection-bound progress; never a trading health certificate."""

    def __init__(self, writer: RawWriter, policy: HealthPolicy) -> None:
        self.writer = writer
        self.policy = policy
        self.started = asyncio.get_running_loop().time()
        self.last_depth = self.started
        self.last_depth_utc: str | None = None
        self.watermarks: dict[str, int] = {}
        self.pending: dict[str, dict[str, Any]] = {}
        self.published: dict[str, float] = {}
        self.epoch = 0
        self.depth_seen = False
        self.bbo_warned = False
        self.last_bbo = self.started
        self.invalidate()

    def path(self, channel: str) -> Path:
        return self.writer.directory / f".eth-{channel}-progress.json"

    def invalidate(self) -> None:
        with storage_operation("checkpoint invalidation"):
            for channel in ("bbo", "l2Book"):
                self.path(channel).unlink(missing_ok=True)
        self.pending.clear()
        self.published.clear()
        self.depth_seen = False

    def connected(self) -> None:
        self.invalidate()
        self.epoch += 1

    def observe(self, raw: Any, stamp: str, received_monotonic: float | None = None) -> bool:
        venue_time = healthy_eth_time(raw, stamp, self.policy.depth_seconds)
        if venue_time is None:
            return False
        channel = raw["channel"]
        if venue_time <= self.watermarks.get(channel, 0):
            return False
        now = (
            asyncio.get_running_loop().time() if received_monotonic is None else received_monotonic
        )
        self.watermarks[channel] = venue_time
        self.pending[channel] = {
            "session_id": self.writer.session,
            "connection_epoch": self.epoch,
            "channel": channel,
            "received_at_utc": stamp,
            "provider_time_ms": venue_time,
            "raw_segment": self.writer._path.name if self.writer._path else None,
            "execution_eligible": False,
        }
        if channel == "l2Book":
            self.last_depth = now
            self.last_depth_utc = stamp
            self.depth_seen = True
            return True
        self.last_bbo = now
        self.bbo_warned = False
        return False

    def publish(self) -> None:
        if not self.depth_seen:
            return
        now = asyncio.get_running_loop().time()
        for channel, record in self.pending.items():
            if now - self.published.get(channel, -math.inf) < 1:
                continue
            target = self.path(channel)
            temporary = target.with_suffix(".tmp")
            with storage_operation("checkpoint publication"):
                try:
                    with temporary.open("w", encoding="utf-8") as output:
                        output.write(json.dumps(record, allow_nan=False) + "\n")
                        output.flush()
                        os.fsync(output.fileno())
                    receipt = datetime.fromisoformat(
                        record["received_at_utc"].replace("Z", "+00:00")
                    ).timestamp()
                    os.utime(temporary, (receipt, receipt))
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
            self.published[channel] = now
            # A control frame must never republish an old receipt as fresh.
        self.pending.clear()

    def warn_bbo(self) -> None:
        age = asyncio.get_running_loop().time() - self.last_bbo
        if age >= self.policy.bbo_warning_seconds and not self.bbo_warned:
            self.writer.marker(
                "bbo_quiet_or_unproven",
                age_seconds=age,
                warning_seconds=self.policy.bbo_warning_seconds,
                execution_eligible=False,
            )
            self.bbo_warned = True


async def receive_public(
    writer: RawWriter,
    coins: list[str],
    *,
    max_reconnects: int = 2,
    health_policy: HealthPolicy | None = None,
) -> None:
    health = MarketProgress(writer, health_policy) if health_policy is not None else None
    timer = asyncio.timeout_at(
        health.last_depth + health.policy.depth_seconds if health is not None else None
    )
    try:
        try:
            async with timer:
                await _receive_public(writer, coins, max_reconnects, health, timer)
        except TimeoutError as exc:
            if health is None or (not timer.expired() and not isinstance(exc, DataStall)):
                raise
            failure = DataStall("ETH_DEPTH_STAGNATION")
            try:
                writer.marker(
                    "data_stall",
                    channel="l2Book",
                    session_id=writer.session,
                    connection_epoch=health.epoch,
                    missing="UNKNOWN",
                    last_valid_depth_utc=health.last_depth_utc,
                    age_seconds=asyncio.get_running_loop().time() - health.last_depth,
                    threshold_seconds=health.policy.depth_seconds,
                )
                writer.marker(
                    "gap_open",
                    channel="l2Book",
                    start_utc=health.last_depth_utc,
                    end_utc=None,
                    missing="UNKNOWN",
                    reason="ETH_DEPTH_STAGNATION",
                )
            except OSError as storage_error:
                carry_storage_failure(failure, storage_error)
                failure.add_note(f"stall marker failed: {storage_error}")
            raise failure from exc
    except BaseException as primary:
        if health is not None:
            try:
                health.invalidate()
            except OSError as storage_error:
                carry_storage_failure(primary, storage_error)
                primary.add_note(f"checkpoint invalidation failed: {storage_error}")
                if isinstance(primary, asyncio.CancelledError):
                    # A requested cancellation is not allowed to swallow a storage fault.
                    raise storage_error from primary
        raise
    else:
        if health is not None:
            health.invalidate()


async def _receive_public(
    writer: RawWriter,
    coins: list[str],
    max_reconnects: int,
    health: MarketProgress | None,
    timer: asyncio.Timeout,
) -> None:
    expected = {(coin, channel) for coin in coins for channel in CHANNELS}
    failures = 0
    gap_start: str | None = None

    def connection_error(exc: Exception) -> Exception | None:
        nonlocal failures, gap_start
        failures += 1
        gap_start = gap_start or utc_now()
        writer.marker("connect_failure", reason=str(exc), gap_start_utc=gap_start)
        return exc if failures > max_reconnects else process_exception(exc)

    connections = cast(
        AsyncGenerator[Any, None],
        connect(
            WS_URL,
            process_exception=connection_error,
            open_timeout=10,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            max_queue=16,
        ).__aiter__(),
    )
    async with aclosing(connections):
        async for websocket in connections:
            if health is not None:
                health.connected()
            writer.marker("connect" if gap_start is None else "reconnect")
            last_received = utc_now()
            acknowledgments: set[tuple[str, str]] = set()
            recovered_depth = False
            try:
                # Deadline includes subscription sends, not just receive time.
                ack_deadline = time.monotonic() + 30
                async with asyncio.timeout(30):
                    for coin, channel in sorted(expected):
                        subscription = {"type": channel, "coin": coin}
                        await websocket.send(
                            json.dumps({"method": "subscribe", "subscription": subscription})
                        )
                        writer.marker("subscribe", subscription=subscription)
                while True:
                    remaining = ack_deadline - time.monotonic()
                    if acknowledgments != expected and remaining <= 0:
                        raise SubscriptionTimeout("missing subscription acknowledgments")
                    try:
                        frame = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=min(5, remaining) if acknowledgments != expected else 5,
                        )
                    except TimeoutError:
                        if acknowledgments != expected and time.monotonic() >= ack_deadline:
                            raise SubscriptionTimeout(
                                "missing subscription acknowledgments"
                            ) from None
                        await websocket.send('{"method":"ping"}')
                        if health is not None:
                            health.warn_bbo()
                        continue
                    stamp = utc_now()
                    received_monotonic = asyncio.get_running_loop().time()
                    last_received = stamp
                    raw = json.loads(frame)
                    record_message(writer, raw, stamp, coins)
                    if health is not None:
                        if (
                            asyncio.get_running_loop().time()
                            >= health.last_depth + health.policy.depth_seconds
                        ):
                            raise DataStall("ETH_DEPTH_STAGNATION")
                        if health.observe(raw, stamp, received_monotonic):
                            recovered_depth = True
                            timer.reschedule(health.last_depth + health.policy.depth_seconds)
                        health.warn_bbo()
                    if raw["channel"] == "subscriptionResponse":
                        subscription = raw["data"]["subscription"]
                        was_ready = acknowledgments == expected
                        acknowledgments.add((subscription["coin"], subscription["type"]))
                        if acknowledgments == expected and not was_ready:
                            writer.marker("subscriptions_ready")
                    if acknowledgments == expected:
                        if health is not None:
                            health.publish()
                        # Preserve bounded proof behavior; continuous recovery is data-based.
                        if gap_start is not None and (health is None or recovered_depth):
                            writer.marker(
                                "gap",
                                start_utc=gap_start,
                                end_utc=stamp,
                                missing="UNKNOWN",
                                coverage=(
                                    "ETH_DEPTH_ONLY" if health is not None else "TRANSPORT_ONLY"
                                ),
                            )
                            gap_start = None
            except ConnectionClosed as exc:
                failures += 1
                gap_start = gap_start or (
                    health.last_depth_utc
                    if health is not None and health.last_depth_utc
                    else last_received
                )
                if health is not None:
                    health.invalidate()
                writer.marker(
                    "disconnect", reason=str(exc), gap_start_utc=gap_start, missing="UNKNOWN"
                )
                if failures > max_reconnects:
                    raise
                continue
            except DataStall:
                raise
            except TimeoutError as exc:
                # The outer freshness timeout cancels this scope, rather than entering here.
                raise SubscriptionTimeout("subscription send timeout") from exc


async def capture(directory: Path, *, duration: float = 180) -> dict[str, Any]:
    """One bounded foreground run followed by real offline file readback."""
    if not math.isfinite(duration) or not 0 < duration <= 180:
        raise ValueError("duration must be finite and in (0, 180]")
    coins: list[str] = []
    with RawWriter(directory) as writer:
        deadline = asyncio.timeout(duration)
        try:
            async with deadline:
                coins, evidence = await asyncio.to_thread(discover_coins)
                for item in evidence:
                    writer.marker("discovery", **item)
                writer.marker("coins", venue_coins=coins)
                await receive_public(writer, coins)
        except TimeoutError:
            if not deadline.expired():
                raise
            writer.marker("bounded_end", duration_seconds=duration)
    counts = {f"{coin}/{channel}": 0 for coin in coins for channel in CHANNELS}
    acks: set[str] = set()
    reopened = 0
    for record in read_records(writer.paths):
        reopened += 1
        if record["kind"] == "data":
            counts[f"{record['venue_coin']}/{record['channel']}"] += 1
        if record.get("event") == "ack":
            acks.add(f"{record['venue_coin']}/{record['channel']}")
    transport_storage = (
        len(coins) == 2
        and len(acks) == 6
        and any(counts[f"{coins[0]}/{channel}"] > 0 for channel in CHANNELS)
    )
    return {
        "transport_storage": "PASS" if transport_storage else "INCOMPLETE",
        "venue_coins": coins,
        "acknowledged": sorted(acks),
        "received_frames": counts,
        "family_coverage": {
            key: "OBSERVED" if count else "INCOMPLETE" for key, count in counts.items()
        },
        "reopened_records": reopened,
        "session_id": writer.session,
        "files": [
            {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in writer.paths
        ],
        "persistent_host_capture": False,
    }


async def _discover_continuous(stop: StopIntent) -> tuple[list[str], list[dict[str, Any]]] | None:
    """Own and boundedly join one discovery worker; never use the default executor."""
    outcome: list[tuple[list[str], list[dict[str, Any]]] | BaseException] = []

    def work() -> None:
        try:
            outcome.append(discover_coins(stop=stop))
        except BaseException as exc:
            outcome.append(exc)

    worker = threading.Thread(target=work, name="hyperliquid-public-discovery", daemon=True)
    worker.start()

    async def join() -> None:
        while worker.is_alive():
            if (
                stop.requested_at is not None
                and time.monotonic() - stop.requested_at >= DISCOVERY_STOP_SECONDS
            ):
                raise TimeoutError("metadata discovery did not stop within join budget")
            await asyncio.sleep(0.02)
        worker.join(timeout=0)

    try:
        await join()
    except BaseException:
        stop.request()
        await join()
        # Do not discard a real metadata failure racing external cancellation.
        if (
            outcome
            and isinstance(outcome[0], BaseException)
            and not isinstance(outcome[0], DiscoveryStopped)
        ):
            raise outcome[0] from None
        raise
    result = outcome[0]
    if isinstance(result, DiscoveryStopped):
        if not stop.event.is_set():
            raise RuntimeError("discovery stopped without requested shutdown")
        return None
    if isinstance(result, BaseException):
        raise result
    return result


async def _receive_until_stop(
    writer: RawWriter,
    coins: list[str],
    stop: StopIntent,
    policy: HealthPolicy | None = None,
) -> None:
    receiver = asyncio.create_task(
        receive_public(writer, coins, health_policy=policy)
        if policy is not None
        else receive_public(writer, coins)
    )
    stopping = asyncio.create_task(stop.event.wait())
    try:
        await asyncio.wait((receiver, stopping), return_when=asyncio.FIRST_COMPLETED)
        if receiver.done():
            receiver.result()  # Provider/storage failure wins even when stop is ready.
            raise RuntimeError("public receiver ended unexpectedly")
        receiver.cancel()
        with suppress(asyncio.CancelledError):
            await receiver
    finally:
        stopping.cancel()
        with suppress(asyncio.CancelledError):
            await stopping
        if not receiver.done():
            receiver.cancel()
            with suppress(asyncio.CancelledError):
                await receiver


async def capture_continuous(
    directory: Path,
    *,
    stop: StopIntent,
    policy: HealthPolicy | None = None,
) -> dict[str, Any]:
    """Explicit indefinite public recording; success only after requested clean stop."""
    policy = HealthPolicy() if policy is None else policy
    policy.validate()
    with RawWriter(directory, retain_paths=False) as writer:
        with storage_operation("startup checkpoint invalidation"):
            for channel in ("bbo", "l2Book"):
                (directory / f".eth-{channel}-progress.json").unlink(missing_ok=True)
        writer.marker("continuity_unknown", previous_session_coverage="UNKNOWN", backfill=False)
        discovered = await _discover_continuous(stop)
        if discovered is not None:
            coins, evidence = discovered
            for item in evidence:
                writer.marker("discovery", **item)
            writer.marker("coins", venue_coins=coins)
            if not stop.event.is_set():
                await _receive_until_stop(writer, coins, stop, policy)
        writer.marker("requested_stop")
    return {
        "mode": "continuous",
        "termination": "clean_requested_stop",
        "session_id": writer.session,
        "segments": writer.segment_count,
    }
