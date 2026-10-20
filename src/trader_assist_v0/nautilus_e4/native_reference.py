# mypy: disable-error-code="import-not-found,misc"
"""Native reference-product admission/readback. Never maps token prices to HL equities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .native_capture import native_event_hash
from .native_catalog import RC7_VERSION, event_multiset, recover_and_promote
from .native_health import NativeHealth

# Scoped requirements, not claims that these exchange-native instruments exist.
CANDIDATES = {
    "BINANCE": (
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "NVDABUSDT",
        "SNDKBUSDT",
        "TSLABUSDT",
        "AAPLBUSDT",
        "METABUSDT",
        "MSFTBUSDT",
        "GOOGLBUSDT",
        "AMDBUSDT",
        "SKHYBUSDT",
    ),
    "OKX": (
        "BTC-USDT-SWAP",
        "ETH-USDT-SWAP",
        "SOL-USDT-SWAP",
        "SKHYNIX-USDT-SWAP",
        "SNDK-USDT-SWAP",
        "NVDA-USDT-SWAP",
        "TSLA-USDT-SWAP",
        "AAPL-USDT-SWAP",
    ),
}
AGES = {"quote": 30_000_000_000, "trade": 30_000_000_000, "1m": 90_000_000_000}
CONTRACT_FIELDS = (
    "id",
    "raw_symbol",
    "base_currency",
    "quote_currency",
    "settlement_currency",
    "is_inverse",
    "price_precision",
    "size_precision",
    "price_increment",
    "size_increment",
    "multiplier",
    "lot_size",
)


def reference_bar_end(event: Any) -> int:
    """Official Binance close-ms versus OKX open-ms; preserve both native clocks."""
    from nautilus_trader.model import AggregationSource, BarAggregation

    kind = event.bar_type
    if (
        kind.spec.step != 1
        or kind.spec.aggregation != BarAggregation.MINUTE
        or kind.aggregation_source != AggregationSource.EXTERNAL
    ):
        raise ValueError("REFERENCE_NOT_EXTERNAL_CLOSED_1M")
    venue = str(kind.instrument_id.venue)
    if venue == "BINANCE":
        end = event.ts_event + 1_000_000  # native Binance closeTime is inclusive milliseconds
    elif venue == "OKX":
        end = event.ts_event + 60_000_000_000
    else:
        raise ValueError("REFERENCE_WRONG_VENUE")
    if end % 60_000_000_000 or end > event.ts_init:
        raise ValueError("REFERENCE_BAR_NOT_CLOSED")
    return int(end)


class ReferenceReader:
    """Bounded latest-input consumer; native streaming remains the sole event store."""

    def __init__(self) -> None:
        self.instruments: dict[str, Any] = {}
        self.hashes: dict[str, str] = {}
        self.latest: dict[str, Any] = {}
        self.rejects: dict[str, int] = {}
        self.health = NativeHealth({})
        self.provider_seen: set[str] = set()

    def admit(self, instrument: Any) -> bool:
        from nautilus_trader.model import CryptoPerpetual, CurrencyPair

        venue, symbol = str(instrument.id.venue), str(instrument.raw_symbol)
        if venue not in CANDIDATES:
            return False
        self.provider_seen.add(venue)
        if symbol not in CANDIDATES[venue]:
            return False
        expected_type = CurrencyPair if venue == "BINANCE" else CryptoPerpetual
        if (
            not isinstance(instrument, expected_type)
            or str(instrument.quote_currency) != "USDT"
            or instrument.multiplier.as_decimal() <= 0
            or instrument.price_increment.as_decimal() <= 0
            or instrument.size_increment.as_decimal() <= 0
        ):
            raise ValueError("REFERENCE_NATIVE_CONTRACT_MISMATCH")
        identity = str(instrument.id)
        prior = self.instruments.get(identity)
        if prior is not None:
            if any(
                str(getattr(prior, f, None)) != str(getattr(instrument, f, None))
                for f in CONTRACT_FIELDS
            ):
                raise ValueError("REFERENCE_NATIVE_CONTRACT_CHANGED")
            return False
        if any(
            str(x.id.venue) == venue and str(x.raw_symbol) == symbol
            for x in self.instruments.values()
        ):
            raise ValueError("REFERENCE_AMBIGUOUS_NATIVE_SYMBOL")
        self.instruments[identity] = instrument
        self.health.required.update({f"{identity}:{kind}": age for kind, age in AGES.items()})
        return True

    def reject(self, reason: str) -> bool:
        self.rejects[reason] = self.rejects.get(reason, 0) + 1
        return False

    def consume(self, event: Any, *, now_ns: int) -> bool:
        name = type(event).__name__
        kind = {"QuoteTick": "quote", "TradeTick": "trade", "Bar": "1m"}.get(name)
        if kind is None:
            return self.reject("UNSUPPORTED_REFERENCE_TYPE")
        identity = str(event.bar_type.instrument_id if kind == "1m" else event.instrument_id)
        instrument = self.instruments.get(identity)
        if instrument is None:
            return self.reject("UNRESOLVED_IDENTITY")
        if not 0 < event.ts_event <= event.ts_init <= now_ns:
            return self.reject("NONCAUSAL_CLOCK")
        try:
            end = reference_bar_end(event) if kind == "1m" else event.ts_event
        except ValueError as exc:
            return self.reject(str(exc))
        if now_ns - event.ts_init > AGES[kind] or now_ns - end > AGES[kind]:
            return self.reject("STALE")
        prices = (
            [event.bid_price, event.ask_price]
            if kind == "quote"
            else [event.price]
            if kind == "trade"
            else [event.open, event.high, event.low, event.close]
        )
        sizes = (
            [event.bid_size, event.ask_size]
            if kind == "quote"
            else [event.size]
            if kind == "trade"
            else [event.volume]
        )
        if (
            any(
                p.as_decimal() <= 0 or p.as_decimal() % instrument.price_increment.as_decimal()
                for p in prices
            )
            or any(q.as_decimal() % instrument.size_increment.as_decimal() for q in sizes)
            or (kind == "trade" and event.size.as_decimal() <= 0)
            or (kind == "quote" and event.ask_price < event.bid_price)
        ):
            return self.reject("NATIVE_PRICE_SIZE_CONTRACT_MISMATCH")
        key = f"{identity}:{kind}"
        digest = native_event_hash(event)
        prior = self.latest.get(key)
        if prior is not None:
            if digest == self.hashes[key] or (kind == "1m" and event.ts_event == prior.ts_event):
                return self.reject("DUPLICATE")
            if (event.ts_event, event.ts_init) < (prior.ts_event, prior.ts_init):
                return self.reject("OUT_OF_ORDER")
        pending_gap = key in self.health.pending_gaps
        gaps = len(self.health.gaps)
        if not self.health.observe(
            key, ts_event=event.ts_event, ts_init=event.ts_init, now=now_ns, event_end_ns=end
        ):
            return self.reject("INVALID_NATIVE_HEALTH_EVENT")
        if pending_gap or len(self.health.gaps) > gaps:
            return self.reject("GAP")
        self.latest[key], self.hashes[key] = event, digest
        return True

    def coverage(self) -> dict[str, Any]:
        resolved = {(str(i.id.venue), str(i.raw_symbol)): i for i in self.instruments.values()}
        result = {}
        for venue, symbols in CANDIDATES.items():
            rows = []
            for symbol in symbols:
                instrument = resolved.get((venue, symbol))
                missing = (
                    [k for k in AGES if f"{instrument.id}:{k}" not in self.hashes]
                    if instrument is not None
                    else list(AGES)
                )
                rows.append(
                    {
                        "candidate": symbol,
                        "instrument_id": str(instrument.id) if instrument is not None else None,
                        "status": (
                            "NATIVE_INPUTS_OBSERVED"
                            if not missing
                            else "MISSING_FAMILIES"
                            if instrument is not None
                            else "NOT_RETURNED_BY_NATIVE_PROVIDER"
                            if venue in self.provider_seen
                            else "PROVIDER_UNAVAILABLE_OR_UNOBSERVED"
                        ),
                        "instrument": instrument.to_dict() if instrument is not None else None,
                        "missing_families": missing,
                    }
                )
            result[venue] = rows
        return {
            "schema": "RC7_NATIVE_REFERENCE_V1",
            "native_version": RC7_VERSION,
            "venues": result,
            "source_callback_hashes": dict(self.hashes),
            "rejects": dict(self.rejects),
            "gaps": self.health.gaps,
            "equity_or_HL_price_equivalence": "NOT_ASSERTED",
        }


def reference_actor(reader: ReferenceReader, *, venues: tuple[str, ...] = tuple(CANDIDATES)) -> Any:
    from nautilus_trader.common import DataActor
    from nautilus_trader.model import BarType, Venue

    class NativeReferenceObserver(DataActor):
        def on_start(self) -> None:
            self.subscribe_socket_state()
            for venue in venues:
                instruments = self.cache.instruments(Venue(venue))
                for instrument in instruments:
                    self.on_instrument(instrument)
                if not instruments:
                    self.request_instruments(venue=Venue(venue))

        def on_instrument(self, instrument: Any) -> None:
            if reader.admit(instrument):
                self.subscribe_quotes(instrument.id)
                self.subscribe_trades(instrument.id)
                self.subscribe_bars(BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"))

        def on_quote(self, event: Any) -> None:
            reader.consume(event, now_ns=self.clock.timestamp_ns())

        def on_trade(self, event: Any) -> None:
            reader.consume(event, now_ns=self.clock.timestamp_ns())

        def on_bar(self, event: Any) -> None:
            reader.consume(event, now_ns=self.clock.timestamp_ns())

        def on_socket_state(self, event: Any) -> None:
            venue = str(event.venue)
            state = str(event.state).split(".")[-1].upper()
            if venue in CANDIDATES and state not in {"CONNECTED", "ACTIVE"}:
                for identity, instrument in reader.instruments.items():
                    if str(instrument.id.venue) == venue:
                        for family in AGES:
                            reader.health.mark_gap(
                                f"{identity}:{family}",
                                "NATIVE_DISCONNECT",
                                self.clock.timestamp_ns(),
                            )

    return NativeReferenceObserver()


def reference_proof(
    root: Path,
    instance_id: str,
    live: ReferenceReader,
    *,
    required_venues: tuple[str, ...] = tuple(CANDIDATES),
) -> dict[str, Any]:
    """Finite sealed proof only. Native full-run APIs do not promise rolling bounded queries."""
    from nautilus_trader.persistence import ParquetDataCatalog

    if not required_venues or not set(required_venues) <= CANDIDATES.keys():
        raise ValueError("REFERENCE_REQUIRED_VENUES_INVALID")
    stage = root / "live" / instance_id
    if list(stage.rglob("*.feather.partial")):
        raise ValueError("REFERENCE_REQUIRES_SEALED_RUN")
    if sum(p.stat().st_size for p in stage.rglob("*.feather")) > 64 * 1024 * 1024:
        raise ValueError("REFERENCE_FINITE_PROOF_SOURCE_TOO_LARGE")
    catalog = ParquetDataCatalog(str(root))
    source = catalog.read_live_run(instance_id)
    # Existing native converter verifies counts/digests and retains Feather; no replacement store.
    archive = recover_and_promote(root, instance_id)
    restored = [*catalog.query_quote_ticks(), *catalog.query_trade_ticks(), *catalog.query_bars()]
    identities = set(live.instruments)

    def relevant(event: Any) -> bool:
        identity = str(
            event.bar_type.instrument_id
            if type(event).__name__ == "Bar"
            else getattr(event, "instrument_id", "")
        )
        return identity in identities and type(event).__name__ in {"QuoteTick", "TradeTick", "Bar"}

    source = [e for e in source if relevant(e)]
    restored = [e for e in restored if relevant(e)]
    if event_multiset(source) != event_multiset(restored):
        raise ValueError("REFERENCE_NATIVE_READBACK_MISMATCH")
    reader = ReferenceReader()
    stored_instruments = catalog.instruments(instrument_ids=list(live.instruments))
    for instrument in stored_instruments:
        original = live.instruments[str(instrument.id)]
        if any(
            str(getattr(instrument, f, None)) != str(getattr(original, f, None))
            for f in CONTRACT_FIELDS
        ):
            raise ValueError("REFERENCE_STORED_CONTRACT_MISMATCH")
        reader.admit(instrument)
    if set(reader.instruments) != identities:
        raise ValueError("REFERENCE_STORED_INSTRUMENT_MISSING")
    seen = set()
    for event in sorted(restored, key=lambda e: (e.ts_init, e.ts_event)):
        seen.add(native_event_hash(event))
        reader.consume(event, now_ns=event.ts_init)
    if not set(live.hashes.values()) <= seen:
        raise ValueError("REFERENCE_CALLBACK_SOURCE_MISSING")
    coverage = reader.coverage()
    for rows in coverage["venues"].values():
        for row in rows:
            identity = row["instrument_id"]
            row["missing_callback_families"] = [
                k for k in AGES if f"{identity}:{k}" not in live.hashes
            ]
    qualified = {
        venue: [
            r["candidate"]
            for r in rows
            if not r["missing_families"] and not r["missing_callback_families"]
        ]
        for venue, rows in coverage["venues"].items()
    }
    coverage.update(
        archive=archive,
        qualified=qualified,
        source="OFFICIAL_NATIVE_FINITE_SEALED_FEATHER_AND_TYPED_PARQUET",
        capture_rejects=live.rejects,
        capture_gaps=live.health.gaps,
        rolling_catalog="UNQUALIFIED",
        readback_count=len(restored),
    )
    coverage["status"] = (
        "AVAILABLE_NATIVE_SUBSET_PROVEN"
        if all(qualified[v] for v in required_venues)
        and not live.health.gaps
        and not reader.health.gaps
        and not (set(live.rejects) | set(reader.rejects)) - {"DUPLICATE"}
        else "INCOMPLETE"
    )
    return coverage
