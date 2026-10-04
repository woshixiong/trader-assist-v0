# mypy: disable-error-code="import-not-found"
"""Bounded exact-version public-data-only E4 probe; never configures execution."""

from __future__ import annotations

import argparse
import asyncio
import calendar
import json
import math
import os
import re
import stat
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
from trader_assist_v0.multi_asset_shadow.resolution import FIRST_LAUNCH_20
from trader_assist_v0.nautilus_e4.capture import SubscriptionPolicy
from trader_assist_v0.nautilus_e4.contracts import (
    NAUTILUS_VERSION,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.safety import assert_public_only

if TYPE_CHECKING:
    from trader_assist_v0.nautilus_e4.host import NautilusE4CaptureStrategy

L0_PROFILE = "FIRST_LAUNCH_20_DATA_COLLECTION_ONLY"
L0_SCHEMA = "trader-assist-v0/l0-qualification/v1"
RC5_SOURCE = "1b0a49d2792a9432a3aca3fcb617ce7a630d905e"
PROVIDER_MAX = {
    "rest_weight_per_60s": 600,
    "ws_connections": 5,
    "ws_new_connections_per_60s": 15,
    "ws_active_plus_pending_subscriptions": 500,
    "ws_outbound_messages_per_60s": 1000,
}
ZERO_COUNTERS = (
    "http_429",
    "provider_throttle_events",
    "unrecovered_subscription_failures",
    "oom_or_process_kill",
    "swap_activity",
    "queue_or_buffer_overflow",
    "dropped_events",
    "storage_failures",
    "unplanned_disconnects",
)


def launch_bars(registry: RegistryVersion, snapshot: PitUniverseSnapshot) -> tuple[str, ...]:
    """Require exact official identities and unique provider-owned mappings."""
    if len(registry.markets) != 20 or len(snapshot.expressions) != 20:
        raise ValueError("L0 requires all 20 Registry/PIT identities")
    if tuple(m.display for m in registry.markets) != tuple(r.display for r in FIRST_LAUNCH_20):
        raise ValueError("L0 canonical market order differs")
    expressions = {e.market_id: e for e in snapshot.expressions}
    if len(expressions) != 20 or len({e.instrument_id for e in expressions.values()}) != 20:
        raise ValueError("L0 duplicate market/instrument mapping")
    bars: list[str] = []
    for market, request in zip(registry.markets, FIRST_LAUNCH_20, strict=True):
        expression = expressions.get(market.identity.market_id)
        if (market.identity.dex, market.identity.coin) != (request.dex, request.coin) or (
            expression is None
            or expression.dex != request.dex
            or expression.provider_coin != request.coin
            or expression.instrument_metadata_hash != market.metadata_hash
        ):
            raise ValueError("L0 Registry/PIT/canonical metadata identity differs")
        bars.extend(f"{expression.instrument_id}-{n}-MINUTE-LAST-EXTERNAL" for n in (1, 5))
    return tuple(bars)


def validate_launch(
    registry: RegistryVersion,
    snapshot: PitUniverseSnapshot,
    manifest: RunManifest,
    bars: tuple[str, ...],
) -> None:
    expected = launch_bars(registry, snapshot)
    if len(bars) != 40 or len(set(bars)) != 40 or set(bars) != set(expected):
        raise ValueError("L0 requires exactly 40 external 1m/5m LAST streams")
    ids = sorted(e.market_id for e in snapshot.expressions)
    if manifest.nautilus_version != "2.0.0rc5" or (
        manifest.pit_snapshot_hash != snapshot.snapshot_hash
        or manifest.provider_instrument_ids
        != tuple(sorted(e.instrument_id for e in snapshot.expressions))
        or manifest.capture_configuration.get("registry_hash") != registry.content_hash
        or manifest.capture_configuration.get("bar_types") != list(expected)
        or manifest.capture_configuration.get("profile") != L0_PROFILE
        or manifest.subscription_policy != {"discovery": ids, "watch": ids, "actionable": []}
    ):
        raise ValueError("L0 manifest/subscription policy differs")


@dataclass
class WarmupDispatchPacer:
    """Delay native request_bars only; rc5 still owns its limiter and client."""

    quiet_until_ns: int
    reservations: deque[tuple[int, int]] = field(default_factory=deque)
    peak_weight: int = 0

    def reserve(self, now_ns: int, raw_max_rows: int) -> bool:
        if raw_max_rows < 1:
            raise ValueError("raw response cardinality bound is required")
        weight = 20 + raw_max_rows // 60
        if weight > 400:
            raise ValueError("one native history request exceeds frozen L0 budget")
        while self.reservations and self.reservations[0][0] <= now_ns - 60_000_000_000:
            self.reservations.popleft()
        total = sum(w for _, w in self.reservations)
        if now_ns < self.quiet_until_ns or total + weight > 400:
            return False
        self.reservations.append((now_ns, weight))
        self.peak_weight = max(self.peak_weight, total + weight)
        return True


@dataclass
class QualificationObservation:
    """Bounded exact live-bar evidence after native recovery; historical bars excluded."""

    bars: tuple[str, ...]
    request_ns: int | None = None
    disconnected_ns: int | None = None
    connected_ns: int | None = None
    window_start_ns: int | None = None
    requests: int = 0
    live: dict[str, dict[int, tuple[int, str]]] = field(default_factory=dict)
    failures: set[str] = field(default_factory=set)
    recovered: set[str] = field(default_factory=set)
    retention_capacity: int = 80

    def request(self, now_ns: int) -> None:
        self.requests += 1
        if self.requests != 1:
            self.failures.add("RECONNECT_REQUEST_COUNT")
        self.request_ns = now_ns

    def socket(self, state: str, now_ns: int) -> None:
        if self.request_ns is None:
            return
        if state == "DISCONNECTED":
            if self.disconnected_ns is not None:
                self.failures.add("UNPLANNED_DISCONNECT")
            self.disconnected_ns = now_ns
        elif state == "CONNECTED":
            if self.disconnected_ns is None or now_ns < self.disconnected_ns:
                self.failures.add("RECOVERY_SEQUENCE")
            else:
                self.connected_ns = now_ns

    def processed(self, bar_type: str, open_ns: int, now_ns: int, payload_hash: str) -> None:
        if bar_type not in self.bars or self.connected_ns is None:
            return
        minutes = 1 if bar_type.endswith("-1-MINUTE-LAST-EXTERNAL") else 5
        close_ns = open_ns + minutes * 60_000_000_000
        if close_ns > now_ns:
            self.failures.add("FUTURE_BAR")
            return
        if close_ns < self.connected_ns:
            return
        if now_ns - close_ns <= 60_000_000_000:
            self.recovered.add(bar_type)
        if self.window_start_ns is None:
            if self.recovered == set(self.bars):
                if self.request_ns is None or now_ns - self.request_ns > 60_000_000_000:
                    self.failures.add("RECOVERY_OVER_60S")
                self.window_start_ns = now_ns
            return
        if close_ns <= self.window_start_ns or close_ns > self.window_start_ns + 900_000_000_000:
            return
        stream = self.live.setdefault(bar_type, {})
        if open_ns in stream:
            self.failures.add(
                "CONFLICTING_BAR" if stream[open_ns][1] != payload_hash else "DUPLICATE_BAR"
            )
        elif len(stream) < self.retention_capacity:
            stream[open_ns] = (now_ns - close_ns, payload_hash)
        else:
            self.failures.add("UNBOUNDED_STREAM_INPUT")

    def evaluate(self, now_ns: int) -> tuple[list[str], dict[str, Any]]:
        blockers = sorted(self.failures)
        summary: dict[str, Any] = {}
        if self.requests != 1 or self.connected_ns is None or self.window_start_ns is None:
            blockers.append("RECOVERY_INCOMPLETE")
        if self.window_start_ns is None or now_ns < self.window_start_ns + 900_000_000_000:
            blockers.append("OBSERVATION_15M_INCOMPLETE")
        for bar in self.bars:
            values = self.live.get(bar, {})
            minutes = 1 if bar.endswith("-1-MINUTE-LAST-EXTERNAL") else 5
            required = 15 if minutes == 1 else 3
            lags = sorted(lag / 1e9 for lag, _ in values.values())
            p95 = None if not lags else lags[math.ceil(0.95 * len(lags)) - 1]
            maximum = None if not lags else max(lags)
            contiguous = all(b - a == minutes * 60_000_000_000 for a, b in pairwise(sorted(values)))
            if (
                len(lags) != required
                or not contiguous
                or p95 is None
                or p95 > 30
                or maximum is None
                or maximum > 60
            ):
                blockers.append(f"STREAM_INCOMPLETE_OR_STALE:{bar}")
            summary[bar] = {"count": len(lags), "p95_seconds": p95, "max_seconds": maximum}
        return blockers, summary


def evaluate_qualification(
    manifest: RunManifest,
    observation: QualificationObservation,
    now_ns: int,
    provider: dict[str, Any],
    resources: list[dict[str, Any]],
    queues: dict[str, Any],
    forecast: dict[str, Any],
) -> dict[str, Any]:
    """Unknown is INCOMPLETE. Never infer provider counts from event callbacks."""
    blockers, streams = observation.evaluate(now_ns)
    if forecast != {
        "bars": 40,
        "bbo": 20,
        "trade": 20,
        "depth10": 20,
        "native_subscriptions": 100,
        "rc5_source": RC5_SOURCE,
    }:
        blockers.append("NATIVE_REGISTRATION_PROOF_INCOMPLETE")
    for key, maximum in PROVIDER_MAX.items():
        v = provider.get(key)
        if (
            not isinstance(v, int | float)
            or isinstance(v, bool)
            or not math.isfinite(v)
            or v < 0
            or v > maximum
        ):
            blockers.append(f"PROVIDER_UNKNOWN_OR_EXCEEDED:{key}")
    for key in ZERO_COUNTERS:
        if provider.get(key) != 0 or type(provider.get(key)) is not int:
            blockers.append(f"ZERO_PREDICATE_UNKNOWN_OR_FAILED:{key}")
    if (
        provider.get("metadata_quiet_seconds", -1) < 60
        or provider.get("warmup_weight_per_60s", 401) > 400
    ):
        blockers.append("REST_COHORT_PROOF_INCOMPLETE")
    native = provider.get("native_http_evidence")
    binding = native.get("log_binding") if isinstance(native, dict) else None
    if (not isinstance(native, dict) or native.get("status") != "PASS"
            or not isinstance(binding, dict) or binding.get("status") != "PASS"
            or any(binding.get(key) != native.get(key) for key in (
                "path", "file_identity", "sha256", "begin_marker", "rc5_source",
            ))
            or native.get("blockers") != [] or native.get("rc5_source") != RC5_SOURCE
            or not isinstance(native.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", native["sha256"]) is None
            or native.get("begin_marker") != native_marker(manifest)
            or not isinstance(native.get("path"), str)
            or native.get("raw_response_reservations_verified") is not True):
        blockers.append("RAW_RESPONSE_WEIGHT_UNPROVEN")
    control_evidence = provider.get("native_ws_control_evidence")
    if (not isinstance(control_evidence, dict) or control_evidence.get("status") != "PASS"
            or control_evidence.get("blockers") != []
            or control_evidence.get("sha256") != (native.get("sha256")
                                                  if isinstance(native, dict) else None)
            or not isinstance(native, dict)
            or any(control_evidence.get(key) != native.get(key) for key in (
                "path", "file_identity", "begin_marker",
            ))
            or control_evidence.get("rc5_source") != RC5_SOURCE):
        blockers.append("WS_CONTROL_PROOF_INCOMPLETE")
    if len(resources) < 16:
        blockers.append("RESOURCE_SAMPLING_INCOMPLETE")
    else:
        try:
            times = [r["ts_ns"] for r in resources]
            if (
                any(not 0 < b - a <= 60_000_000_000 for a, b in pairwise(times))
                or times[-1] - times[0] < 900_000_000_000
            ):
                blockers.append("RESOURCE_SAMPLING_WINDOW")
            if (
                max(r["memory_used_percent"] for r in resources) > 80
                or max(r["cpu_percent"] for r in resources) > 80
                or sum(r["cpu_percent"] for r in resources[1:]) / (len(resources) - 1) > 20
            ):
                blockers.append("RESOURCE_CEILING")
            if (
                resources[-1]["root_used_percent"] > 70
                or resources[-1]["root_7d_projection_percent"] > 70
            ):
                blockers.append("DISK_CEILING")
            if any(r["swap_activity"] != 0 for r in resources):
                blockers.append("SWAP_ACTIVITY")
        except (KeyError, TypeError, ValueError):
            blockers.append("RESOURCE_FIELDS_INCOMPLETE")
    if (
        queues.get("native_capacity") != "NOT_APPLICABLE_UNBOUNDED"
        or queues.get("monitor_observed") is not True
        or queues.get("monotonic_backlog_3_cohorts") is not False
    ):
        blockers.append("NATIVE_QUEUE_PROOF_INCOMPLETE")
    finite = queues.get("finite")
    if not isinstance(finite, list) or not finite:
        blockers.append("FINITE_BUFFER_PROOF_INCOMPLETE")
    else:
        for q in finite:
            try:
                if (
                    q["capacity"] <= 0
                    or q["max_depth"] / q["capacity"] > 0.8
                    or q["end_depth"] / q["capacity"] > 0.2
                ):
                    blockers.append("FINITE_BUFFER_CEILING")
            except (KeyError, TypeError, ZeroDivisionError):
                blockers.append("FINITE_BUFFER_PROOF_INCOMPLETE")
    result = {
        "schema": L0_SCHEMA,
        "status": "INCOMPLETE" if blockers else "PASS",
        "blockers": sorted(set(blockers)),
        "release_sha": manifest.git_sha,
        "release_tree": manifest.git_tree,
        "manifest_hash": manifest.manifest_hash,
        "snapshot_hash": manifest.pit_snapshot_hash,
        "end_ns": now_ns,
        "profile": L0_PROFILE,
        "strategy_evaluation": "NOT_EVALUABLE",
        "reason": "COST_AUTHORITY_ABSENT",
        "submission_status": "NOT_SUBMITTED",
        "streams": streams,
        "provider": provider,
        "resources": resources,
        "queues": queues,
        "forecast": forecast,
    }
    result["digest"] = sha256_hex(canonical_json_bytes(result))
    return result


NATIVE_STARTUP_SEPARATOR = "=" * 65
NATIVE_MARKER_PREFIX = "L0-NATIVE-"


def native_marker(manifest: RunManifest) -> str:
    """Qualification LiveNode name; native startup header supplies the boundary."""
    identity = canonical_json_bytes({
        "run_id": manifest.run_id, "manifest_hash": manifest.manifest_hash,
        "release_sha": manifest.git_sha, "release_tree": manifest.git_tree,
    })
    return NATIVE_MARKER_PREFIX + sha256_hex(identity)


def _log_timestamp_ns(value: Any) -> int:
    if type(value) is int and value > 0:
        return value
    if not isinstance(value, str):
        raise ValueError("native timestamp is absent")
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z", value)
    if match is None:
        raise ValueError("native timestamp is malformed")
    seconds = calendar.timegm(datetime.fromisoformat(match[1]).timetuple())
    return seconds * 1_000_000_000 + int((match[2] or "").ljust(9, "0"))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _rolling_weight(events: list[tuple[int, int]]) -> int:
    ordered = sorted(events)
    pending: deque[tuple[int, int]] = deque()
    total = peak = 0
    for timestamp, weight in ordered:
        while pending and pending[0][0] <= timestamp - 60_000_000_000:
            total -= pending.popleft()[1]
        pending.append((timestamp, weight))
        total += weight
        peak = max(peak, total)
    return peak


HTTP_COMPONENT = "nautilus_hyperliquid::http::client"
DATA_COMPONENT = "nautilus_hyperliquid::data"
NATIVE_LEVELS = ("TRACE", "DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL")
CANDLE_ENDPOINT_PATTERN = (
    r'CandleSnapshot \{ req: CandleSnapshotRequest \{ coin: ("(?:[^"\\]|\\.)*"), '
    r'interval: ("(?:[^"\\]|\\.)*"), start_time: (0|[1-9]\d*), '
    r'end_time: (0|[1-9]\d*) \} \}'
)


def _read_bound_native_log(
    path: Path, *, file_identity: tuple[int, int], begin_marker: str,
) -> tuple[bytes, list[dict[str, Any]]]:
    """One stable, complete, unique-envelope rc5 run, independently of predicates."""
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != file_identity
            or path.resolve() != path.absolute()
            or set(path.parent.glob(path.name + "*")) != {path}):
        raise ValueError("native file identity/rotation/path ambiguity")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != file_identity:
            raise ValueError("native file changed at open")
        raw = stream.read()
        after = os.fstat(stream.fileno())
    final = path.lstat()
    def identity(state: os.stat_result) -> tuple[int, int, int, int]:
        return state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns
    if identity(before) != identity(after) or identity(after) != identity(final):
        raise ValueError("native log changed during read")
    if not raw.endswith(b"\n"):
        raise ValueError("native log incomplete")
    records = [json.loads(line, object_pairs_hook=_unique_object)
               for line in raw.decode("utf-8").splitlines()]
    if not records:
        raise ValueError("native log empty")
    seen: set[bytes] = set()
    titles = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("native envelope malformed")
        encoded = canonical_json_bytes(record)
        if encoded in seen:
            raise ValueError("duplicate native envelope")
        seen.add(encoded)
        component, message, level = record["component"], record["message"], record["level"]
        if (not all(isinstance(v, str) for v in (component, message, level))
                or level not in NATIVE_LEVELS):
            raise ValueError("native envelope fields malformed")
        _log_timestamp_ns(record["timestamp"])
        if index == 0 and (component != begin_marker or message != NATIVE_STARTUP_SEPARATOR):
            raise ValueError("native pre-marker content")
        if component.startswith(NATIVE_MARKER_PREFIX):
            if component != begin_marker:
                raise ValueError("mixed native run")
            if message.strip().startswith("NAUTILUS TRADER -"):
                titles += 1
                if titles > 1:
                    raise ValueError("duplicate native header")
    return raw, records


def _instrument_bookkeeping(component: str, level: str, message: str) -> bool:
    """rc5 HTTP-module instrument warnings are owned by overall safety, not REST."""
    return component == HTTP_COMPONENT and level in ("WARN", "WARNING") and any(
        re.fullmatch(pattern, message) is not None for pattern in (
            r"Missing cached Hyperliquid instrument for dex='[^']*' raw_symbol='[^']*'",
            r"Dropping Hyperliquid instrument: sanitized symbol '[^']*' collides with "
            r"an earlier def \(raw_symbol='[^']*'\)",
            r"Instrument '[^']*' carries no 'asset_index' info value; leaving the cached "
            r"asset index unchanged",
            r"Instrument '[^']*' carries no 'asset_index' info value and has no cached "
            r"asset index; orders for it will be rejected",
        )
    )


def _non_http_data_record(component: str, message: str) -> bool:
    return component == DATA_COMPONENT and any(
        re.fullmatch(pattern, message) is not None for pattern in (
            r"WebSocket error: .+",
            r"Failed targeted (?:l2Book|bbo) resubscribe for .+: .+",
            r"Requested full WebSocket reconnect after failed targeted stream recovery",
            r"Hyperliquid stale stream recovery disabled: "
            r"stale_stream_recovery_cooldown_secs must be positive",
            r"Unsupported custom data (?:subscription|unsubscription): .+",
            r"Instrument .+ not found in cache",
            r"Failed to send instrument: .+",
        )
    )


def parse_native_http_log(
    path: Path, *, manifest: RunManifest, dispatches: list[dict[str, Any]],
    file_identity: tuple[int, int], sync_succeeded: bool,
) -> dict[str, Any]:
    """Only complete current-run native DEBUG evidence can establish HTTP weights."""
    blockers: set[str] = set()
    result: dict[str, Any] = {
        "status": "INCOMPLETE", "path": str(path), "sha256": None,
        "file_identity": list(file_identity), "rc5_source": RC5_SOURCE,
        "begin_marker": native_marker(manifest), "metadata_requests": 5,
        "metadata_weight": 100, "matched_requests": [],
        "native_retry_count": 0, "matched_retries": [], "http_429": 0,
    }
    result["log_binding"] = dict(status="INCOMPLETE", path=str(path),
                                 file_identity=list(file_identity),
                                 begin_marker=native_marker(manifest), rc5_source=RC5_SOURCE)
    if sync_succeeded is not True:
        blockers.add("NATIVE_LOG_SYNC_UNPROVEN")
    try:
        raw, records = _read_bound_native_log(
            path, file_identity=file_identity, begin_marker=native_marker(manifest),
        )
        result["sha256"] = sha256_hex(raw)
        result["log_binding"].update(sha256=result["sha256"],
                                     status="PASS" if sync_succeeded is True else "INCOMPLETE")
    except (OSError, KeyError, ValueError, TypeError, UnicodeError):
        result["blockers"] = sorted(blockers | {"NATIVE_LOG_FILE_OR_PARSE_AMBIGUITY"})
        return result
    ledger: dict[str, dict[str, Any]] = {}
    identities: dict[tuple[str, str, int, int], str] = {}
    try:
        expected_bars = manifest.capture_configuration["bar_types"]
        if (not isinstance(expected_bars, list)
                or not all(isinstance(bar, str) for bar in expected_bars)
                or len(dispatches) != 40 or len(set(expected_bars)) != 40):
            raise ValueError("exact 40-request ledger is required")
        for dispatch in dispatches:
            bar = dispatch["bar_type"]
            if bar in ledger or bar not in expected_bars:
                raise ValueError("duplicate/unexpected logical dispatch")
            for key in ("start", "end", "raw_max_rows", "reserved_weight", "ts_ns"):
                if type(dispatch[key]) is not int or dispatch[key] <= 0:
                    raise ValueError("malformed dispatch")
            if dispatch["interval"] not in ("1m", "5m"):
                raise ValueError("malformed dispatch interval")
            minute = 1 if dispatch["interval"] == "1m" else 5
            expressions = manifest.capture_configuration["expressions"]
            if not isinstance(expressions, list) or not all(
                isinstance(e, dict) for e in expressions
            ):
                raise ValueError("manifest expression mapping malformed")
            if not any(
                bar == f"{e['instrument_id']}-{minute}-MINUTE-LAST-EXTERNAL"
                and dispatch["coin"] == e["provider_coin"]
                for e in expressions
            ):
                raise ValueError("dispatch differs from manifest provider identity")
            interval_ms = 60_000 if dispatch["interval"] == "1m" else 300_000
            rows = (dispatch["end"] - dispatch["start"]) // interval_ms + 1
            if (rows <= 0 or dispatch["raw_max_rows"] < rows
                    or dispatch["reserved_weight"] != 20 + dispatch["raw_max_rows"] // 60):
                raise ValueError("raw window/reservation differs")
            identity = (dispatch["coin"], dispatch["interval"],
                        dispatch["start"], dispatch["end"])
            if identity in identities:
                raise ValueError("ambiguous native request identity")
            identities[identity] = bar
            ledger[bar] = dispatch
    except (KeyError, TypeError, ValueError):
        blockers.add("NATIVE_DISPATCH_LEDGER_INCOMPLETE")
    bootstraps = 0
    metadata_ns: int | None = None
    completions: dict[str, int] = {}
    debits: dict[str, tuple[int, int]] = {}
    retries: list[tuple[int, int, str, int, int, int]] = []
    completion_indices: dict[str, int] = {}
    metadata_index: int | None = None
    populated_indices: list[tuple[int, int]] = []
    run_start_ns = _log_timestamp_ns(records[0]["timestamp"])
    for index, record in enumerate(records):
        try:
            message, component, level = record["message"], record["component"], record["level"]
            timestamp = _log_timestamp_ns(record["timestamp"])
            # Evidence-shaped records cannot escape ownership checks via TRACE or
            # another adapter namespace. Levels here bind exact rc5 call sites.
            owner = None
            expected_levels: tuple[str, ...] = ()
            if message.startswith(("Fetched ", "Bootstrapped ")):
                owner, expected_levels = DATA_COMPONENT, ("DEBUG",)
            elif message.startswith(("Info debited extra weight:", "Populated asset indices map")):
                owner, expected_levels = HTTP_COMPONENT, ("DEBUG",)
            elif message.startswith(("429 Too Many Requests;", "Transient error; retrying:")):
                owner, expected_levels = HTTP_COMPONENT, ("WARN", "WARNING")
            if owner is not None and (component != owner or level not in expected_levels):
                raise ValueError("HTTP evidence owner/level differs from rc5 source")
            failure_owner = None
            if message.startswith(("request_bars failed:", "Failed to send bars response:",
                                   "Failed to convert candle to bar:")):
                failure_owner = DATA_COMPONENT
            elif message.startswith((
                "Failed to load Hyperliquid", "Failed to load allPerpMetas",
                "Failed to parse Hyperliquid", "Failed to load perpDexs",
                "Skipping Hyperliquid outcome metadata:",
            )):
                failure_owner = HTTP_COMPONENT
            if failure_owner is not None:
                blockers.add("NATIVE_HTTP_REQUEST_METADATA_OR_TRANSPORT_FAILURE")
                if component != failure_owner:
                    raise ValueError("HTTP failure owner differs from rc5 source")
            if _instrument_bookkeeping(component, level, message):
                continue
            if _non_http_data_record(component, message):
                continue
            if component not in (HTTP_COMPONENT, DATA_COMPONENT):
                continue
            if component == HTTP_COMPONENT and message.startswith((
                "transport error:", "request failed:",
            )):
                blockers.add("NATIVE_HTTP_REQUEST_METADATA_OR_TRANSPORT_FAILURE")
            if level == "TRACE":
                # Raw HTTP TRACE is never proof of response weight or controls.
                continue
            if message.startswith("429 Too Many Requests;"):
                if re.fullmatch(
                    r"429 Too Many Requests; backing off: endpoint=.+, "
                    r"attempt=(0|[1-9]\d*), wait_ms=([1-9]\d*)", message,
                ) is None:
                    raise ValueError("malformed native 429 evidence")
                result["http_429"] += 1
                blockers.add("NATIVE_HTTP_429_RETRY")
                continue
            if message.startswith("Transient error; retrying:"):
                match = re.fullmatch(
                    r"Transient error; retrying: endpoint=(.+), attempt=(0|[1-9]\d*), "
                    r"status=(408|5\d{2}), wait_ms=([1-9]\d*)", message,
                )
                if (match is None or component != "nautilus_hyperliquid::http::client"
                        or level.upper() not in ("WARN", "WARNING")):
                    blockers.add("NATIVE_TRANSIENT_RETRY_EVIDENCE_INCOMPLETE")
                else:
                    retries.append((index, timestamp, match[1], int(match[2]),
                                    int(match[3]), int(match[4])))
                continue
            if level.upper() in ("WARNING", "WARN", "ERROR", "CRITICAL"):
                blockers.add("NATIVE_RETRY_FALLBACK_OR_FAILURE")
            if message.startswith("Populated asset indices map"):
                if re.fullmatch(r"Populated asset indices map \(count=\d+\)", message) is None:
                    raise ValueError("malformed metadata phase")
                populated_indices.append((index, timestamp))
            if message.startswith("Bootstrapped "):
                if re.fullmatch(
                    r"Bootstrapped \d+ instruments with \d+ coin mappings", message,
                ) is None:
                    raise ValueError("malformed metadata completion")
                bootstraps += 1
                metadata_ns = timestamp
                metadata_index = index
            elif message.startswith("Fetched "):
                match = re.fullmatch(r"Fetched (\d+) bars for (.+)", message)
                if match is None or match[2] not in ledger or match[2] in completions:
                    raise ValueError("unmatched/duplicate completion")
                if timestamp < ledger[match[2]]["ts_ns"]:
                    raise ValueError("completion before dispatch")
                completions[match[2]] = timestamp
                completion_indices[match[2]] = index
            elif message.startswith("Info debited extra weight:"):
                match = re.fullmatch(
                    r"Info debited extra weight: endpoint=(CandleSnapshot .+), "
                    r"base_w=20, extra=([1-9]\d*)", message,
                )
                if match is None:
                    raise ValueError("unexpected/malformed native debit")
                endpoint = match[1]
                if re.fullmatch(CANDLE_ENDPOINT_PATTERN, endpoint) is None:
                    raise ValueError("debit endpoint differs from rc5 grammar")
                fields: dict[str, Any] = {}
                for name in ("coin", "interval", "start_time", "end_time"):
                    expression = (rf'{name}: ("(?:[^"\\]|\\.)*")'
                                  if name in ("coin", "interval") else rf"{name}: (\d+)")
                    values = re.findall(expression, endpoint)
                    if len(values) != 1:
                        raise ValueError("ambiguous native debit field")
                    fields[name] = json.loads(values[0])
                request_key = (fields["coin"], fields["interval"],
                               fields["start_time"], fields["end_time"])
                bar = identities.get(request_key)
                if bar is None or bar in debits or timestamp < ledger[bar]["ts_ns"]:
                    raise ValueError("unmatched/duplicate debit")
                debits[bar] = (int(match[2]), timestamp)
            elif any(term in message.lower() for term in (
                "fallback", "falling back", "infer", "retry", "rate limit", "429",
                "transport error", "request failed", "info request", "spotmeta",
                "allperpmetas", "outcomemeta", "perpdexs", "candlesnapshot",
            )):
                blockers.add("UNEXPECTED_OR_AMBIGUOUS_NATIVE_HTTP_RECORD")
        except (KeyError, TypeError, ValueError):
            blockers.add("NATIVE_RECORD_MALFORMED_UNMATCHED_OR_DUPLICATE")
    if bootstraps != 1 or metadata_ns is None:
        blockers.add("NATIVE_METADATA_COHORT_INCOMPLETE")
    if set(completions) != set(ledger) or len(completions) != 40:
        blockers.add("NATIVE_COMPLETION_COHORT_INCOMPLETE")
    # Retry authority is the exact native WARN record, never callback length.
    # rc5 attempt starts at zero and permits three retry records per request.
    retry_sequences: dict[str, tuple[int, int, int]] = {}
    warmup_retries: list[tuple[int, int]] = []
    metadata_retries: list[tuple[int, int]] = []
    metadata_order = {"SpotMeta": 0, "AllPerpMetas:0": 1, "OutcomeMeta": 2,
                      "AllPerpMetas:1": 3, "PerpDexs": 4}
    last_metadata_order = -1
    for index, timestamp, endpoint, attempt, status, wait_ms in retries:
        try:
            if attempt >= 3:
                raise ValueError("rc5 retry attempt exhausted")
            candle = re.fullmatch(CANDLE_ENDPOINT_PATTERN, endpoint)
            if candle is not None:
                request_key = (json.loads(candle[1]), json.loads(candle[2]),
                               int(candle[3]), int(candle[4]))
                bar = identities.get(request_key)
                if (bar is None or bar not in completions
                        or timestamp < ledger[bar]["ts_ns"]
                        or index >= completion_indices[bar]
                        or timestamp + wait_ms * 1_000_000 > completions[bar]):
                    raise ValueError("retry outside authorized warmup lifecycle")
                if bar in debits and (timestamp > debits[bar][1]
                                     or timestamp + wait_ms * 1_000_000 > debits[bar][1]):
                    raise ValueError("retry after successful response debit")
                request_id = bar
                cohort = "warmup"
            elif endpoint in ("SpotMeta", "AllPerpMetas", "OutcomeMeta", "PerpDexs"):
                if (run_start_ns is None or metadata_ns is None or metadata_index is None
                        or not run_start_ns <= timestamp < metadata_ns
                        or index >= metadata_index
                        or timestamp + wait_ms * 1_000_000 > metadata_ns):
                    raise ValueError("retry outside startup metadata lifecycle")
                request_id = endpoint
                # allPerpMetas occurs twice; the native completion of instrument
                # definitions separates the two source-bound startup requests.
                if endpoint == "AllPerpMetas":
                    if len(populated_indices) != 1:
                        raise ValueError("metadata occurrence is not uniquely bound")
                    populated_index, populated_ns = populated_indices[0]
                    phase = 0 if index < populated_index else 1
                    if ((phase == 0 and timestamp + wait_ms * 1_000_000 > populated_ns)
                            or (phase == 1 and timestamp < populated_ns)):
                        raise ValueError("metadata retry crosses request phase")
                    request_id += f":{phase}"
                elif populated_indices:
                    if len(populated_indices) != 1:
                        raise ValueError("ambiguous startup metadata phase")
                    populated_index, populated_ns = populated_indices[0]
                    early = endpoint in ("SpotMeta", "OutcomeMeta")
                    if ((early and (index >= populated_index
                                    or timestamp + wait_ms * 1_000_000 > populated_ns))
                            or (not early and (index <= populated_index
                                               or timestamp < populated_ns))):
                        raise ValueError("metadata retry in impossible startup phase")
                order = metadata_order[request_id]
                if order < last_metadata_order:
                    raise ValueError("metadata request order differs from rc5 startup")
                last_metadata_order = order
                cohort = "metadata"
            else:
                raise ValueError("unexpected retry endpoint")
            previous = retry_sequences.get(request_id)
            if previous is None:
                if attempt != 0:
                    raise ValueError("missing initial retry attempt")
            elif (attempt != previous[0] + 1 or index <= previous[1]
                  or timestamp < previous[2]):
                raise ValueError("duplicate/impossible retry sequence")
            retry_sequences[request_id] = (attempt, index, timestamp + wait_ms * 1_000_000)
            evidence = dict(request_id=request_id, cohort=cohort, endpoint=endpoint,
                            attempt=attempt, status=status, wait_ms=wait_ms,
                            ts_ns=timestamp, base_weight=20)
            result["matched_retries"].append(evidence)
            (warmup_retries if cohort == "warmup" else metadata_retries).append((timestamp, 20))
        except (KeyError, TypeError, ValueError):
            blockers.add("NATIVE_TRANSIENT_RETRY_EVIDENCE_INCOMPLETE")
    result["native_retry_count"] = len(result["matched_retries"])
    if result["native_retry_count"]:
        blockers.add("NATIVE_TRANSIENT_RETRY_ZERO_PREDICATE_FAILED")
    events: list[tuple[int, int]] = list(warmup_retries)
    for bar, dispatch in ledger.items():
        if bar not in completions:
            continue
        extra, debit_ns = debits.get(bar, (0, dispatch["ts_ns"]))
        if debit_ns > completions[bar]:
            blockers.add("NATIVE_DEBIT_AFTER_COMPLETION")
        actual = 20 + extra
        if actual > dispatch["reserved_weight"]:
            blockers.add("NATIVE_WEIGHT_EXCEEDS_RESERVATION")
        if metadata_ns is None or dispatch["ts_ns"] < metadata_ns + 60_000_000_000:
            blockers.add("NATIVE_METADATA_QUIET_BOUNDARY_UNPROVEN")
        events.append((dispatch["ts_ns"], actual))
        result["matched_requests"].append({
            **dispatch, "actual_extra": extra, "actual_weight": actual,
            "completion_ns": completions[bar], "debit_ns": None if extra == 0 else debit_ns,
        })
    peak = _rolling_weight(events)
    result["warmup_weight_per_60s"] = peak
    result["rest_weight_per_60s"] = _rolling_weight(
        events + metadata_retries + ([] if metadata_ns is None else [(metadata_ns, 100)])
    )
    if peak > 400 or result["rest_weight_per_60s"] > 600:
        blockers.add("NATIVE_REST_BUDGET_EXCEEDED")
    result["metadata_end_ns"] = metadata_ns
    result["matched_debits"] = len(debits)
    result["blockers"] = sorted(blockers)
    if result["http_429"]:
        result["status"] = "FAIL"
    elif blockers and blockers <= {"NATIVE_TRANSIENT_RETRY_ZERO_PREDICATE_FAILED",
                                   "NATIVE_REST_BUDGET_EXCEEDED"}:
        result["status"] = "FAIL"
    if not blockers:
        result.update(status="PASS", http_429=0, native_retry_count=0,
                      provider_throttle_events=0, transport_failures=0,
                      metadata_quiet_seconds=60, raw_response_reservations_verified=True)
    return result


WS_CONTROL_COMPONENT = "nautilus_network::websocket::client"


def parse_native_ws_controls(
    path: Path, *, native_http: dict[str, Any], epochs: list[dict[str, int]],
    outbound_forecast: list[tuple[int, int]], close_reserve: int,
    native_constant_upper_bound: int = 0,
    planned_reconnect_request_ns: int | None = None,
) -> dict[str, Any]:
    """B1d: control TRACE plus source-bound native dispatches, never HTTP bodies."""
    blockers: set[str] = set()
    result: dict[str, Any] = dict(status="INCOMPLETE", blockers=[], windows=[],
                                  path=str(path), sha256=native_http.get("sha256"),
                                  file_identity=native_http.get("file_identity"),
                                  begin_marker=native_http.get("begin_marker"),
                                  rc5_source=RC5_SOURCE,
                                  epochs=epochs, close_reserve=close_reserve,
                                  native_constant_upper_bound=native_constant_upper_bound,
                                  outbound_forecast=outbound_forecast)
    try:
        binding = native_http.get("log_binding")
        if (not isinstance(binding, dict) or binding.get("status") != "PASS"
                or binding.get("rc5_source") != RC5_SOURCE or binding.get("path") != str(path)
                or binding.get("begin_marker") != native_http.get("begin_marker")
                or binding.get("file_identity") != native_http.get("file_identity")
                or binding.get("sha256") != native_http.get("sha256")):
            raise ValueError("current-run immutable native binding is absent")
        raw, records = _read_bound_native_log(
            path, file_identity=tuple(binding["file_identity"]),
            begin_marker=binding["begin_marker"],
        )
        if sha256_hex(raw) != binding["sha256"]:
            raise ValueError("native file binding changed")
        if (not records or records[0]["component"] != native_http.get("begin_marker")
                or records[0]["message"] != NATIVE_STARTUP_SEPARATOR):
            raise ValueError("current-run native header missing")
        if type(native_constant_upper_bound) is not int or native_constant_upper_bound < 0:
            raise ValueError("native source forecast reserve is malformed")
        if type(close_reserve) is not int or not 0 <= close_reserve <= 2:
            raise ValueError("planned reconnect close reserve is ambiguous")
        if not 1 <= len(epochs) <= 2:
            raise ValueError("extra/missing connection epochs")
        previous_end = 0
        for epoch in epochs:
            start, end = epoch["start_ns"], epoch["end_ns"]
            if (type(start) is not int or type(end) is not int
                    or not 0 < start < end or start < previous_end):
                raise ValueError("malformed/unplanned connection epoch")
            previous_end = end
        if not outbound_forecast or any(type(t) is not int or type(w) is not int
                                        or t <= 0 or w < 0 for t, w in outbound_forecast):
            raise ValueError("native outbound forecast missing/malformed")
    except (OSError, UnicodeError, KeyError, TypeError, ValueError):
        result["blockers"] = ["WS_CONTROL_FILE_EPOCH_OR_FORECAST_INCOMPLETE"]
        return result
    pings: list[int] = []
    pongs: list[int] = []
    seen: set[bytes] = set()
    previous_timestamp = 0
    planned = _planned_ws_lifecycle(records, epochs, planned_reconnect_request_ns)
    for record in records:
        try:
            encoded = canonical_json_bytes(record)
            if encoded in seen:
                raise ValueError("duplicate native record")
            seen.add(encoded)
            timestamp = _log_timestamp_ns(record["timestamp"])
            component, message, level = record["component"], record["message"], record["level"]
            if not all(isinstance(v, str) for v in (component, message, level)):
                raise ValueError("malformed native record")
            if component.startswith(NATIVE_MARKER_PREFIX):
                if component != native_http["begin_marker"]:
                    raise ValueError("mixed current-run identity")
            candidate = message.startswith("Received ping") or message.startswith("Received pong")
            if candidate:
                if component != WS_CONTROL_COMPONENT or level != "TRACE":
                    raise ValueError("unmatched control component/level")
                if timestamp < previous_timestamp:
                    raise ValueError("control record ordering is ambiguous")
                previous_timestamp = timestamp
                if not any(e["start_ns"] <= timestamp <= e["end_ns"] for e in epochs):
                    raise ValueError("control outside known data connection epoch")
                if re.fullmatch(r"Received ping frame \([0-9]+ bytes\)", message):
                    pings.append(timestamp)
                elif message == "Received pong":
                    pongs.append(timestamp)
                else:
                    raise ValueError("malformed control message")
            if ((component.startswith("nautilus_network::websocket")
                 or component.startswith("nautilus_hyperliquid::websocket"))
                    and (level.upper() in ("WARN", "WARNING", "ERROR", "CRITICAL")
                         or "throttle" in message.lower() or "retry" in message.lower())):
                if canonical_json_bytes(record) not in planned:
                    raise ValueError("native WS retry/throttle/failure")
            if component == DATA_COMPONENT and message.startswith((
                "WebSocket error:", "Failed targeted ", "Requested full WebSocket reconnect",
            )):
                raise ValueError("native data-owned WS failure")
            if (component == WS_CONTROL_COMPONENT and message.startswith((
                "Reconnect aborted", "Reconnect interrupted", "Backoff interrupted",
                "Skipping reconnect handlers",
            ))):
                raise ValueError("reconnect lifecycle did not complete")
            if (component == WS_CONTROL_COMPONENT
                    and message.startswith(("Backing off", "Reconnection attempt"))
                    and canonical_json_bytes(record) not in planned):
                raise ValueError("unbound reconnect lifecycle")
        except (KeyError, TypeError, ValueError):
            blockers.add("WS_CONTROL_TRACE_AMBIGUITY_OR_FAILURE")
    if not pongs:
        blockers.add("WS_CONTROL_TRACE_MISSING")
    points = sorted(set(pings + pongs + [t for t, _ in outbound_forecast]
                        + [e["start_ns"] for e in epochs]))
    peak = 0
    for right in points:
        left = right - 60_000_000_000
        auto_pong = sum(left < t <= right for t in pings)
        protocol_pong = sum(left < t <= right for t in pongs)
        intersecting = sum(e["start_ns"] <= right and e["end_ns"] > left for e in epochs)
        auto_ping = protocol_pong + intersecting
        native_outbound = (sum(w for t, w in outbound_forecast if left < t <= right)
                           + native_constant_upper_bound)
        upper = native_outbound + auto_pong + auto_ping + close_reserve
        if intersecting > 2 or upper > 1000:
            blockers.add("WS_OUTBOUND_OR_EPOCH_CEILING")
        peak = max(peak, upper)
        result["windows"].append(dict(end_ns=right, auto_pong_count=auto_pong,
                                      protocol_pong_rx_count=protocol_pong,
                                      epochs_intersecting=intersecting,
                                      auto_ping_upper_bound=auto_ping,
                                      native_outbound_forecast=native_outbound,
                                      close_control_reserve=close_reserve,
                                      outbound_upper_bound=upper))
    result.update(blockers=sorted(blockers), max_rolling_60s=peak,
                  auto_pong_count=len(pings), protocol_pong_rx_count=len(pongs))
    if not blockers:
        result["status"] = "PASS"
    return result


def _planned_ws_lifecycle(
    records: list[dict[str, Any]], epochs: list[dict[str, int]], request_ns: int | None,
) -> set[bytes]:
    """rc5 controller delay + first attempt, uniquely inside the requested gap."""
    if type(request_ns) is not int or len(epochs) != 2:
        return set()
    candidates = [r for r in records if r["component"] == WS_CONTROL_COMPONENT
                  and r["message"].startswith(("Backing off", "Reconnection attempt"))]
    delays = [r for r in candidates if r["message"].startswith("Backing off")]
    attempts = [r for r in candidates if r["message"].startswith("Reconnection attempt")]
    if len(delays) > 1 or len(attempts) != 1:
        return set()
    attempt = attempts[0]
    attempt_ns = _log_timestamp_ns(attempt["timestamp"])
    if (attempt["level"] != "DEBUG"
            or re.fullmatch(r"Reconnection attempt 1 of (unlimited|[1-9]\d*)",
                            attempt["message"]) is None
            or not request_ns <= epochs[0]["end_ns"] <= attempt_ns <= epochs[1]["start_ns"]):
        return set()
    if delays:
        delay = delays[0]
        match = re.fullmatch(r"Backing off for ((?:0|[1-9]\d*)(?:\.\d+)?)s\.\.\.",
                             delay["message"])
        delay_ns = _log_timestamp_ns(delay["timestamp"])
        if (match is None or delay["level"] not in ("WARN", "WARNING")
                or records.index(delay) >= records.index(attempt)
                or not epochs[0]["end_ns"] <= delay_ns < attempt_ns
                or float(match[1]) <= 0 or not math.isfinite(float(match[1]))
                or delay_ns + math.ceil(float(match[1]) * 1e9) > attempt_ns):
            return set()
    return {canonical_json_bytes(r) for r in candidates}


def _apply_ws_proof(provider: dict[str, Any], control: dict[str, Any]) -> None:
    native = provider.get("native_http_evidence", {})
    for key in ("provider_throttle_events", "transport_failures"):
        if (control.get("status") != "PASS" or native.get("status") != "PASS"):
            if provider.get(key) == 0:
                provider.pop(key)
    if control.get("status") != "PASS":
        return
    provider.update(ws_connections=1, ws_new_connections_per_60s=2,
                    ws_active_plus_pending_subscriptions=100,
                    ws_outbound_messages_per_60s=control["max_rolling_60s"],
                    unrecovered_subscription_failures=0,
                    unplanned_disconnects=0, oom_or_process_kill=0)
    # Shared zeros require every owner. Preserve positives and unknown HTTP state.


PASS = 0
PROVIDER_DATA_INCOMPLETE = 2
APPLICATION_FAILURE = 3


def _external_minute_bar_type(instrument_id: str) -> str:
    """Build the shortest provider-supported external BarType via public APIs."""
    from nautilus_trader.model import (
        AggregationSource,
        BarAggregation,
        BarSpecification,
        BarType,
        InstrumentId,
        PriceType,
    )

    return str(
        BarType(
            InstrumentId.from_str(instrument_id),
            BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        )
    )


def _write_result(path: Path | None, payload: dict[str, Any]) -> None:
    encoded = canonical_json_bytes(payload) + b"\n"
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(encoded)
        temporary.replace(path)
    print(encoded.decode().strip())


def _ci_identity(instrument_id: str, provider_coin: str) -> tuple[PitUniverseSnapshot, RunManifest]:
    market_id = sha256_hex(f"HYPERLIQUID|MAIN|{provider_coin}".encode())
    expression = MarketExpression(
        market_id=market_id,
        dex="MAIN",
        provider_coin=provider_coin,
        instrument_id=instrument_id,
        expression_id=f"ci-public-{provider_coin.lower()}",
        instrument_metadata_version="PUBLIC_PROVIDER_PROBE_V1",
        instrument_metadata_hash=sha256_hex(f"PUBLIC_PROVIDER_PROBE_V1|{instrument_id}".encode()),
    )
    snapshot = PitUniverseSnapshot.create(observed_at_ns=time.time_ns(), expressions=(expression,))
    raw_sha = os.environ.get("E4_EXACT_HEAD", "0" * 40)
    git_sha = raw_sha if len(raw_sha) == 40 else "0" * 40
    raw_tree = os.environ.get("E4_EXACT_TREE", "0" * 40)
    git_tree = raw_tree if len(raw_tree) == 40 else "0" * 40
    manifest = RunManifest.create(
        run_id=f"e4-public-provider-{git_sha[:12]}",
        git_sha=git_sha,
        git_tree=git_tree,
        snapshot=snapshot,
        process_epoch=f"process-{git_sha[:12]}",
        continuity_epoch=f"continuity-{git_sha[:12]}",
        admission_epoch=f"admission-{git_sha[:12]}",
        capture_configuration={
            "expressions": [expression.model_dump(mode="json")],
            "probe": "BOUNDED_PUBLIC_PROVIDER_V1",
        },
        subscription_policy={
            "discovery": [market_id],
            "watch": [market_id],
            "actionable": [],
        },
        trial_ledger_id="public-provider-probe-v1",
    )
    return snapshot, manifest


def _run_live(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    from trader_assist_v0.nautilus_e4.host import build_capture_strategy, build_public_data_node

    if args.ci_instrument_id:
        snapshot, manifest = _ci_identity(args.ci_instrument_id, args.provider_coin)
        watch_market_ids = [snapshot.expressions[0].market_id]
    else:
        if args.manifest is None or args.snapshot is None or args.evidence_path is None:
            raise ValueError("live probe requires --manifest, --snapshot, and --evidence-path")
        manifest = RunManifest.model_validate_json(args.manifest.read_bytes())
        snapshot = PitUniverseSnapshot.model_validate_json(args.snapshot.read_bytes())
        watch_market_ids = args.watch_market_id
    if args.evidence_path is None:
        raise ValueError("live probe requires --evidence-path")
    discovery = frozenset(item.market_id for item in snapshot.expressions)
    policy = SubscriptionPolicy(
        discovery=discovery,
        watch=frozenset(watch_market_ids),
        actionable=frozenset(args.actionable_market_id),
    )
    bar_types = tuple(args.bar_type)
    if args.ci_instrument_id and not bar_types:
        bar_types = (_external_minute_bar_type(args.ci_instrument_id),)
    if not bar_types:
        raise ValueError("live public-provider proof requires a finalized Bar subscription")
    node = build_public_data_node()
    strategy: NautilusE4CaptureStrategy | None = None
    timer: threading.Timer | None = None
    try:
        strategy = build_capture_strategy(
            manifest=manifest,
            snapshot=snapshot,
            policy=policy,
            bar_types=bar_types,
            evidence_root=args.evidence_path,
        )
        node.add_strategy(strategy)
        handle = node.handle()
        timer = threading.Timer(args.run_seconds, handle.stop)
        timer.start()
        node.run()
    finally:
        if timer is not None:
            timer.cancel()
        node.dispose()
    assert strategy is not None
    observation = strategy.public_provider_observation
    passed = bool(observation["provider_observation_pass"])
    return (
        PASS if passed else PROVIDER_DATA_INCOMPLETE,
        {
            "schema_version": "E4_PUBLIC_PROVIDER_PROBE_RESULT_V1",
            "status": "PASS" if passed else "PROVIDER_DATA_INCOMPLETE",
            "failure_class": None if passed else "PROVIDER_OR_DATA_INCOMPLETENESS",
            "claim": "FRESH_PUBLIC_DATA_OBSERVED_FOR_EVERY_REQUESTED_SUBSCRIPTION_KIND",
            "bounded_run_seconds": args.run_seconds,
            "nautilus_version": NAUTILUS_VERSION,
            "exact_head": manifest.git_sha,
            "exact_tree": manifest.git_tree,
            "public_data_only": True,
            "zero_credentials": True,
            "zero_execution_client": True,
            "zero_signing": True,
            "zero_exchange_write": True,
            "PUBLIC_HYPERLIQUID_DATA_ONLY": True,
            "QUOTE_OBSERVED": observation["quote_observed"],
            "TRADE_OBSERVED": observation["trade_observed"],
            "BAR_SUBSCRIPTION_REGISTERED": observation["bar_subscription_registered"],
            "FINALIZED_BAR_CALLBACK_OBSERVED": observation["finalized_bar_callback_observed"],
            "FINALIZED_BAR_EVIDENCE_PERSISTED": observation["finalized_bar_evidence_persisted"],
            "observation": observation,
            "capture_health": strategy.capture_health,
        },
    )



@dataclass
class _ResourceSchedule:
    """Absolute measured slots, a finite tail, and no invented catch-up samples."""

    overall_deadline: float
    anchor: float | None = None
    next_sample: float = 0.0
    attempts: int = 0

    @property
    def deadline(self) -> float:
        return min(self.overall_deadline, self.anchor + 930 if self.anchor is not None
                   else self.overall_deadline)

    def due(self, now: float) -> bool:
        return now >= self.next_sample and now <= self.deadline and self.attempts < 33

    def attempted(self, now: float, *, accepted: bool) -> None:
        self.attempts += 1
        if self.anchor is None and accepted:
            self.anchor = now
        self.next_sample = (now + 30 if self.anchor is None else
                            self.anchor + (math.floor((now - self.anchor) / 30) + 1) * 30)

    @staticmethod
    def complete(resources: list[dict[str, Any]]) -> bool:
        return (len(resources) >= 16
                and resources[-1]["ts_ns"] - resources[0]["ts_ns"] >= 900_000_000_000
                and all(0 < b["ts_ns"] - a["ts_ns"] <= 60_000_000_000
                        for a, b in pairwise(resources)))


@dataclass
class _ResourceSampler:
    previous_cpu: tuple[int, int] | None = None
    swap_baseline: tuple[int, int] | None = None
    initial_bytes: int = 0
    initial_sample_ns: int | None = None

    def collect(self, root: Path) -> dict[str, Any]:
        memory = {line.split()[0].rstrip(":"): int(line.split()[1])
                  for line in Path("/proc/meminfo").read_text().splitlines()}
        cpu = [int(v) for v in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
        if len(cpu) != 8 or any(v < 0 for v in cpu):
            raise ValueError("CPU fields incomplete")
        current_cpu = (sum(cpu), cpu[3] + cpu[4])
        cpu_percent = 0.0
        if self.previous_cpu is not None:
            delta = current_cpu[0] - self.previous_cpu[0]
            idle = current_cpu[1] - self.previous_cpu[1]
            if delta <= 0 or not 0 <= idle <= delta:
                raise ValueError("CPU sampling is ambiguous")
            cpu_percent = 100 * (1 - idle / delta)
        swaps = dict(line.split() for line in Path("/proc/vmstat").read_text().splitlines())
        current_swap = (int(swaps["pswpin"]), int(swaps["pswpout"]))
        baseline = self.swap_baseline or current_swap
        if any(current < start for current, start in zip(current_swap, baseline, strict=True)):
            raise ValueError("swap sampling is ambiguous")
        filesystem = os.statvfs("/")
        total = filesystem.f_blocks * filesystem.f_frsize
        used = (filesystem.f_blocks - filesystem.f_bfree) * filesystem.f_frsize
        evidence_bytes = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        # Timestamp only after every field is actually measured successfully.
        now = time.time_ns()
        initial_ns = self.initial_sample_ns if self.initial_sample_ns is not None else now
        initial_bytes = self.initial_bytes if self.initial_sample_ns is not None else evidence_bytes
        duration = max(1, now - initial_ns) / 1e9
        projected = used + max(0, evidence_bytes - initial_bytes) / duration * 604800
        sample = dict(ts_ns=now, memory_used_percent=100 * (
            1 - memory["MemAvailable"] / memory["MemTotal"]), cpu_percent=cpu_percent,
            swap_activity=sum(current_swap) - sum(baseline), root_used_percent=100 * used / total,
            root_7d_projection_percent=100 * projected / total)
        if any(not math.isfinite(v) or v < 0 for v in sample.values()):
            raise ValueError("resource measurement invalid")
        self.previous_cpu, self.swap_baseline = current_cpu, baseline
        self.initial_sample_ns, self.initial_bytes = initial_ns, initial_bytes
        return sample


async def _run_l0_qualification(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    """Use the existing production node/consumer only; never start a host service."""
    from nautilus_trader.common import logging_sync_to_disk

    from trader_assist_v0.multi_asset_shadow.production import (
        E4ThreeSetupProductionApplication,
        _ObservedQueue,
        compose_three_setup_application,
        load_three_setup_config,
    )

    if args.config_path is None or args.evidence_path is None:
        raise ValueError("L0 qualification requires config and a new evidence root")
    config = load_three_setup_config(args.config_path)
    if not config.data_collection_only or args.ci_instrument_id or args.actionable_market_id:
        raise ValueError("L0 qualification requires the exact data-only zero-write profile")
    application = compose_three_setup_application(
        config=config, qualification_root=args.evidence_path,
    )
    if not isinstance(application, E4ThreeSetupProductionApplication):
        raise ValueError("qualification requires the existing E4 production application")
    capture = application.capture
    manifest = capture.capture_session.manifest
    observation = capture.qualification_observation
    if observation is None:
        raise ValueError("qualification observation was not enabled")
    shutdown = asyncio.Event()
    run = asyncio.create_task(application.run(shutdown))
    root = args.evidence_path.absolute()
    log_path = root / "native.jsonl"
    file_identity = None
    started = time.monotonic()
    resources: list[dict[str, Any]] = []
    sample_failures: list[str] = []
    queue_cohorts: list[dict[str, Any]] = []
    sampler = _ResourceSampler()
    schedule = _ResourceSchedule(started + args.run_seconds)
    try:
        while not run.done() and time.monotonic() < schedule.deadline:
            now = time.time_ns()
            if file_identity is None and log_path.exists():
                state = log_path.lstat()
                if stat.S_ISREG(state.st_mode):
                    file_identity = (state.st_dev, state.st_ino)
            if capture.warmup_health.get("readiness") == "READY" and not observation.requests:
                capture.request_l0_reconnect()
            if observation.window_start_ns is not None:
                if schedule.due(time.monotonic()):
                    accepted = False
                    try:
                        sample = sampler.collect(root)
                        cohort = dict(capture.l0_health["queue_states"])
                        resources.append(sample)
                        queue_cohorts.append(cohort)
                        accepted = True
                    except (OSError, KeyError, ValueError, ZeroDivisionError, IndexError):
                        sample_failures.append("TARGET_RESOURCE_SAMPLE_INCOMPLETE")
                    schedule.attempted(time.monotonic(), accepted=accepted)
                # The original BAR cutoff cannot preempt the final measured sample.
                if (now >= observation.window_start_ns + 900_000_000_000
                        and schedule.complete(resources)):
                    break
                if schedule.attempts >= 33:
                    sample_failures.append("TARGET_RESOURCE_SAMPLE_BOUND_EXHAUSTED")
                    break
            await asyncio.sleep(0.1)
    finally:
        capture.finish_l0_qualification()
        shutdown.set()
        await run
    sync_succeeded = False
    try:
        synced = logging_sync_to_disk()
        sync_succeeded = synced is None or synced is True
    except Exception:
        sample_failures.append("NATIVE_LOG_SYNC_UNPROVEN")
    health = capture.l0_health
    native = parse_native_http_log(
        log_path, manifest=manifest, dispatches=health["history_requests"],
        file_identity=file_identity or (-1, -1), sync_succeeded=sync_succeeded,
    )
    provider = dict(native)
    provider["native_http_evidence"] = native
    provider["rest_weight_per_60s"] = native.get("rest_weight_per_60s")
    # Native socket/outbound counts and every zero predicate require exact proof.
    # An unknown is retained rather than synthesized from observed data callbacks.
    if resources:
        provider["swap_activity"] = max(r["swap_activity"] for r in resources)
    registrations = health["native_registered"]
    counts = {kind: sum(r["kind"] == kind for r in registrations)
              for kind in ("bar", "bbo", "trade", "depth10")}
    unique = {(r["kind"], r["identity"]) for r in registrations}
    expected_registrations = {("bar", bar) for bar in observation.bars}
    expected_registrations.update(
        (kind, expression.instrument_id) for expression in application.snapshot.expressions
        for kind in ("bbo", "trade", "depth10")
    )
    forecast = {}
    if (counts == {"bar": 40, "bbo": 20, "trade": 20, "depth10": 20}
            and len(unique) == 100 and unique == expected_registrations
            and set(health["registered_bars"]) == set(observation.bars)):
        forecast = dict(bars=40, bbo=20, trade=20, depth10=20,
                        native_subscriptions=100, rc5_source=RC5_SOURCE)
    control: dict[str, Any] = dict(status="INCOMPLETE", blockers=["WS_CONTROL_BINDING_MISSING"])
    try:
        binding = native["log_binding"]
        if binding["status"] != "PASS":
            raise ValueError("native file binding is unproven")
        raw, records = _read_bound_native_log(
            log_path, file_identity=tuple(binding["file_identity"]),
            begin_marker=binding["begin_marker"],
        )
        if sha256_hex(raw) != binding["sha256"]:
            raise ValueError("native forecast file changed")
        first_ns = _log_timestamp_ns(records[0]["timestamp"])
        end_ns = max(_log_timestamp_ns(r["timestamp"]) for r in records) + 1
        if (not forecast or observation.disconnected_ns is None
                or observation.connected_ns is None or observation.requests != 1):
            raise ValueError("exact native registration/reconnect proof missing")
        socket_events = health["socket_events"]
        if any(e["client_id"] != "HYPERLIQUID"
               or e["endpoint"] != "hyperliquid-data-streams" for e in socket_events):
            raise ValueError("unexpected WS client/endpoint")
        disconnects = [e for e in socket_events if e["state"] == "DISCONNECTED"]
        connects = [e for e in socket_events if e["state"] == "CONNECTED"]
        if (len(disconnects) != 1 or len(connects) > 2
                or any(e["ts_ns"] < observation.request_ns for e in disconnects)):
            raise ValueError("extra/unplanned data connection epoch")
        epochs = [dict(start_ns=first_ns, end_ns=observation.disconnected_ns),
                  dict(start_ns=observation.connected_ns, end_ns=end_ns)]
        planned = _planned_ws_lifecycle(records, epochs, observation.request_ns)
        native_outbound = [(first_ns, 0)]
        # Retain both exact 100-request cohorts as an upper bound in every window.
        registration_upper = 200
        # Reserve the full-run rc5 30s adapter-heartbeat count in EVERY window,
        # conservatively including delayed/catch-up ticks.
        heartbeat_upper = (end_ns - first_ns + 29_999_999_999) // 30_000_000_000 + 1
        for r in records:
            if r["message"].startswith("Sending unsubscribe payload"):
                if (r["component"] != "nautilus_hyperliquid::websocket::handler"
                        or r["level"] != "DEBUG"
                        or re.fullmatch(r"Sending unsubscribe payload \([0-9]+ bytes\)",
                                        r["message"]) is None):
                    raise ValueError("unbound native unsubscribe forecast")
                registration_upper += 1
            if (r["level"] in ("WARN", "WARNING", "ERROR", "CRITICAL")
                    and canonical_json_bytes(r) not in planned
                    and (r["component"] not in (HTTP_COMPONENT, DATA_COMPONENT)
                         or _instrument_bookkeeping(r["component"], r["level"], r["message"])
                         or _non_http_data_record(r["component"], r["message"]))):
                sample_failures.append("NATIVE_NON_HTTP_SAFETY_FAILURE_OR_AMBIGUITY")
        control = parse_native_ws_controls(
            log_path, native_http=native, epochs=epochs,
            outbound_forecast=native_outbound, close_reserve=2,
            native_constant_upper_bound=heartbeat_upper + registration_upper,
            planned_reconnect_request_ns=observation.request_ns,
        )
        control["adapter_heartbeat_whole_run_upper_bound"] = heartbeat_upper
        control["socket_events"] = socket_events
    except (OSError, KeyError, TypeError, ValueError):
        sample_failures.append("WS_NATIVE_FORECAST_EPOCH_OR_ZERO_PREDICATE_INCOMPLETE")
    provider["native_ws_control_evidence"] = control
    _apply_ws_proof(provider, control)
    capture_health = capture.capture_health
    provider["storage_failures"] = capture_health.get("storage_failures")
    queue = application.e4_runtime._queue
    finite = [queue.health()] if isinstance(queue, _ObservedQueue) else []
    if isinstance(queue, _ObservedQueue):
        provider["queue_or_buffer_overflow"] = queue.overflows + sum(
            "OVERFLOW" in f or f == "UNBOUNDED_STREAM_INPUT" for f in observation.failures)
        fanout = capture_health.get("markettruth_fanout", {})
        if isinstance(fanout, dict) and type(fanout.get("publish_error_count")) is int:
            provider["dropped_events"] = (queue.overflows + fanout["publish_error_count"]
                                          + len(capture_health["admitted_observer_failures"]))
    finite.append(health["live_processing_buffer"])
    finite.extend(dict(capacity=observation.retention_capacity, max_depth=len(values),
                       end_depth=len(values)) for values in observation.live.values())
    monotonic: bool | None = None
    if len(queue_cohorts) >= 3 and all(cohort for cohort in queue_cohorts):
        channels = set.intersection(*(set(cohort) for cohort in queue_cohorts))
        if channels:
            monotonic = any(
                a[channel]["depth"] < b[channel]["depth"] < c[channel]["depth"]
                for a, b, c in zip(
                    queue_cohorts, queue_cohorts[1:], queue_cohorts[2:], strict=False
                )
                for channel in channels
            )
    queues = dict(native_capacity="NOT_APPLICABLE_UNBOUNDED",
                  monitor_observed=health["queue_events"] > 0,
                  monotonic_backlog_3_cohorts=monotonic, finite=finite,
                  native_cohorts=queue_cohorts)
    report = evaluate_qualification(manifest, observation, time.time_ns(),
                                    provider, resources, queues, forecast)
    report["native_registrations"] = registrations
    report["blockers"] = sorted(set(report["blockers"] + sample_failures + native["blockers"]
                                    + control["blockers"]))
    if report["blockers"]:
        report["status"] = "INCOMPLETE"
    report.pop("digest")
    report["digest"] = sha256_hex(canonical_json_bytes(report))
    return (PASS if report["status"] == "PASS" else PROVIDER_DATA_INCOMPLETE), report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-path", type=Path)
    parser.add_argument("--qualify-l0", action="store_true")
    parser.add_argument("--config-path", type=Path)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--watch-market-id", action="append", default=[])
    parser.add_argument("--actionable-market-id", action="append", default=[])
    parser.add_argument("--bar-type", action="append", default=[])
    parser.add_argument("--ci-instrument-id")
    parser.add_argument("--provider-coin", default="ETH")
    parser.add_argument("--run-seconds", type=int, default=0)
    args = parser.parse_args()
    maximum = 2400 if args.qualify_l0 else 300
    if args.run_seconds < 0 or args.run_seconds > maximum:
        raise SystemExit(f"--run-seconds must be between 0 and {maximum}")
    if args.qualify_l0 and args.run_seconds < 900:
        raise SystemExit("L0 qualification requires at least 900 seconds")
    proof = assert_public_only(env=os.environ)
    from trader_assist_v0.nautilus_e4.host import assert_exact_nautilus_version

    assert_exact_nautilus_version()
    if args.run_seconds == 0:
        _write_result(
            args.result_path,
            {
                "schema_version": "E4_PUBLIC_PROVIDER_PROBE_RESULT_V1",
                "status": "NOT_RUN_CONFIG_CHECK_ONLY",
                "failure_class": None,
                "zero_write_proof": proof.model_dump(mode="json"),
            },
        )
        return PASS
    try:
        exit_code, result = (asyncio.run(_run_l0_qualification(args))
                             if args.qualify_l0 else _run_live(args))
    except Exception as exc:
        _write_result(
            args.result_path,
            {
                "schema_version": "E4_PUBLIC_PROVIDER_PROBE_RESULT_V1",
                "status": "APPLICATION_FAILURE",
                "failure_class": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "bounded_run_seconds": args.run_seconds,
                "public_data_only": True,
                "zero_credentials": True,
                "zero_execution_client": True,
                "zero_signing": True,
                "zero_exchange_write": True,
            },
        )
        return APPLICATION_FAILURE
    _write_result(args.result_path, result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
