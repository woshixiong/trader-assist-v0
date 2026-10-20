# mypy: disable-error-code="import-not-found,misc"
"""Run the single native public rc7 owner with an approved PIT universe.

No historical prewarm, secret loading, private API, or exchange-write mode.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot
from trader_assist_v0.nautilus_e4.native_archive import (
    DEFAULT_ARCHIVE_BYTES,
    MAX_QUALIFICATION_SECONDS,
    ArchiveCapacityError,
    observe_archive,
    require_archive_capacity,
)
from trader_assist_v0.nautilus_e4.native_capture import (
    STREAM_AGES,
    NativeUniverse,
    closed_bar_window,
    native_event_hash,
)
from trader_assist_v0.nautilus_e4.native_catalog import ArchiveIntegrityError, read_staged_run
from trader_assist_v0.nautilus_e4.native_health import NativeHealth
from trader_assist_v0.nautilus_e4.native_runtime import build_native_node


def require_qualified_stop(proof: dict[str, Any], instance_id: str) -> None:
    """Only this invocation's complete proof may admit a zero process exit.

    Used only for an explicitly bounded qualification; production has no
    planned stop. Earlier proof files cannot certify the current invocation.
    """
    if (
        proof.get("status") != "SEALED_STAGE_READABLE"
        or proof.get("instance_id") != instance_id
        or proof.get("bounded_duration_complete") is not True
        or proof.get("public_coverage") != "PASS"
        or proof.get("missing_streams") != []
        or proof.get("event_failures") != []
        or proof.get("freshness_reasons") != []
        or not proof.get("types")
        or not proof.get("stream_counts")
    ):
        raise RuntimeError("CYCLE_NOT_VERIFIED_FAIL_CLOSED")


def capture_gap(previous_last_ns: int | None, first_ns: int | None) -> dict[str, Any]:
    """Callback interval across runs, not an estimate of lost exchange events."""
    if previous_last_ns is not None and first_ns is not None and first_ns < previous_last_ns:
        raise ValueError("CAPTURE_GAP_CLOCK_INVALID")
    return {
        "state": "CAPTURE_GAP",
        "measurement": "CALLBACK_INTERVAL" if previous_last_ns and first_ns else "UNKNOWN",
        "previous_last_observed_ns": previous_last_ns,
        "first_observed_ns": first_ns,
        "interval_ns": first_ns - previous_last_ns if previous_last_ns and first_ns else None,
    }


def capture_observer(
    universe: NativeUniverse,
    health: NativeHealth,
    *,
    strategy_manifest: Any = None,
    ledger_root: Path | None = None,
    metadata_root: Path | None = None,
    qualification_reconnect: bool = False,
    contexts_only: bool = False,
) -> Any:
    from nautilus_trader.common import DataActor
    from nautilus_trader.model import BarType, BookType, CryptoPerpetual, InstrumentId, Venue

    from trader_assist_v0.nautilus_e4.native_context import (
        CONTEXT_AGES,
        ContextResearchReader,
        register_native_context_types,
    )

    register_native_context_types()

    context_reader = ContextResearchReader(set())
    evaluators: dict[str, Any] = {}
    coverage_ledger = None
    if metadata_root is not None:
        from trader_assist_v0.nautilus_e4.shadow_ledger import ShadowLedger

        coverage_ledger = ShadowLedger(
            metadata_root / "coverage.sqlite",
            strategy_id="NATIVE_PUBLIC_COVERAGE",
            strategy_version="2.0.0rc7",
        )

    class NativeObserver(DataActor):
        context_reader: Any = None
        gap_written = 0
        reconnect_requested = False
        coverage_closed = False

        def request_native_gap_history(self) -> None:
            # Use supported provider requests only. These responses are evidence,
            # never inserted as live callbacks or allowed to re-arm freshness.
            if not hasattr(self, "requested_gap_history"):
                self.requested_gap_history: set[tuple[str, int]] = set()
            for gap in health.gaps:
                stream = str(gap["stream"])
                if stream not in health.required:
                    continue
                key = (stream, cast(int, gap["prior_ts_init"]))
                if key in self.requested_gap_history:
                    continue
                self.requested_gap_history.add(key)
                instrument, kind = stream.rsplit(":", 1)
                now = self.clock.timestamp_ns()
                start = datetime.fromtimestamp(
                    cast(int, gap["prior_ts_event"]) / 1_000_000_000, UTC
                )
                end = datetime.fromtimestamp(now / 1_000_000_000, UTC)
                if kind in {"1m", "5m"}:
                    request = self.request_bars(
                        BarType.from_str(f"{instrument}-{kind[:-1]}-MINUTE-LAST-EXTERNAL"),
                        start=start,
                        end=end,
                        limit=5000,
                    )
                elif kind == "trade":
                    request = self.request_trades(
                        InstrumentId.from_str(instrument), start=start, end=end
                    )
                else:
                    continue  # No quote/depth historical guarantee in the pinned adapter.
                if coverage_ledger is not None:
                    coverage_ledger.append(
                        event_id=f"native-history-request:{request}",
                        kind="NATIVE_HISTORY_REQUEST",
                        ts_ns=now,
                        payload={
                            "stream": stream,
                            "request_id": str(request),
                            "start_ns": gap["prior_ts_event"],
                            "end_ns": now,
                            "coverage": "REQUESTED_NOT_PROVEN",
                        },
                    )

        def record_history(self, events: Any, kind: str) -> None:
            if coverage_ledger is None or self.coverage_closed:
                return
            now = self.clock.timestamp_ns()
            for event in events:
                if kind == "Bar":
                    try:
                        closed_bar_window(event, now_ns=now)
                    except ValueError:
                        continue  # Never accept the provider's current partial candle.
                digest = native_event_hash(event)
                coverage_ledger.append(
                    event_id=f"native-history:{kind}:{digest}",
                    kind="NATIVE_HISTORY_RESPONSE",
                    ts_ns=event.ts_init,
                    payload={
                        "type": kind,
                        "native_sha256": digest,
                        "ts_event": event.ts_event,
                        "ts_init": event.ts_init,
                        "coverage": "OBSERVED_NOT_LIVE_OR_ARCHIVE_BACKFILL_CERTIFIED",
                    },
                )

        def on_historical_bars(self, bars: Any) -> None:
            self.record_history(bars, "Bar")

        def on_historical_trades(self, trades: Any) -> None:
            self.record_history(trades, "TradeTick")

        def persist_gaps(self) -> None:
            if coverage_ledger is None or self.coverage_closed:
                return
            while self.gap_written < len(health.gap_events):
                event = health.gap_events[self.gap_written]
                coverage_ledger.append(
                    event_id=f"{self.actor_id}:{self.clock.timestamp_ns()}:{self.gap_written}",
                    kind="CAPTURE_GAP",
                    ts_ns=self.clock.timestamp_ns(),
                    payload=event,
                )
                self.gap_written += 1

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
            if f"{identity}:mark" in health.required:
                return  # Refresh must not resubscribe or replace strategy state.
            ages = CONTEXT_AGES if contexts_only else {**STREAM_AGES, **CONTEXT_AGES}
            health.required.update(
                {f"{identity}:{kind}": age * 1_000_000_000 for kind, age in ages.items()}
            )
            context_reader.instrument_ids.add(str(identity))
            self.context_reader = context_reader
            from nautilus_trader.model import DataType

            self.subscribe_mark_prices(identity)
            self.subscribe_index_prices(identity)
            self.subscribe_funding_rates(identity)
            self.subscribe_data(
                DataType("HyperliquidOpenInterest", {"instrument_id": str(identity)})
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
            if contexts_only:
                return
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
            self.persist_gaps()
            if accepted and health.connected:
                self.request_native_gap_history()

        def on_quote(self, event: Any) -> None:
            if event.bid_price.as_decimal() <= 0 or event.ask_price < event.bid_price:
                health.failures.add("INVALID_BBO")
                return
            self.record(event, "quote", str(event.instrument_id))
            # Isolated public qualification only: exercise the official native
            # reconnect command once, never implement a recovery controller.
            if (
                qualification_reconnect
                and not self.reconnect_requested
                and health.first_observed_ns is not None
                and self.clock.timestamp_ns() - health.first_observed_ns >= 60_000_000_000
            ):
                from nautilus_trader.model import ClientId

                self.reconnect_requested = True
                self.reconnect_socket(ClientId("HYPERLIQUID"), "hyperliquid-data-streams")

        def on_mark_price(self, event: Any) -> None:
            self.record_context(event, "mark")

        def on_index_price(self, event: Any) -> None:
            self.record_context(event, "index")

        def on_funding_rate(self, event: Any) -> None:
            self.record_context(event, "funding")

        def on_data(self, value: Any) -> None:
            event = getattr(value, "data", value)
            if type(event).__name__ == "HyperliquidOpenInterest":
                self.record_context(event, "oi")

        def record_context(self, event: Any, kind: str) -> None:
            self.record(event, kind, str(event.instrument_id))
            context_reader.consume(event, now_ns=self.clock.timestamp_ns())

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
            self.persist_gaps()
            if coverage_ledger is not None:
                coverage_ledger.verify()
                coverage_ledger.close()
                self.coverage_closed = True
            for evaluator in evaluators.values():
                evaluator.ledger.verify()
                evaluator.ledger.close()

        def on_socket_state(self, event: Any) -> None:
            state = str(event.state).split(".")[-1].upper()
            if event.endpoint == "hyperliquid-data-streams":
                health.socket(state in {"CONNECTED", "ACTIVE"}, now=self.clock.timestamp_ns())
                self.persist_gaps()

    return NativeObserver()


async def run(args: argparse.Namespace) -> None:
    references = getattr(args, "reference_venues", False)
    if references and (args.sandbox or args.sandbox_probe or args.strategy_manifest is not None):
        raise ValueError("reference runtime is public nontrading only")
    if (
        args.duration_seconds is not None
        and not 30 <= args.duration_seconds <= MAX_QUALIFICATION_SECONDS
    ):
        raise ValueError("qualification capture duration must be 30..900 seconds")
    if args.qualification_reconnect and (
        args.duration_seconds is None or os.environ.get("GITHUB_ACTIONS") != "true"
    ):
        raise ValueError("reconnect probe requires bounded isolated GitHub CI")
    if args.sandbox_probe and (not args.sandbox or args.strategy_manifest is not None):
        raise ValueError("Sandbox protocol probe must be isolated from strategy and real execution")
    from trader_assist_v0.multi_asset_shadow.resolution import FIRST_LAUNCH_20

    snapshot = (
        PitUniverseSnapshot.model_validate_json(args.snapshot.read_text())
        if args.snapshot is not None
        else None
    )
    coins = (
        tuple(e.provider_coin for e in snapshot.expressions)
        if snapshot is not None
        else (
            tuple(item.coin for item in FIRST_LAUNCH_20)
            if getattr(args, "first_launch_20", False)
            else tuple(args.provider_coins)
        )
    )
    context_probe = getattr(args, "context_probe", False)
    if context_probe and (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or args.duration_seconds is None
        or args.duration_seconds > 90
    ):
        raise ValueError("context probe requires bounded <=90s isolated GitHub CI")
    universe = NativeUniverse(coins, snapshot)
    args.root.mkdir(parents=True, exist_ok=True)
    prior_proof_path = args.root / "close-proof.json"
    previous_last_ns = (
        json.loads(prior_proof_path.read_text()).get("last_observed_ns")
        if prior_proof_path.exists()
        else None
    )
    health = NativeHealth({})
    previous_reference_boundaries = {}
    previous_health_path = args.root / "health.json"
    if previous_health_path.exists():
        previous_health = json.loads(previous_health_path.read_text())
        previous_reference_boundaries = (
            previous_health.get("native_reference_coverage", {})
            .get("freshness", {})
            .get("last_native", {})
        )
        boundaries = previous_health.get("last_native", {})
        for gap in previous_health.get("gaps", []):
            if gap.get("next_ts_init") is None and gap["stream"] not in boundaries:
                boundaries[gap["stream"]] = {
                    "ts_event": gap["prior_ts_event"],
                    "ts_init": gap["prior_ts_init"],
                }
        health.restore_boundaries(boundaries, now=time.time_ns())
    require_archive_capacity(
        observe_archive(args.root),
        max_bytes=args.max_archive_bytes,
        free_bytes=shutil.disk_usage(args.root).free,
        minimum_free_bytes=health.minimum_free_bytes,
    )
    # Native recovery runs before starting a new writer. Completed promotion
    # identities are idempotent; a corrupt prior run prevents false readiness.
    from nautilus_trader.persistence import ParquetDataCatalog

    catalog = ParquetDataCatalog(str(args.root))
    recovery = [
        read_staged_run(args.root, run_id, require_closed=True)
        for run_id in catalog.list_live_runs()
    ]
    (args.root / "recovery-proof.json").write_text(json.dumps(recovery, indent=2) + "\n")
    require_archive_capacity(
        observe_archive(args.root),
        max_bytes=args.max_archive_bytes,
        free_bytes=shutil.disk_usage(args.root).free,
        minimum_free_bytes=health.minimum_free_bytes,
    )
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
    node = build_native_node(
        args.root,
        sandbox=args.sandbox,
        sandbox_fee_model=fee_model,
        venues=("HYPERLIQUID", "BINANCE", "OKX") if references else ("HYPERLIQUID",),
    )
    reference_reader = None
    if references:
        from trader_assist_v0.nautilus_e4.native_reference import ReferenceReader, reference_actor

        reference_reader = ReferenceReader()
        reference_reader.health.restore_boundaries(
            previous_reference_boundaries,
            now=time.time_ns(),
        )
        node.add_actor(reference_actor(reference_reader))
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
    observer = capture_observer(
        universe,
        health,
        strategy_manifest=strategy_manifest,
        ledger_root=args.root / "shadow-ledger",
        metadata_root=args.root,
        qualification_reconnect=args.qualification_reconnect,
        contexts_only=context_probe,
    )
    node.add_actor(observer)
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
            archive = observe_archive(args.root, args.root / "live" / instance_id)
            free_bytes = shutil.disk_usage(args.root).free
            output = health.report(now=now, generated=now, free_bytes=free_bytes)
            output["archive"] = archive.evidence(now_ns=now)
            output["capture_gap"] = capture_gap(previous_last_ns, health.first_observed_ns)
            observer.persist_gaps()
            output["missing_provider_coins"] = universe.missing
            if reference_reader is not None:
                reference_report = reference_reader.coverage()
                reference_report["freshness"] = reference_reader.health.report(
                    now=now,
                    generated=now,
                    free_bytes=free_bytes,
                )
                output["native_reference_coverage"] = reference_report
            output["instance_id"] = instance_id
            output["capture_state"] = "CONTINUOUS_NATIVE_STAGE_CAPTURE"
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
            require_archive_capacity(
                archive,
                max_bytes=args.max_archive_bytes,
                free_bytes=free_bytes,
                minimum_free_bytes=health.minimum_free_bytes,
            )
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
        except Exception as exc:
            health.failures.add(str(exc))
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
                node.dispose()  # Native explicit close/seal must always run.
            except Exception as exc:
                failure = failure or exc
        health.connected = False
        closed_report_ns = time.time_ns()
        stopped = health.report(
            now=closed_report_ns,
            generated=closed_report_ns,
            free_bytes=shutil.disk_usage(args.root).free,
        )
        if reference_reader is not None:
            reference_reader.health.connected = False
            stopped_reference = reference_reader.coverage()
            stopped_reference["freshness"] = reference_reader.health.report(
                now=closed_report_ns,
                generated=closed_report_ns,
                free_bytes=shutil.disk_usage(args.root).free,
            )
            stopped["native_reference_coverage"] = stopped_reference
        stopped["capture_state"] = "STOPPED"
        (args.root / "health.json").write_text(json.dumps(stopped, indent=2) + "\n")
    if failure is not None:
        raise failure
    proof = read_staged_run(args.root, instance_id, require_closed=True)
    archive = observe_archive(args.root, args.root / "live" / instance_id)
    # Explicit close can flush additional buffered rows. Exceeding the budget
    # retains the evidence and fails; it never silently prunes source files.
    try:
        require_archive_capacity(
            archive,
            max_bytes=args.max_archive_bytes,
            free_bytes=shutil.disk_usage(args.root).free,
            minimum_free_bytes=health.minimum_free_bytes,
        )
    except RuntimeError as exc:
        stopped["reasons"] = sorted({*stopped["reasons"], str(exc)})
        stopped["archive"] = archive.evidence(now_ns=time.time_ns())
        (args.root / "health.json").write_text(json.dumps(stopped, indent=2) + "\n")
        raise
    missing = sorted(set(health.required) - health.counts.keys())
    freshness = set(last_active_report.get("reasons", ["NO_RUNTIME_HEALTH_REPORT"])) - {
        "WRITER_UNKNOWN_OR_FAILED",
        "CATALOG_UNVERIFIED",
    }
    if not 0 <= stopped_ns - last_active_report.get("generated_ns", 0) <= health.report_max_age_ns:
        freshness.add("HEALTH_REPORT_STALE_AT_STOP")
    elapsed = time.monotonic() - started
    duration_complete = bool(last_active_report.get("bounded_stop_requested"))
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
        policy="CONTINUOUS_NATIVE_INTERVAL_STAGE_NO_AUTOMATIC_PROMOTION",
        archive_bytes=archive.total_bytes,
        max_archive_bytes=args.max_archive_bytes,
        retention="RETAIN_ALL_STOP_AT_BUDGET_NO_AUTOMATIC_DELETION",
        sandbox=sandbox_proof,
        first_observed_ns=health.first_observed_ns,
        last_observed_ns=health.last_observed_ns,
        capture_gap=capture_gap(previous_last_ns, health.first_observed_ns),
        stream_gaps=health.gaps,
        reconnect_probe_requested=observer.reconnect_requested,
    )
    (args.root / "close-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    stopped.update(
        capture_state="STOPPED_STAGE_READABLE_CATALOG_UNQUALIFIED",
        capture_gap=proof["capture_gap"],
        archive={
            **archive.evidence(now_ns=time.time_ns()),
            "writer": "CLOSED",
            "catalog": "NOT_VERIFIED_OR_PROMOTED",
            "instance_id": instance_id,
            "typed_integrity": proof["types"],
        },
    )
    (args.root / "health.json").write_text(json.dumps(stopped, indent=2) + "\n")
    if args.duration_seconds is None:
        raise RuntimeError("UNEXPECTED_NATIVE_NODE_STOP")
    if not duration_complete:
        raise RuntimeError("NATIVE_RUN_STOPPED_BEFORE_REQUESTED_DURATION")
    if context_probe:
        from trader_assist_v0.nautilus_e4.native_context import context_proof

        if universe.missing or observer.context_reader is None:
            raise ValueError("CONTEXT_PROVIDER_METADATA_UNRESOLVED")
        result = context_proof(
            args.root,
            instance_id,
            {e.instrument_id for e in universe.resolved.values()},
            observer.context_reader.hashes,
        )
        result["provider_snapshot"] = proof["provider_snapshot"]
        result["live_freshness_reasons"] = proof["freshness_reasons"]
        result["stream_gaps"] = proof["stream_gaps"]
        (args.root / "context-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    else:
        require_qualified_stop(proof, instance_id)
    print(json.dumps({"qualification_exit": "VERIFIED_STAGED_STOP", "instance_id": instance_id}))


def main() -> None:
    parser = argparse.ArgumentParser()
    universe_args = parser.add_mutually_exclusive_group(required=True)
    universe_args.add_argument("--snapshot", type=Path)
    universe_args.add_argument("--provider-coins", nargs="+")
    universe_args.add_argument("--first-launch-20", action="store_true")
    parser.add_argument(
        "--reference-venues",
        action="store_true",
        help="opt-in native Binance JSON Spot + OKX SWAP; no orders",
    )
    parser.add_argument("--context-probe", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--duration-seconds", type=int, help="isolated qualification only; default is continuous"
    )
    parser.add_argument("--qualification-reconnect", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--max-archive-bytes", type=int, default=DEFAULT_ARCHIVE_BYTES)
    parser.add_argument("--startup-timeout-seconds", type=int, default=90)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--sandbox-probe", action="store_true")
    parser.add_argument("--strategy-manifest", type=Path)
    parser.add_argument("--maker-rate")
    parser.add_argument("--taker-rate")
    args = parser.parse_args()
    if (
        args.duration_seconds is not None
        and not 30 <= args.duration_seconds <= MAX_QUALIFICATION_SECONDS
    ):
        parser.error("bounded capture duration must be 30..900 seconds")
    if args.max_archive_bytes <= 0:
        parser.error("archive budget must be positive")
    if args.sandbox_probe and (not args.sandbox or args.strategy_manifest is not None):
        parser.error(
            "protocol probe requires Sandbox and must be isolated from registered strategy"
        )
    try:
        asyncio.run(run(args))
    except (ArchiveCapacityError, ArchiveIntegrityError, ValueError, OSError) as exc:
        print(f"FATAL_CAPTURE_STOP:{exc}", file=sys.stderr, flush=True)
        raise SystemExit(78) from exc


if __name__ == "__main__":
    main()
