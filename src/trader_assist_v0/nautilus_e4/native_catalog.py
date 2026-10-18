"""rc7 native storage composition and fail-closed typed promotion verification.

The native writer is the only market-data archive owner. Project evidence may
reference these records but must not create another full market-data catalog.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

RC7_VERSION = "2.0.0rc7"
RC7_WHEEL_SHA256 = "b3928f37d75d57508030a421dc762186ad1f9ffc5d5420d7daf1d2c6badb8044"
BACKTEST_BATCH_DELTAS = True


def streaming_config(root: Path) -> Any:
    from nautilus_trader.persistence import DataCatalogConfig, RotationConfig, StreamingConfig

    root.mkdir(parents=True, exist_ok=True)
    # Tagged guide: never split equal ts_init rows across rotating/promoted files.
    # One shared root also makes native crash-recovery/manual promotion target the same catalog.
    return StreamingConfig(
        writer_path=str(root),
        catalog=DataCatalogConfig(path=str(root)),
        rotation_config=RotationConfig.no_rotation(),
        promotion_interval_ms=None,
        promote_on_close=True,
        delete_feather_after_promotion=False,
        use_ts_event_for_ts_init=False,
        replace_existing=False,
        flush_interval_ms=1000,
    )


def _identity(event: Any) -> str:
    # Official typed serialization preserves economic precision and ts_event/ts_init.
    payload = type(event).to_dict(event)
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
    queries = {
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
    # Native read recovers unlocked partial files, retaining complete record batches.
    if live:
        catalog.read_live_run(instance_id)
    else:
        catalog.read_backtest(instance_id)
    for data_type in catalog.list_data_types():
        if isinstance(data_type, NautilusDataType):
            catalog.convert_stream_to_data(
                instance_id, data_type, Environment.LIVE if live else Environment.BACKTEST
            )
    return verify_promoted_run(root, instance_id, live=live)


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
