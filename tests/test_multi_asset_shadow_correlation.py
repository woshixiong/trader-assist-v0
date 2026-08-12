from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from math import sqrt

import pytest

from trader_assist_v0.multi_asset_shadow.correlation_engine import (
    MIN_PAIRED_RETURNS,
    PRIMARY_THRESHOLD,
    CloseObservation,
    CorrelationStatus,
    ShadowSignal,
    build_correlation_report,
    pearson_correlation,
)

EVENT = datetime(2026, 2, 1, tzinfo=UTC)
STEP_MS = 300_000


def _returns(kind: str, count: int) -> tuple[Decimal, ...]:
    scale = Decimal("0.001")
    orthogonal_x = (Decimal(1), Decimal(-1), Decimal(0), Decimal(0))
    orthogonal_y = (Decimal(0), Decimal(0), Decimal(1), Decimal(-1))
    coefficient = Decimal("0.85")
    residual = Decimal(str(sqrt(1 - 0.85**2)))
    result: list[Decimal] = []
    for index in range(count):
        x = orthogonal_x[index % len(orthogonal_x)]
        y = orthogonal_y[index % len(orthogonal_y)]
        if kind == "a":
            value = x
        elif kind == "b":
            value = coefficient * x + residual * y
        elif kind == "c":
            value = coefficient * x - residual * y
        elif kind == "anti":
            value = -x
        else:
            raise AssertionError(f"unknown deterministic return kind {kind}")
        result.append(value * scale)
    return tuple(result)


def _observations(
    market_id: str,
    kind: str,
    *,
    count: int = 600,
    end: datetime = EVENT,
    closed: set[int] | None = None,
) -> tuple[CloseObservation, ...]:
    price = Decimal("100")
    end_ms = int(end.timestamp() * 1000) - 1
    values = _returns(kind, count)
    observations = [
        CloseObservation(
            market_id=market_id,
            close_time_ms=end_ms - count * STEP_MS,
            close=price,
            is_open_market=True,
            source_candle_hash=f"{market_id[0]}0" * 32,
        )
    ]
    for index, value in enumerate(values, start=1):
        price *= Decimal(1) + value
        observations.append(
            CloseObservation(
                market_id=market_id,
                close_time_ms=end_ms - (count - index) * STEP_MS,
                close=price,
                is_open_market=closed is None or index in closed,
                source_candle_hash=(f"{market_id[0]}{index % 10}") * 32,
            )
        )
    return tuple(observations)


def _signal(
    shadow_order_id: str,
    market_id: str,
    *,
    setup: str = "SWEEP_RECLAIM",
    direction: str = "LONG",
    confirmed_at: datetime = EVENT,
    depth: str = "100",
    spread: str = "2",
    day_notional: str = "1000",
    oi: str = "500",
    outcome_r: str | None = "1",
    outcome_mfe: str | None = None,
    outcome_mae: str | None = None,
) -> ShadowSignal:
    return ShadowSignal(
        shadow_order_id=shadow_order_id,
        market_id=market_id,
        setup_family=setup,
        direction=direction,
        confirmed_at=confirmed_at,
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
        p10_weak_depth_10bps=Decimal(depth),
        p95_spread_bps=Decimal(spread),
        exchange_day_notional=Decimal(day_notional),
        oi_notional=Decimal(oi),
        outcome_r=None if outcome_r is None else Decimal(outcome_r),
        outcome_mfe=None if outcome_mfe is None else Decimal(outcome_mfe),
        outcome_mae=None if outcome_mae is None else Decimal(outcome_mae),
    )


def _history(*market_kinds: tuple[str, str]) -> dict[str, tuple[CloseObservation, ...]]:
    return {market_id: _observations(market_id, kind) for market_id, kind in market_kinds}


def test_pearson_is_exact_for_linear_inputs_and_rejects_zero_variance() -> None:
    assert pearson_correlation((Decimal(1), Decimal(2)), (Decimal(3), Decimal(5))) == Decimal(1)
    assert pearson_correlation((Decimal(1), Decimal(2)), (Decimal(5), Decimal(3))) == Decimal(-1)
    assert pearson_correlation((Decimal(1), Decimal(1)), (Decimal(3), Decimal(5))) is None
    with pytest.raises(ValueError, match="equally sized"):
        pearson_correlation((Decimal(1),), ())


