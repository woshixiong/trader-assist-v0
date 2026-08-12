"""Provider-finalized 5m evidence, persistence, and causal aggregation.

The only way to obtain a :class:`Closed5mAdmission` is the finality path in
this module.  A websocket candle is deliberately only a candidate; its close
timestamp is not enough to make it strategy or Registry authority.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import cast

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .models import ClosedBar, MarketLifecycle, RegistryMarket, RegistryVersion
from .registry import MarketRegistryManager

_FIVE_MINUTES_MS = 300_000


class DataRouteError(ValueError):
    pass


@dataclass(frozen=True)
class _ProviderCandidate:
    market_id: str
    coin: str
    open_time_ms: int
    payload: dict[str, object]
    fingerprint: str


class Closed5mAdmission:
    """Opaque, one-use provider-finality capability (not a general model)."""

    __slots__ = ("_issuer", "_used", "bar")

    def __init__(self, *, bar: ClosedBar, issuer: object) -> None:
        self.bar = bar
        self._issuer = issuer
        self._used = False

    def _consume(self) -> bool:
        if self._used:
            return False
        self._used = True
        return True


class ClosedBarStore:
    """SQLite evidence store with immutable registry and finality linkage."""

    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS closed_bars (
                market_id TEXT NOT NULL, interval TEXT NOT NULL, open_time_ms INTEGER NOT NULL,
                canonical_hash TEXT NOT NULL, registry_version TEXT NOT NULL,
                registry_content_hash TEXT NOT NULL, finality_identity TEXT NOT NULL,
                finalized_at_ms INTEGER NOT NULL, payload_json BLOB NOT NULL,
                PRIMARY KEY (market_id, interval, open_time_ms)
            )"""
        )
        self.connection.commit()

    def put(
        self,
        bar: ClosedBar,
        *,
        registry_version: str = "UNBOUND_TEST_ONLY",
        registry_content_hash: str = "0" * 64,
        finality_identity: str | None = None,
        finalized_at_ms: int | None = None,
    ) -> bool:
        encoded = bar.model_dump_json().encode("utf-8")
        finality = finality_identity or bar.canonical_hash
        finalized = (
            finalized_at_ms
            if finalized_at_ms is not None
            else int(bar.received_at.timestamp() * 1000)
        )
        existing = self.connection.execute(
            "SELECT canonical_hash FROM closed_bars "
            "WHERE market_id=? AND interval=? AND open_time_ms=?",
            (bar.market_id, bar.interval, bar.open_time_ms),
        ).fetchone()
        if existing is not None:
            if existing[0] == bar.canonical_hash:
                return False
            raise DataRouteError("conflicting closed bar identity")
        self.connection.execute(
            "INSERT INTO closed_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bar.market_id,
                bar.interval,
                bar.open_time_ms,
                bar.canonical_hash,
                registry_version,
                registry_content_hash,
                finality,
                finalized,
                encoded,
            ),
        )
        self.connection.commit()
        return True

    def last_open(self, market_id: str) -> int | None:
        row = self.connection.execute(
            "SELECT MAX(open_time_ms) FROM closed_bars WHERE market_id=? AND interval='5m'",
            (market_id,),
        ).fetchone()
        return None if row is None or row[0] is None else int(row[0])

    def bars(self, market_id: str, *, interval: str = "5m") -> tuple[ClosedBar, ...]:
        rows = self.connection.execute(
            "SELECT payload_json FROM closed_bars "
            "WHERE market_id=? AND interval=? ORDER BY open_time_ms",
            (market_id, interval),
        ).fetchall()
        return tuple(ClosedBar.model_validate_json(row[0]) for row in rows)

    def close(self) -> None:
        self.connection.close()


