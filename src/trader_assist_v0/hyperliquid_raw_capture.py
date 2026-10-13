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
from contextlib import aclosing, suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO, cast
from urllib.request import Request, urlopen
from uuid import uuid4

from websockets.asyncio.client import connect, process_exception
from websockets.exceptions import ConnectionClosed

INFO_URL = "https://api.hyperliquid.xyz/info"
WS_URL = "wss://api.hyperliquid.xyz/ws"
CHANNELS = ("trades", "bbo", "l2Book")
MAX_SEGMENT_BYTES = 64 * 1024 * 1024


DISCOVERY_STOP_SECONDS = 12.0


class DiscoveryStopped(Exception):
    """Only deliberate stop between successfully validated metadata requests."""


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
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = (self.directory / ".capture.lock").open("a", encoding="utf-8")
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.marker("start", session_id=self.session)
        except BaseException as exc:
            try:
                self._release()
            except BaseException as release_error:
                exc.add_note(f"writer startup release also failed: {release_error}")
            raise
        return self

    def _release(self) -> None:
        try:
            if self._file is not None:
                self._file.close()
                self._file = None
        finally:
            if self._lock is not None:
                self._lock.close()
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
                failure.add_note(f"writer finalization also failed: {finalization_error}")
            # A preceding clean stop marker is intent, not proof of successful fsync.
            try:
                self.marker("finalization_failure", clean=False, reason=str(finalization_error))
            except BaseException:
                pass
        finally:
            try:
                self._release()
            except BaseException as release_error:
                if failure is None:
                    failure = release_error
                else:
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
        subscription = raw.get("data", {}).get("subscription", {})
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


async def receive_public(writer: RawWriter, coins: list[str], *, max_reconnects: int = 2) -> None:
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
            writer.marker("connect" if gap_start is None else "reconnect")
            last_received = utc_now()
            acknowledgments: set[tuple[str, str]] = set()
            try:
                for coin, channel in sorted(expected):
                    subscription = {"type": channel, "coin": coin}
                    await websocket.send(
                        json.dumps({"method": "subscribe", "subscription": subscription})
                    )
                    writer.marker("subscribe", subscription=subscription)
                ack_deadline = time.monotonic() + 30
                while True:
                    if acknowledgments != expected and time.monotonic() >= ack_deadline:
                        raise ValueError("missing subscription acknowledgments")
                    try:
                        frame = await asyncio.wait_for(websocket.recv(), timeout=5)
                    except TimeoutError:
                        await websocket.send('{"method":"ping"}')
                        continue
                    stamp = utc_now()
                    last_received = stamp
                    raw = json.loads(frame)
                    record_message(writer, raw, stamp, coins)
                    if raw["channel"] == "subscriptionResponse":
                        subscription = raw["data"]["subscription"]
                        acknowledgments.add((subscription["coin"], subscription["type"]))
                        if acknowledgments == expected:
                            writer.marker("subscriptions_ready")
                            if gap_start is not None:
                                writer.marker(
                                    "gap", start_utc=gap_start, end_utc=stamp, missing="UNKNOWN"
                                )
                                gap_start = None
            except ConnectionClosed as exc:
                failures += 1
                gap_start = gap_start or last_received
                writer.marker(
                    "disconnect", reason=str(exc), gap_start_utc=gap_start, missing="UNKNOWN"
                )
                if failures > max_reconnects:
                    raise
                continue


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


async def _receive_until_stop(writer: RawWriter, coins: list[str], stop: StopIntent) -> None:
    receiver = asyncio.create_task(receive_public(writer, coins))
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


async def capture_continuous(directory: Path, *, stop: StopIntent) -> dict[str, Any]:
    """Explicit indefinite public recording; success only after requested clean stop."""
    with RawWriter(directory, retain_paths=False) as writer:
        discovered = await _discover_continuous(stop)
        if discovered is not None:
            coins, evidence = discovered
            for item in evidence:
                writer.marker("discovery", **item)
            writer.marker("coins", venue_coins=coins)
            if not stop.event.is_set():
                await _receive_until_stop(writer, coins, stop)
        writer.marker("requested_stop")
    return {
        "mode": "continuous",
        "termination": "clean_requested_stop",
        "session_id": writer.session,
        "segments": writer.segment_count,
    }