def test_minimum_paired_return_count_and_missing_open_sessions_fail_closed() -> None:
    enough = {
        "a": _observations("a", "a", count=MIN_PAIRED_RETURNS),
        "b": _observations("b", "b", count=MIN_PAIRED_RETURNS),
    }
    computed = build_correlation_report((_signal("one", "a"), _signal("two", "b")), enough)
    assert computed.pairwise_correlations[0].paired_return_count == MIN_PAIRED_RETURNS
    assert computed.pairwise_correlations[0].status is CorrelationStatus.COMPUTED

    too_short = {
        "a": _observations("a", "a", count=MIN_PAIRED_RETURNS - 1),
        "b": _observations("b", "b", count=MIN_PAIRED_RETURNS - 1),
    }
    insufficient = build_correlation_report((_signal("one", "a"), _signal("two", "b")), too_short)
    assert insufficient.pairwise_correlations[0].status is CorrelationStatus.INSUFFICIENT_DATA
    assert insufficient.correlation_unknown_count == 2
    assert all(cluster.correlation_unknown for cluster in insufficient.exposure_clusters)

    sessions = {
        "a": _observations("a", "a"),
        "b": _observations("b", "b", closed={index for index in range(1, 601) if index % 2}),
    }
    missing_sessions = build_correlation_report(
        (_signal("one", "a"), _signal("two", "b")), sessions
    )
    assert missing_sessions.pairwise_correlations[0].paired_return_count < MIN_PAIRED_RETURNS
    assert missing_sessions.pairwise_correlations[0].status is CorrelationStatus.INSUFFICIENT_DATA


def test_fourteen_day_cut_excludes_older_returns() -> None:
    old_end = EVENT - timedelta(days=14, minutes=5)
    history = {
        "a": _observations("a", "a", end=EVENT) + _observations("a", "a", end=old_end),
        "b": _observations("b", "b", end=EVENT) + _observations("b", "anti", end=old_end),
    }
    report = build_correlation_report((_signal("one", "a"), _signal("two", "b")), history)
    pair = report.pairwise_correlations[0]
    assert pair.paired_return_count == 600
    assert pair.window_start == EVENT - timedelta(days=14)
    assert pair.window_end == EVENT
    assert pair.pearson is not None and pair.pearson > PRIMARY_THRESHOLD


@pytest.mark.parametrize(
    ("market_id", "observation_index", "evidence_field"),
    (
        ("a", 0, "left_previous_candle_hash"),
        ("a", 1, "left_current_candle_hash"),
        ("b", 0, "right_previous_candle_hash"),
        ("b", 1, "right_current_candle_hash"),
    ),
)
def test_correlation_data_hash_binds_all_four_return_candle_hash_positions(
    market_id: str, observation_index: int, evidence_field: str
) -> None:
    signals = (_signal("one", "a"), _signal("two", "b"))
    history = _history(("a", "a"), ("b", "b"))
    baseline = build_correlation_report(signals, history).pairwise_correlations[0]
    changed_market = list(history[market_id])
    changed_market[observation_index] = replace(
        changed_market[observation_index], source_candle_hash="f" * 64
    )
    attacked_history = dict(history)
    attacked_history[market_id] = tuple(changed_market)
    attacked = build_correlation_report(signals, attacked_history).pairwise_correlations[0]

    assert baseline.pearson == attacked.pearson
    assert baseline.paired_return_count == attacked.paired_return_count
    assert baseline.correlation_data_hash != attacked.correlation_data_hash
    assert getattr(attacked.paired_return_evidence[0], evidence_field) == "f" * 64


def test_primary_and_sensitivity_thresholds_use_the_same_engine() -> None:
    report = build_correlation_report(
        (_signal("one", "a"), _signal("two", "b")), _history(("a", "a"), ("b", "b"))
    )
    sensitivity = {item.threshold: item for item in report.sensitivity}
    assert tuple(sensitivity) == (Decimal("0.70"), Decimal("0.80"), Decimal("0.90"))
    assert len(sensitivity[Decimal("0.70")].exposure_clusters) == 1
    assert len(sensitivity[Decimal("0.80")].exposure_clusters) == 1
    assert len(sensitivity[Decimal("0.90")].exposure_clusters) == 2