def _provider_bar(
    *, market: RegistryMarket, payload: object, received_at: datetime, source_id: str
) -> ClosedBar:
    if received_at.tzinfo is None or not isinstance(payload, dict):
        raise DataRouteError("provider candle is invalid")
    try:
        interval = payload["i"]
        coin = payload["s"]
        open_ms = payload["t"]
        close_ms = payload["T"]
        values = (payload["o"], payload["h"], payload["l"], payload["c"], payload["v"])
    except KeyError as exc:
        raise DataRouteError("provider candle is incomplete") from exc
    if (
        interval != "5m"
        or coin != market.identity.coin
        or not isinstance(open_ms, int)
        or not isinstance(close_ms, int)
        or open_ms < 0
        or open_ms % _FIVE_MINUTES_MS != 0
        # Hyperliquid candles are [t, t + interval), carrying T=end-1ms.
        or close_ms != open_ms + _FIVE_MINUTES_MS - 1
    ):
        raise DataRouteError("provider candle does not have exact 5m geometry")
    try:
        return ClosedBar.create(
            market_id=market.identity.market_id,
            open_time_ms=open_ms,
            close_time_ms=close_ms,
            open=Decimal(str(values[0])),
            high=Decimal(str(values[1])),
            low=Decimal(str(values[2])),
            close=Decimal(str(values[3])),
            volume=Decimal(str(values[4])),
            source_id=source_id,
            provenance_hash=sha256_hex(canonical_json_bytes(payload)),
            received_at=received_at.astimezone(UTC),
        )
    except (ArithmeticError, ValueError) as exc:
        raise DataRouteError("provider candle values are invalid") from exc


