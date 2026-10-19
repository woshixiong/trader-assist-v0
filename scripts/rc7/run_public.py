# mypy: disable-error-code="import-not-found,misc"
"""Run the single native public rc7 owner with an approved PIT universe.

No historical prewarm, secret loading, private API, or exchange-write mode.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot
from trader_assist_v0.nautilus_e4.native_capture import (
    STREAM_AGES,
    NativeUniverse,
    closed_bar_window,
    native_event_hash,
)
from trader_assist_v0.nautilus_e4.native_catalog import recover_and_promote, verify_promoted_run
from trader_assist_v0.nautilus_e4.native_health import NativeHealth
from trader_assist_v0.nautilus_e4.native_runtime import build_native_node


def capture_observer(
    universe: NativeUniverse,
    health: NativeHealth,
    *,
    strategy_manifest: Any = None,
    ledger_root: Path | None = None,
    metadata_root: Path | None = None,
) -> Any:
    from nautilus_trader.common import DataActor
    from nautilus_trader.model import BarType, BookType, CryptoPerpetual, InstrumentId, Venue

    evaluators: dict[str, Any] = {}

    class NativeObserver(DataActor):
        def on_start(self) -> None:
            self.subscribe_socket_state()
            # connect() publishes bootstrap instruments before opening its native
            # session. Admit already-delivered cache entries as well as callbacks;
            # neither actor/event-queue ordering can cause a startup false failure.
            for native in self.cache.instruments(Venue("HYPERLIQUID")):
                self.on_instrument(native)
            if not universe.missing:
                return
            if universe.snapshot is None:
                # Public native provider refresh; no hand-built HTTP or symbol IDs.
                self.request_instruments(venue=Venue("HYPERLIQUID"))
            else:
                for expression in universe.snapshot.expressions:
                    self.subscribe_instrument(InstrumentId.from_str(expression.instrument_id))

        def on_instrument(self, native: Any) -> None:
            if str(native.raw_symbol) not in universe.coins:
                return
            if not isinstance(native, CryptoPerpetual):
                health.failures.add("UNSUPPORTED_NATIVE_INSTRUMENT_TYPE")
                raise TypeError("approved capture requires native Hyperliquid perpetual")
            try:
                expression = universe.admit(native)
            except ValueError:
                health.failures.add("PROVIDER_METADATA_IDENTITY_MISMATCH")
                raise
            if expression is None:
                return
            identity = native.id
            if f"{identity}:quote" in health.required:
                return  # Refresh must not resubscribe or replace strategy state.
            health.required.update(
                {f"{identity}:{kind}": age * 1_000_000_000 for kind, age in STREAM_AGES.items()}
            )
            if metadata_root is not None and not universe.missing:
                (metadata_root / "resolved-pit-universe.json").write_text(
                    universe.current_snapshot(now_ns=self.clock.timestamp_ns()).model_dump_json(
                        indent=2
                    )
                    + "\n"
                )
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
                self.subscribe_bars(BarType.from_str(f"{identity}-{minutes}-MINUTE-LAST-EXTERNAL"))

        def record(
            self, event: Any, kind: str, identity: str, *, event_end_ns: int | None = None
        ) -> None:
            accepted = health.observe(
                f"{identity}:{kind}",
                ts_event=event.ts_event,
                ts_init=event.ts_init,
                now=self.clock.timestamp_ns(),
                event_end_ns=event_end_ns,
            )

            if accepted and not health.connected:
                # An actual valid native event proves receiving transport, including
                # when initial socket CONNECTED preceded actor subscription.
                health.socket(True)

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
            try:
                open_ms, close_ms = closed_bar_window(event, now_ns=self.clock.timestamp_ns())
            except ValueError as exc:
                health.failures.add(str(exc))
                return
            self.record(
                event,
                f"{event.bar_type.spec.step}m",
                str(event.bar_type.instrument_id),
                event_end_ns=(close_ms + 1) * 1_000_000,
            )
            identity = str(event.bar_type.instrument_id)
            if event.bar_type.spec.step != 5 or identity not in evaluators:
                return
            from trader_assist_v0.multi_asset_shadow.models import ClosedBar

            expression = universe.resolved[
                str(self.cache.instrument(event.bar_type.instrument_id).raw_symbol)
            ]
            closed = ClosedBar.create(
                market_id=expression.market_id,
                open_time_ms=open_ms,
                close_time_ms=close_ms,
                open=event.open.as_decimal(),
                high=event.high.as_decimal(),
                low=event.low.as_decimal(),
                close=event.close.as_decimal(),
                volume=event.volume.as_decimal(),
                source_id="NATIVE_HYPERLIQUID_RC7",
                provenance_hash=native_event_hash(event),
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
    if args.sandbox_probe and (not args.sandbox or args.strategy_manifest is not None):
        raise ValueError("Sandbox protocol probe must be isolated from strategy and real execution")
    snapshot = (
        PitUniverseSnapshot.model_validate_json(args.snapshot.read_text())
        if args.snapshot is not None
        else None
    )
    coins = (
        tuple(e.provider_coin for e in snapshot.expressions)
        if snapshot is not None
        else tuple(args.provider_coins)
    )
    universe = NativeUniverse(coins, snapshot)
    args.root.mkdir(parents=True, exist_ok=True)
    # Native recovery runs before starting a new writer. Completed promotion
    # identities are idempotent; a corrupt prior run prevents false readiness.
    from nautilus_trader.persistence import ParquetDataCatalog

    catalog = ParquetDataCatalog(str(args.root))
    recovery = [recover_and_promote(args.root, run_id) for run_id in catalog.list_live_runs()]
    (args.root / "recovery-proof.json").write_text(json.dumps(recovery, indent=2) + "\n")
    health = NativeHealth({})
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
    probe_ledger = None
    sandbox_proof: dict[str, Any] = {}
    if args.sandbox_probe:
        from trader_assist_v0.nautilus_e4.native_sandbox import attach_sandbox_probe
        from trader_assist_v0.nautilus_e4.shadow_ledger import ShadowLedger

        attach_sandbox_probe(node)
        probe_ledger = ShadowLedger(
            args.root / "sandbox-probe.sqlite",
            strategy_id="OFFICIAL_EXEC_TESTER_PROTOCOL_ONLY",
            strategy_version="2.0.0rc7",
        )
    node.add_actor(
        capture_observer(
            universe,
            health,
            strategy_manifest=strategy_manifest,
            ledger_root=args.root / "shadow-ledger",
            metadata_root=args.root,
        )
    )
    instance_id = str(node.instance_id)
    # Official run_async borrow contract: capture shared read/stop handles now,
    # never access node.cache/portfolio while the node is being run asynchronously.
    native_cache, native_portfolio, handle = node.cache, node.portfolio, node.handle()
    failure: Exception | None = None
    started = time.monotonic()
    last_active_report: dict[str, Any] = {}

    async def report() -> None:
        while True:
            now = time.time_ns()
            output = health.report(
                now=now, generated=now, free_bytes=shutil.disk_usage(args.root).free
            )
            output["missing_provider_coins"] = universe.missing
            output["instance_id"] = instance_id
            output["capture_state"] = "CAPTURING_CATALOG_PENDING_CLOSE"
            if universe.missing:
                output["status"] = "DEGRADED"
            last_active_report.clear()
            last_active_report.update(output)
            target = args.root / "health.json"
            pending = target.with_suffix(".tmp")
            pending.write_text(json.dumps(output, indent=2) + "\n")
            pending.replace(target)
            if probe_ledger is not None and node.is_running:
                from trader_assist_v0.nautilus_e4.native_sandbox import record_sandbox_state

                sandbox_proof.update(
                    record_sandbox_state(native_cache, native_portfolio, probe_ledger, now_ns=now)
                )
            if shutil.disk_usage(args.root).free < health.minimum_free_bytes:
                handle.stop()
                raise RuntimeError("DISK_LOW")
            elapsed = time.monotonic() - started
            if elapsed >= args.startup_timeout_seconds and (universe.missing or not health.counts):
                handle.stop()
                raise RuntimeError("PUBLIC_PROVIDER_UNAVAILABLE_OR_NO_EVENTS")
            if args.duration_seconds is not None and elapsed >= args.duration_seconds:
                last_active_report["bounded_stop_requested"] = True
                last_active_report["capture_end_ns"] = now
                handle.stop()
                return
            await asyncio.sleep(5)

    async def stop_on_report_failure() -> None:
        try:
            await report()
        except Exception:
            handle.stop()
            raise

    monitor = asyncio.create_task(stop_on_report_failure())
    try:
        await node.run_async()
    except Exception as exc:
        failure = exc
    finally:
        stopped_ns = last_active_report.get("capture_end_ns", time.time_ns())
        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            failure = failure or exc
        finally:
            try:
                if probe_ledger is not None and failure is None:
                    from trader_assist_v0.nautilus_e4.native_sandbox import record_sandbox_state

                    sandbox_proof.update(
                        record_sandbox_state(
                            native_cache, native_portfolio, probe_ledger, now_ns=time.time_ns()
                        )
                    )
            except Exception as exc:
                failure = failure or exc
            finally:
                if probe_ledger is not None:
                    probe_ledger.close()
            try:
                node.dispose()  # Native explicit close/promotion must always run.
            except Exception as exc:
                failure = failure or exc
        health.socket(False)
        stopped = health.report(
            now=time.time_ns(),
            generated=time.time_ns(),
            free_bytes=shutil.disk_usage(args.root).free,
        )
        stopped["capture_state"] = "STOPPED"
        (args.root / "health.json").write_text(json.dumps(stopped, indent=2) + "\n")
    if failure is not None:
        raise failure
    proof = verify_promoted_run(args.root, instance_id)
    missing = sorted(set(health.required) - health.counts.keys())
    freshness = set(last_active_report.get("reasons", ["NO_RUNTIME_HEALTH_REPORT"])) - {
        "WRITER_UNKNOWN_OR_FAILED",
        "CATALOG_UNVERIFIED",
    }
    if not 0 <= stopped_ns - last_active_report.get("generated_ns", 0) <= health.report_max_age_ns:
        freshness.add("HEALTH_REPORT_STALE_AT_STOP")
    elapsed = time.monotonic() - started
    duration_complete = args.duration_seconds is None or bool(
        last_active_report.get("bounded_stop_requested")
    )
    proof.update(
        provider_snapshot=universe.current_snapshot(now_ns=time.time_ns()).model_dump(mode="json"),
        stream_counts=health.counts,
        missing_streams=missing,
        event_failures=sorted(health.failures),
        freshness_reasons=sorted(freshness),
        public_coverage=(
            "PASS"
            if not missing and not health.failures and not freshness and duration_complete
            else "INCOMPLETE"
        ),
        requested_duration_seconds=args.duration_seconds,
        elapsed_seconds=elapsed,
        bounded_duration_complete=duration_complete,
        policy="NO_ROTATION_PROMOTE_ON_EXPLICIT_CLOSE_RETAIN_FEATHER",
        sandbox=sandbox_proof,
    )
    (args.root / "close-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    if not duration_complete:
        raise RuntimeError("NATIVE_RUN_STOPPED_BEFORE_REQUESTED_DURATION")


def main() -> None:
    parser = argparse.ArgumentParser()
    universe_args = parser.add_mutually_exclusive_group(required=True)
    universe_args.add_argument("--snapshot", type=Path)
    universe_args.add_argument("--provider-coins", nargs="+")
    parser.add_argument("--duration-seconds", type=int)
    parser.add_argument("--startup-timeout-seconds", type=int, default=90)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--sandbox-probe", action="store_true")
    parser.add_argument("--strategy-manifest", type=Path)
    parser.add_argument("--maker-rate")
    parser.add_argument("--taker-rate")
    args = parser.parse_args()
    if args.duration_seconds is not None and not 30 <= args.duration_seconds <= 900:
        parser.error("bounded capture duration must be 30..900 seconds")
    if args.sandbox_probe and (not args.sandbox or args.strategy_manifest is not None):
        parser.error(
            "protocol probe requires Sandbox and must be isolated from registered strategy"
        )
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
