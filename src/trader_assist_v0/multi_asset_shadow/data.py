"""Provider-finalized 5m evidence, persistence, and causal aggregation.

The only way to obtain a :class:`Closed5mAdmission` is the finality path in
this module.  A websocket candle is deliberately only a candidate; its close
timestamp is not enough to make it strategy or Registry authority.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
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
# Internal tuning value only: source 5m bars grouped into one bounded durable
# SQLite transaction during historical admission.  Not an architectural
# constant; callers never observe batch boundaries.
_HISTORY_BATCH_BARS = 64
# Internal bound for the call-local rolling aggregate window: the largest
# aggregation window needs at most its 11 predecessor bars in memory.
_WINDOW_CACHE_BARS = 11


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
        return self._insert(
            bar,
            registry_version=registry_version,
            registry_content_hash=registry_content_hash,
            finality_identity=finality_identity,
            finalized_at_ms=finalized_at_ms,
            commit=True,
        )

    def put_deferred(
        self,
        bar: ClosedBar,
        *,
        registry_version: str = "UNBOUND_TEST_ONLY",
        registry_content_hash: str = "0" * 64,
        finality_identity: str | None = None,
        finalized_at_ms: int | None = None,
    ) -> bool:
        """Insert inside a caller-owned :meth:`transaction` without committing."""
        return self._insert(
            bar,
            registry_version=registry_version,
            registry_content_hash=registry_content_hash,
            finality_identity=finality_identity,
            finalized_at_ms=finalized_at_ms,
            commit=False,
        )

    def _insert(
        self,
        bar: ClosedBar,
        *,
        registry_version: str,
        registry_content_hash: str,
        finality_identity: str | None,
        finalized_at_ms: int | None,
        commit: bool,
    ) -> bool:
        encoded = bar.model_dump_json().encode("utf-8")
        finality = finality_identity or bar.canonical_hash
        finalized = (
            finalized_at_ms
            if finalized_at_ms is not None
            else int(bar.received_at.timestamp() * 1000)
        )
        existing = self.connection.execute(
            "SELECT canonical_hash, payload_json FROM closed_bars "
            "WHERE market_id=? AND interval=? AND open_time_ms=?",
            (bar.market_id, bar.interval, bar.open_time_ms),
        ).fetchone()
        if existing is not None:
            prior = ClosedBar.model_validate_json(existing[1])
            if existing[0] == bar.canonical_hash or _same_candle_contents(prior, bar):
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
        if commit:
            self.connection.commit()
        return True

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Bounded multi-row transaction; rollback discards uncommitted evidence."""
        try:
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def last_open(self, market_id: str) -> int | None:
        row = self.connection.execute(
            "SELECT MAX(open_time_ms) FROM closed_bars WHERE market_id=? AND interval='5m'",
            (market_id,),
        ).fetchone()
        return None if row is None or row[0] is None else int(row[0])

    def tail_bars(
        self, market_id: str, *, at_or_before_ms: int, limit: int, interval: str = "5m"
    ) -> tuple[ClosedBar, ...]:
        """Causally-required tail only: newest <= ``at_or_before_ms``, ascending."""
        rows = self.connection.execute(
            "SELECT payload_json FROM closed_bars "
            "WHERE market_id=? AND interval=? AND open_time_ms<=? "
            "ORDER BY open_time_ms DESC LIMIT ?",
            (market_id, interval, at_or_before_ms, limit),
        ).fetchall()
        return tuple(ClosedBar.model_validate_json(row[0]) for row in reversed(rows))

    def is_contiguous_5m(self, market_id: str) -> bool:
        """Exact continuity proof from SQL aggregates, not full deserialization.

        With unique primary-key opens, a gap-free ascending sequence is exactly
        ``max - min == (count - 1) * 5m``; any interior gap breaks the identity.
        """
        row = self.connection.execute(
            "SELECT COUNT(*), MIN(open_time_ms), MAX(open_time_ms) FROM closed_bars "
            "WHERE market_id=? AND interval='5m'",
            (market_id,),
        ).fetchone()
        if row is None or row[0] == 0:
            return True
        return int(row[2]) - int(row[1]) == (int(row[0]) - 1) * _FIVE_MINUTES_MS

    def bars(self, market_id: str, *, interval: str = "5m") -> tuple[ClosedBar, ...]:
        rows = self.connection.execute(
            "SELECT payload_json FROM closed_bars "
            "WHERE market_id=? AND interval=? ORDER BY open_time_ms",
            (market_id, interval),
        ).fetchall()
        return tuple(ClosedBar.model_validate_json(row[0]) for row in rows)

    def close(self) -> None:
        self.connection.close()