class MultiAssetDataAuthority:
    """Per-market fail-closed A1 data authority.

    REST history is a provider-finality source for warmup/recovery; websocket
    traffic can only nominate a candidate which requires a stable targeted
    REST confirmation after the real interval end and a bounded hold.
    """

    def __init__(self, *, store: ClosedBarStore, registry: MarketRegistryManager) -> None:
        self.store = store
        self.registry = registry
        self._last_open: dict[str, int] = {}
        self._failed: set[str] = set()
        self._candidates: dict[tuple[str, int], _ProviderCandidate] = {}
        self._restore()

    def _restore(self) -> None:
        registry = self.registry.active() or self.registry.pending_version()
        if registry is None:
            return
        for market in registry.markets:
            last = self.store.last_open(market.identity.market_id)
            if last is not None:
                self._last_open[market.identity.market_id] = last

    def request_registry_apply(self, version: str) -> None:
        self.registry.request_apply(version)

    def market_failed(self, market_id: str) -> bool:
        return market_id in self._failed

    def can_formalize(self, market: RegistryMarket) -> bool:
        return (
            market.lifecycle is MarketLifecycle.ACTIVE
            and market.identity.market_id not in self._failed
        )

    def offer_ws_candidate(
        self, *, market: RegistryMarket, payload: object, received_at: datetime
    ) -> str:
        """Record a websocket candidate only; never write evidence here."""
        bar = _provider_bar(
            market=market,
            payload=payload,
            received_at=received_at,
            source_id="hyperliquid-public-ws-candidate",
        )
        key = (bar.market_id, bar.open_time_ms)
        fingerprint = sha256_hex(canonical_json_bytes(payload))
        if not isinstance(payload, dict):
            raise DataRouteError("provider candle is invalid")
        current = self._candidates.get(key)
        if current is not None and current.fingerprint != fingerprint:
            # A changing unfinalized candle is normal.  Replace it, but a
            # previously finalized conflict is caught by immutable storage.
            self._candidates.pop(key)
        self._candidates[key] = _ProviderCandidate(
            bar.market_id,
            market.identity.coin,
            bar.open_time_ms,
            dict(cast(dict[str, object], payload)),
            fingerprint,
        )
        return fingerprint

    def discard_ws_candidate(self, *, market_id: str, open_time_ms: int) -> None:
        """Forget a superseded runtime candidate without creating evidence."""
        self._candidates.pop((market_id, open_time_ms), None)

    def confirm_ws_candidate(
        self,
        *,
        market: RegistryMarket,
        open_time_ms: int,
        candidate_fingerprint: str,
        snapshot: Sequence[object],
        stable_snapshot: Sequence[object],
        received_at: datetime,
        hold_ms: int = 3_000,
        first_observed_monotonic: float | None = None,
        second_observed_monotonic: float | None = None,
        observation_gap_ms: int = 1_000,
    ) -> ClosedBar | None:
        """Admit a websocket candidate only after exact stable REST finality."""
        candidate = self._candidates.get((market.identity.market_id, open_time_ms))
        if candidate is None:
            raise DataRouteError("stale or superseded candle candidate")
        if candidate.fingerprint != candidate_fingerprint:
            raise DataRouteError("stale or superseded candle candidate")
        if observation_gap_ms < 0 or (
            received_at.tzinfo is None
            or int(received_at.timestamp() * 1000) < open_time_ms + _FIVE_MINUTES_MS + hold_ms
        ):
            return None
        if (
            first_observed_monotonic is None
            or second_observed_monotonic is None
            or second_observed_monotonic < first_observed_monotonic
            or (second_observed_monotonic - first_observed_monotonic) * 1000 < observation_gap_ms
        ):
            raise DataRouteError("targeted REST confirmation observation gap is insufficient")
        matches = [
            item for item in snapshot if isinstance(item, dict) and item.get("t") == open_time_ms
        ]
        stable_matches = [
            item
            for item in stable_snapshot
            if isinstance(item, dict) and item.get("t") == open_time_ms
        ]
        if (
            len(matches) != 1
            or len(stable_matches) != 1
            or canonical_json_bytes(matches[0]) != canonical_json_bytes(stable_matches[0])
        ):
            raise DataRouteError("targeted REST confirmation is not exact")
        confirmed = _provider_bar(
            market=market,
            payload=matches[0],
            received_at=received_at,
            source_id="hyperliquid-public-candleSnapshot-final",
        )
        if sha256_hex(canonical_json_bytes(matches[0])) != candidate.fingerprint:
            # The WS update was only a candidate.  Use the REST final value;
            # it is authoritative so long as its identity was not superseded.
            candidate = _ProviderCandidate(
                candidate.market_id,
                candidate.coin,
                candidate.open_time_ms,
                dict(matches[0]),
                sha256_hex(canonical_json_bytes(matches[0])),
            )
            self._candidates[(market.identity.market_id, open_time_ms)] = candidate
        self._candidates.pop((market.identity.market_id, open_time_ms), None)
        return self._admit(market=market, bar=confirmed, finality_identity=candidate.fingerprint)

    def admit_rest_history(
        self, *, market: RegistryMarket, snapshot: Sequence[object], received_at: datetime
    ) -> tuple[ClosedBar, ...]:
        """Warmup/backfill path: accepted official history is already closed."""
        output: list[ClosedBar] = []
        for payload in sorted(
            snapshot, key=lambda item: item.get("t", -1) if isinstance(item, dict) else -1
        ):
            bar = _provider_bar(
                market=market,
                payload=payload,
                received_at=received_at,
                source_id="hyperliquid-public-candleSnapshot-history",
            )
            # Snapshot can include its current open candle.  Exact geometry is
            # necessary but not sufficient: receipt must be after end.
            if int(received_at.timestamp() * 1000) <= bar.close_time_ms:
                continue
            admitted = self._admit(market=market, bar=bar, finality_identity=bar.provenance_hash)
            if admitted is not None:
                output.append(admitted)
        self._clear_failure_if_contiguous(market.identity.market_id)
        return tuple(output)

    def _admit(
        self, *, market: RegistryMarket, bar: ClosedBar, finality_identity: str
    ) -> ClosedBar | None:
        prior = self._last_open.get(bar.market_id)
        if prior is not None and bar.open_time_ms > prior + _FIVE_MINUTES_MS:
            self._failed.add(bar.market_id)
            raise DataRouteError("closed 5m gap detected")
        binding = self._binding_registry(market)
        try:
            inserted = self.store.put(
                bar,
                registry_version=binding.version,
                registry_content_hash=binding.content_hash,
                finality_identity=finality_identity,
            )
        except DataRouteError:
            self._failed.add(bar.market_id)
            raise
        self._last_open[bar.market_id] = max(
            bar.open_time_ms, prior if prior is not None else bar.open_time_ms
        )
        if not inserted:
            return None
        self._persist_aggregates(
            bar, binding_version=binding.version, binding_hash=binding.content_hash
        )
        admission = Closed5mAdmission(bar=bar, issuer=self.registry._boundary_issuer)
        self.registry._apply_admitted(admission)
        return bar

    def _binding_registry(self, market: RegistryMarket) -> RegistryVersion:
        """Return the exact validated Registry version that authorized acquisition."""
        active = self.registry.active()
        if active is not None and any(
            item.identity.market_id == market.identity.market_id for item in active.markets
        ):
            return active
        pending = self.registry.pending_version()
        if pending is not None and any(
            item.identity.market_id == market.identity.market_id for item in pending.markets
        ):
            return pending
        raise DataRouteError("market is not authorized by an active or pending Registry")

    def _persist_aggregates(
        self, bar: ClosedBar, *, binding_version: str, binding_hash: str
    ) -> None:
        all_five = self.store.bars(bar.market_id)
        for minutes, count in ((15, 3), (60, 12)):
            window = tuple(item for item in all_five if item.open_time_ms <= bar.open_time_ms)[
                -count:
            ]
            if len(window) == count and window[0].open_time_ms % (minutes * 60_000) == 0:
                aggregate = aggregate_closed_5m(window, minutes=minutes)
                self.store.put(
                    aggregate,
                    registry_version=binding_version,
                    registry_content_hash=binding_hash,
                    finality_identity=aggregate.provenance_hash,
                )

    def _clear_failure_if_contiguous(self, market_id: str) -> None:
        values = self.store.bars(market_id)
        if all(
            right.open_time_ms - left.open_time_ms == _FIVE_MINUTES_MS
            for left, right in pairwise(values)
        ):
            self._failed.discard(market_id)


