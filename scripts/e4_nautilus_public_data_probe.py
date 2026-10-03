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
    if (not isinstance(native, dict) or native.get("status") != "PASS"
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
    }
    if sync_succeeded is not True:
        blockers.add("NATIVE_LOG_SYNC_UNPROVEN")
    try:
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode)
                or (before.st_dev, before.st_ino) != file_identity
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
        if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                or (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or not raw.endswith(b"\n")):
            raise ValueError("native log is not a complete stable file")
        result["sha256"] = sha256_hex(raw)
        records = [json.loads(line, object_pairs_hook=_unique_object)
                   for line in raw.decode("utf-8").splitlines()]
        if not records:
            raise ValueError("empty native file")
    except (OSError, ValueError, TypeError, UnicodeError):
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
    begins = bootstraps = 0
    title_count = 0
    seen_records: set[bytes] = set()
    metadata_ns: int | None = None
    completions: dict[str, int] = {}
    debits: dict[str, tuple[int, int]] = {}
    for index, record in enumerate(records):
        try:
            if not isinstance(record, dict):
                raise ValueError("native record must be an object")
            encoded_record = canonical_json_bytes(record)
            if encoded_record in seen_records:
                raise ValueError("duplicate native record")
            seen_records.add(encoded_record)
            message, component = record["message"], record["component"]
            if not isinstance(message, str) or not isinstance(component, str):
                raise ValueError("native message/component malformed")
            timestamp = _log_timestamp_ns(record["timestamp"])
            level = record["level"]
            if not isinstance(level, str) or level.upper() not in (
                "TRACE", "DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"
            ):
                raise ValueError("native level malformed")
            if component.startswith(NATIVE_MARKER_PREFIX):
                if component != native_marker(manifest):
                    blockers.add("NATIVE_LOG_RUN_BOUNDARY_AMBIGUITY")
                if message == NATIVE_STARTUP_SEPARATOR:
                    if index == 0:
                        begins += 1
                    elif begins != 1:
                        blockers.add("NATIVE_LOG_RUN_BOUNDARY_AMBIGUITY")
                    # Native headers contain separators at both ends. A second
                    # header is rejected below by the repeated title record.
                if message.strip().startswith("NAUTILUS TRADER -") :
                    title_count += 1
                    if title_count > 1:
                        blockers.add("NATIVE_LOG_RUN_BOUNDARY_AMBIGUITY")
            if index == 0 and (component != native_marker(manifest)
                              or message != NATIVE_STARTUP_SEPARATOR):
                blockers.add("NATIVE_LOG_PRE_MARKER_CONTENT")
            if begins != 1:
                blockers.add("NATIVE_LOG_RUN_BOUNDARY_AMBIGUITY")
            if level.upper() == "TRACE":
                # B1d controls are audited separately; raw HTTP is never authority.
                continue
            native = component.startswith("nautilus_hyperliquid::")
            relevant = (message.startswith(("Fetched ", "Info debited extra weight:",
                                           "Bootstrapped ", "429 Too Many Requests;",
                                           "Transient error; retrying:")))
            if relevant and not native:
                raise ValueError("unmatched native component")
            if not native:
                continue
            if level.upper() in ("WARNING", "WARN", "ERROR", "CRITICAL"):
                blockers.add("NATIVE_RETRY_FALLBACK_OR_FAILURE")
            if re.fullmatch(r"Bootstrapped \d+ instruments with \d+ coin mappings", message):
                bootstraps += 1
                metadata_ns = timestamp
            elif message.startswith("Fetched "):
                match = re.fullmatch(r"Fetched (\d+) bars for (.+)", message)
                if match is None or match[2] not in ledger or match[2] in completions:
                    raise ValueError("unmatched/duplicate completion")
                if timestamp < ledger[match[2]]["ts_ns"]:
                    raise ValueError("completion before dispatch")
                completions[match[2]] = timestamp
            elif message.startswith("Info debited extra weight:"):
                match = re.fullmatch(
                    r"Info debited extra weight: endpoint=(CandleSnapshot .+), "
                    r"base_w=20, extra=([1-9]\d*)", message,
                )
                if match is None:
                    raise ValueError("unexpected/malformed native debit")
                endpoint = match[1]
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
    if begins != 1:
        blockers.add("NATIVE_LOG_RUN_BOUNDARY_AMBIGUITY")
    if bootstraps != 1 or metadata_ns is None:
        blockers.add("NATIVE_METADATA_COHORT_INCOMPLETE")
    if set(completions) != set(ledger) or len(completions) != 40:
        blockers.add("NATIVE_COMPLETION_COHORT_INCOMPLETE")
    events: list[tuple[int, int]] = []
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
        events + ([] if metadata_ns is None else [(metadata_ns, 100)])
    )
    if peak > 400 or result["rest_weight_per_60s"] > 600:
        blockers.add("NATIVE_REST_BUDGET_EXCEEDED")
    result["metadata_end_ns"] = metadata_ns
    result["matched_debits"] = len(debits)
    result["blockers"] = sorted(blockers)
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
) -> dict[str, Any]:
    """B1d: control TRACE plus source-bound native dispatches, never HTTP bodies."""
    blockers: set[str] = set()
    result: dict[str, Any] = dict(status="INCOMPLETE", blockers=[], windows=[],
                                  path=str(path), sha256=native_http.get("sha256"),
                                  rc5_source=RC5_SOURCE,
                                  epochs=epochs, close_reserve=close_reserve,
                                  native_constant_upper_bound=native_constant_upper_bound,
                                  outbound_forecast=outbound_forecast)
    try:
        if native_http.get("status") != "PASS" or native_http.get("blockers") != []:
            raise ValueError("current-run complete native evidence is absent")
        raw = path.read_bytes()
        state = path.lstat()
        if (not stat.S_ISREG(state.st_mode) or path.resolve() != path.absolute()
                or [state.st_dev, state.st_ino] != native_http.get("file_identity")
                or sha256_hex(raw) != native_http.get("sha256")):
            raise ValueError("native file binding changed")
        records = [json.loads(line, object_pairs_hook=_unique_object)
                   for line in raw.decode().splitlines()]
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
                raise ValueError("native WS retry/throttle/failure")
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
    previous_cpu: tuple[int, int] | None = None
    swap_baseline: tuple[int, int] | None = None
    initial_bytes = 0
    initial_sample_ns = None
    next_sample = 0.0
    try:
        while not run.done() and time.monotonic() - started < args.run_seconds:
            now = time.time_ns()
            if file_identity is None and log_path.exists():
                state = log_path.lstat()
                if stat.S_ISREG(state.st_mode):
                    file_identity = (state.st_dev, state.st_ino)
            if capture.warmup_health.get("readiness") == "READY" and not observation.requests:
                capture.request_l0_reconnect()
            if observation.window_start_ns is not None:
                if time.monotonic() >= next_sample:
                    try:
                        memory = {line.split()[0].rstrip(":"): int(line.split()[1])
                                  for line in Path("/proc/meminfo").read_text().splitlines()}
                        cpu = [int(v) for v in Path("/proc/stat").read_text().splitlines()[0]
                               .split()[1:9]]
                        current_cpu = (sum(cpu), cpu[3] + cpu[4])
                        cpu_percent = 0.0
                        if previous_cpu is not None:
                            delta = current_cpu[0] - previous_cpu[0]
                            if delta <= 0:
                                raise ValueError("CPU sampling is ambiguous")
                            cpu_percent = 100 * (1 - (current_cpu[1] - previous_cpu[1]) / delta)
                        previous_cpu = current_cpu
                        swaps = dict(line.split() for line in Path("/proc/vmstat").read_text()
                                     .splitlines())
                        current_swap = (int(swaps["pswpin"]), int(swaps["pswpout"]))
                        if swap_baseline is None:
                            swap_baseline = current_swap
                        swap_delta = sum(current_swap) - sum(swap_baseline)
                        filesystem = os.statvfs("/")
                        total = filesystem.f_blocks * filesystem.f_frsize
                        used = (filesystem.f_blocks - filesystem.f_bfree) * filesystem.f_frsize
                        evidence_bytes = sum(p.stat().st_size for p in root.rglob("*")
                                             if p.is_file())
                        if initial_sample_ns is None:
                            initial_sample_ns, initial_bytes = now, evidence_bytes
                        duration = max(1, now - initial_sample_ns) / 1e9
                        projected = (used + max(0, evidence_bytes - initial_bytes)
                                     / duration * 604800)
                        resources.append(dict(
                            ts_ns=now, memory_used_percent=100 * (
                                1 - memory["MemAvailable"] / memory["MemTotal"]),
                            cpu_percent=cpu_percent, swap_activity=swap_delta,
                            root_used_percent=100 * used / total,
                            root_7d_projection_percent=100 * projected / total,
                        ))
                        queue_cohorts.append(dict(capture.l0_health["queue_states"]))
                    except (OSError, KeyError, ValueError, ZeroDivisionError):
                        sample_failures.append("TARGET_RESOURCE_SAMPLE_INCOMPLETE")
                    next_sample = time.monotonic() + 60
                if now >= observation.window_start_ns + 900_000_000_000:
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
    forecast = {}
    if (counts == {"bar": 40, "bbo": 20, "trade": 20, "depth10": 20}
            and len(unique) == 100 and set(health["registered_bars"]) == set(observation.bars)):
        forecast = dict(bars=40, bbo=20, trade=20, depth10=20,
                        native_subscriptions=100, rc5_source=RC5_SOURCE)
    control: dict[str, Any] = dict(status="INCOMPLETE", blockers=["WS_CONTROL_BINDING_MISSING"])
    try:
        records = [json.loads(line, object_pairs_hook=_unique_object)
                   for line in log_path.read_text().splitlines()]
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
        native_outbound = [(first_ns, 0)]
        # Retain both exact 100-request cohorts as an upper bound in every window.
        registration_upper = 200
        # Reserve the full-run rc5 30s adapter-heartbeat count in EVERY window,
        # conservatively including delayed/catch-up ticks.
        heartbeat_upper = (end_ns - first_ns + 29_999_999_999) // 30_000_000_000 + 1
        for r in records:
            if (r["component"] == "nautilus_hyperliquid::websocket::handler"
                    and re.fullmatch(r"Sending unsubscribe payload \([0-9]+ bytes\)",
                                     r["message"])):
                registration_upper += 1
            if r["level"] in ("WARN", "WARNING", "ERROR", "CRITICAL"):
                raise ValueError("native warning/error prevents zero-failure proof")
        control = parse_native_ws_controls(
            log_path, native_http=native, epochs=epochs,
            outbound_forecast=native_outbound, close_reserve=2,
            native_constant_upper_bound=heartbeat_upper + registration_upper,
        )
        control["adapter_heartbeat_whole_run_upper_bound"] = heartbeat_upper
        control["socket_events"] = socket_events
        if control["status"] == "PASS":
            provider.update(ws_connections=1, ws_new_connections_per_60s=2,
                            ws_active_plus_pending_subscriptions=100,
                            ws_outbound_messages_per_60s=control["max_rolling_60s"],
                            provider_throttle_events=0, unrecovered_subscription_failures=0,
                            unplanned_disconnects=0, oom_or_process_kill=0)
    except (OSError, KeyError, TypeError, ValueError):
        sample_failures.append("WS_NATIVE_FORECAST_EPOCH_OR_ZERO_PREDICATE_INCOMPLETE")
    provider["native_ws_control_evidence"] = control
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
