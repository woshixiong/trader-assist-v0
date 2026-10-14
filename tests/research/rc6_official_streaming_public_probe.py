#!/usr/bin/env python3
"""One GitHub-only, public-data, official rc6 native streaming qualification.

This file is a test harness only. It does not place orders, open an execution
client, write market data, or modify Trade OS's pinned Nautilus environment.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
import traceback


PACKAGE_ID = "RC6_OFFICIAL_NATIVE_STREAMING_GITHUB_PUBLIC_SPIKE_1"
INSTRUMENT_TEXT = "ETH-USD-PERP.HYPERLIQUID"
FAMILIES = ("quote", "trade", "depth", "bar")
MAX_DISTINCT_FINGERPRINTS = 200_000
TARGET_OBSERVATION_SECS = 180
MAX_RECEPTION_SECS = 240


class ResearchContractError(Exception):
    pass


class NativeArchiveError(Exception):
    pass


class ProviderEvidenceError(Exception):
    pass


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


def pvalue(item):
    # No binary float conversion: both the raw fixed-point integer and
    # the declared decimal precision are part of every event fingerprint.
    return [str(item.raw), int(item.precision)]


def event_payload(item):
    """First-party typed model fields, never repr/log-line parsing."""
    from nautilus_trader.model import Bar
    from nautilus_trader.model import OrderBookDepth
    from nautilus_trader.model import QuoteTick
    from nautilus_trader.model import TradeTick

    common = {"ts_event": int(item.ts_event), "ts_init": int(item.ts_init)}
    if isinstance(item, QuoteTick):
        return "quote", dict(
            common, instrument_id=str(item.instrument_id),
            bid_price=pvalue(item.bid_price), bid_size=pvalue(item.bid_size),
            ask_price=pvalue(item.ask_price), ask_size=pvalue(item.ask_size),
        )
    if isinstance(item, TradeTick):
        return "trade", dict(
            common, instrument_id=str(item.instrument_id),
            trade_id=str(item.trade_id), aggressor_side=str(item.aggressor_side),
            price=pvalue(item.price), size=pvalue(item.size),
        )
    if isinstance(item, OrderBookDepth):
        def book_order(order):
            return [
                str(order.side), pvalue(order.price), pvalue(order.size),
                int(order.order_id),
            ]

        return "depth", dict(
            common, instrument_id=str(item.instrument_id),
            bids=[book_order(x) for x in item.bids],
            asks=[book_order(x) for x in item.asks],
            bid_counts=[int(x) for x in item.bid_counts],
            ask_counts=[int(x) for x in item.ask_counts],
            flags=int(item.flags), sequence=int(item.sequence),
        )
    if isinstance(item, Bar):
        return "bar", dict(
            common, instrument_id=str(item.bar_type.instrument_id),
            bar_type=str(item.bar_type),
            open=pvalue(item.open), high=pvalue(item.high),
            low=pvalue(item.low), close=pvalue(item.close),
            volume=pvalue(item.volume),
        )
    return None, None


class FamilyEvidence:
    """Bounded in-memory, multiset-preserving observation; no data recorder."""
    def __init__(self, instrument, bar_type):
        self.instrument = instrument
        self.bar_type = bar_type
        self.counters = {kind: Counter() for kind in FAMILIES}
        self.timing = {
            kind: {"first_event": None, "last_event": None,
                   "min_ts_init": None, "max_ts_init": None,
                   "min_ts_event": None, "max_ts_event": None}
            for kind in FAMILIES
        }
        self.errors = []
        self.depth_levels = {"bids_min": None, "bids_max": None,
                             "asks_min": None, "asks_max": None}
        self.callback_first_utc = None
        self.callback_last_utc = None
        self.frozen = False

    def add(self, item, expected_kind=None):
        if self.frozen:
            raise ResearchContractError("typed callback after evidence freeze")
        kind, value = event_payload(item)
        if kind is None:
            if expected_kind is not None:
                raise ResearchContractError("unexpected typed callback object")
            return
        if expected_kind is not None and expected_kind != kind:
            raise ResearchContractError("callback category differs from native type")
        if value["instrument_id"] != self.instrument:
            raise ResearchContractError("unexpected instrument in typed callback/readback")
        if kind == "bar" and value["bar_type"] != self.bar_type:
            raise ResearchContractError("unexpected non-external/non-1m bar type")

        if len(self.counters[kind]) >= MAX_DISTINCT_FINGERPRINTS:
            raise ResearchContractError("bounded fingerprint multiset cap reached")
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
        key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.counters[kind][key] += 1
        t = self.timing[kind]
        for src, min_key, max_key in (
            ("ts_init", "min_ts_init", "max_ts_init"),
            ("ts_event", "min_ts_event", "max_ts_event"),
        ):
            stamp = value[src]
            t[min_key] = stamp if t[min_key] is None else min(t[min_key], stamp)
            t[max_key] = stamp if t[max_key] is None else max(t[max_key], stamp)
        t["first_event"] = t["first_event"] or value["ts_event"]
        t["last_event"] = value["ts_event"]

        if kind == "depth":
            for side, name in (("bids", "bids"), ("asks", "asks")):
                n = len(value[side])
                kmin, kmax = name + "_min", name + "_max"
                self.depth_levels[kmin] = n if self.depth_levels[kmin] is None else min(self.depth_levels[kmin], n)
                self.depth_levels[kmax] = n if self.depth_levels[kmax] is None else max(self.depth_levels[kmax], n)

    def count(self, kind):
        return sum(self.counters[kind].values())

    def digest(self, kind):
        entries = sorted(self.counters[kind].items())
        encoded = json.dumps(entries, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def summary(self, kind):
        return {"count": self.count(kind), "digest": self.digest(kind),
                **self.timing[kind]}


def catalog_evidence(rows, instrument, bar_type):
    info = FamilyEvidence(instrument, bar_type)
    for item in rows:
        info.add(item)
    info.frozen = True
    return info


async def probe(out):
    # Import from the actually installed rc6 wheel, not a project's rc5 source.
    dist_version = importlib.metadata.version("nautilus-trader")
    if dist_version != "2.0.0rc6":
        raise NativeArchiveError("installed official package version mismatch")
    out["wheel_version"] = dist_version

    from nautilus_trader.adapters.hyperliquid import HyperliquidDataClientConfig
    from nautilus_trader.adapters.hyperliquid import HyperliquidDataClientFactory
    from nautilus_trader.adapters.hyperliquid import HyperliquidEnvironment
    from nautilus_trader.common import DataActor
    from nautilus_trader.common import DataActorConfig
    from nautilus_trader.common import Environment
    from nautilus_trader.live import LiveNodeBuilder
    from nautilus_trader.live import LiveNodeConfig
    from nautilus_trader.model import ActorId
    from nautilus_trader.model import AggregationSource
    from nautilus_trader.model import BarAggregation
    from nautilus_trader.model import BarSpecification
    from nautilus_trader.model import BarType
    from nautilus_trader.model import BookType
    from nautilus_trader.model import ClientId
    from nautilus_trader.model import InstrumentId
    from nautilus_trader.model import PriceType
    from nautilus_trader.model import TraderId
    from nautilus_trader.persistence import DataCatalogConfig
    from nautilus_trader.persistence import ParquetDataCatalog
    from nautilus_trader.persistence import StreamingConfig
    from nautilus_trader.testkit import DataTesterConfig

    instrument = InstrumentId.from_str(INSTRUMENT_TEXT)
    client_id = ClientId.from_str("HYPERLIQUID")
    bar_type = BarType(
        instrument,
        BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    if not bar_type.is_externally_aggregated():
        raise ResearchContractError("bar must be official EXTERNAL 1m")
    out["bar_type"] = str(bar_type)
    out["book_type"] = str(BookType.L2_MBP)
    out["subscriber_contract"] = "same client/instrument/L2_MBP/no depth override/external bar type"
    out["subscriber_dedup_basis"] = "official rc6 DataClientAdapter key retention; one native client"
    received = FamilyEvidence(INSTRUMENT_TEXT, str(bar_type))
    root = Path(os.environ["RC6_DATA_ROOT"])
    stage_root = root / "stage"
    catalog_root = root / "promoted"
    stage_root.mkdir(parents=True, exist_ok=False)
    catalog_root.mkdir(parents=True, exist_ok=False)

    class ReadOnlyObserver(DataActor):
        def __init__(self):
            super().__init__(DataActorConfig(actor_id=ActorId.from_str("RC6-OBSERVER")))
            self.on_start_utc = None
            self.on_stop_utc = None

        def on_start(self):
            self.on_start_utc = utc_timestamp()
            self.subscribe_quotes(instrument, client_id)
            self.subscribe_trades(instrument, client_id)
            self.subscribe_book_depth(instrument, BookType.L2_MBP,
                                      depth=None, client_id=client_id, managed=True)
            self.subscribe_bars(bar_type, client_id)

        def on_stop(self):
            self.on_stop_utc = utc_timestamp()
            # Keep observation alive during the native stop/drain phase.

        def accept(self, kind, item):
            now = utc_timestamp()
            if received.callback_first_utc is None:
                received.callback_first_utc = now
            received.callback_last_utc = now
            received.add(item, expected_kind=kind)

        def on_quote(self, data):
            self.accept("quote", data)

        def on_trade(self, data):
            self.accept("trade", data)

        def on_book_depth(self, data):
            self.accept("depth", data)

        def on_bar(self, data):
            self.accept("bar", data)

    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId.from_str("RC6-PUBLIC-001"),
        streaming=StreamingConfig(
            writer_path=str(stage_root),
            catalog=DataCatalogConfig(path=str(catalog_root)),
            promote_on_close=True,
            delete_feather_after_promotion=False,
        ),
    )
    node = (
        LiveNodeBuilder.from_config("RC6-PUBLIC-STREAMING-RESEARCH", config=config)
        .add_data_client(
            None,
            HyperliquidDataClientFactory(),
            HyperliquidDataClientConfig(environment=HyperliquidEnvironment.MAINNET),
        )
        .build()
    )
    out["instance_id"] = str(node.instance_id)
    out["lifecycle"]["registered_utc"] = utc_timestamp()
    node.add_builtin_actor(
        "DataTester",
        DataTesterConfig(
            actor_id=ActorId.from_str("RC6-DATA-TESTER"),
            client_id=client_id,
            instrument_ids=[instrument],
            bar_types=[bar_type],
            subscribe_quotes=True,
            subscribe_trades=True,
            subscribe_book_depth=True,
            subscribe_bars=True,
            book_depth=None,
            manage_book=True,
            log_data=False,
            stats_interval_secs=0,
        ),
    )
    observer = ReadOnlyObserver()
    node.add_actor(observer)
    handle = node.handle()

    # run_async is the first-party hosted lifecycle; cancellation/timeout
    # cannot earn PASS. A single stop request is sent after the 180s target.
    running = asyncio.create_task(node.run_async())
    out["lifecycle"]["run_started_utc"] = utc_timestamp()
    run_started = time.monotonic()
    done, _ = await asyncio.wait({running}, timeout=TARGET_OBSERVATION_SECS)
    if done:
        await running  # surface the actual native/provider failure if present
        raise ProviderEvidenceError("live node exited before bounded observation target")
    out["lifecycle"]["stop_requested_utc"] = utc_timestamp()
    handle.stop()
    try:
        await asyncio.wait_for(asyncio.shield(running), timeout=MAX_RECEPTION_SECS - TARGET_OBSERVATION_SECS)
    except asyncio.TimeoutError as exc:
        running.cancel()
        raise NativeArchiveError("native graceful drain did not complete before deadline") from exc
    out["lifecycle"]["run_completed_utc"] = utc_timestamp()
    out["observation_wall_seconds"] = round(time.monotonic() - run_started, 3)
    node.dispose()
    out["lifecycle"]["disposed_utc"] = utc_timestamp()
    out["lifecycle"]["actor_started_utc"] = observer.on_start_utc
    out["lifecycle"]["actor_stopped_utc"] = observer.on_stop_utc
    out["lifecycle"]["first_callback_utc"] = received.callback_first_utc
    out["lifecycle"]["last_callback_utc"] = received.callback_last_utc
    received.frozen = True
    if observer.on_start_utc is None or observer.on_stop_utc is None:
        raise ResearchContractError("observer lifecycle incomplete")
    if out["observation_wall_seconds"] > MAX_RECEPTION_SECS:
        raise ResearchContractError("observation exceeded hard reception ceiling")

    # B1a: stage-root read_live_run is FEATHER evidence only.
    folder = stage_root / "live" / str(node.instance_id)
    sealed = list(folder.rglob("*.feather")) if folder.exists() else []
    partial = list(folder.rglob("*.partial")) if folder.exists() else []
    out["staging"] = {
        "run_path_present": folder.is_dir(),
        "sealed_file_count": len(sealed),
        "sealed_bytes": sum(f.stat().st_size for f in sealed),
        "unsealed_partial_count": len(partial),
    }
    if not folder.is_dir() or not sealed or partial or any(f.stat().st_size <= 0 for f in sealed):
        raise NativeArchiveError("Feather stage not sealed/nonempty after native close")
    stage_rows = ParquetDataCatalog(str(stage_root)).read_live_run(str(node.instance_id))
    staged = catalog_evidence(stage_rows, INSTRUMENT_TEXT, str(bar_type))

    # B1b: a SEPARATE promoted catalog root and four official typed queries.
    parquet_files = list(catalog_root.rglob("*.parquet"))
    out["promotion"] = {
        "parquet_file_count": len(parquet_files),
        "parquet_bytes": sum(f.stat().st_size for f in parquet_files),
    }
    if not parquet_files or any(f.stat().st_size <= 0 for f in parquet_files):
        raise NativeArchiveError("native close did not promote nonempty Parquet files")

    low = min(
        x.timing[k]["min_ts_init"] for x in (received, staged)
        for k in FAMILIES if x.count(k) > 0
    )
    high = max(
        x.timing[k]["max_ts_init"] for x in (received, staged)
        for k in FAMILIES if x.count(k) > 0
    ) + 1
    promoted_catalog = ParquetDataCatalog(str(catalog_root))
    promoted = FamilyEvidence(INSTRUMENT_TEXT, str(bar_type))
    queries = {
        "quote": ("query_quote_ticks", [INSTRUMENT_TEXT]),
        "trade": ("query_trade_ticks", [INSTRUMENT_TEXT]),
        "depth": ("query_order_book_depths", [INSTRUMENT_TEXT]),
        "bar": ("query_bars", [str(bar_type)]),
    }
    for kind, (method, identifiers) in queries.items():
        query = getattr(promoted_catalog, method)
        bounded = query(identifiers=identifiers, start=low, end=high)
        complete = query(identifiers=identifiers)
        if len(bounded) != len(complete):
            raise NativeArchiveError(kind + ": timestamp predicate hid promoted records")
        for item in complete:
            actual_kind, _ = event_payload(item)
            if actual_kind != kind:
                raise ResearchContractError(kind + ": typed catalog result family mismatch")
            promoted.add(item, expected_kind=kind)
    promoted.frozen = True
    out["promotion"]["typed_queries"] = list(queries)
    out["comparison_ns_bounds"] = [low, high]

    all_good = True
    for kind in FAMILIES:
        a, b, c = received, staged, promoted
        counts = [a.count(kind), b.count(kind), c.count(kind)]
        digests = [a.digest(kind), b.digest(kind), c.digest(kind)]
        matching = all(v > 0 for v in counts) and len(set(counts)) == 1 and len(set(digests)) == 1
        out["families"][kind] = {
            "received_count": counts[0],
            "feather_stage_count": counts[1],
            "promoted_parquet_count": counts[2],
            "received_digest": digests[0],
            "feather_digest": digests[1],
            "promoted_digest": digests[2],
            "equal": matching,
            "first_last_ts": a.timing[kind],
        }
        all_good &= matching
    out["depth_levels"] = received.depth_levels
    if all_good:
        out["result_class"] = "PASS_GITHUB_E5_BOUNDED_ONE_SYMBOL_ALL_FOUR"
    elif any(received.count(k) == 0 for k in FAMILIES):
        raise ProviderEvidenceError("one or more authentic four-family callbacks missing")
    elif any(staged.count(k) != promoted.count(k) for k in FAMILIES):
        raise NativeArchiveError("native Feather-to-Parquet promotion differs by family")
    elif any(received.count(k) != staged.count(k) for k in FAMILIES):
        raise NativeArchiveError("native bus callback vs Feather staged count mismatch")
    else:
        raise ResearchContractError("three-layer event identity, precision or digest mismatch")


def main():
    out = {
        "package_id": PACKAGE_ID,
        "base_sha": os.environ.get("RC6_REPO_BASE"),
        "pr_head_sha": os.environ.get("RC6_PR_HEAD"),
        "wheel_file": os.environ.get("RC6_WHEEL_FILENAME"),
        "wheel_sha256": os.environ.get("RC6_WHEEL_SHA256"),
        "instrument": INSTRUMENT_TEXT,
        "observation_target_secs": TARGET_OBSERVATION_SECS,
        "source_reception_ceiling_secs": MAX_RECEPTION_SECS,
        "zero_exchange_writes": True,
        "only_one_official_public_data_client": True,
        "lifecycle": {},
        "families": {},
        "limitations": [
            "One public ETH perpetual, short lived CI runner only.",
            "Observed means typed DataActor callbacks, not all venue wire frames.",
            "No 24h coverage, raw exchange completeness, restart, or rc5 migration proof.",
        ],
        "result_class": "NOT_TESTED",
    }
    try:
        if not out["pr_head_sha"] or len(out["pr_head_sha"]) != 40:
            raise ResearchContractError("missing exact PR-head binding")
        if not out["wheel_sha256"] or len(out["wheel_sha256"]) != 64:
            raise ResearchContractError("official wheel provenance unavailable")
        asyncio.run(probe(out))
    except ProviderEvidenceError as exc:
        out["result_class"] = "FAIL_PROVIDER"
        out["reason"] = str(exc)[:350]
    except ResearchContractError as exc:
        out["result_class"] = "FAIL_RESEARCH_CONTRACT"
        out["reason"] = str(exc)[:350]
    except NativeArchiveError as exc:
        out["result_class"] = "FAIL_NATIVE"
        out["reason"] = str(exc)[:350]
    except Exception as exc:
        out["result_class"] = "FAIL_NATIVE"
        out["reason"] = (type(exc).__name__ + ": " + str(exc))[:350]
        out["exception_type"] = type(exc).__name__
    finally:
        target = Path(os.environ.get("RC6_RESULT_PATH", "/tmp/rc6-result.json"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("RC6_BOUNDED_RESULT=" + out["result_class"], flush=True)
    return 0 if out["result_class"] == "PASS_GITHUB_E5_BOUNDED_ONE_SYMBOL_ALL_FOUR" else 1


if __name__ == "__main__":
    raise SystemExit(main())
