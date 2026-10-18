"""Run the single native public rc7 owner with an approved PIT universe.

No historical prewarm, secret loading, private API, or exchange-write mode.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Any

from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot
from trader_assist_v0.nautilus_e4.native_catalog import verify_promoted_run
from trader_assist_v0.nautilus_e4.native_health import NativeHealth
from trader_assist_v0.nautilus_e4.native_runtime import build_native_node


def capture_observer(snapshot: PitUniverseSnapshot, health: NativeHealth) -> Any:
    from nautilus_trader.common import DataActor
    from nautilus_trader.model import BarType, BookType, InstrumentId

    class NativeObserver(DataActor):
        def on_start(self) -> None:
            self.subscribe_socket_state()
            for expression in snapshot.expressions:
                identity = InstrumentId.from_str(expression.instrument_id)
                native = self.cache.instrument(identity)
                if native is None or str(native.raw_symbol) != expression.provider_coin:
                    health.failures.add("PROVIDER_METADATA_IDENTITY_MISMATCH")
                    raise ValueError(f"native provider metadata mismatch: {identity}")
                self.subscribe_quotes(identity)
                self.subscribe_trades(identity)
                self.subscribe_book_depth(identity, BookType.L2_MBP)
                for minutes in (1, 5):
                    self.subscribe_bars(
                        BarType.from_str(f"{identity}-{minutes}-MINUTE-LAST-EXTERNAL")
                    )

        def record(self, event: Any, kind: str, identity: str) -> None:
            health.observe(
                f"{identity}:{kind}",
                ts_event=event.ts_event,
                ts_init=event.ts_init,
                now=self.clock.timestamp_ns(),
            )

        def on_quote(self, event: Any) -> None:
            if event.bid_price.as_decimal() <= 0 or event.ask_price < event.bid_price:
                health.failures.add("INVALID_BBO")
                return
            self.record(event, "quote", str(event.instrument_id))

        def on_trade(self, event: Any) -> None:
            self.record(event, "trade", str(event.instrument_id))

        def on_book_depth(self, event: Any) -> None:
            if not event.bids or not event.asks:
                health.failures.add("INCOMPLETE_BOOK")
                return
            self.record(event, "book", str(event.instrument_id))

        def on_bar(self, event: Any) -> None:
            # Native external bars are completed provider callbacks. A future timestamp
            # is rejected by health; no historical callback is admitted as current live.
            self.record(event, f"{event.bar_type.spec.step}m", str(event.bar_type.instrument_id))

        def on_socket_state(self, event: Any) -> None:
            state = str(event.state).split(".")[-1].upper()
            if event.endpoint == "hyperliquid-data-streams":
                health.socket(state in {"CONNECTED", "ACTIVE"})

    return NativeObserver()


async def run(args: argparse.Namespace) -> None:
    snapshot = PitUniverseSnapshot.model_validate_json(args.snapshot.read_text())
    # Only the frozen snapshot universe is subscribed. Provider cache validates each identity.
    if not any(e.provider_coin == "ETH" for e in snapshot.expressions):
        raise ValueError("approved snapshot must include ETH")
    if not any(":" in e.provider_coin for e in snapshot.expressions):
        raise ValueError("approved snapshot must include a genuine HIP-3 expression")
    required = {
        f"{e.instrument_id}:{kind}": age
        for e in snapshot.expressions
        for kind, age in {
            "quote": 30_000_000_000,
            "trade": 60_000_000_000,
            "book": 30_000_000_000,
            "1m": 120_000_000_000,
            "5m": 360_000_000_000,
        }.items()
    }
    health = NativeHealth(required)
    node = build_native_node(args.root, sandbox=args.sandbox)
    node.add_actor(capture_observer(snapshot, health))
    failure: Exception | None = None

    async def report() -> None:
        while True:
            now = time.time_ns()
            output = health.report(
                now=now, generated=now, free_bytes=shutil.disk_usage(args.root).free
            )
            target = args.root / "health.json"
            pending = target.with_suffix(".tmp")
            pending.write_text(json.dumps(output, indent=2) + "\n")
            pending.replace(target)
            if "DISK_LOW" in output["reasons"]:
                node.handle().stop()
                raise RuntimeError("DISK_LOW")
            await asyncio.sleep(5)

    monitor = asyncio.create_task(report())
    try:
        await node.run_async()
    except Exception as exc:
        failure = exc
    finally:
        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass
        node.dispose()  # native close/promotion failure must propagate
    if failure is not None:
        raise failure
    from nautilus_trader.persistence import ParquetDataCatalog

    catalog = ParquetDataCatalog(str(args.root))
    runs = catalog.list_live_runs()
    if not runs:
        raise RuntimeError("native run missing")
    proofs = [verify_promoted_run(args.root, run_id) for run_id in runs]
    (args.root / "close-proof.json").write_text(json.dumps(proofs, indent=2) + "\n")
    # Catalog checks only become verified after explicit close/readback. During
    # capture HEALTHY remains blocked until live promotion is separately qualified.


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sandbox", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
