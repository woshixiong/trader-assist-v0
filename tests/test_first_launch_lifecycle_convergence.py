"""Finite-state proof of the pure First-Launch lifecycle reconciliation planner.

Layer 1 of the final convergence acceptance: exhaustively enumerate the
PRE_ACTIVE state space of a small synthetic cohort (N=3, 3^3 = 27 lifecycle
configurations) crossed with failure, snapshot readiness, and WARMING
history-currency eligibility, and prove the Initial-Launch invariants for
every generated transition:

- no illegal lifecycle regression;
- every update is exactly one legal Registry ``_LIFECYCLE_NEXT`` transition;
- ACTIVE_COUNT is only ever 0 or N (never 1..N-1);
- a failed launch member holds the whole cohort;
- repeated reconciliation with eventually-healthy prerequisites converges
  monotonically to all ACTIVE;
- a post-live cohort containing DRAINING (zero ACTIVE) never re-enters
  First-Launch semantics.
"""

from __future__ import annotations

from itertools import product

from trader_assist_v0.multi_asset_shadow.models import MarketLifecycle
from trader_assist_v0.multi_asset_shadow.registry import _LIFECYCLE_NEXT
from trader_assist_v0.multi_asset_shadow.runtime import (
    _PRE_ACTIVE_RANK,
    plan_lifecycle_updates,
)

N = 3
MARKET_IDS = ("market-0", "market-1", "market-2")
PRE_ACTIVE = (
    MarketLifecycle.WARMING,
    MarketLifecycle.HISTORY_READY,
    MarketLifecycle.SNAPSHOT_READY,
)
ALL_CONFIGURATIONS = tuple(
    dict(zip(MARKET_IDS, states, strict=True))
    for states in product(PRE_ACTIVE, repeat=N)
)


def reconcile(
    lifecycles: dict[str, MarketLifecycle],
    *,
    failed: frozenset[str] = frozenset(),
    history_current: frozenset[str] | None = None,
    snapshot_ready: bool = True,
) -> dict[str, MarketLifecycle]:
    return plan_lifecycle_updates(
        lifecycles,
        failed_market_ids=failed,
        history_current_ids=frozenset(lifecycles)
        if history_current is None
        else history_current,
        snapshot_ready=snapshot_ready,
    )


def apply_updates(
    lifecycles: dict[str, MarketLifecycle], updates: dict[str, MarketLifecycle]
) -> dict[str, MarketLifecycle]:
    return {**lifecycles, **updates}


def assert_legal_one_step(
    lifecycles: dict[str, MarketLifecycle], updates: dict[str, MarketLifecycle]
) -> None:
    for market_id, target in updates.items():
        source = lifecycles[market_id]
        assert target in _LIFECYCLE_NEXT[source], f"illegal transition {source} -> {target}"
        if target is MarketLifecycle.ACTIVE:
            assert source is MarketLifecycle.SNAPSHOT_READY
        else:
            assert _PRE_ACTIVE_RANK[target] == _PRE_ACTIVE_RANK[source] + 1, (
                f"not exactly one stage: {source} -> {target}"
            )
        assert target is not MarketLifecycle.DISABLED


def test_launch_mode_is_exactly_all_pre_active() -> None:
    """Initial-Launch convergence mode is 'every non-terminal member
    PRE_ACTIVE and no ACTIVE member' — never merely ACTIVE_COUNT == 0."""
    for lifecycles in ALL_CONFIGURATIONS:
        updates = reconcile(lifecycles)
        assert_legal_one_step(lifecycles, updates)
        successor = apply_updates(lifecycles, updates)
        active = sum(
            1 for state in successor.values() if state is MarketLifecycle.ACTIVE
        )
        assert active in (0, N), f"partial ACTIVE successor: {successor}"


def test_exhaustive_no_partial_active_and_single_min_stage_group() -> None:
    """For every configuration x failure x snapshot_ready x history currency,
    the planner only advances the minimum PRE_ACTIVE stage, one legal step,
    and never produces a 1..N-1 ACTIVE successor."""
    failed_choices = (frozenset(), frozenset({MARKET_IDS[0]}), frozenset({MARKET_IDS[1]}))
    history_choices = (
        frozenset(MARKET_IDS),
        frozenset({MARKET_IDS[0]}),
        frozenset(),
    )
    for lifecycles in ALL_CONFIGURATIONS:
        for failed in failed_choices:
            for snapshot_ready in (True, False):
                for history_current in history_choices:
                    updates = reconcile(
                        lifecycles,
                        failed=failed,
                        history_current=history_current,
                        snapshot_ready=snapshot_ready,
                    )
                    if failed:
                        # A failed launch member holds the entire cohort.
                        assert updates == {}, (lifecycles, failed, updates)
                        continue
                    assert_legal_one_step(lifecycles, updates)
                    minimum = min(
                        _PRE_ACTIVE_RANK[state] for state in lifecycles.values()
                    )
                    for market_id, target in updates.items():
                        source = lifecycles[market_id]
                        # Only markets at the minimum stage advance; markets
                        # already ahead must remain unchanged.
                        assert _PRE_ACTIVE_RANK[source] == minimum, (
                            lifecycles,
                            market_id,
                            target,
                        )
                    successor = apply_updates(lifecycles, updates)
                    active = sum(
                        1
                        for state in successor.values()
                        if state is MarketLifecycle.ACTIVE
                    )
                    assert active in (0, N), (lifecycles, updates, successor)
                    # Snapshot readiness gates every post-WARMING stage.
                    if not snapshot_ready:
                        assert all(
                            target is MarketLifecycle.HISTORY_READY
                            for target in updates.values()
                        )
                    # A WARMING group advances only with unanimous current
                    # authoritative history.
                    warming = [
                        market_id
                        for market_id, state in lifecycles.items()
                        if state is MarketLifecycle.WARMING
                    ]
                    if warming and not set(warming) <= history_current:
                        assert updates == {}


