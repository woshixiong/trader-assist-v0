"""Bounded Three Setup read projection over E4's sole durable market admission log.

This module has no market transport or durable market-history writer. Its SQLite
connection is private, in-memory only, and exists to retain the mature domain
queries while E4 remains the source of every reconstructed market fact.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from typing import TYPE_CHECKING

from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

from .data import aggregate_closed_5m
from .hyperliquid_public import PublicDataError
from .integration import PublicL2Snapshot, ScannerPublicSnapshot
from .models import ClosedBar, MarketLifecycle, RegistryMarket
from .outcome_engine import OneMinuteBar
from .planning import (
    HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS,
    HARD_MAX_SPREAD_BPS,
    PublicBbo,
    Side,
    assess_l2,
)
from .runtime import RuntimeReadinessSnapshot
from .shadow_records import EvidenceStore as DomainEvidenceStore
from .shadow_records.records import E4MarketBarReference, OutcomeE4BarReference

if TYPE_CHECKING:
    from .registry import MarketRegistryManager

_BAR_STEP = {"1m": 60_000, "5m": 300_000}
_BAR_TYPE = re.compile(r"(?:^|[-_])(1|5)[-_]MINUTE(?:[-_]|$)", re.IGNORECASE)
_MAX_5M = 4_096
_MAX_1M = 4_096


def _native_levels(raw: object) -> tuple[tuple[Decimal, Decimal], ...]:
    if not isinstance(raw, list) or not raw or len(raw) > 10:
        raise E4ProjectionError("E4 Depth10 lacks native levels")
    parsed = []
    padded = False
    for item in raw:
        if not isinstance(item, list) or len(item) != 2:
            raise E4ProjectionError("E4 Depth10 level shape is invalid")
        try:
            price, size = Decimal(str(item[0])), Decimal(str(item[1]))
        except (ArithmeticError, ValueError) as exc:
            raise E4ProjectionError("E4 Depth10 level is invalid") from exc
        if not price.is_finite() or not size.is_finite() or price < 0 or size < 0:
            raise E4ProjectionError("E4 Depth10 level is invalid")
        if price == 0 or size == 0:
            padded = True
            continue
        if padded:
            raise E4ProjectionError("E4 Depth10 has an interior empty level")
        parsed.append((price, size))
    if not parsed:
        raise E4ProjectionError("E4 Depth10 has no liquid level")
    return tuple(parsed)


class E4ProjectionError(ValueError):
    """The domain cannot prove a requested E4 market fact."""


class E4MemoryBarStore:
    """Legacy query shape backed only by a bounded process-local read projection."""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """CREATE TABLE closed_bars (
            market_id TEXT, interval TEXT, open_time_ms INTEGER, canonical_hash TEXT,
            registry_version TEXT, registry_content_hash TEXT, finality_identity TEXT,
            finalized_at_ms INTEGER, payload_json BLOB,
            PRIMARY KEY(market_id, interval, open_time_ms))"""
        )

    def put(
        self,
        bar: ClosedBar,
        *,
        registry_version: str,
        registry_content_hash: str,
        finality_identity: str,
    ) -> None:
        row = self.connection.execute(
            "SELECT canonical_hash FROM closed_bars "
            "WHERE market_id=? AND interval=? AND open_time_ms=?",
            (bar.market_id, bar.interval, bar.open_time_ms),
        ).fetchone()
        if row is not None:
            if row[0] != bar.canonical_hash:
                raise E4ProjectionError("conflicting E4 bar projection slot")
            return
        self.connection.execute(
            "INSERT INTO closed_bars VALUES (?,?,?,?,?,?,?,?,?)",
            (
                bar.market_id,
                bar.interval,
                bar.open_time_ms,
                bar.canonical_hash,
                registry_version,
                registry_content_hash,
                finality_identity,
                int(bar.received_at.timestamp() * 1_000),
                bar.model_dump_json().encode(),
            ),
        )
        self.connection.commit()

    def tail_bars(
        self, market_id: str, *, at_or_before_ms: int, limit: int, interval: str = "5m"
    ) -> tuple[ClosedBar, ...]:
        rows = self.connection.execute(
            "SELECT payload_json FROM closed_bars WHERE market_id=? AND interval=? "
            "AND open_time_ms<=? ORDER BY open_time_ms DESC LIMIT ?",
            (market_id, interval, at_or_before_ms, limit),
        ).fetchall()
        return tuple(ClosedBar.model_validate_json(row[0]) for row in reversed(rows))

    def bars_between(
        self, market_id: str, *, after_open_time_ms: int, at_or_before_ms: int, interval: str = "5m"
    ) -> tuple[ClosedBar, ...]:
        rows = self.connection.execute(
            "SELECT payload_json FROM closed_bars WHERE market_id=? AND interval=? "
            "AND open_time_ms>? AND open_time_ms<=? ORDER BY open_time_ms",
            (market_id, interval, after_open_time_ms, at_or_before_ms),
        ).fetchall()
        return tuple(ClosedBar.model_validate_json(row[0]) for row in rows)

    def last_open(self, market_id: str) -> int | None:
        row = self.connection.execute(
            "SELECT MAX(open_time_ms) FROM closed_bars WHERE market_id=? AND interval='5m'",
            (market_id,),
        ).fetchone()
        return None if row[0] is None else int(row[0])

    def is_contiguous_5m(self, market_id: str) -> bool:
        row = self.connection.execute(
            "SELECT COUNT(*), MIN(open_time_ms), MAX(open_time_ms) FROM closed_bars "
            "WHERE market_id=? AND interval='5m'",
            (market_id,),
        ).fetchone()
        return bool(row[0] == 0 or row[2] - row[1] == (row[0] - 1) * 300_000)

    def close(self) -> None:
        self.connection.close()


class E4MarketTruthProjection:
    """One E4-backed read authority; all mutable market indexes are disposable."""

    def __init__(
        self,
        *,
        e4_store: E4EvidenceStore,
        domain_evidence: DomainEvidenceStore,
        registry: MarketRegistryManager,
        manifest: RunManifest,
        snapshot: PitUniverseSnapshot,
        warmup_health: Callable[[], dict[str, object]],
        capture_health: Callable[[], dict[str, object]],
        clock_ms: Callable[[], int],
    ) -> None:
        if e4_store.load_manifest() != manifest or e4_store.load_snapshot() != snapshot:
            raise E4ProjectionError("E4 manifest/PIT identity differs from durable evidence")
        self.e4_store = e4_store
        self.domain_evidence = domain_evidence
        self.registry = registry
        self.manifest = manifest
        self.snapshot = snapshot
        self._expressions = {item.market_id: item for item in snapshot.expressions}
        self._warmup_health = warmup_health
        self._capture_health = capture_health
        self.clock_ms = clock_ms
        self.store = E4MemoryBarStore()
        self._events: dict[str, AdmittedEvent] = {}
        self._bar_events: dict[tuple[str, str, int], AdmittedEvent] = {}
        self._one_minute: dict[tuple[str, int], OneMinuteBar] = {}
        self._depth: dict[str, AdmittedEvent] = {}
        self._failed_markets: set[str] = set()
        self._last_ordinal = 0
        self._last_hash: str | None = None
        self._replaying = True
        for event in e4_store.load_admissions():
            self.accept(event)
        self._replaying = False
        self._check_retained_refs()
        self._prune()

    def validate_market(self, market: RegistryMarket) -> bool:
        expression = self._expressions.get(market.identity.market_id)
        return bool(
            expression is not None
            and expression.dex == market.identity.dex
            and expression.provider_coin == market.identity.coin
            and expression.instrument_metadata_hash == market.metadata_hash
            and market.price_max_decimals == 6 - market.size_decimals
        )

    def _validate_event(self, event: AdmittedEvent) -> None:
        expression = self._expressions.get(event.source.market_id)
        if expression is None or (
            event.source.expression_id != expression.expression_id
            or event.source.instrument_id != expression.instrument_id
            or event.source.provider_id != expression.provider_id
        ):
            raise E4ProjectionError("admission is outside exact E4 PIT expression")
        if event.admission_ordinal < self._last_ordinal:
            raise E4ProjectionError("E4 admission ordinal regressed")
        if (
            event.admission_ordinal == self._last_ordinal
            and event.admission_hash != self._last_hash
        ):
            raise E4ProjectionError("conflicting E4 admission ordinal")

    @staticmethod
    def _bar_interval(event: AdmittedEvent) -> str:
        match = _BAR_TYPE.search(event.source.event_context)
        if match is None:
            raise E4ProjectionError("E4 bar lacks exact 1m/5m interval identity")
        return f"{match.group(1)}m"

    def _bound_registry(self, market_id: str) -> tuple[str, str]:
        active = self.registry.active()
        pending = self.registry.pending_version()
        binding = next(
            (
                version
                for version in (active, pending)
                if version is not None
                and market_id in {m.identity.market_id for m in version.markets}
            ),
            None,
        )
        if binding is None:
            raise E4ProjectionError("E4 market has no validated Registry binding")
        market = next(m for m in binding.markets if m.identity.market_id == market_id)
        if not self.validate_market(market):
            raise E4ProjectionError("Registry metadata differs from current E4 PIT")
        return binding.version, binding.content_hash

    def accept(self, event: AdmittedEvent) -> str | None:
        """Accept a durably admitted E4 fact; return its completed interval if any."""
        self._validate_event(event)
        if (
            event.admission_ordinal == self._last_ordinal
            and event.admission_hash == self._last_hash
        ):
            return None
        if event.admission_hash in self._events:
            return None
        self._last_ordinal = max(self._last_ordinal, event.admission_ordinal)
        self._last_hash = event.admission_hash
        if event.source.data_kind not in (DataKind.BAR, DataKind.DEPTH10):
            return None
        self._events[event.admission_hash] = event
        if event.source.data_kind is DataKind.DEPTH10:
            try:
                self._accept_depth(event)
            except Exception:
                self._events.pop(event.admission_hash, None)
                raise
            if self._depth.get(event.source.market_id) != event:
                self._events.pop(event.admission_hash, None)
            return None
        if event.source.data_kind is not DataKind.BAR:
            return None
        selected = (self.registry.active(), self.registry.pending_version())
        if event.source.market_id not in {
            market.identity.market_id
            for version in selected
            if version is not None
            for market in version.markets
        }:
            return None
        interval = self._bar_interval(event)
        step = _BAR_STEP[interval]
        open_ms = event.source.ts_event // 1_000_000
        close_ms = open_ms + step
        if (
            event.source.ts_event % 1_000_000
            or open_ms < 0
            or open_ms % step
            or event.source.ts_init < close_ms * 1_000_000
        ):
            raise E4ProjectionError("E4 bar does not have exact closed interval geometry")
        payload = event.source.payload
        if payload.get("finalized") is not True:
            raise E4ProjectionError("E4 bar is not finalized")
        values = tuple(
            Decimal(str(payload[name])) for name in ("open", "high", "low", "close", "volume")
        )
        slot = (event.source.market_id, interval, open_ms)
        prior = self._bar_events.get(slot)
        if prior is not None:
            if prior.source.payload != event.source.payload:
                self._failed_markets.add(event.source.market_id)
                raise E4ProjectionError("conflicting E4 closed-bar slot")
            return None
        self._bar_events[slot] = event
        if interval == "1m":
            bar_1m = OneMinuteBar.create(
                market_id=event.source.market_id,
                open_time_ms=open_ms,
                open=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
                source_id="E4_NAUTILUS_1M",
            )
            self._one_minute[(bar_1m.market_id, open_ms)] = bar_1m
            if not self._replaying:
                self._prune()
            return (
                interval
                if not event.out_of_order and event.continuity_state is EvidenceState.COMPLETE
                else None
            )
        version, content_hash = self._bound_registry(event.source.market_id)
        bar_5m = ClosedBar.create(
            market_id=event.source.market_id,
            open_time_ms=open_ms,
            close_time_ms=close_ms - 1,
            open=values[0],
            high=values[1],
            low=values[2],
            close=values[3],
            volume=values[4],
            source_id=f"e4:{event.admission_hash}",
            provenance_hash=event.source.payload_hash,
            received_at=datetime.fromtimestamp(event.admission_ts / 1_000_000_000, UTC),
        )
        self.store.put(
            bar_5m,
            registry_version=version,
            registry_content_hash=content_hash,
            finality_identity=event.admission_hash,
        )
        if not self._replaying:
            record = E4MarketBarReference.create(
                identity={"market_id": bar_5m.market_id, "open_time_ms": open_ms},
                market_id=bar_5m.market_id,
                open_time_ms=open_ms,
                registry_version=version,
                registry_content_hash=content_hash,
                e4_run_id=self.manifest.run_id,
                admission_hash=event.admission_hash,
                admission_ordinal=event.admission_ordinal,
                source_identity=event.source_identity,
            )
            self.domain_evidence._write_controlled((record,))
        for minutes, count in ((15, 3), (60, 12)):
            first_open = open_ms - (count - 1) * 300_000
            if first_open < 0 or first_open % (minutes * 60_000):
                continue
            window = self.store.tail_bars(bar_5m.market_id, at_or_before_ms=open_ms, limit=count)
            if len(window) == count and window[-1].open_time_ms == open_ms:
                try:
                    aggregate = aggregate_closed_5m(window, minutes=minutes)
                except ValueError:
                    continue
                self.store.put(
                    aggregate,
                    registry_version=version,
                    registry_content_hash=content_hash,
                    finality_identity=aggregate.provenance_hash,
                )
        if not self._replaying:
            self._prune()
        return interval if not event.out_of_order else None

    def _accept_depth(self, event: AdmittedEvent) -> None:
        if event.out_of_order:
            return
        payload = event.source.payload
        sides = []
        for name, descending in (("bids", True), ("asks", False)):
            levels = _native_levels(payload.get(name))
            if any(
                (right[0] > left[0] if descending else right[0] < left[0])
                for left, right in pairwise(levels)
            ):
                raise E4ProjectionError("E4 Depth10 levels are not ordered")
            sides.append(levels)
        if sides[0][0][0] >= sides[1][0][0]:
            raise E4ProjectionError("E4 Depth10 is crossed")
        if str(sides[0][0][0]) != payload.get("bid_price") or str(sides[1][0][0]) != payload.get(
            "ask_price"
        ):
            raise E4ProjectionError("Depth10 top-of-book compatibility mismatch")
        prior = self._depth.get(event.source.market_id)
        if (
            prior is not None
            and event.source.ts_event == prior.source.ts_event
            and event.source.payload != prior.source.payload
        ):
            self._failed_markets.add(event.source.market_id)
            raise E4ProjectionError("conflicting E4 Depth10 snapshot")
        if prior is None or event.source.ts_event >= prior.source.ts_event:
            self._depth[event.source.market_id] = event
            if prior is not None:
                self._events.pop(prior.admission_hash, None)

    def _prune(self) -> None:
        """Keep only bounded read windows; E4 durable admissions remain untouched."""
        markets = {slot[0] for slot in self._bar_events}
        for market_id in markets:
            for interval, limit in (("5m", _MAX_5M), ("1m", _MAX_1M)):
                opens = sorted(
                    slot[2]
                    for slot in self._bar_events
                    if slot[0] == market_id and slot[1] == interval
                )
                if len(opens) <= limit:
                    continue
                cutoff = opens[-limit]
                stale = tuple(
                    slot
                    for slot in self._bar_events
                    if slot[0] == market_id and slot[1] == interval and slot[2] < cutoff
                )
                for slot in stale:
                    event = self._bar_events.pop(slot)
                    self._events.pop(event.admission_hash, None)
                    if interval == "1m":
                        self._one_minute.pop((market_id, slot[2]), None)
                if interval == "5m":
                    self.store.connection.execute(
                        "DELETE FROM closed_bars WHERE market_id=? AND open_time_ms<?",
                        (market_id, cutoff),
                    )
                    self.store.connection.commit()

    def _check_retained_refs(self) -> None:
        rows = self.domain_evidence._connection.execute(
            "SELECT payload_json FROM immutable_records WHERE record_type='e4_market_bar_ref'"
        ).fetchall()
        retained_slots: set[tuple[str, str, int]] = set()
        latest_retained_ordinal: dict[str, int] = {}
        for row in rows:
            import json

            ref = json.loads(row[0])
            event = self._events.get(ref["admission_hash"])
            if (
                event is None
                or event.admission_ordinal != ref["admission_ordinal"]
                or event.source_identity != ref["source_identity"]
            ):
                raise E4ProjectionError("retained 5m E4 lineage is missing or corrupt")
            slot = (ref["market_id"], "5m", ref["open_time_ms"])
            retained_slots.add(slot)
            latest_retained_ordinal[ref["market_id"]] = max(
                latest_retained_ordinal.get(ref["market_id"], 0),
                int(ref["admission_ordinal"]),
            )
            if self._bar_events.get(slot) != event:
                raise E4ProjectionError("retained 5m reference contradicts E4 admission")
            self.store.connection.execute(
                "UPDATE closed_bars SET registry_version=?, registry_content_hash=? "
                "WHERE market_id=? AND interval='5m' AND open_time_ms=?",
                (
                    ref["registry_version"],
                    ref["registry_content_hash"],
                    ref["market_id"],
                    ref["open_time_ms"],
                ),
            )
        self.store.connection.commit()
        new_refs = []
        for slot, event in self._bar_events.items():
            if slot[1] != "5m" or slot in retained_slots:
                continue
            if event.admission_ordinal <= latest_retained_ordinal.get(slot[0], 0):
                raise E4ProjectionError("5m E4 lineage has a missing retained slot")
            if slot[0] not in latest_retained_ordinal and any(self.registry.history.glob("*.json")):
                raise E4ProjectionError("5m E4 lineage predates known Registry epoch")
            row = self.store.connection.execute(
                "SELECT registry_version, registry_content_hash FROM closed_bars "
                "WHERE market_id=? AND interval='5m' AND open_time_ms=?",
                (slot[0], slot[2]),
            ).fetchone()
            if row is None:
                raise E4ProjectionError("E4 5m projection slot is absent")
            new_refs.append(
                E4MarketBarReference.create(
                    identity={"market_id": slot[0], "open_time_ms": slot[2]},
                    market_id=slot[0],
                    open_time_ms=slot[2],
                    registry_version=row[0],
                    registry_content_hash=row[1],
                    e4_run_id=self.manifest.run_id,
                    admission_hash=event.admission_hash,
                    admission_ordinal=event.admission_ordinal,
                    source_identity=event.source_identity,
                )
            )
        if new_refs:
            self.domain_evidence._write_controlled(tuple(new_refs))

    def prove_boundary_evidence(
        self,
        *,
        boundary_open_time_ms: int,
        market_ids: frozenset[str],
        base_registry_version: str,
        base_registry_hash: str,
    ) -> bool:
        if self._cohort_continuity_epoch(boundary_open_time_ms, market_ids) is None:
            return False
        durable = {event.admission_hash for event in self.e4_store.load_admissions()}
        for market_id in market_ids:
            slot = (market_id, "5m", boundary_open_time_ms)
            event = self._bar_events.get(slot)
            row = self.store.connection.execute(
                "SELECT registry_version, registry_content_hash FROM closed_bars "
                "WHERE market_id=? AND interval='5m' AND open_time_ms=?",
                (market_id, boundary_open_time_ms),
            ).fetchone()
            if (
                event is None
                or event.admission_hash not in durable
                or event.continuity_state is not EvidenceState.COMPLETE
                or event.out_of_order
                or row != (base_registry_version, base_registry_hash)
            ):
                return False
            retained = self.domain_evidence._connection.execute(
                "SELECT 1 FROM immutable_records WHERE record_type='e4_market_bar_ref' "
                "AND json_extract(payload_json, '$.market_id')=? "
                "AND json_extract(payload_json, '$.open_time_ms')=? "
                "AND json_extract(payload_json, '$.admission_hash')=? LIMIT 1",
                (market_id, boundary_open_time_ms, event.admission_hash),
            ).fetchone()
            if retained is None:
                return False
        return True

    def _cohort_continuity_epoch(
        self, boundary_open_time_ms: int, market_ids: frozenset[str]
    ) -> str | None:
        """Prove one exact-T continuity epoch for the whole required cohort."""
        if not market_ids:
            return None
        events = tuple(
            self._bar_events.get((market_id, "5m", boundary_open_time_ms))
            for market_id in market_ids
        )
        if any(
            event is None
            or event.continuity_state is not EvidenceState.COMPLETE
            or event.out_of_order
            for event in events
        ):
            return None
        epochs = {event.continuity_epoch for event in events if event is not None}
        if len(epochs) != 1:
            return None
        epoch = next(iter(epochs))
        current = self._capture_health().get("continuity_epoch")
        if current is not None and (not isinstance(current, str) or current != epoch):
            return None
        return epoch

    def prove_initial_boundary_evidence(
        self,
        *,
        boundary_open_time_ms: int,
        market_ids: frozenset[str],
        pending_registry_version: str,
        pending_registry_hash: str,
    ) -> bool:
        health = self._capture_health()
        warmup = self._warmup_health()
        if (
            warmup.get("readiness") != "READY"
            or health.get("stream_health") != "HEALTHY"
            or health.get("continuity_requirements_remaining") != 0
            or health.get("storage_failures") != 0
            or health.get("admitted_observer_failures")
            or any(market_id in self._failed_markets for market_id in market_ids)
        ):
            return False
        return self.prove_boundary_evidence(
            boundary_open_time_ms=boundary_open_time_ms,
            market_ids=market_ids,
            base_registry_version=pending_registry_version,
            base_registry_hash=pending_registry_hash,
        )

    def can_formalize(self, market: RegistryMarket) -> bool:
        return (
            market.lifecycle is MarketLifecycle.ACTIVE
            and self.validate_market(market)
            and not self.market_failed(market.identity.market_id)
        )

    def market_failed(self, market_id: str) -> bool:
        return market_id in self._failed_markets

    def fail_market(self, market_id: str) -> None:
        self._failed_markets.add(market_id)

    def one_minute_window(
        self, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]:
        return tuple(
            self._one_minute[(market_id, point)]
            for point in range(start_ms, end_ms, 60_000)
            if (market_id, point) in self._one_minute
        )

    def outcome_reference(self, bar: OneMinuteBar) -> OutcomeE4BarReference:
        event = self._bar_events.get((bar.market_id, "1m", bar.open_time_ms))
        if event is None or event.admission_hash not in {
            value.admission_hash for value in self.e4_store.load_admissions()
        }:
            raise E4ProjectionError("Outcome 1m E4 lineage is unavailable")
        return OutcomeE4BarReference.create(
            identity={"market_id": bar.market_id, "open_time_ms": bar.open_time_ms},
            market_id=bar.market_id,
            open_time_ms=bar.open_time_ms,
            canonical_hash=bar.canonical_hash,
            e4_run_id=self.manifest.run_id,
            e4_root=str(self.e4_store.root),
            admission_epoch=event.admission_epoch,
            admission_hash=event.admission_hash,
            admission_ordinal=event.admission_ordinal,
            source_identity=event.source_identity,
            continuity_epoch=event.continuity_epoch,
            process_epoch=event.process_epoch,
        )

    def resolve_outcome_reference(self, ref: OutcomeE4BarReference) -> OneMinuteBar:
        payload = ref.payload
        event = self._events.get(str(payload["admission_hash"]))
        key = (str(payload["market_id"]), int(payload["open_time_ms"]))
        bar = self._one_minute.get(key)
        if (
            event is None
            or bar is None
            or event.admission_hash
            not in {value.admission_hash for value in self.e4_store.load_admissions()}
            or event.admission_ordinal != payload["admission_ordinal"]
            or event.source_identity != payload["source_identity"]
            or event.continuity_epoch != payload["continuity_epoch"]
            or event.process_epoch != payload["process_epoch"]
            or event.admission_epoch != payload["admission_epoch"]
            or str(self.e4_store.root) != payload["e4_root"]
            or bar.canonical_hash != payload["canonical_hash"]
        ):
            raise E4ProjectionError("Outcome 1m E4 lineage is missing or corrupt")
        return bar

    def current_depth(self, market_id: str, now_ms: int) -> AdmittedEvent:
        event = self._depth.get(market_id)
        if event is None or market_id in self._failed_markets:
            raise PublicDataError("E4 Depth10 is unavailable")
        age = now_ms - event.source.ts_event // 1_000_000
        if age < 0 or age > 10_000:
            raise PublicDataError("E4 Depth10 is stale or future")
        return event

    def readiness_snapshot(self) -> RuntimeReadinessSnapshot:
        registry = self.registry.active() or self.registry.pending_version()
        if registry is None:
            raise E4ProjectionError("Registry identity is unavailable")
        now_ms = self.clock_ms()
        active = tuple(m for m in registry.markets if m.lifecycle is MarketLifecycle.ACTIVE)
        latest = max((self.store.last_open(m.identity.market_id) or -1 for m in active), default=-1)
        health = self._capture_health()
        warmup = self._warmup_health()
        common = (
            warmup.get("readiness") == "READY"
            and health.get("stream_health") in {"HEALTHY", "REESTABLISHING"}
            and health.get("storage_failures") == 0
            and not health.get("admitted_observer_failures")
        )
        candidate_ready = tuple(
            m.identity.market_id
            for m in active
            if (
                common
                and not self.market_failed(m.identity.market_id)
                and self.validate_market(m)
                and self.store.last_open(m.identity.market_id) == latest
                and latest >= 0
                and now_ms <= latest + 360_000
                and self.store.is_contiguous_5m(m.identity.market_id)
            )
        )
        data_ready = bool(active) and len(candidate_ready) == len(active)
        ready = candidate_ready if data_ready else ()
        failed = tuple(
            m.identity.market_id for m in active if self.market_failed(m.identity.market_id)
        )
        return RuntimeReadinessSnapshot.create(
            registry_version=registry.version,
            registry_content_hash=registry.content_hash,
            data_ready=data_ready,
            ready_market_ids=ready,
            failed_market_ids=failed,
            latest_closed_5m_open_time_ms=latest,
            observed_at_ms=now_ms,
        )

    def close(self) -> None:
        self.store.close()


class E4PlanningData:
    """Existing economic gate over exactly one current admitted Depth10 fact."""

    def __init__(self, projection: E4MarketTruthProjection) -> None:
        self.projection = projection
        self._selected: dict[str, AdmittedEvent] = {}

    def fetch_bbo(self, *, market: RegistryMarket, now_ms: int) -> PublicBbo:
        event = self.projection.current_depth(market.identity.market_id, now_ms)
        self._selected[market.identity.market_id] = event
        payload = event.source.payload
        return PublicBbo(
            best_bid=Decimal(str(payload["bid_price"])),
            best_ask=Decimal(str(payload["ask_price"])),
            observed_at_ms=event.source.ts_event // 1_000_000,
            market_id=market.identity.market_id,
            coin=market.identity.coin,
        )

    def fetch_l2(self, *, market: RegistryMarket, side: Side, bbo: PublicBbo) -> PublicL2Snapshot:
        event = self._selected.pop(market.identity.market_id, None)
        if event is None or event != self.projection.current_depth(
            market.identity.market_id, self.projection.clock_ms()
        ):
            raise PublicDataError("BBO/L2 E4 admission changed")
        payload = event.source.payload
        if bbo.best_bid != Decimal(str(payload["bid_price"])) or bbo.best_ask != Decimal(
            str(payload["ask_price"])
        ):
            raise PublicDataError("BBO/L2 E4 admission mismatch")
        levels = _native_levels(payload["asks"] if side is Side.LONG else payload["bids"])
        return PublicL2Snapshot(
            market_id=market.identity.market_id,
            coin=market.identity.coin,
            observed_at_ms=event.source.ts_event // 1_000_000,
            best_bid=bbo.best_bid,
            best_ask=bbo.best_ask,
            levels=levels,
            provenance_hash=event.admission_hash,
        )

    def fetch_scanner_snapshot(
        self,
        *,
        market: RegistryMarket,
        now_ms: int,
        btc_returns: tuple[Decimal | None, Decimal | None, Decimal | None],
    ) -> ScannerPublicSnapshot:
        event = self.projection.current_depth(market.identity.market_id, now_ms)
        payload = event.source.payload
        bid = Decimal(str(payload["bid_price"]))
        ask = Decimal(str(payload["ask_price"]))
        assessments = tuple(
            assess_l2(
                market_id=market.identity.market_id,
                coin=market.identity.coin,
                side=side,
                observed_at_ms=event.source.ts_event // 1_000_000,
                best_bid=bid,
                best_ask=ask,
                levels=tuple(
                    (Decimal(str(p)), Decimal(str(s))) for p, s in self._levels(payload, side)
                ),
                provenance_hash=event.admission_hash,
            )
            for side in (Side.LONG, Side.SHORT)
        )
        healthy = PublicBbo(bid, ask).spread_bps <= HARD_MAX_SPREAD_BPS and all(
            item.sufficient_depth
            and item.one_way_slippage_bps is not None
            and item.one_way_slippage_bps <= HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS
            for item in assessments
        )
        return ScannerPublicSnapshot(
            current_spread_price=ask - bid, liquidity_healthy=healthy, btc_returns=btc_returns
        )

    @staticmethod
    def _levels(payload: dict[str, object], side: Side) -> list[list[str]]:
        return [
            [str(p), str(s)]
            for p, s in _native_levels(payload["asks" if side is Side.LONG else "bids"])
        ]