def test_complete_linkage_rejects_pairwise_chain_trap() -> None:
    signals = (
        _signal("a", "a", depth="300"),
        _signal("b", "b", depth="200"),
        _signal("c", "c", depth="100"),
    )
    report = build_correlation_report(signals, _history(("a", "a"), ("b", "b"), ("c", "c")))
    members = [
        tuple(item.market_id for item in cluster.members)
        for cluster in report.exposure_clusters
    ]
    assert members == [("a", "b"), ("c",)]
    values = {pair.market_ids: pair.pearson for pair in report.pairwise_correlations}
    assert values[("a", "b")] is not None and values[("a", "b")] >= PRIMARY_THRESHOLD
    assert values[("a", "c")] is not None and values[("a", "c")] >= PRIMARY_THRESHOLD
    assert values[("b", "c")] is not None and values[("b", "c")] < PRIMARY_THRESHOLD


def test_fixed_fifteen_minute_event_window_includes_boundary_only() -> None:
    signals = (
        _signal("a", "a", confirmed_at=EVENT),
        _signal("b", "b", confirmed_at=EVENT + timedelta(minutes=15)),
        _signal("c", "c", confirmed_at=EVENT + timedelta(minutes=15, microseconds=1)),
    )
    report = build_correlation_report(signals, _history(("a", "a"), ("b", "b"), ("c", "c")))
    assert [len(cluster.members) for cluster in report.exposure_clusters] == [2, 1]
    assert report.exposure_clusters[0].event_start == EVENT
    assert report.exposure_clusters[1].event_start == EVENT + timedelta(minutes=15, microseconds=1)


def test_setup_and_cross_setup_exposure_clusters_are_distinct_views() -> None:
    report = build_correlation_report(
        (
            _signal("a", "a", setup="SWEEP_RECLAIM"),
            _signal("b", "b", setup="BREAKOUT_RETEST"),
        ),
        _history(("a", "a"), ("b", "b")),
    )
    assert report.setup_research_cluster_count == 2
    assert report.exposure_cluster_count == 1
    assert report.exposure_clusters[0].setup_family is None


def test_opposite_directions_never_exposure_cluster() -> None:
    report = build_correlation_report(
        (_signal("a", "a", direction="LONG"), _signal("b", "b", direction="SHORT")),
        _history(("a", "a"), ("b", "b")),
    )
    assert report.exposure_cluster_count == 2
    assert all(len(cluster.members) == 1 for cluster in report.exposure_clusters)


def test_deterministic_leader_market_id_fallback_and_report_counts() -> None:
    signals = (
        _signal("z-order", "z", outcome_r="3"),
        _signal("a-order", "a", outcome_r="1"),
        _signal("b-order", "b", outcome_r="2"),
    )
    report = build_correlation_report(signals, _history(("z", "a"), ("a", "a"), ("b", "b")))
    assert report.raw_market_level.raw_shadow_order_count == 3
    assert report.exposure_cluster_count == 1
    assert report.cluster_normalized.cluster_count == 1
    assert report.leader_only.leader_only_count == 1
    assert report.leader_only.leaders[0].market_id == "a"
    assert {member.member_weight for member in report.cluster_normalized.members} == {
        Fraction(1, 3)
    }
    assert sum(
        (member.member_weight for member in report.cluster_normalized.members), Fraction()
    ) == Fraction(1)
    assert all(
        member.raw_market_evidence.shadow_order_id == member.shadow_order_id
        for member in report.cluster_normalized.members
    )
    assert report.cluster_compression_ratio == Decimal(1) / Decimal(3)