def test_examples_from_final_invariant_spec() -> None:
    """19 SNAPSHOT_READY + 1 HISTORY_READY must become 20 SNAPSHOT_READY
    before 20 ACTIVE — never 19 ACTIVE + 1 SNAPSHOT_READY."""
    ids = tuple(f"m{index}" for index in range(20))
    mixed = dict.fromkeys(ids, MarketLifecycle.SNAPSHOT_READY)
    mixed[ids[7]] = MarketLifecycle.HISTORY_READY
    updates = reconcile(mixed)
    assert updates == {ids[7]: MarketLifecycle.SNAPSHOT_READY}
    coherent = apply_updates(mixed, updates)
    assert set(coherent.values()) == {MarketLifecycle.SNAPSHOT_READY}
    assert reconcile(coherent) == dict.fromkeys(ids, MarketLifecycle.ACTIVE)

    # 5 WARMING / 7 HISTORY_READY / 8 SNAPSHOT_READY converges monotonically
    # through 12 HISTORY_READY / 8 SNAPSHOT_READY and 20 SNAPSHOT_READY to
    # 20 ACTIVE.
    staged = dict.fromkeys(ids, MarketLifecycle.WARMING)
    for index in range(5, 12):
        staged[ids[index]] = MarketLifecycle.HISTORY_READY
    for index in range(12, 20):
        staged[ids[index]] = MarketLifecycle.SNAPSHOT_READY
    seen: list[dict[str, MarketLifecycle]] = []
    current = staged
    for _ in range(4):
        seen.append(current)
        current = apply_updates(current, reconcile(current))
        active = sum(1 for s in current.values() if s is MarketLifecycle.ACTIVE)
        assert active in (0, 20)
    assert set(current.values()) == {MarketLifecycle.ACTIVE}
    assert set(seen[1].values()) == {MarketLifecycle.HISTORY_READY, MarketLifecycle.SNAPSHOT_READY}
    assert set(seen[2].values()) == {MarketLifecycle.SNAPSHOT_READY}


def test_repeated_reconciliation_converges_monotonically_to_all_active() -> None:
    """From every one of the 27 configurations, with eventually-healthy
    prerequisites, repeated reconciliation reaches all ACTIVE with no
    regression, and activation is always the whole cohort at once."""
    for lifecycles in ALL_CONFIGURATIONS:
        current = lifecycles
        for _ in range(2 * N):
            updates = reconcile(current)
            if not updates:
                break
            successor = apply_updates(current, updates)
            for market_id in MARKET_IDS:
                before = _PRE_ACTIVE_RANK.get(current[market_id])
                after = _PRE_ACTIVE_RANK.get(successor[market_id])
                if before is not None and after is not None:
                    assert after >= before, (current, successor, market_id)
            active = sum(
                1 for state in successor.values() if state is MarketLifecycle.ACTIVE
            )
            assert active in (0, N), (current, updates, successor)
            current = successor
        assert set(current.values()) == {MarketLifecycle.ACTIVE}, current


def test_draining_never_reclassified_as_first_launch() -> None:
    """Zero ACTIVE alone must not re-enter First-Launch semantics: a post-live
    cohort containing DRAINING uses hot-add rules, where a failed member does
    NOT hold healthy peers."""
    post_live = {
        MARKET_IDS[0]: MarketLifecycle.DRAINING,
        MARKET_IDS[1]: MarketLifecycle.WARMING,
        MARKET_IDS[2]: MarketLifecycle.WARMING,
    }
    updates = reconcile(
        post_live,
        failed=frozenset({MARKET_IDS[1]}),
        history_current=frozenset({MARKET_IDS[1], MARKET_IDS[2]}),
    )
    # The healthy WARMING hot-add advances despite its failed peer; the
    # failed peer and the DRAINING member do not move.
    assert updates == {MARKET_IDS[2]: MarketLifecycle.HISTORY_READY}

    # Control: the same shape without DRAINING IS First Launch and the failed
    # member holds the whole cohort.
    launch = {
        MARKET_IDS[0]: MarketLifecycle.SNAPSHOT_READY,
        MARKET_IDS[1]: MarketLifecycle.WARMING,
        MARKET_IDS[2]: MarketLifecycle.WARMING,
    }
    assert reconcile(launch, failed=frozenset({MARKET_IDS[1]})) == {}


def test_active_cohort_keeps_hot_add_independence() -> None:
    """Post-launch, healthy hot-adds progress independently and a failed
    hot-add never pauses them or regresses the ACTIVE cohort."""
    live = {
        MARKET_IDS[0]: MarketLifecycle.ACTIVE,
        MARKET_IDS[1]: MarketLifecycle.WARMING,
        MARKET_IDS[2]: MarketLifecycle.SNAPSHOT_READY,
    }
    updates = reconcile(live, failed=frozenset({MARKET_IDS[2]}))
    assert updates == {MARKET_IDS[1]: MarketLifecycle.HISTORY_READY}
    assert MARKET_IDS[0] not in updates
    assert MARKET_IDS[2] not in updates


def test_empty_cohort_is_no_update() -> None:
    assert reconcile({}) == {}
