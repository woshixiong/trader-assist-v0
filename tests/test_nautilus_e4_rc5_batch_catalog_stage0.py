"""Issue #320 Stage0: bounded RC5 public callbacks -> post-run native catalog.

This file alone owns its opt-in test subprocesses. It never configures execution
clients, credentials or in-callback persistence. All live claims are finite.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import threading
import time

import pytest

BRANCH = "trade-os/rc5-stage0-p0-20261011"
REPO = "woshixiong/trader-assist-v0"
SOFT_RICH = 40
SOFT_BAR = 350
HARD_RICH = 65
HARD_BAR = 410
MAX_STAGE = 600
MAX_DEPTH = 128
MAX_RICH = 512
MAX_OBJECTS = 32
MAX_BAR = 8
MAX_RSS_KIB = 1024 * 1024
MAX_E4_BYTES = 32 * 1024 * 1024
ETH = "ETH-USD-PERP.HYPERLIQUID"
FAMILIES = ("Quote", "Trade", "Depth10", "Bar1m", "Bar5m")


def _emit(value: object) -> None:
    print(json.dumps(value, sort_keys=True, default=str), flush=True)


def _read_value(obj: object, attr: str) -> object:
    value = getattr(obj, attr)
    return value() if callable(value) else value


def _e4_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def _resources() -> dict[str, int]:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "rss_kib": int(r.ru_maxrss),
        "cpu_millis": int((r.ru_utime + r.ru_stime) * 1000),
    }


def _identity(instrument: object) -> dict[str, object]:
    instrument_id = str(_read_value(instrument, "id"))
    raw = str(_read_value(instrument, "raw_symbol"))
    symbol = instrument_id.split(".", 1)[0]
    if not instrument_id.endswith(".HYPERLIQUID") or not symbol.endswith("-USD-PERP"):
        raise RuntimeError("INSTRUMENT_ID_NOT_HYPERLIQUID_PERP")
    dex = symbol.split(":", 1)[0] if ":" in symbol else "MAIN"
    if not raw or (dex == "MAIN" and ":" in raw):
        raise RuntimeError("RAW_SYMBOL_DEX_INCONSISTENT")
    return {
        "instrument_id": instrument_id,
        "provider_coin": raw,
        "dex": dex,
        "price_precision": int(_read_value(instrument, "price_precision")),
        "size_precision": int(_read_value(instrument, "size_precision")),
    }


async def _discover_native() -> dict[str, dict[str, object]]:
    from nautilus_trader.adapters.hyperliquid import HyperliquidEnvironment, HyperliquidHttpClient

    client = HyperliquidHttpClient(
        private_key=None,
        vault_address=None,
        account_address=None,
        environment=HyperliquidEnvironment.MAINNET,
    )
    instruments = await asyncio.wait_for(
        client.load_instrument_definitions(
            include_spot=False,
            include_perps=True,
            include_perps_hip3=True,
            include_outcomes=False,
        ),
        timeout=30,
    )
    exact: dict[str, dict[str, object]] = {}
    skhx: list[dict[str, object]] = []
    for instrument in instruments:
        desc = _identity(instrument)
        instrument_id = str(desc["instrument_id"])
        if instrument_id == ETH:
            exact["ETH"] = desc
        if instrument_id.split(".", 1)[0].endswith(":SKHX-USD-PERP"):
            skhx.append(desc)
    if "ETH" not in exact:
        raise RuntimeError("ETH_NATIVE_DISCOVERY_MISSING")
    if len(skhx) > 1:
        raise RuntimeError("SKHX_NATIVE_IDENTITY_AMBIGUOUS")
    if skhx:
        if skhx[0]["dex"] == "MAIN" or "SKHX" not in str(skhx[0]["provider_coin"]):
            raise RuntimeError("SKHX_NATIVE_DEX_OR_COIN_INVALID")
        exact["SKHX"] = skhx[0]
    return exact


def _timestamp_check(bar: object, received_ns: int, subscribed_ns: int) -> dict[str, int]:
    bar_type = str(_read_value(bar, "bar_type"))
    if bar_type.endswith("-1-MINUTE-LAST-EXTERNAL"):
        interval = 60_000_000_000
    elif bar_type.endswith("-5-MINUTE-LAST-EXTERNAL"):
        interval = 300_000_000_000
    else:
        raise RuntimeError("BAR_TYPE_NOT_EXTERNAL_1M_5M")
    opened = int(_read_value(bar, "ts_event"))
    initialized = int(_read_value(bar, "ts_init"))
    close = opened + interval
    if not 0 < opened < close < 2**64 or opened % 1_000_000 or opened % interval:
        raise RuntimeError("BAR_UTC_ALIGNMENT_OR_PRECISION")
    if initialized < close or received_ns < close:
        raise RuntimeError("BAR_CLOCK_CAUSALITY")
    if initialized < subscribed_ns or received_ns < subscribed_ns:
        raise RuntimeError("BAR_OUTSIDE_LIVE_SUBSCRIPTION")
    if initialized > received_ns + 1_000_000_000:
        raise RuntimeError("CLOCK_INCONSISTENT")
    return {
        "ts_event": opened,
        "ts_init": initialized,
        "close_boundary_ns": close,
        "callback_receive_ns": received_ns,
        "native_lag_ns": initialized - close,
        "callback_lag_ns": received_ns - close,
        "dispatch_lag_ns": received_ns - initialized,
    }


def _clock_pair() -> tuple[int, int]:
    return time.time_ns(), time.monotonic_ns()


def _check_clocks(begin: tuple[int, int], end: tuple[int, int]) -> None:
    elapsed_wall = end[0] - begin[0]
    elapsed_mono = end[1] - begin[1]
    if elapsed_mono < 0 or elapsed_wall < 0 or abs(elapsed_wall - elapsed_mono) > 1_000_000_000:
        raise RuntimeError("CLOCK_DISCONTINUITY")


def _fingerprint(event: object, family: str) -> tuple[object, ...]:
    timestamp = (int(_read_value(event, "ts_event")), int(_read_value(event, "ts_init")))
    if family == "Quote":
        return timestamp + tuple(str(_read_value(event, key)) for key in
                                 ("instrument_id", "bid_price", "ask_price",
                                  "bid_size", "ask_size"))
    if family == "Trade":
        return timestamp + tuple(str(_read_value(event, key)) for key in
                                 ("instrument_id", "trade_id", "aggressor_side", "price", "size"))
    if family == "Depth10":
        levels = []
        for side in ("bids", "asks"):
            levels.append(tuple((str(_read_value(o, "price")), str(_read_value(o, "size")))
                                for o in _read_value(event, side)))
        return (*timestamp, str(_read_value(event, "instrument_id")), *levels)
    return timestamp + tuple(str(_read_value(event, key)) for key in
                             ("bar_type", "open", "high", "low", "close", "volume"))


def _catalog_roundtrip(items: dict[str, list[object]], instruments: list[object],
                       root: Path, identity: dict[str, dict[str, object]]) -> dict[str, object]:
    from nautilus_trader.persistence import ParquetDataCatalog

    catalog = ParquetDataCatalog(str(root))
    catalog.write_instruments(instruments)
    written: dict[str, object] = {}
    for key, original in items.items():
        if not original:
            written[key] = {"retained": 0, "written": 0, "queried": 0, "status": "DATA_INCOMPLETE"}
            continue
        family = key.split("|", 1)[0]
        ordered = [o for _, o in sorted(enumerate(original), key=lambda p:
                                       (int(_read_value(p[1], "ts_init")), p[0]))]
        writer = {
            "Quote": catalog.write_quote_ticks,
            "Trade": catalog.write_trade_ticks,
            "Depth10": catalog.write_order_book_depths,
            "Bar1m": catalog.write_bars,
            "Bar5m": catalog.write_bars,
        }[family]
        writer(ordered)
        identifier = key.split("|", 1)[1]
        query = {
            "Quote": lambda: catalog.query_quote_ticks(identifiers=[identifier]),
            "Trade": lambda: catalog.query_trade_ticks(identifiers=[identifier]),
            "Depth10": lambda: catalog.query_order_book_depths(instrument_ids=[identifier]),
            "Bar1m": lambda: catalog.query_bars(identifiers=[identifier]),
            "Bar5m": lambda: catalog.query_bars(identifiers=[identifier]),
        }[family]
        queried = query()
        before = Counter(_fingerprint(x, family) for x in ordered)
        after = Counter(_fingerprint(x, family) for x in queried)
        if before != after or len(queried) != len(ordered):
            raise RuntimeError("CATALOG_NATIVE_TYPED_ROUNDTRIP_MISMATCH:" + key)
        written[key] = {"retained": len(ordered), "written": len(ordered),
                        "queried": len(queried), "status": "PASS"}
    if catalog.query_quote_ticks(identifiers=["STAGE0-NONEXISTENT-PERP.HYPERLIQUID"]):
        raise RuntimeError("CATALOG_WRONG_INSTRUMENT_QUERY_LEAK")
    return written


def _manifest(infos: list[dict[str, object]], watch: bool, profile: bool,
              head: str, tree: str, run_id: str):
    from trader_assist_v0.contracts.common import sha256_hex
    from trader_assist_v0.nautilus_e4.contracts import (
        MarketExpression, PitUniverseSnapshot, RunManifest,
    )
    from scripts.e4_nautilus_public_data_probe import L0_PROFILE

    expressions = tuple(
        MarketExpression(
            market_id=sha256_hex(("HYPERLIQUID|" + str(i["dex"]) + "|" +
                                  str(i["provider_coin"])).encode()),
            dex=str(i["dex"]),
            provider_coin=str(i["provider_coin"]),
            instrument_id=str(i["instrument_id"]),
            expression_id="stage0-" + str(i["instrument_id"]).lower(),
            instrument_metadata_version="PUBLIC_NATIVE_STAGE0_V1",
            instrument_metadata_hash=sha256_hex(("STAGE0|" + str(i["instrument_id"])).encode()),
        )
        for i in infos
    )
    snapshot = PitUniverseSnapshot.create(observed_at_ns=time.time_ns(), expressions=expressions)
    ids = [e.market_id for e in expressions]
    config = {"expressions": [e.model_dump(mode="json") for e in expressions],
              "probe": "ISSUE_320_STAGE0"}
    if profile:
        config["profile"] = L0_PROFILE
    manifest = RunManifest.create(
        run_id=run_id,
        git_sha=head,
        git_tree=tree,
        snapshot=snapshot,
        process_epoch="process-" + run_id,
        continuity_epoch="continuity-" + run_id,
        admission_epoch="admission-" + run_id,
        capture_configuration=config,
        subscription_policy={"discovery": ids, "watch": ids if watch else [], "actionable": []},
        trial_ledger_id="issue320-stage0",
    )
    return snapshot, manifest


def _run_native(mode: str, infos: list[dict[str, object]], root: Path,
                head: str, tree: str) -> dict[str, object]:
    from nautilus_trader.model import Bar, BarType, OrderBookDepth10, QuoteTick, TradeTick
    from trader_assist_v0.nautilus_e4.host import (
        NautilusE4CaptureStrategy, NautilusE4CaptureStrategyConfig, build_public_data_node,
    )
    from trader_assist_v0.nautilus_e4.safety import assert_public_only

    assert_public_only(env=os.environ, config={"data_clients": {"HYPERLIQUID": {}},
                                                "exec_clients": {}})
    try:
        assert_public_only(env={"HYPERLIQUID_PRIVATE_KEY": "STAGE0-NEGATIVE-SENTINEL"})
    except RuntimeError:
        pass
    else:
        raise RuntimeError("PUBLIC_ONLY_NEGATIVE_SENTINEL_NOT_REJECTED")

    live_bars = mode == "bar"
    run_id = "stage0-" + mode + "-" + str(time.time_ns())
    snap, manifest = _manifest(infos, not live_bars, live_bars, head, tree, run_id)
    names = [str(i["instrument_id"]) for i in infos]
    bar_types = tuple(str(BarType.from_str(name + "-" + minutes + "-MINUTE-LAST-EXTERNAL"))
                      for name in names for minutes in ("1", "5")) if live_bars else ()
    config = NautilusE4CaptureStrategyConfig(
        manifest_json=manifest.model_dump_json(),
        snapshot_json=snap.model_dump_json(),
        expressions_json="[" + ",".join(e.model_dump_json() for e in snap.expressions) + "]",
        discovery_market_ids=tuple(e.market_id for e in snap.expressions),
        watch_market_ids=() if live_bars else tuple(e.market_id for e in snap.expressions),
        actionable_market_ids=(),
        bar_types=bar_types,
        evidence_root=str(root / "e4"),
    )
    class Stage0Strategy(NautilusE4CaptureStrategy):
        def __init__(self, cfg):
            super().__init__(cfg)
            self.samples = defaultdict(list)
            self.received = Counter()
            self.forwarded = Counter()
            self.native_bar_times = defaultdict(list)
            self.historical_counts = Counter()
            self.stop_handle = None
            self.stopped_reason = None
            self.subscribed_ns = 0
            self.baseline_cpu = _resources()["cpu_millis"]
            self.stop_requested = False

        def on_start(self):
            super().on_start()
            self.subscribed_ns = time.time_ns()

        def _stop(self, reason):
            if self.stopped_reason is None:
                self.stopped_reason = reason
            if not self.stop_requested:
                self.stop_requested = True
                self.stop_handle.stop()

        def _allow(self, key, is_depth=False):
            self.received[key] += 1
            if self.stopped_reason is not None:
                return False
            if is_depth and self.forwarded["Depth10"] >= MAX_DEPTH:
                self._stop("RESOURCE_CAP_STOP:DEPTH10")
                return False
            if not live_bars and sum(self.forwarded[k] for k in
                                     ("Quote", "Trade", "Depth10")) >= MAX_RICH:
                self._stop("RESOURCE_CAP_STOP:RICH")
                return False
            if live_bars and self.forwarded[key] >= MAX_BAR:
                self._stop("RESOURCE_CAP_STOP:BAR")
                return False
            return True

        def _sample(self):
            usage = _resources()
            if usage["rss_kib"] > MAX_RSS_KIB:
                self._stop("RESOURCE_CAP_STOP:RSS")
            if not live_bars and usage["cpu_millis"] - self.baseline_cpu > 30_000:
                self._stop("RESOURCE_CAP_STOP:CPU")
            if _e4_bytes(root / "e4") > MAX_E4_BYTES:
                self._stop("RESOURCE_CAP_STOP:E4_BYTES")

        def _capture(self, family, identifier, item, callback):
            key = family + "|" + identifier
            if not self._allow(key, family == "Depth10"):
                return
            callback(item)
            self.forwarded[key] += 1
            if family in ("Quote", "Trade", "Depth10"):
                self.forwarded[family] += 1
            if len(self.samples[key]) < (MAX_BAR if live_bars else MAX_OBJECTS):
                self.samples[key].append(item)
            if sum(v for k, v in self.forwarded.items() if "|" in k) % 8 == 0:
                self._sample()
            if (
                (family == "Depth10" and self.forwarded["Depth10"] >= MAX_DEPTH)
                or (
                    not live_bars
                    and sum(self.forwarded[k] for k in ("Quote", "Trade", "Depth10")) >= MAX_RICH
                )
                or (live_bars and self.forwarded[key] >= MAX_BAR)
            ):
                self._stop("RESOURCE_CAP_STOP:CALLBACK_LIMIT")

        def on_quote(self, tick: QuoteTick):
            self._capture("Quote", str(tick.instrument_id), tick, super().on_quote)

        def on_trade(self, tick: TradeTick):
            self._capture("Trade", str(tick.instrument_id), tick, super().on_trade)

        def on_book_depth(self, depth: OrderBookDepth10):
            self._capture("Depth10", str(depth.instrument_id), depth, super().on_book_depth)

        def on_historical_bars(self, bars):
            for item in bars:
                self.historical_counts[str(item.bar_type)] += 1
            super().on_historical_bars(bars)

        def on_bar(self, bar: Bar):
            received_ns = time.time_ns()
            identifier = str(bar.bar_type)
            if identifier not in bar_types:
                raise RuntimeError("LIVE_BAR_NOT_IN_EXACT_SUBSCRIPTIONS")
            key = ("Bar1m" if "-1-MINUTE-" in identifier else "Bar5m") + "|" + identifier
            if self.stopped_reason is not None:
                self.received[key] += 1
                return
            timing = _timestamp_check(bar, received_ns, self.subscribed_ns)
            signature = _fingerprint(bar, key.split("|", 1)[0])
            if any(v["ts_event"] == timing["ts_event"] and v["fingerprint"] != signature
                   for v in self.native_bar_times[key]):
                raise RuntimeError("BAR_CONFLICTING_LIVE_OHLCV")
            self.native_bar_times[key].append({**timing, "fingerprint": signature})
            self._capture(key.split("|", 1)[0], identifier, bar, super().on_bar)

    strategy = Stage0Strategy(config)
    node = build_public_data_node(l0=live_bars)
    node.add_strategy(strategy)
    strategy.stop_handle = node.handle()
    _time = _clock_pair()
    timer = threading.Timer(SOFT_BAR if live_bars else SOFT_RICH, strategy.stop_handle.stop)
    timer.daemon = True
    timer.start()
    clean_return = False
    native_instruments = []
    try:
        node.run()
        clean_return = True
        strategy._sample()
        for name in names:
            model = __import__("nautilus_trader.model", fromlist=["InstrumentId"])
            obj = strategy.cache.instrument(model.InstrumentId.from_str(name))
            if obj is None:
                raise RuntimeError("POST_RUN_NATIVE_INSTRUMENT_CACHE_MISSING:" + name)
            native_instruments.append(obj)
    finally:
        timer.cancel()
        node.dispose()
    _check_clocks(_time, _clock_pair())
    if not clean_return:
        raise RuntimeError("LIVE_NODE_UNCLEAN_RETURN")
    for key, objs in strategy.samples.items():
        for obj in objs:
            _fingerprint(obj, key.split("|", 1)[0])  # verify post-dispose lifetime
    catalog = _catalog_roundtrip(strategy.samples, native_instruments, root / "catalog",
                                 {str(i["instrument_id"]): i for i in infos})
    observed = {}
    for key, count in strategy.received.items():
        observed[key] = {"received": count,
                         "forwarded": strategy.forwarded[key],
                         "retained": len(strategy.samples[key]),
                         "roundtrip": catalog.get(key, {"status": "DATA_INCOMPLETE"}),
                         "status": ("RESOURCE_CAP_STOP" if strategy.stopped_reason else
                                    "PASS" if strategy.forwarded[key] else "DATA_INCOMPLETE")}
    for info in infos:
        ident = str(info["instrument_id"])
        for family in FAMILIES if live_bars else FAMILIES[:3]:
            key = family + "|" + (ident + "-" + ("1" if family == "Bar1m" else "5") +
                                   "-MINUTE-LAST-EXTERNAL" if family.startswith("Bar") else ident)
            observed.setdefault(key, {"received": 0, "forwarded": 0, "retained": 0,
                                      "roundtrip": {"status": "DATA_INCOMPLETE"},
                                      "status": "DATA_INCOMPLETE"})
    return {"mode": mode, "run_id": run_id, "result": observed, "catalog": catalog,
            "live_bar_clocks": {k: [{x: v for x, v in entry.items() if x != "fingerprint"}
                                   for entry in entries]
                                for k, entries in strategy.native_bar_times.items()},
            "historical_not_counted": dict(strategy.historical_counts),
            "resource_stop": strategy.stopped_reason,
            "rss_cpu": _resources(),
            "e4_bytes": _e4_bytes(root / "e4"),
            "E4_CONTINUOUS_RAW_RETENTION": "NOT_QUALIFIED"}


def _child() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage0-child", choices=("discover", "rich", "bar"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--meta", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--head")
    parser.add_argument("--tree")
    a = parser.parse_args()
    try:
        if a.stage0_child == "discover":
            from trader_assist_v0.nautilus_e4.safety import assert_public_only
            assert_public_only(env=os.environ)
            result = {"discovered": asyncio.run(_discover_native())}
        else:
            assert a.meta and a.root and a.head and a.tree
            infos = json.loads(a.meta.read_text())
            result = _run_native(a.stage0_child, infos, a.root, a.head, a.tree)
        a.output.write_text(json.dumps({"ok": True, "result": result}, default=str))
        return 0
    except Exception as exc:
        a.output.write_text(json.dumps({"ok": False, "error": repr(exc)}))
        print("STAGE0_STOP:" + repr(exc), file=sys.stderr, flush=True)
        return 2


def _run_child(mode: str, folder: Path, timeout: int, meta: list[dict[str, object]] | None,
               head: str, tree: str) -> dict[str, object]:
    out = folder / (mode + "-" + str(time.monotonic_ns()) + ".json")
    info = folder / "selected.json"
    if meta is not None:
        info.write_text(json.dumps(meta))
    command = [sys.executable, str(Path(__file__).resolve()), "--stage0-child", mode,
               "--output", str(out), "--meta", str(info), "--root",
               str(folder / ("attempt-" + mode)), "--head", head, "--tree", tree]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                              check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("NATIVE_RUN_HARD_TIMEOUT:" + mode) from exc
    if not out.exists():
        raise RuntimeError("NATIVE_ABORT_NO_RESULT:" + mode + ":exit=" + str(done.returncode))
    data = json.loads(out.read_text())
    if done.returncode or not data["ok"]:
        raise RuntimeError("STAGE0_UNEXPECTED_CHILD_FAILURE:" + mode + ":" +
                           str(data.get("error")) + ":" + done.stderr[-500:])
    return data["result"]


def _exact_git_ref() -> tuple[str, str]:
    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], check=True, capture_output=True,
                                text=True, timeout=5)
        return result.stdout.strip()
    return git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")


def test_rc5_stage0_native_public_batch_catalog(capsys):
    enabled = (
        os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
        and os.environ.get("GITHUB_REPOSITORY") == REPO
        and os.environ.get("GITHUB_HEAD_REF") == BRANCH
        and os.environ.get("NAUTILUS_E4_REQUIRED") == "1"
    )
    if not enabled:
        pytest.skip("Stage0 one-off exact branch opt-in only (not ordinary PR regression)")
    from trader_assist_v0.nautilus_e4.host import assert_exact_nautilus_version
    from trader_assist_v0.nautilus_e4.safety import assert_public_only

    assert_exact_nautilus_version()
    assert_public_only(env=os.environ)
    head, tree = _exact_git_ref()
    started = time.monotonic()
    reports: dict[str, object] = {"STAGE0_EXECUTED": "YES", "head": head, "tree": tree,
                                  "E4_CONTINUOUS_RAW_RETENTION": "NOT_QUALIFIED"}
    with capsys.disabled():
        _emit({"STAGE0_EXECUTED": "YES", "head": head, "tree": tree})
    with tempfile.TemporaryDirectory(prefix="issue320-stage0-") as temp:
        folder = Path(temp)
        try:
            native = _run_child("discover", folder, 35, None, head, tree)["discovered"]
            reports["native_discovery"] = native
            selected = [native["ETH"]]
            if "SKHX" in native:
                selected.append(native["SKHX"])
            for idx, info in enumerate(selected):
                if time.monotonic() - started > MAX_STAGE - (HARD_RICH + 25):
                    raise RuntimeError("STAGE0_EXPERIMENT_BUDGET_EXHAUSTED")
                reports["W_RICH_" + ("ETH" if idx == 0 else "SKHX")] = _run_child(
                    "rich", folder, HARD_RICH, [info], head, tree)
            if time.monotonic() - started > MAX_STAGE - (HARD_BAR + 25):
                raise RuntimeError("STAGE0_EXPERIMENT_BUDGET_EXHAUSTED")
            reports["W_BAR_BOTH"] = _run_child("bar", folder, HARD_BAR, selected, head, tree)
            if "SKHX" not in native:
                reports["SKHX_STATUS"] = "SKHX_NOT_QUALIFIED"
            reports["elapsed_s"] = round(time.monotonic() - started, 3)
            if reports["elapsed_s"] > MAX_STAGE:
                raise RuntimeError("STAGE0_EXPERIMENT_BUDGET_EXCEEDED")
            with capsys.disabled():
                _emit(reports)
        except Exception as exc:
            reports["failure"] = str(exc)
            reports["elapsed_s"] = round(time.monotonic() - started, 3)
            with capsys.disabled():
                _emit(reports)
            pytest.fail("STAGE0_STOP_ENGINEERING_CONTROL:" + str(exc))


if __name__ == "__main__":
    sys.exit(_child())