def aggregate_closed_5m(candles: Iterable[ClosedBar], *, minutes: int) -> ClosedBar:
    """Build one 15m or 1h candle from a complete consecutive 5m window only."""
    count = {15: 3, 60: 12}.get(minutes)
    if count is None:
        raise DataRouteError("only 15m and 1h aggregation is authorized")
    values = tuple(candles)
    if len(values) != count or any(value.interval != "5m" for value in values):
        raise DataRouteError("aggregation needs exactly complete closed 5m input")
    if len({value.market_id for value in values}) != 1:
        raise DataRouteError("aggregation cannot cross market identities")
    if any(
        right.open_time_ms - left.open_time_ms != _FIVE_MINUTES_MS
        for left, right in pairwise(values)
    ):
        raise DataRouteError("aggregation input has a gap")
    if values[0].open_time_ms % (minutes * 60_000) != 0:
        raise DataRouteError("aggregation window is not aligned")
    provenance = ClosedBar.hash_payload(
        {"source_bars": [item.canonical_hash for item in values], "aggregate_minutes": minutes}
    )
    return ClosedBar.create(
        market_id=values[0].market_id,
        interval="15m" if minutes == 15 else "1h",
        open_time_ms=values[0].open_time_ms,
        close_time_ms=values[-1].close_time_ms,
        open=values[0].open,
        high=max(item.high for item in values),
        low=min(item.low for item in values),
        close=values[-1].close,
        volume=sum((item.volume for item in values), Decimal()),
        source_id="local-5m-causal-aggregation",
        provenance_hash=provenance,
        received_at=values[-1].received_at,
    )
