"""Thin evidence-derived bootstrap for the public multi-asset Shadow route.

The application owns no durable workflow state. Every restart derives Scanner,
Strategy, Formalization, and Outcome work from finalized bars and EvidenceStore.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from .data import MultiAssetDataAuthority
from .hyperliquid_public import (
    HyperliquidPublicClient,
    HyperliquidPublicPlanningAdapter,
    HyperliquidRestOneMinuteProvider,
    PublicDataError,
)
from .integration import (
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    FormalizationArtifacts,
    IntegrationError,
    MultiAssetShadowCoordinator,
    RetainedFormalDecision,
    ScannerCompositionReceipt,
    ScannerPublicSnapshot,
    TargetResolutionError,
)
from .models import ClosedBar, MarketLifecycle, RegistryMarket
from .notification_engine import NotificationKind, ScannerWatchNotificationView
from .outcome_engine import FormalShadowOutcome, OutcomeEngine, OutcomeEngineError
from .planning import CostModel, PlanningError, PlanRejection
from .registry import MarketRegistryManager
from .runtime import BoundaryMode, MultiAssetPublicRuntime
from .shadow_records import EvidenceStore, FormalizationDispositionStatus
from .strategy_kernel import ScannerChase, ScannerState

_FIVE_MINUTES_MS = 300_000
_MAX_FORMAL_ATTEMPTS = 3
_DETERMINISTIC_REJECTIONS = frozenset(
    {
        PlanRejection.LIQUIDITY_HARD_LIMIT,
        PlanRejection.CHASE_LIMIT_EXCEEDED,
        PlanRejection.TARGET_FEASIBILITY_FAILED,
    }
)


class BootstrapIntegrityError(RuntimeError):
    """A composed authority contradicted retained evidence."""


class BoundaryDisposition(StrEnum):
    """Non-durable result of one per-market runtime wakeup."""

    PROCESSED = "PROCESSED"
    DEFERRED_WAITING_FOR_PEERS = "DEFERRED_WAITING_FOR_PEERS"


@dataclass(frozen=True)
class BoundaryFailure:
    stage: str
    market_id: str | None
    error_type: str
    reason: str


@dataclass(frozen=True)
class BoundaryReport:
    boundary_open_time_ms: int
    evaluation_mode: BoundaryMode
    disposition: BoundaryDisposition
    scanner_run_count: int
    evaluated_market_ids: tuple[str, ...]
    formal_shadow_order_ids: tuple[str, ...]
    plan_rejections: tuple[tuple[str, PlanRejection], ...]
    failures: tuple[BoundaryFailure, ...]


@dataclass(frozen=True)
class OutcomeCadenceReport:
    evaluated_outcomes: tuple[FormalShadowOutcome, ...]
    failure: BoundaryFailure | None = None


class MultiAssetProductionBootstrap:
    """Small dispatcher/reconciler; durable state remains in authoritative stores."""

    def __init__(
        self,
        *,
        registry: MarketRegistryManager,
        data_authority: MultiAssetDataAuthority,
        evidence: EvidenceStore,
        outbox: EvidenceOutbox,
        outcome_adapter: EvidenceOutcomeAdapter,
        outcome_engine: OutcomeEngine,
        planning_data: HyperliquidPublicPlanningAdapter,
        coordinator: MultiAssetShadowCoordinator,
        runtime: MultiAssetPublicRuntime,
        clock: Callable[[], datetime],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self.registry = registry
        self.data_authority = data_authority
        self.evidence = evidence
        self.outbox = outbox
        self.outcome_adapter = outcome_adapter
        self.outcome_engine = outcome_engine
        self.planning_data = planning_data
        self.coordinator = coordinator
        self.runtime = runtime
        self.clock = clock
        self.sleep = sleep
        self._lock = asyncio.Lock()

    @classmethod
    def compose(
        cls,
        *,
        registry: MarketRegistryManager,
        data_authority: MultiAssetDataAuthority,
        public_client: HyperliquidPublicClient,
        evidence_db_path: Path,
        cost_model: CostModel,
        release_sha: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> MultiAssetProductionBootstrap:
        if data_authority.registry is not registry:
            raise BootstrapIntegrityError("data authority and composition Registry differ")
        evidence = EvidenceStore(evidence_db_path)
        outbox = EvidenceOutbox(evidence)
        outcome_adapter = EvidenceOutcomeAdapter(evidence)
        one_minute = HyperliquidRestOneMinuteProvider(public_client, registry)
        outcome = outcome_adapter.restore_engine(
            now_ms=_clock_ms(clock), provider=one_minute
        )
        planning = HyperliquidPublicPlanningAdapter(public_client)
        runtime = MultiAssetPublicRuntime(
            registry=registry,
            authority=data_authority,
            client=public_client,
            clock=clock,
            sleep=sleep,
        )
        coordinator = MultiAssetShadowCoordinator(
            registry=registry,
            data_authority=data_authority,
            evidence=evidence,
            outbox=outbox,
            outcome_engine=outcome,
            outcome_adapter=outcome_adapter,
            planning_data=planning,
            cost_model=cost_model,
            release_sha=release_sha,
            runtime_readiness=runtime,
        )
        application = cls(
            registry=registry,
            data_authority=data_authority,
            evidence=evidence,
            outbox=outbox,
            outcome_adapter=outcome_adapter,
            outcome_engine=outcome,
            planning_data=planning,
            coordinator=coordinator,
            runtime=runtime,
            clock=clock,
            sleep=sleep,
        )
        runtime.on_finalized_5m = application.on_finalized_5m
        return application

    async def on_finalized_5m(
        self, bar: ClosedBar, mode: BoundaryMode
    ) -> BoundaryReport:
        return await self.process_boundary(bar.open_time_ms, mode)

    async def process_boundary(
        self, boundary_open_time_ms: int, mode: BoundaryMode
    ) -> BoundaryReport:
        if boundary_open_time_ms < 0 or boundary_open_time_ms % _FIVE_MINUTES_MS:
            raise BootstrapIntegrityError("boundary must be an aligned 5m open")
        async with self._lock:
            markets, waiting_for_peers = self._boundary_markets(boundary_open_time_ms)
            if waiting_for_peers:
                return BoundaryReport(
                    boundary_open_time_ms=boundary_open_time_ms,
                    evaluation_mode=mode,
                    disposition=BoundaryDisposition.DEFERRED_WAITING_FOR_PEERS,
                    scanner_run_count=0,
                    evaluated_market_ids=(),
                    formal_shadow_order_ids=(),
                    plan_rejections=(),
                    failures=(),
                )
            failures: list[BoundaryFailure] = []
            compositions: dict[str, ScannerCompositionReceipt] = {}
            scanner_run_count = 0
            live_scanner_ready = mode is not BoundaryMode.LIVE_ACTIONABLE
            if mode is BoundaryMode.LIVE_ACTIONABLE:
                self._expire_prior_pending(boundary_open_time_ms)
                try:
                    scan = self.coordinator.retained_scanner_run(
                        boundary_open_time_ms=boundary_open_time_ms
                    )
                    if scan is None:
                        snapshots = await self._scanner_snapshots(markets, boundary_open_time_ms)
                        scan = self.coordinator.scan_finalized(
                            snapshots,
                            observed_at=self.clock(),
                            evaluation_mode=mode,
                        )
                        scanner_run_count = 1
                    for market in markets:
                        composition = self.coordinator.compose_scanner_market(
                            receipt=scan, market_id=market.identity.market_id
                        )
                        compositions[market.identity.market_id] = composition
                        self._publish_watch(market, composition)
                    live_scanner_ready = len(compositions) == len(markets)
                except (IntegrationError, PlanningError, PublicDataError) as exc:
                    failures.append(_failure("SCANNER", None, exc))

            evaluated: list[str] = []
            for market in markets:
                if not live_scanner_ready:
                    break
                market_id = market.identity.market_id
                try:
                    missing = self.coordinator.strategy_recovery_boundaries(
                        market_id=market_id,
                        current_source_open_time_ms=boundary_open_time_ms,
                    )
                    boundaries = missing
                    if (
                        boundary_open_time_ms not in missing
                        and not self.coordinator.has_retained_strategy_evaluation(
                            market_id=market_id,
                            source_open_time_ms=boundary_open_time_ms,
                        )
                    ):
                        boundaries += (boundary_open_time_ms,)
                    for source_open in boundaries:
                        is_current_live = (
                            mode is BoundaryMode.LIVE_ACTIONABLE
                            and source_open == boundary_open_time_ms
                        )
                        current_composition = (
                            compositions.get(market_id) if is_current_live else None
                        )
                        selected = (
                            None
                            if current_composition is None
                            else current_composition.selected_candidate
                        )
                        selected_record = (
                            None
                            if current_composition is None
                            else current_composition.selected_candidate_record
                        )
                        evaluation_mode = (
                            mode
                            if source_open == boundary_open_time_ms
                            else BoundaryMode.RECOVERY_CONTEXT_ONLY
                        )
                        self.coordinator.evaluate_finalized_market(
                            market_id=market_id,
                            scanner_linkage=None if selected is None else selected.linkage,
                            scanner_candidate_record_id=(
                                None if selected_record is None else selected_record.record_id
                            ),
                            source_open_time_ms=source_open,
                            evaluation_mode=evaluation_mode,
                        )
                    evaluated.append(market_id)
                except IntegrationError as exc:
                    failures.append(_failure("STRATEGY", market_id, exc))

            formalized: list[FormalizationArtifacts] = []
            rejections: list[tuple[str, PlanRejection]] = []
            if mode is BoundaryMode.LIVE_ACTIONABLE:
                if live_scanner_ready:
                    for pending in self.coordinator.pending_formal_decisions():
                        if pending.source_open_time_ms != boundary_open_time_ms:
                            continue
                        result = await self._process_pending(pending, failures)
                        if isinstance(result, FormalizationArtifacts):
                            formalized.append(result)
                        elif isinstance(result, PlanRejection):
                            rejections.append((pending.market_id, result))

            outcome_report = self.advance_outcomes()
            if outcome_report.failure is not None:
                failures.append(outcome_report.failure)
            return BoundaryReport(
                boundary_open_time_ms=boundary_open_time_ms,
                evaluation_mode=mode,
                disposition=BoundaryDisposition.PROCESSED,
                scanner_run_count=scanner_run_count,
                evaluated_market_ids=tuple(evaluated),
                formal_shadow_order_ids=tuple(
                    item.shadow_order.record_id for item in formalized
                ),
                plan_rejections=tuple(rejections),
                failures=tuple(failures),
            )

    async def reconcile(self) -> tuple[FormalizationArtifacts, ...]:
        """Retry still-actionable retained Formal decisions after restart/reconnect."""
        readiness = self.runtime.readiness_snapshot()
        current = readiness.latest_closed_5m_open_time_ms
        self._expire_prior_pending(current)
        artifacts: list[FormalizationArtifacts] = []
        failures: list[BoundaryFailure] = []
        for pending in self.coordinator.pending_formal_decisions():
            if pending.source_open_time_ms != current:
                continue
            result = await self._process_pending(pending, failures)
            if isinstance(result, FormalizationArtifacts):
                artifacts.append(result)
        self.advance_outcomes()
        return tuple(artifacts)

    async def _process_pending(
        self, pending: RetainedFormalDecision, failures: list[BoundaryFailure]
    ) -> FormalizationArtifacts | PlanRejection | None:
        for attempt in range(_MAX_FORMAL_ATTEMPTS):
            try:
                result = self.coordinator.process_retained_formal_decision(
                    strategy_evaluation_id=pending.strategy_evaluation_id,
                    strategy_decision_id=pending.strategy_decision_id,
                    now_ms=_clock_ms(self.clock),
                )
            except TargetResolutionError as exc:
                self.coordinator.record_formalization_disposition(
                    decision=pending,
                    status=FormalizationDispositionStatus.REJECTED,
                    reason="INVALID_FROZEN_TARGET_GEOMETRY",
                    decided_at=self.clock(),
                )
                failures.append(_failure("TARGET_REJECTED", pending.market_id, exc))
                return PlanRejection.TARGET_FEASIBILITY_FAILED
            except (PublicDataError, PlanningError) as exc:
                if attempt + 1 == _MAX_FORMAL_ATTEMPTS:
                    failures.append(_failure("FORMAL_TRANSIENT", pending.market_id, exc))
                    return None
                await self.sleep(0.05 * (attempt + 1))
                continue
            except IntegrationError as exc:
                failures.append(_failure("FORMAL_AUTHORITY", pending.market_id, exc))
                return None
            if result is PlanRejection.BBO_INVALID_OR_STALE:
                if attempt + 1 == _MAX_FORMAL_ATTEMPTS:
                    return result
                await self.sleep(0.05 * (attempt + 1))
                continue
            if isinstance(result, PlanRejection):
                if result not in _DETERMINISTIC_REJECTIONS:
                    return result
                self.coordinator.record_formalization_disposition(
                    decision=pending,
                    status=FormalizationDispositionStatus.REJECTED,
                    reason=result.value,
                    decided_at=self.clock(),
                )
            return result
        return None

    def _expire_prior_pending(self, current_boundary_open_time_ms: int) -> None:
        for pending in self.coordinator.pending_formal_decisions():
            if pending.source_open_time_ms >= current_boundary_open_time_ms:
                continue
            self.coordinator.record_formalization_disposition(
                decision=pending,
                status=FormalizationDispositionStatus.EXPIRED,
                reason="ORIGINATING_LIVE_5M_BOUNDARY_ENDED",
                decided_at=self.clock(),
            )

    def advance_outcomes(self) -> OutcomeCadenceReport:
        try:
            return OutcomeCadenceReport(
                self.outcome_engine.tick(now_ms=_clock_ms(self.clock))
            )
        except (OutcomeEngineError, PublicDataError) as exc:
            return OutcomeCadenceReport((), _failure("OUTCOME", None, exc))

    def close(self) -> None:
        self.evidence.close()

    def _boundary_markets(
        self, boundary_open_time_ms: int
    ) -> tuple[tuple[RegistryMarket, ...], bool]:
        active = self.registry.active()
        if active is None:
            raise BootstrapIntegrityError("active Registry is required")
        readiness = self.runtime.readiness_snapshot()
        required = tuple(
            market for market in active.markets if market.lifecycle is MarketLifecycle.ACTIVE
        )
        required_ids = {market.identity.market_id for market in required}
        if not required_ids:
            # No actionable cohort exists yet (first launch before the whole
            # selected cohort reaches ACTIVE): wait for peers, never act on a
            # partial cohort.
            return required, True
        if (
            readiness.registry_version != active.version
            or readiness.registry_content_hash != active.content_hash
            or readiness.latest_closed_5m_open_time_ms != boundary_open_time_ms
        ):
            raise BootstrapIntegrityError(
                "runtime readiness contradicts active Registry authority"
            )
        if not readiness.data_ready or required_ids & set(readiness.failed_market_ids):
            # Expected operational non-readiness: a failed required peer or a
            # runtime still completing warmup is a normal fail-closed defer
            # for the whole cohort, not an integrity failure and not an
            # application failure of whichever healthy market finalized.
            return required, True
        waiting = False
        for market in required:
            row = self.data_authority.store.connection.execute(
                """SELECT registry_version, registry_content_hash FROM closed_bars
                   WHERE market_id = ? AND interval = '5m' AND open_time_ms = ?""",
                (market.identity.market_id, boundary_open_time_ms),
            ).fetchone()
            if row is None:
                waiting = True
                continue
            if row != (active.version, active.content_hash):
                raise BootstrapIntegrityError(
                    "retained boundary is not bound to active Registry authority"
                )
        if waiting:
            return required, True
        if set(readiness.ready_market_ids) != required_ids:
            # Incomplete readiness set: expected non-readiness, defer for the
            # whole cohort instead of failing the healthy markets' callback.
            return required, True
        return required, False

    async def _scanner_snapshots(
        self, markets: tuple[RegistryMarket, ...], boundary_open_time_ms: int
    ) -> dict[str, ScannerPublicSnapshot]:
        btc_returns = self._btc_returns(markets, boundary_open_time_ms)
        snapshots: dict[str, ScannerPublicSnapshot] = {}
        for market in markets:
            snapshots[market.identity.market_id] = await asyncio.to_thread(
                self.planning_data.fetch_scanner_snapshot,
                market=market,
                now_ms=_clock_ms(self.clock),
                btc_returns=btc_returns,
            )
        return snapshots

    def _btc_returns(
        self, markets: tuple[RegistryMarket, ...], boundary_open_time_ms: int
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        btc = tuple(
            market
            for market in markets
            if market.identity.dex == "MAIN" and market.identity.coin == "BTC"
        )
        if len(btc) != 1:
            return (None, None, None)
        bars = self.data_authority.store.bars(btc[0].identity.market_id)
        if not bars or bars[-1].open_time_ms != boundary_open_time_ms or len(bars) < 13:
            return (None, None, None)
        current = bars[-1].close
        values = tuple(current / bars[-1 - offset].close - 1 for offset in (3, 6, 12))
        return values  # type: ignore[return-value]

    def _publish_watch(
        self, market: RegistryMarket, composition: ScannerCompositionReceipt
    ) -> None:
        candidate = composition.selected_candidate
        if candidate is None or composition.selected_candidate_record is None:
            return
        raw = next(
            item
            for item in composition.scan_receipt.observations
            if item.market_id == market.identity.market_id
        )
        metrics = raw.metrics
        scan = self.evidence.get(composition.scan_receipt.scanner_evidence_id)
        if scan is None or not isinstance(scan.payload.get("observed_at"), str):
            raise IntegrationError("selected WATCH lacks retained observation time")
        observed_at = datetime.fromisoformat(
            str(scan.payload["observed_at"]).replace("Z", "+00:00")
        ).astimezone(UTC)
        self.coordinator.publish_watch(
            ScannerWatchNotificationView(
                kind=(
                    NotificationKind.WATCH_NEW_MARKET
                    if candidate.state is ScannerState.WATCH_NEW_MARKET
                    else NotificationKind.WATCH
                ),
                market_display=market.display,
                tier=market.tier,
                side=None if candidate.side is None else candidate.side.value,
                observation_time=observed_at,
                return_15m=None if metrics is None else metrics.return_15m,
                return_30m=None if metrics is None else metrics.return_30m,
                return_60m=None if metrics is None else metrics.return_60m,
                rank=None,
                move_atr=None if metrics is None else metrics.move_atr_15m,
                relative_volume=None if metrics is None else metrics.relative_volume_5m,
                prior_level=(
                    None
                    if candidate.breakout_level is None
                    else format(candidate.breakout_level, "f")
                ),
                distance_to_level=candidate.chase_distance_atr,
                liquidity_summary=None,
                scanner_r3_state=candidate.state.value,
                session=None,
                scanner_parameter_version=candidate.parameter_version,
                watch_id=candidate.candidate_id,
                do_not_chase=candidate.chase in {ScannerChase.LATE, ScannerChase.REJECTED},
            )
        )


def _clock_ms(clock: Callable[[], datetime]) -> int:
    now = clock()
    if now.tzinfo is None:
        raise BootstrapIntegrityError("composition clock must be timezone-aware")
    return int(now.timestamp() * 1000)


def _failure(stage: str, market_id: str | None, error: Exception) -> BoundaryFailure:
    return BoundaryFailure(stage, market_id, type(error).__name__, str(error))
