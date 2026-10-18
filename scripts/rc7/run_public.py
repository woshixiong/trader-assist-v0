# mypy: disable-error-code="import-not-found,misc"
"""Run the single native public rc7 owner with an approved PIT universe.

No historical prewarm, secret loading, private API, or exchange-write mode.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot
from trader_assist_v0.nautilus_e4.native_catalog import verify_promoted_run
from trader_assist_v0.nautilus_e4.native_health import NativeHealth
from trader_assist_v0.nautilus_e4.native_runtime import build_native_node


def capture_observer(
    snapshot: PitUniverseSnapshot,
    health: NativeHealth,
    *,
    strategy_manifest: Any = None,
    ledger_root: Path | None = None,
) -> Any:
    from nautilus_trader.common import DataActor
    from nautilus_trader.model import BarType, BookType, InstrumentId

    evaluators: dict[str, Any] = {}

    class NativeObserver(DataActor):
        def on_start(self) -> None:
            self.subscribe_socket_state()
            for expression in snapshot.expressions:
                identity = InstrumentId.from_str(expression.instrument_id)
                native = self.cache.instrument(identity)
                if native is None or str(native.raw_symbol) != expression.provider_coin:
                    health.failures.add("PROVIDER_METADATA_IDENTITY_MISMATCH")
                    raise ValueError(f"native provider metadata mismatch: {identity}")
                if strategy_manifest is not None:
                    from trader_assist_v0.nautilus_e4.registered_shadow import (
                        RegisteredShadowEvaluator,
                    )
                    from trader_assist_v0.nautilus_e4.shadow_ledger import ShadowLedger

                    assert ledger_root is not None
                    ledger = ShadowLedger(
                        ledger_root / f"{expression.market_id}.sqlite",
                        strategy_id=strategy_manifest.package_version,
                        strategy_version=strategy_manifest.strategy_version,
                    )
                    evaluators[str(identity)] = RegisteredShadowEvaluator(
                        manifest=strategy_manifest,
                        market_id=expression.market_id,
                        minimum_tick=native.price_increment.as_decimal(),
                        ledger=ledger,
                    )
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
            identity = str(event.bar_type.instrument_id)
            if event.bar_type.spec.step != 5 or identity not in evaluators:
                return
            from trader_assist_v0.multi_asset_shadow.models import ClosedBar

            open_ms = event.ts_event // 1_000_000
            close_ms = open_ms + 300_000
            if (
                event.ts_event % 1_000_000
                or open_ms % 300_000
                or event.ts_init < close_ms * 1_000_000
            ):
                health.failures.add("STRATEGY_BAR_NOT_CLOSED")
                return
            expression = next(e for e in snapshot.expressions if e.instrument_id == identity)
            closed = ClosedBar.create(
                market_id=expression.market_id,
                open_time_ms=open_ms,
                close_time_ms=close_ms - 1,
                open=event.open.as_decimal(),
                high=event.high.as_decimal(),
                low=event.low.as_decimal(),
                close=event.close.as_decimal(),
                volume=event.volume.as_decimal(),
                source_id="NATIVE_HYPERLIQUID_RC7",
                provenance_hash=hashlib.sha256(event.to_json_bytes()).hexdigest(),
                received_at=datetime.fromtimestamp(event.ts_init / 1_000_000_000, UTC),
            )
            evaluators[identity].evaluate(closed, now_ns=self.clock.timestamp_ns())

        def on_stop(self) -> None:
            for evaluator in evaluators.values():
                evaluator.ledger.verify()
                evaluator.ledger.close()

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
    fee_model = None
    if args.sandbox:
        if args.maker_rate is None or args.taker_rate is None:
            raise ValueError("Sandbox requires explicit simulated --maker-rate and --taker-rate")
        from nautilus_trader.execution import MakerTakerFeeModel

        rates = (Decimal(args.maker_rate), Decimal(args.taker_rate))
        if any(not rate.is_finite() or rate < 0 for rate in rates):
            raise ValueError("Sandbox fee assumptions must be finite nonnegative rates")
        fee_model = MakerTakerFeeModel(*rates)
    strategy_manifest = None
    if args.strategy_manifest is not None:
        from trader_assist_v0.nautilus_pilot.strategy_package import StrategyPackageManifest

        strategy_manifest = StrategyPackageManifest.model_validate_json(
            args.strategy_manifest.read_text()
        )
    node = build_native_node(args.root, sandbox=args.sandbox, sandbox_fee_model=fee_model)
    node.add_actor(
        capture_observer(
            snapshot,
            health,
            strategy_manifest=strategy_manifest,
            ledger_root=args.root / "shadow-ledger",
        )
    )
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
            if shutil.disk_usage(args.root).free < health.minimum_free_bytes:
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
    parser.add_argument("--strategy-manifest", type=Path)
    parser.add_argument("--maker-rate")
    parser.add_argument("--taker-rate")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