def test_cluster_metrics_are_deterministic_and_missing_outcomes_remain_unavailable() -> None:
    signals = (
        _signal("a", "a", outcome_r="2", outcome_mfe="3", outcome_mae="-0.5"),
        _signal("b", "b", outcome_r="-1", outcome_mfe="0.5", outcome_mae="-2"),
        _signal("c", "c", outcome_r=None, outcome_mfe=None, outcome_mae=None),
    )
    report = build_correlation_report(
        signals, _history(("a", "a"), ("b", "b"), ("c", "a"))
    )
    metrics = report.exposure_clusters[0].research_metrics
    assert metrics.mean_r == Decimal("0.5")
    assert metrics.median_r == Decimal("0.5")
    assert metrics.best_r == Decimal("2")
    assert metrics.worst_r == Decimal("-1")
    assert metrics.mean_mfe == Decimal("1.75")
    assert metrics.mean_mae == Decimal("-1.25")
    assert metrics.member_count == 3
    assert metrics.win_loss_dispersion is not None
    assert metrics.win_loss_dispersion.win_count == 1
    assert metrics.win_loss_dispersion.loss_count == 1
    assert metrics.win_loss_dispersion.breakeven_count == 0
    assert metrics.win_loss_dispersion.unavailable_count == 1

    unavailable = build_correlation_report(
        (_signal("a", "a", outcome_r=None), _signal("b", "b", outcome_r=None)),
        _history(("a", "a"), ("b", "b")),
    ).exposure_clusters[0].research_metrics
    assert unavailable.mean_r is None
    assert unavailable.median_r is None
    assert unavailable.best_r is None
    assert unavailable.worst_r is None
    assert unavailable.mean_mfe is None
    assert unavailable.mean_mae is None
    assert unavailable.win_loss_dispersion is None


def test_three_research_performance_views_have_r_equity_and_drawdown() -> None:
    two_thirds = Decimal(2) / Decimal(3)
    negative_third = Decimal(-1) / Decimal(3)
    normalized_total = two_thirds + negative_third
    report = build_correlation_report(
        (
            _signal("a", "a", outcome_r="2"),
            _signal("b", "b", outcome_r="-1"),
            _signal("c", "c", outcome_r=None),
        ),
        _history(("a", "a"), ("b", "b"), ("c", "a")),
    )
    raw = report.raw_market_level
    assert raw.ordered_r_observations == (Decimal(2), Decimal(-1))
    assert raw.cumulative_r_equity_curve == (Decimal(2), Decimal(1))
    assert raw.r_space_drawdown == (Decimal(0), Decimal(1))

    normalized = report.cluster_normalized
    assert normalized.ordered_r_observations == (two_thirds, negative_third)
    assert normalized.cumulative_r_equity_curve == (two_thirds, normalized_total)
    assert normalized.r_space_drawdown == (
        Decimal(0),
        two_thirds - normalized_total,
    )
    assert normalized.members[2].weighted_outcome_r is None

    leader = report.leader_only
    assert leader.ordered_r_observations == (Decimal(2),)
    assert leader.cumulative_r_equity_curve == (Decimal(2),)
    assert leader.r_space_drawdown == (Decimal(0),)


def test_leader_uses_exact_five_field_order() -> None:
    signals = (
        _signal("depth-loses", "b", depth="99", spread="1", day_notional="9999", oi="9999"),
        _signal("spread-loses", "c", depth="100", spread="3", day_notional="9999", oi="9999"),
        _signal("notional-loses", "d", depth="100", spread="2", day_notional="999", oi="9999"),
        _signal("oi-loses", "e", depth="100", spread="2", day_notional="1000", oi="499"),
        _signal("lexical-loses", "z", depth="100", spread="2", day_notional="1000", oi="500"),
        _signal("winner", "a", depth="100", spread="2", day_notional="1000", oi="500"),
    )
    report = build_correlation_report(
        signals,
        _history(
            ("a", "a"),
            ("b", "a"),
            ("c", "a"),
            ("d", "a"),
            ("e", "a"),
            ("z", "a"),
        ),
    )
    assert report.leader_only.leaders[0].shadow_order_id == "winner"


def test_report_is_order_invariant() -> None:
    signals = (
        _signal("a", "a", depth="300"),
        _signal("b", "b", depth="200"),
        _signal("c", "c", depth="100"),
    )
    history = _history(("a", "a"), ("b", "b"), ("c", "c"))
    forward = build_correlation_report(signals, history)
    reversed_report = build_correlation_report(
        tuple(reversed(signals)), dict(reversed(tuple(history.items())))
    )
    assert forward == reversed_report
