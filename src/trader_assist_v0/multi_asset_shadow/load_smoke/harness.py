"""Offline, deterministic correctness smoke for the fixed Manual-40 route.

This is deliberately a narrow release check, not a capacity-discovery or
performance benchmark framework.  Its adapters are synthetic and it only
exercises the existing public 5m/finality contracts.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.finality import (
    CandidateGeneration,
    ConfirmationResult,
    GenerationFinalityAuthority,
)
from trader_assist_v0.multi_asset_shadow.models import RegistryMarket, RegistryVersion
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.resolution import INITIAL_40, resolve_initial_40

_CYCLE_MS = 300_000
_CYCLES = 12
_RECEIVED_AT = datetime(2026, 8, 12, 2, 0, tzinfo=UTC)


@dataclass(frozen=True)
class LoadSmokeReport:
    """Fixed evidence fields; none represent production throughput."""

    fixed_market_count: int
    five_m_events_processed: int
    max_pending_finality_generations: int
    max_active_confirmations: int
    bars_persisted: int
    fifteen_m_aggregates: int
    one_h_aggregates: int
    failed_market_count: int
    healthy_markets_progress: int
    reconnect_result: str
    shutdown_pending_state: str
    full_universe_continuous_1m: bool
    continuous_l2: bool
    account_private_or_write_surface: bool

    def evidence_lines(self) -> tuple[str, ...]:
        """Render only the required, stable key-value evidence."""
        return (
            f"FIXED_MARKET_COUNT={self.fixed_market_count}",
            f"5M_EVENTS_PROCESSED={self.five_m_events_processed}",
            f"MAX_PENDING_FINALITY_GENERATIONS={self.max_pending_finality_generations}",
            f"MAX_ACTIVE_CONFIRMATIONS={self.max_active_confirmations}",
            f"BARS_PERSISTED={self.bars_persisted}",
            f"15M_AGGREGATES={self.fifteen_m_aggregates}",
            f"1H_AGGREGATES={self.one_h_aggregates}",
            f"FAILED_MARKET_COUNT={self.failed_market_count}",
            f"HEALTHY_MARKETS_PROGRESS={self.healthy_markets_progress}",
            f"RECONNECT_RESULT={self.reconnect_result}",
            f"SHUTDOWN_PENDING_STATE={self.shutdown_pending_state}",
        )


def _resolved_markets() -> tuple[RegistryMarket, ...]:
    """Resolve the existing Manual-40 fixture through its normal resolver."""
    native: list[object] = []
    xyz: list[object] = []
    for request in INITIAL_40:
        record = {"name": request.coin, "szDecimals": 2, "maxLeverage": 10}
        (native if request.dex == "MAIN" else xyz).append(record)
    resolved = resolve_initial_40(
        perp_dexes=[{"name": "main"}, {"name": "xyz"}],
        all_perp_metas=[{"universe": native}, {"universe": xyz}],
        observed_at=_RECEIVED_AT,
    )
    markets = tuple(item.market for item in resolved if item.status == "RESOLVED")
    if len(markets) != 40 or any(market is None for market in markets):
        raise AssertionError("Manual-40 fixture did not resolve exactly 40 markets")
    return tuple(market for market in markets if market is not None)


def _bar(market: RegistryMarket, open_time_ms: int) -> dict[str, object]:
    price = Decimal("100") + Decimal(open_time_ms // _CYCLE_MS)
    return {
        "i": "5m",
        "s": market.identity.coin,
        "t": open_time_ms,
        "T": open_time_ms + _CYCLE_MS - 1,
        "o": str(price),
        "h": str(price + 2),
        "l": str(price - 1),
        "c": str(price + 1),
        "v": "10",
    }


def _authority(root: Path, markets: tuple[RegistryMarket, ...]) -> MultiAssetDataAuthority:
    registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(version="manual-40", created_at=_RECEIVED_AT, markets=markets)
    registry.stage(seed)
    registry.request_apply(seed.version)
    return MultiAssetDataAuthority(
        store=ClosedBarStore(root / "evidence.sqlite"), registry=registry
    )


def _exercise_causal_cycles(
    root: Path, markets: tuple[RegistryMarket, ...]
) -> tuple[int, int, int]:
    authority = _authority(root, markets)
    received_at = datetime.fromtimestamp((_CYCLES * _CYCLE_MS + 1) / 1000, UTC)
    for cycle in range(_CYCLES):
        open_time_ms = cycle * _CYCLE_MS
        for market in markets:
            authority.admit_rest_history(
                market=market,
                snapshot=[_bar(market, open_time_ms)],
                received_at=received_at,
            )
    five_m = sum(len(authority.store.bars(market.identity.market_id)) for market in markets)
    fifteen_m = sum(
        len(authority.store.bars(market.identity.market_id, interval="15m")) for market in markets
    )
    one_h = sum(
        len(authority.store.bars(market.identity.market_id, interval="1h")) for market in markets
    )
    authority.store.close()
    return five_m, fifteen_m, one_h


async def _exercise_finality(markets: tuple[RegistryMarket, ...]) -> tuple[int, int, int, str, str]:
    """Exercise bounded slots, failure isolation, supersession, and cleanup."""
    active = 0
    maximum_active = 0
    release = asyncio.Event()
    started = asyncio.Event()
    started_count = 0
    completed: set[str] = set()
    observed_fingerprints: list[tuple[str, str]] = []
    failed: set[str] = set()
    discarded: list[str] = []

    async def confirm(generation: CandidateGeneration) -> ConfirmationResult:
        nonlocal active, maximum_active, started_count
        active += 1
        maximum_active = max(maximum_active, active)
        started_count += 1
        if started_count == 4:
            started.set()
        await release.wait()
        active -= 1
        if generation.market.display == "WTIOIL":
            return ConfirmationResult.FAILED
        completed.add(generation.identity.market_id)
        observed_fingerprints.append((generation.identity.market_id, generation.fingerprint))
        return ConfirmationResult.COMPLETE

    coordinator = GenerationFinalityAuthority(
        confirm=confirm,
        discard=lambda identity: discarded.append(identity.market_id),
        mark_failed=failed.add,
        now_ms=lambda: 303_000,
        sleep=asyncio.sleep,
        confirmation_concurrency=4,
    )
    for market in markets:
        coordinator.offer(market=market, open_time_ms=0, fingerprint="A")
    max_pending = len(coordinator.pending)
    await started.wait()
    # The exact same open advances A -> B -> C but retains one market worker.
    superseded = markets[0]
    coordinator.offer(market=superseded, open_time_ms=0, fingerprint="B")
    coordinator.offer(market=superseded, open_time_ms=0, fingerprint="C")
    release.set()
    await asyncio.gather(*tuple(coordinator.tasks.values()))
    if failed != {next(m.identity.market_id for m in markets if m.display == "WTIOIL")}:
        raise AssertionError("one failed market was not isolated")
    if len(completed) != 39 or coordinator.pending or coordinator.tasks:
        raise AssertionError("healthy markets did not finish bounded finality")
    superseded_observations = [
        fingerprint
        for market_id, fingerprint in observed_fingerprints
        if market_id == superseded.identity.market_id
    ]
    if superseded_observations != ["A", "C"]:
        raise AssertionError("same-open supersession ran a stale generation")

    # Reconnect invalidation and shutdown both drain pending confirmation state.
    async def wait_for_cleanup(_: float) -> None:
        await asyncio.Event().wait()

    pending = GenerationFinalityAuthority(
        confirm=confirm,
        discard=lambda identity: discarded.append(identity.market_id),
        mark_failed=failed.add,
        now_ms=lambda: 0,
        sleep=wait_for_cleanup,
        confirmation_concurrency=4,
    )
    for market in markets:
        pending.offer(market=market, open_time_ms=0, fingerprint="pending")
    await asyncio.sleep(0)
    await pending.invalidate_all()
    reconnect = "CLEARED" if not pending.pending and not pending.tasks else "UNCLEARED"
    for market in markets:
        pending.offer(market=market, open_time_ms=0, fingerprint="shutdown")
    await asyncio.sleep(0)
    await pending.close()
    shutdown = "CLEARED" if not pending.pending and not pending.tasks else "UNCLEARED"
    return max_pending, maximum_active, len(completed), reconnect, shutdown


def run_fixed_40_load_smoke(root: Path) -> LoadSmokeReport:
    """Run all fixed scenarios with no network, account, credential, or write adapter."""
    markets = _resolved_markets()
    five_m, fifteen_m, one_h = _exercise_causal_cycles(root / "causal", markets)
    max_pending, max_active, healthy, reconnect, shutdown = asyncio.run(_exercise_finality(markets))
    return LoadSmokeReport(
        fixed_market_count=len(markets),
        five_m_events_processed=five_m,
        max_pending_finality_generations=max_pending,
        max_active_confirmations=max_active,
        bars_persisted=five_m + fifteen_m + one_h,
        fifteen_m_aggregates=fifteen_m,
        one_h_aggregates=one_h,
        failed_market_count=1,
        healthy_markets_progress=healthy,
        reconnect_result=reconnect,
        shutdown_pending_state=shutdown,
        full_universe_continuous_1m=False,
        continuous_l2=False,
        account_private_or_write_surface=False,
    )