def _same_candle_contents(left: ClosedBar, right: ClosedBar) -> bool:
    """Compare final market contents without receipt/source evidence metadata."""
    return (
        left.market_id,
        left.interval,
        left.open_time_ms,
        left.close_time_ms,
        left.open,
        left.high,
        left.low,
        left.close,
        left.volume,
    ) == (
        right.market_id,
        right.interval,
        right.open_time_ms,
        right.close_time_ms,
        right.open,
        right.high,
        right.low,
        right.close,
        right.volume,
    )


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
        """Warmup/backfill path: accepted official history is already closed.

        Repeated contiguous calls with bounded snapshot chunks are equivalent
        to one call: already-retained identical evidence stays idempotent and
        conflicts/gaps fail closed.  While a pending Registry version exists,
        every causal 5m row is durably committed before Registry activation
        consumes its admission capability; once active authority exists,
        subsequent rows use bounded durable SQLite transactions.
        """
        output: list[ClosedBar] = []
        accepted = self._accepted_history(market, snapshot, received_at)
        # Call-local rolling window: survives repeated contiguous calls via
        # bounded SQL reseeding, and any failure aborts the call so it can
        # never serve evidence from an uncommitted batch.
        window_cache: dict[str, tuple[ClosedBar, ...]] = {}
        index = 0
        total = len(accepted)
        while index < total:
            if self.registry.pending_version() is not None:
                bar = accepted[index]
                index += 1
                admitted = self._admit(
                    market=market,
                    bar=bar,
                    finality_identity=bar.provenance_hash,
                    window_cache=window_cache,
                )
                if admitted is not None:
                    output.append(admitted)
            else:
                chunk = accepted[index : index + _HISTORY_BATCH_BARS]
                index += len(chunk)
                output.extend(
                    self._admit_history_batch(
                        market=market, bars=chunk, window_cache=window_cache
                    )
                )
        self._clear_failure_if_contiguous(market.identity.market_id)
        return tuple(output)

    @staticmethod
    def _accepted_history(
        market: RegistryMarket, snapshot: Sequence[object], received_at: datetime
    ) -> tuple[ClosedBar, ...]:
        """Validate and order one snapshot lazily-equivalently to per-payload flow."""
        accepted: list[ClosedBar] = []
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
            accepted.append(bar)
        return tuple(accepted)

    def _admit_history_batch(
        self,
        *,
        market: RegistryMarket,
        bars: Sequence[ClosedBar],
        window_cache: dict[str, tuple[ClosedBar, ...]],
    ) -> list[ClosedBar]:
        """Admit one bounded batch inside a single durable SQLite transaction."""
        market_id = market.identity.market_id
        inserted: list[ClosedBar] = []
        try:
            # Registry activation is deferred until after this transaction
            # commits, so the binding cannot change inside it.
            binding = self._binding_registry(market)
            with self.store.transaction():
                for bar in bars:
                    if self._admit_transactional(
                        market=market, bar=bar, binding=binding, window_cache=window_cache
                    ):
                        inserted.append(bar)
        except BaseException:
            # Uncommitted batch is rolled back; committed batches remain valid.
            # Uncertain admission state is fail-closed and in-memory progress
            # returns to durable SQLite truth.
            self._failed.add(market_id)
            self._restore_durable_last_open(market_id)
            raise
        # Registry activation may only consume a capability whose causal 5m
        # row is already durable: batching runs only when no pending Registry
        # version can be activated mid-transaction, and commits happen above.
        for bar in inserted:
            admission = Closed5mAdmission(bar=bar, issuer=self.registry._boundary_issuer)
            self.registry._apply_admitted(admission)
        return inserted

    def _admit_transactional(
        self,
        *,
        market: RegistryMarket,
        bar: ClosedBar,
        binding: RegistryVersion,
        window_cache: dict[str, tuple[ClosedBar, ...]],
    ) -> bool:
        """Insert one bar inside an open batch transaction (no commit here)."""
        prior = self._last_open.get(bar.market_id)
        if prior is not None and bar.open_time_ms > prior + _FIVE_MINUTES_MS:
            self._failed.add(bar.market_id)
            raise DataRouteError("closed 5m gap detected")
        try:
            inserted = self.store.put_deferred(
                bar,
                registry_version=binding.version,
                registry_content_hash=binding.content_hash,
                finality_identity=bar.provenance_hash,
            )
        except DataRouteError:
            self._failed.add(bar.market_id)
            raise
        self._last_open[bar.market_id] = max(
            bar.open_time_ms, prior if prior is not None else bar.open_time_ms
        )
        if not inserted:
            self._track_window_tail(window_cache, bar)
            return False
        self._persist_aggregates(
            bar,
            binding_version=binding.version,
            binding_hash=binding.content_hash,
            defer_commit=True,
            window_cache=window_cache,
        )
        # Extend the rolling tail only after the window was built from the
        # predecessor cache, so the next window can be served in memory.
        self._track_window_tail(window_cache, bar)
        return True

    def _restore_durable_last_open(self, market_id: str) -> None:
        durable = self.store.last_open(market_id)
        if durable is None:
            self._last_open.pop(market_id, None)
        else:
            self._last_open[market_id] = durable

    def _admit(
        self,
        *,
        market: RegistryMarket,
        bar: ClosedBar,
        finality_identity: str,
        window_cache: dict[str, tuple[ClosedBar, ...]] | None = None,
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
            if window_cache is not None:
                self._track_window_tail(window_cache, bar)
            return None
        self._persist_aggregates(
            bar,
            binding_version=binding.version,
            binding_hash=binding.content_hash,
            window_cache=window_cache,
        )
        if window_cache is not None:
            self._track_window_tail(window_cache, bar)
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
        self,
        bar: ClosedBar,
        *,
        binding_version: str,
        binding_hash: str,
        defer_commit: bool = False,
        window_cache: dict[str, tuple[ClosedBar, ...]] | None = None,
    ) -> None:
        insert = self.store.put_deferred if defer_commit else self.store.put
        for minutes, count in ((15, 3), (60, 12)):
            # A window ending at this bar exists only when it would be aligned:
            # window[0].open = bar.open - (count-1)*5m must be a multiple of
            # count*5m.  Otherwise no aggregate can be produced, so no tail is
            # loaded at all.
            span = count * _FIVE_MINUTES_MS
            if (bar.open_time_ms - (count - 1) * _FIVE_MINUTES_MS) % span != 0:
                continue
            window = self._aggregate_window(bar, count=count, window_cache=window_cache)
            if len(window) == count:
                aggregate = aggregate_closed_5m(window, minutes=minutes)
                insert(
                    aggregate,
                    registry_version=binding_version,
                    registry_content_hash=binding_hash,
                    finality_identity=aggregate.provenance_hash,
                )

    def _aggregate_window(
        self,
        bar: ClosedBar,
        *,
        count: int,
        window_cache: dict[str, tuple[ClosedBar, ...]] | None,
    ) -> tuple[ClosedBar, ...]:
        """Return the last ``count`` stored 5m bars ending at ``bar``.

        Served from the call-local rolling tail when it already proves every
        causal predecessor is stored; otherwise one bounded SQL tail query.
        Both routes yield the same canonical evidence: the cache contains only
        bars whose durable insertion was verified in this call or reseeded
        from the store, and the 5m grid makes their positions unique.
        """
        if window_cache is not None:
            cached = window_cache.get(bar.market_id)
            if (
                cached is not None
                and len(cached) >= count - 1
                and cached[-1].open_time_ms + _FIVE_MINUTES_MS == bar.open_time_ms
            ):
                return (*cached[-(count - 1) :], bar)
        return self.store.tail_bars(
            bar.market_id, at_or_before_ms=bar.open_time_ms, limit=count
        )

    @staticmethod
    def _track_window_tail(
        window_cache: dict[str, tuple[ClosedBar, ...]], bar: ClosedBar
    ) -> None:
        cached = window_cache.get(bar.market_id)
        if cached is None:
            window_cache[bar.market_id] = (bar,)
        elif cached[-1].open_time_ms + _FIVE_MINUTES_MS == bar.open_time_ms:
            window_cache[bar.market_id] = (*cached, bar)[-_WINDOW_CACHE_BARS:]
        elif bar.open_time_ms == cached[-1].open_time_ms:
            pass
        else:
            # Out-of-order admission cannot extend the rolling tail; restart
            # tracking from this bar and let the next window reseed from SQL.
            window_cache[bar.market_id] = (bar,)

    def _clear_failure_if_contiguous(self, market_id: str) -> None:
        # Exact bounded proof: with unique primary-key opens, contiguity is
        # max - min == (count - 1) * 5m; no historical deserialization.
        if self.store.is_contiguous_5m(market_id):
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
