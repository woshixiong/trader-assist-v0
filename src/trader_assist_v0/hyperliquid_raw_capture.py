"""Bounded public Hyperliquid raw capture; no account or execution interface."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import math
import os
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.request import Request, urlopen
from uuid import uuid4

from websockets.asyncio.client import connect, process_exception
from websockets.exceptions import ConnectionClosed

INFO_URL = "https://api.hyperliquid.xyz/info"
WS_URL = "wss://api.hyperliquid.xyz/ws"
CHANNELS = ("trades", "bbo", "l2Book")
MAX_SEGMENT_BYTES = 64 * 1024 * 1024


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
) -> tuple[list[str], list[dict[str, Any]]]:
    """Resolve unique active ETH and builder-deployed SKHX from venue metadata."""
    evidence: list[dict[str, Any]] = []

    def fetch(request: dict[str, str]) -> Any:
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
    return [eth[0], skhx[0]], evidence


class RawWriter:
    """Single locked owner; one active segment, no overwrite or retention deletion."""

    def __init__(
        self,
        directory: Path,
        *,
        max_bytes: int = MAX_SEGMENT_BYTES,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        if max_bytes < 1024:
            raise ValueError("segment size must be at least 1024 bytes")
        self.directory = directory
        self.max_bytes = max_bytes
        self.clock = clock
        self.session = uuid4().hex
        self.paths: list[Path] = []
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
        except BaseException:
            self._release()
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
        try:
            self.marker("stop", clean=exc_type is None, reason=None if exc is None else str(exc))
            self._finish_segment()
        finally:
            self._release()

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
            self._line(self._control("segment_end", segment=self.paths[-1].name))
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
            path = self.directory / f"{self._date}-{self.session}-{len(self.paths):06d}.ndjson"
            self._file = path.open("x", encoding="utf-8")
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

    async for websocket in connect(
        WS_URL,
        process_exception=connection_error,
        open_timeout=10,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=5,
        max_queue=16,
    ):
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
            writer.marker("disconnect", reason=str(exc), gap_start_utc=gap_start, missing="UNKNOWN")
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
