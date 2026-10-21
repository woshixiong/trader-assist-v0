# mypy: disable-error-code="import-not-found,misc"
"""rc7 native storage composition and fail-closed typed promotion verification.

The native writer is the only market-data archive owner. Project evidence may
reference these records but must not create another full market-data catalog.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

RC7_VERSION = "2.0.0rc7"
RC7_WHEEL_SHA256 = "b3928f37d75d57508030a421dc762186ad1f9ffc5d5420d7daf1d2c6badb8044"
BACKTEST_BATCH_DELTAS = True
STAGE_ROTATION_NS = 300_000_000_000


class ArchiveIntegrityError(RuntimeError):
    """Fatal native archive read/recovery failure; never automatically restart."""


def archive_data_types(profile: str) -> list[Any] | None:
    """Native family-global archival selection; does not change live subscriptions."""
    from nautilus_trader.model import NautilusDataType

    if profile == "FULL_NATIVE":
        return None
    if profile != "LEAN":
        raise ValueError("UNSUPPORTED_NATIVE_ARCHIVE_PROFILE")
    return [
        NautilusDataType.Bar,
        NautilusDataType.MarkPriceUpdate,
        NautilusDataType.IndexPriceUpdate,
        NautilusDataType.FundingRateUpdate,
        NautilusDataType.Custom("HyperliquidOpenInterest"),
    ]


def streaming_config(
    root: Path, *, continuous: bool = False, archive_profile: str = "FULL_NATIVE"
) -> Any:
    from nautilus_trader.model import NautilusInstrumentType
    from nautilus_trader.persistence import DataCatalogConfig, RotationConfig, StreamingConfig

    selected = archive_data_types(archive_profile)
    root.mkdir(parents=True, exist_ok=True)
    # Tagged guide: never split equal ts_init rows across rotating/promoted files.
    # One shared root also makes native crash-recovery/manual promotion target the same catalog.
    return StreamingConfig(
        writer_path=str(root),
        catalog=DataCatalogConfig(path=str(root), compression="zstd"),
        data_types=selected,
        # With a native family whitelist, metadata must be explicitly included too.
        # These are the actual admitted native types of the three public clients.
        instrument_types=(
            [NautilusInstrumentType("CryptoPerpetual"), NautilusInstrumentType("CurrencyPair")]
            if archive_profile == "LEAN"
            else None
        ),
        rotation_config=(
            RotationConfig.interval(STAGE_ROTATION_NS)
            if continuous
            else RotationConfig.no_rotation()
        ),
        promotion_interval_ms=None,
        # Rotation may split equal ts_init across files. Keep native staging,
        # including on close; explicit conversion must prove disjoint intervals.
        promote_on_close=not continuous,
        delete_feather_after_promotion=False,
        use_ts_event_for_ts_init=False,
        replace_existing=False,
        flush_interval_ms=1000,
    )


def read_staged_run(
    root: Path, instance_id: str, *, require_closed: bool = False
) -> dict[str, Any]:
    """Official sealed-Feather reader, not a complete live-run/catalog certificate.

    Locked partials remain untouched; unlocked crash remnants are recovered by
    Nautilus. This native API sorts by ts_init and loads the available run in
    memory. It does not promise an atomic snapshot or global equal-time ordering
    across data families. No promotion or custom storage occurs here.
    """
    from nautilus_trader.persistence import ParquetDataCatalog

    try:
        data = ParquetDataCatalog(str(root)).read_live_run(instance_id)
        partials = sorted(
            str(p.relative_to(root))
            for p in (root / "live" / instance_id).rglob("*.feather.partial")
        )
        if require_closed and (partials or not data):
            raise RuntimeError("CLOSED_NATIVE_STAGE_INCOMPLETE")
        types = {}
        for name in sorted({type(event).__name__ for event in data}):
            count, digest = event_multiset(
                [event for event in data if type(event).__name__ == name]
            )
            types[name] = {"count": count, "sha256": digest}
        return {
            "status": "SEALED_STAGE_READABLE",
            "instance_id": instance_id,
            "types": types,
            "open_partials": partials,
            "complete_stopped_run": require_closed,
            "catalog": "NOT_VERIFIED_OR_PROMOTED",
            "source_retained": True,
        }
    except Exception as exc:
        raise ArchiveIntegrityError(f"NATIVE_STAGE_READ_FAILURE:{exc}") from exc


def _identity(event: Any) -> str:
    # Native read_live_run wraps registered custom records in CustomData, which
    # has no to_dict. Use the official inner type, not a new codec/store.
    event = getattr(event, "data", event)
    if type(event).__name__ == "HyperliquidOpenInterest":
        from .native_context import context_identity

        return "HyperliquidOpenInterest:" + context_identity(event)[2]
    # Official typed serialization preserves economic precision and ts_event/ts_init.
    payload = type(event).to_dict(event)
    # The tagged native promotion contract adopts neighbouring precision for
    # CLEAR's zero-valued sentinel order. Compare its numeric zeros, while
    # retaining every nonzero value, action, sequence, flag and timestamp.
    if type(event).__name__ == "OrderBookDelta" and event.is_clear:
        order = payload["order"]
        if event.order.side is None and event.order.order_id == 0:
            for key in ("price", "size"):
                if Decimal(order[key]) == 0:
                    order[key] = "0"
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def event_multiset(events: list[Any]) -> tuple[int, str]:
    counts = Counter(_identity(event) for event in events)
    digest = hashlib.sha256(json.dumps(sorted(counts.items()), separators=(",", ":")).encode())
    return len(events), digest.hexdigest()


def verify_promoted_run(root: Path, instance_id: str, *, live: bool = True) -> dict[str, Any]:
    """Require complete source->typed catalog counts/digests, including duplicates.

    Query only the exact staged event time range/identifiers; never compare the
    Actor callback window with the native sink's larger lifecycle. Any missing
    family, read/precision/promotion error propagates; nothing becomes PASS.
    """
    from nautilus_trader.model import Bar, OrderBookDelta, OrderBookDepth, QuoteTick, TradeTick
    from nautilus_trader.persistence import ParquetDataCatalog

    catalog = ParquetDataCatalog(str(root))
    staged = catalog.read_live_run(instance_id) if live else catalog.read_backtest(instance_id)
    stage = root / ("live" if live else "backtest") / instance_id
    if list(stage.rglob("*.feather.partial")):
        # Native recovery leaves locked or unrecoverable files in place. Reading
        # the sealed subset is not evidence of a complete stopped run.
        raise RuntimeError("ACTIVE_OR_UNRECOVERED_NATIVE_STAGE")
    queries: dict[type[Any], Callable[..., list[Any]]] = {
        QuoteTick: catalog.query_quote_ticks,
        TradeTick: catalog.query_trade_ticks,
        OrderBookDepth: catalog.query_order_book_depths,
        OrderBookDelta: catalog.query_order_book_deltas,
        Bar: catalog.query_bars,
    }
    result: dict[str, Any] = {}
    for cls, query in queries.items():
        source = [item for item in staged if isinstance(item, cls)]
        if not source:
            continue
        identifiers = sorted(
            {str(item.bar_type if isinstance(item, Bar) else item.instrument_id) for item in source}
        )
        restored = query(
            identifiers=identifiers,
            start=min(e.ts_init for e in source),
            end=max(e.ts_init for e in source),
        )
        expected, actual = event_multiset(source), event_multiset(restored)
        if expected != actual:
            raise RuntimeError(f"CATALOG_INTEGRITY_FAILURE:{cls.__name__}:{expected}:{actual}")
        result[cls.__name__] = {"count": expected[0], "sha256": expected[1]}
    if not result:
        raise RuntimeError("NO_TYPED_MARKET_DATA_IN_STAGE")
    return {
        "status": "PASS",
        "instance_id": instance_id,
        "types": result,
        "wire_receive_timestamp": "NOT_EXPOSED",
        "source_retained": True,
    }


def recover_and_promote(root: Path, instance_id: str, *, live: bool = True) -> dict[str, Any]:
    """Use official locked-partial recovery and replay identities; no custom copier."""
    from nautilus_trader.common import Environment
    from nautilus_trader.model import NautilusDataType
    from nautilus_trader.persistence import ParquetDataCatalog

    catalog = ParquetDataCatalog(str(root))
    from nautilus_trader.model import Bar, OrderBookDelta, OrderBookDepth, QuoteTick, TradeTick

    staged = catalog.read_live_run(instance_id) if live else catalog.read_backtest(instance_id)
    families = {
        QuoteTick: NautilusDataType.QuoteTick,
        TradeTick: NautilusDataType.TradeTick,
        OrderBookDepth: NautilusDataType.OrderBookDepth,
        OrderBookDelta: NautilusDataType.OrderBookDelta,
        Bar: NautilusDataType.Bar,
    }
    environment = Environment.LIVE if live else Environment.BACKTEST
    try:
        verify_promoted_run(root, instance_id, live=live)
    except RuntimeError as exc:
        if not str(exc).startswith("CATALOG_INTEGRITY_FAILURE:"):
            raise
        # Automatic and manual rc7 promotion use different replay identities.
        # Never re-import an already complete automatic promotion. A partial
        # catalog which cannot be promoted natively still fails with sources retained.
        for cls, data_type in families.items():
            if any(isinstance(event, cls) for event in staged):
                catalog.convert_stream_to_data(instance_id, data_type, environment)
    ids = sorted(
        {
            str(event.bar_type.instrument_id if isinstance(event, Bar) else event.instrument_id)
            for event in staged
            if isinstance(event, tuple(families))
        }
    )
    present = {str(item.id) for item in catalog.instruments(instrument_ids=ids)}
    missing = sorted(set(ids) - present)
    if missing:
        # read_live_run/read_backtest return Data only, not instrument records.
        # The tagged converter explicitly requires the aggregate Instrument
        # family, not NautilusInstrumentType.CryptoPerpetual.
        catalog.convert_stream_to_data(
            instance_id,
            NautilusDataType.Instrument,
            environment,
            identifiers=missing,
        )
        restored = {str(item.id) for item in catalog.instruments(instrument_ids=ids)}
        if not set(ids) <= restored:
            raise RuntimeError("RECOVERY_NATIVE_INSTRUMENT_DEFINITIONS_MISSING")
    return verify_promoted_run(root, instance_id, live=live)


def replay_catalog_quotes(root: Path, instance_id: str, *, live: bool = True) -> dict[str, Any]:
    """Two native Engine runs over the exact promoted run's typed quote window.

    This is data replay qualification, with no orders or strategy economics.
    Existing matched strategy replay remains the financial-behavior owner.
    """
    from decimal import Decimal

    from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.common import DataActor
    from nautilus_trader.execution import MakerTakerFeeModel
    from nautilus_trader.model import AccountType, BookType, Money, OmsType, QuoteTick, Venue
    from nautilus_trader.persistence import ParquetDataCatalog

    verify_promoted_run(root, instance_id, live=live)
    catalog = ParquetDataCatalog(str(root))
    stage = catalog.read_live_run(instance_id) if live else catalog.read_backtest(instance_id)
    source = [event for event in stage if isinstance(event, QuoteTick)]
    if not source:
        raise RuntimeError("REPLAY_REQUIRES_PROMOTED_QUOTES")
    if any(event.ts_init < event.ts_event for event in source):
        raise RuntimeError("NONCAUSAL_QUOTE_TIMESTAMP")
    ids = sorted({str(event.instrument_id) for event in source})
    quotes = catalog.query_quote_ticks(
        identifiers=ids,
        start=min(event.ts_init for event in source),
        end=max(event.ts_init for event in source),
    )
    first_init = min(event.ts_init for event in source)
    # Native range queries retain the latest pre-start definition. Do not load
    # later definitions into an earlier replay (including after a capture restart).
    instruments = catalog.instruments(instrument_ids=ids, start=first_init, end=first_init)
    if {str(item.id) for item in instruments} != set(ids):
        raise RuntimeError("REPLAY_NATIVE_INSTRUMENT_DEFINITIONS_MISSING")

    def observer(received: list[Any]) -> Any:
        class Observer(DataActor):
            def on_start(self) -> None:
                for instrument in instruments:
                    self.subscribe_quotes(instrument.id)

            def on_quote(self, event: Any) -> None:
                received.append(event)

        return Observer()

    repetitions: list[str] = []
    for _ in range(2):
        received: list[Any] = []
        engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True, run_analysis=False))
        try:
            engine.add_venue(
                venue=Venue("HYPERLIQUID"),
                oms_type=OmsType.NETTING,
                account_type=AccountType.MARGIN,
                starting_balances=[Money.from_str("100000 USDC")],
                book_type=BookType.L1_MBP,
                fee_model=MakerTakerFeeModel(Decimal(0), Decimal(0)),
            )
            for instrument in instruments:
                engine.add_instrument(instrument)
            engine.add_actor(observer(received))
            engine.add_data(quotes)
            engine.run()
            if event_multiset(received) != event_multiset(source):
                raise RuntimeError("REPLAY_TYPED_EVENT_MISMATCH")
            repetitions.append(
                hashlib.sha256(
                    "\n".join(_identity(event) for event in received).encode()
                ).hexdigest()
            )
        finally:
            engine.dispose()
    if repetitions[0] != repetitions[1]:
        raise RuntimeError("NATIVE_REPLAY_NONDETERMINISTIC")
    return {
        "status": "PASS",
        "quote_count": len(source),
        "ordered_sha256": repetitions[0],
        "native_engine_runs": 2,
        "orders": "NONE_DATA_REPLAY_ONLY",
        "book_batch_deltas": BACKTEST_BATCH_DELTAS,
    }


def replay_data_config(
    root: Path, data_type: Any, instrument_id: Any, *, start: int, end: int
) -> Any:
    from nautilus_trader.backtest import BacktestDataConfig

    if not 0 < start <= end:
        raise ValueError("replay must have an explicit causal time range")
    return BacktestDataConfig(
        catalog_path=str(root),
        data_type=data_type,
        instrument_id=instrument_id,
        start_time=start,
        end_time=end,
        batch_deltas=BACKTEST_BATCH_DELTAS,
    )
