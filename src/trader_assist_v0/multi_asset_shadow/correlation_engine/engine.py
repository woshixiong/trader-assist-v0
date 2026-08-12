"""One causal, complete-linkage correlation engine for Shadow research.

This module is deliberately a pure transform.  It accepts caller-supplied
closed 5m observations and Shadow signals, performs no I/O, and owns no
execution, account, credential, or exchange-write capability.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, pairwise

CORRELATION_LOOKBACK = timedelta(days=14)
CORRELATION_EVENT_WINDOW = timedelta(minutes=15)
MIN_PAIRED_RETURNS = 500
PRIMARY_THRESHOLD = Decimal("0.80")
SENSITIVITY_THRESHOLDS = (Decimal("0.70"), PRIMARY_THRESHOLD, Decimal("0.90"))
_FIVE_MINUTES_MS = 300_000


class CorrelationEngineError(ValueError):
    """Raised for invalid or non-causal correlation inputs."""


class CorrelationStatus(StrEnum):
    COMPUTED = "COMPUTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNDEFINED = "UNDEFINED"


class ClusterKind(StrEnum):
    SETUP_RESEARCH = "SETUP_RESEARCH_CLUSTER"
    EXPOSURE = "EXPOSURE_CLUSTER"


@dataclass(frozen=True)
class CloseObservation:
    """One caller-validated, closed 5m candle suitable for research.

    ``is_open_market`` is explicit so an off-session or maintenance candle
    cannot accidentally become paired evidence for a non-24/7 market.
    """

    market_id: str
    close_time_ms: int
    close: Decimal
    is_open_market: bool
    source_candle_hash: str

    def __post_init__(self) -> None:
        if not self.market_id or self.close_time_ms < 0:
            raise CorrelationEngineError("closed observation identity is invalid")
        if self.close_time_ms % _FIVE_MINUTES_MS != _FIVE_MINUTES_MS - 1:
            raise CorrelationEngineError("observation must have exact closed 5m geometry")
        if not self.close.is_finite() or self.close <= 0:
            raise CorrelationEngineError("close must be positive and finite")
        if len(self.source_candle_hash) != 64:
            raise CorrelationEngineError("source candle hash is invalid")


@dataclass(frozen=True)
class ShadowSignal:
    """The authorized research fields needed for deterministic clustering."""

    shadow_order_id: str
    market_id: str
    setup_family: str
    direction: str
    confirmed_at: datetime
    strategy_version: str
    parameter_version: str
    p10_weak_depth_10bps: Decimal
    p95_spread_bps: Decimal
    exchange_day_notional: Decimal
    oi_notional: Decimal
    outcome_r: Decimal | None = None
    outcome_mfe: Decimal | None = None
    outcome_mae: Decimal | None = None

    def __post_init__(self) -> None:
        if not all(
            (
                self.shadow_order_id,
                self.market_id,
                self.setup_family,
                self.direction,
                self.strategy_version,
                self.parameter_version,
            )
        ):
            raise CorrelationEngineError("signal identity is incomplete")
        if self.confirmed_at.tzinfo is None:
            raise CorrelationEngineError("confirmed_at must be timezone-aware")
        values = (
            self.p10_weak_depth_10bps,
            self.p95_spread_bps,
            self.exchange_day_notional,
            self.oi_notional,
        )
        if any(not value.is_finite() or value < 0 for value in values):
            raise CorrelationEngineError("leader ordering fields must be finite and non-negative")
        outcomes = (self.outcome_r, self.outcome_mfe, self.outcome_mae)
        if any(value is not None and not value.is_finite() for value in outcomes):
            raise CorrelationEngineError("outcome research fields must be finite when present")

    @property
    def confirmed_at_utc(self) -> datetime:
        return self.confirmed_at.astimezone(UTC)


@dataclass(frozen=True)
class PairedReturnEvidence:
    left_previous_candle_hash: str
    left_current_candle_hash: str
    right_previous_candle_hash: str
    right_current_candle_hash: str


@dataclass(frozen=True)
class PairwiseCorrelation:
    market_ids: tuple[str, str]
    window_start: datetime
    window_end: datetime
    paired_return_count: int
    status: CorrelationStatus
    pearson: Decimal | None
    paired_return_evidence: tuple[PairedReturnEvidence, ...]
    correlation_data_hash: str


@dataclass(frozen=True)
class WinLossDispersion:
    win_count: int
    loss_count: int
    breakeven_count: int
    unavailable_count: int


@dataclass(frozen=True)
class ClusterResearchMetrics:
    mean_r: Decimal | None
    median_r: Decimal | None
    best_r: Decimal | None
    worst_r: Decimal | None
    mean_mfe: Decimal | None
    mean_mae: Decimal | None
    member_count: int
    win_loss_dispersion: WinLossDispersion | None


@dataclass(frozen=True)
class Cluster:
    cluster_id: str
    kind: ClusterKind
    threshold: Decimal
    strategy_version: str
    parameter_version: str
    setup_family: str | None
    direction: str
    event_start: datetime
    members: tuple[ShadowSignal, ...]
    leader: ShadowSignal
    correlation_unknown: bool
    research_metrics: ClusterResearchMetrics


@dataclass(frozen=True)
class RawMarketLevelReport:
    signals: tuple[ShadowSignal, ...]
    ordered_r_observations: tuple[Decimal, ...]
    cumulative_r_equity_curve: tuple[Decimal, ...]
    r_space_drawdown: tuple[Decimal, ...]

    @property
    def raw_shadow_order_count(self) -> int:
        return len(self.signals)


@dataclass(frozen=True)
class ClusterNormalizedMember:
    cluster_id: str
    shadow_order_id: str
    member_weight: Fraction
    weighted_outcome_r: Decimal | None
    raw_market_evidence: ShadowSignal


@dataclass(frozen=True)
class ClusterNormalizedReport:
    members: tuple[ClusterNormalizedMember, ...]
    cluster_count: int
    ordered_r_observations: tuple[Decimal, ...]
    cumulative_r_equity_curve: tuple[Decimal, ...]
    r_space_drawdown: tuple[Decimal, ...]


@dataclass(frozen=True)
class LeaderOnlyReport:
    leaders: tuple[ShadowSignal, ...]
    ordered_r_observations: tuple[Decimal, ...]
    cumulative_r_equity_curve: tuple[Decimal, ...]
    r_space_drawdown: tuple[Decimal, ...]

    @property
    def leader_only_count(self) -> int:
        return len(self.leaders)


@dataclass(frozen=True)
class SensitivityReport:
    threshold: Decimal
    setup_research_clusters: tuple[Cluster, ...]
    exposure_clusters: tuple[Cluster, ...]


@dataclass(frozen=True)
class CorrelationReport:
    raw_market_level: RawMarketLevelReport
    setup_research_clusters: tuple[Cluster, ...]
    exposure_clusters: tuple[Cluster, ...]
    cluster_normalized: ClusterNormalizedReport
    leader_only: LeaderOnlyReport
    pairwise_correlations: tuple[PairwiseCorrelation, ...]
    sensitivity: tuple[SensitivityReport, ...]
    correlation_unknown_count: int

    @property
    def setup_research_cluster_count(self) -> int:
        return len(self.setup_research_clusters)

    @property
    def exposure_cluster_count(self) -> int:
        return len(self.exposure_clusters)

    @property
    def cluster_compression_ratio(self) -> Decimal | None:
        raw_count = self.raw_market_level.raw_shadow_order_count
        if raw_count == 0:
            return None
        return Decimal(self.exposure_cluster_count) / Decimal(raw_count)


@dataclass(frozen=True)
class _Return:
    close_time_ms: int
    value: Decimal
    previous_candle_hash: str
    current_candle_hash: str


def _leader_key(signal: ShadowSignal) -> tuple[Decimal, Decimal, Decimal, Decimal, str]:
    """The exact frozen five-field leader ordering."""
    return (
        -signal.p10_weak_depth_10bps,
        signal.p95_spread_bps,
        -signal.exchange_day_notional,
        -signal.oi_notional,
        signal.market_id,
    )


def _signal_time_key(
    signal: ShadowSignal,
) -> tuple[datetime, tuple[Decimal, Decimal, Decimal, Decimal, str], str]:
    return signal.confirmed_at_utc, _leader_key(signal), signal.shadow_order_id


def _validate_signals(signals: Sequence[ShadowSignal]) -> tuple[ShadowSignal, ...]:
    ids = [signal.shadow_order_id for signal in signals]
    if len(ids) != len(set(ids)):
        raise CorrelationEngineError("shadow_order_id must be unique")
    return tuple(sorted(signals, key=_signal_time_key))


def _market_returns(observations: Sequence[CloseObservation]) -> tuple[_Return, ...]:
    ordered = tuple(sorted(observations, key=lambda item: item.close_time_ms))
    times = [item.close_time_ms for item in ordered]
    if len(times) != len(set(times)):
        raise CorrelationEngineError("market observations contain duplicate close times")
    returns: list[_Return] = []
    for prior, current in pairwise(ordered):
        if (
            prior.is_open_market
            and current.is_open_market
            and current.close_time_ms - prior.close_time_ms == _FIVE_MINUTES_MS
        ):
            returns.append(
                _Return(
                    close_time_ms=current.close_time_ms,
                    value=current.close / prior.close - Decimal(1),
                    previous_candle_hash=prior.source_candle_hash,
                    current_candle_hash=current.source_candle_hash,
                )
            )
    return tuple(returns)


def pearson_correlation(left: Sequence[Decimal], right: Sequence[Decimal]) -> Decimal | None:
    """Return Pearson's r, or ``None`` when a variance is zero."""
    if len(left) != len(right) or not left:
        raise CorrelationEngineError("Pearson inputs must be non-empty and equally sized")
    left_mean = sum(left, Decimal()) / Decimal(len(left))
    right_mean = sum(right, Decimal()) / Decimal(len(right))
    left_deltas = tuple(value - left_mean for value in left)
    right_deltas = tuple(value - right_mean for value in right)
    numerator = sum((a * b for a, b in zip(left_deltas, right_deltas, strict=True)), Decimal())
    left_variance = sum((value * value for value in left_deltas), Decimal())
    right_variance = sum((value * value for value in right_deltas), Decimal())
    denominator = (left_variance * right_variance).sqrt()
    if denominator == 0:
        return None
    return numerator / denominator


def _correlation_data_hash(
    market_ids: tuple[str, str], pairs: Sequence[tuple[_Return, _Return]]
) -> str:
    payload = "".join(
        (
            f"{left.close_time_ms}|{left.previous_candle_hash}|{left.current_candle_hash}|"
            f"{right.previous_candle_hash}|{right.current_candle_hash};"
        )
        for left, right in pairs
    )
    return sha256(("|".join(market_ids) + "|" + payload).encode("utf-8")).hexdigest()


def _market_pair_ids(first_market_id: str, second_market_id: str) -> tuple[str, str]:
    if first_market_id <= second_market_id:
        return first_market_id, second_market_id
    return second_market_id, first_market_id


def _pairwise_correlation(
    *,
    first_market_id: str,
    second_market_id: str,
    returns_by_market: Mapping[str, tuple[_Return, ...]],
    event_start: datetime,
) -> PairwiseCorrelation:
    market_ids = _market_pair_ids(first_market_id, second_market_id)
    if market_ids[0] not in returns_by_market or market_ids[1] not in returns_by_market:
        raise CorrelationEngineError("every signal market requires supplied closed observations")
    lower_ms = int((event_start - CORRELATION_LOOKBACK).timestamp() * 1000)
    upper_ms = int(event_start.timestamp() * 1000)
    left = {
        item.close_time_ms: item
        for item in returns_by_market[market_ids[0]]
        if lower_ms <= item.close_time_ms <= upper_ms
    }
    right = {
        item.close_time_ms: item
        for item in returns_by_market[market_ids[1]]
        if lower_ms <= item.close_time_ms <= upper_ms
    }
    pairs = tuple((left[time], right[time]) for time in sorted(set(left) & set(right)))
    evidence = tuple(
        PairedReturnEvidence(
            left_previous_candle_hash=left.previous_candle_hash,
            left_current_candle_hash=left.current_candle_hash,
            right_previous_candle_hash=right.previous_candle_hash,
            right_current_candle_hash=right.current_candle_hash,
        )
        for left, right in pairs
    )
    status = CorrelationStatus.COMPUTED
    value: Decimal | None = None
    if len(pairs) < MIN_PAIRED_RETURNS:
        status = CorrelationStatus.INSUFFICIENT_DATA
    else:
        value = pearson_correlation(
            tuple(item[0].value for item in pairs), tuple(item[1].value for item in pairs)
        )
        if value is None:
            status = CorrelationStatus.UNDEFINED
    return PairwiseCorrelation(
        market_ids=market_ids,
        window_start=event_start - CORRELATION_LOOKBACK,
        window_end=event_start,
        paired_return_count=len(pairs),
        status=status,
        pearson=value,
        paired_return_evidence=evidence,
        correlation_data_hash=_correlation_data_hash(market_ids, pairs),
    )


def _event_windows(
    signals: Sequence[ShadowSignal],
) -> tuple[tuple[datetime, tuple[ShadowSignal, ...]], ...]:
    """Fixed, non-rolling windows, independently scoped by version and direction."""
    scoped: dict[tuple[str, str, str], list[ShadowSignal]] = defaultdict(list)
    for signal in signals:
        scoped[(signal.strategy_version, signal.parameter_version, signal.direction)].append(signal)
    windows: list[tuple[datetime, tuple[ShadowSignal, ...]]] = []
    for scope_signals in scoped.values():
        ordered = sorted(scope_signals, key=_signal_time_key)
        cursor = 0
        while cursor < len(ordered):
            start = ordered[cursor].confirmed_at_utc
            stop = start + CORRELATION_EVENT_WINDOW
            members: list[ShadowSignal] = []
            while cursor < len(ordered) and ordered[cursor].confirmed_at_utc <= stop:
                members.append(ordered[cursor])
                cursor += 1
            windows.append((start, tuple(members)))
    return tuple(sorted(windows, key=lambda item: item[0]))


def _cluster_id(
    *,
    kind: ClusterKind,
    strategy_version: str,
    parameter_version: str,
    setup_family: str | None,
    direction: str,
    event_start: datetime,
    members: Sequence[ShadowSignal],
) -> str:
    # This is the frozen SHA256 concatenation.  Setup family exists only for
    # Setup Research Clusters, exactly as the governing formula specifies.
    fields = [strategy_version, parameter_version]
    if kind is ClusterKind.SETUP_RESEARCH:
        if setup_family is None:
            raise CorrelationEngineError("setup cluster requires setup family")
        fields.append(setup_family)
    fields.extend((direction, event_start.astimezone(UTC).isoformat()))
    fields.extend(sorted(item.shadow_order_id for item in members))
    return sha256("".join(fields).encode("utf-8")).hexdigest()


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal()) / Decimal(len(values))


def _median(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _cluster_research_metrics(members: Sequence[ShadowSignal]) -> ClusterResearchMetrics:
    r_values = tuple(signal.outcome_r for signal in members if signal.outcome_r is not None)
    mfe_values = tuple(signal.outcome_mfe for signal in members if signal.outcome_mfe is not None)
    mae_values = tuple(signal.outcome_mae for signal in members if signal.outcome_mae is not None)
    dispersion = None
    if r_values:
        dispersion = WinLossDispersion(
            win_count=sum(value > 0 for value in r_values),
            loss_count=sum(value < 0 for value in r_values),
            breakeven_count=sum(value == 0 for value in r_values),
            unavailable_count=len(members) - len(r_values),
        )
    return ClusterResearchMetrics(
        mean_r=_mean(r_values),
        median_r=_median(r_values),
        best_r=max(r_values) if r_values else None,
        worst_r=min(r_values) if r_values else None,
        mean_mfe=_mean(mfe_values),
        mean_mae=_mean(mae_values),
        member_count=len(members),
        win_loss_dispersion=dispersion,
    )


def _cluster_window(
    *,
    kind: ClusterKind,
    candidates: Sequence[ShadowSignal],
    event_start: datetime,
    threshold: Decimal,
    pair_lookup: Mapping[tuple[datetime, str, str], PairwiseCorrelation],
    unknown_signal_ids: set[str],
) -> tuple[Cluster, ...]:
    clusters: list[list[ShadowSignal]] = []
    for candidate in sorted(candidates, key=_leader_key):
        accepted = False
        for cluster in clusters:
            all_correlated = True
            for member in cluster:
                key = (event_start, *_market_pair_ids(candidate.market_id, member.market_id))
                result = pair_lookup[key]
                if result.status is not CorrelationStatus.COMPUTED or result.pearson is None:
                    all_correlated = False
                    break
                if result.pearson < threshold:
                    all_correlated = False
                    break
            if all_correlated:
                cluster.append(candidate)
                accepted = True
                break
        if not accepted:
            clusters.append([candidate])
    built: list[Cluster] = []
    for members in clusters:
        ordered_members = tuple(sorted(members, key=_leader_key))
        member_has_unknown_pair = any(
            signal.shadow_order_id in unknown_signal_ids for signal in ordered_members
        )
        unknown = member_has_unknown_pair or any(
            pair_lookup[(event_start, *_market_pair_ids(left.market_id, right.market_id))].status
            is not CorrelationStatus.COMPUTED
            for left, right in combinations(ordered_members, 2)
        )
        setup = ordered_members[0].setup_family if kind is ClusterKind.SETUP_RESEARCH else None
        built.append(
            Cluster(
                cluster_id=_cluster_id(
                    kind=kind,
                    strategy_version=ordered_members[0].strategy_version,
                    parameter_version=ordered_members[0].parameter_version,
                    setup_family=setup,
                    direction=ordered_members[0].direction,
                    event_start=event_start,
                    members=ordered_members,
                ),
                kind=kind,
                threshold=threshold,
                strategy_version=ordered_members[0].strategy_version,
                parameter_version=ordered_members[0].parameter_version,
                setup_family=setup,
                direction=ordered_members[0].direction,
                event_start=event_start,
                members=ordered_members,
                leader=ordered_members[0],
                correlation_unknown=unknown,
                research_metrics=_cluster_research_metrics(ordered_members),
            )
        )
    return tuple(built)


def _clusters_for_threshold(
    *,
    signals: Sequence[ShadowSignal],
    windows: Sequence[tuple[datetime, tuple[ShadowSignal, ...]]],
    threshold: Decimal,
    pair_lookup: Mapping[tuple[datetime, str, str], PairwiseCorrelation],
    unknown_signal_ids: set[str],
) -> tuple[tuple[Cluster, ...], tuple[Cluster, ...]]:
    setup_clusters: list[Cluster] = []
    exposure_clusters: list[Cluster] = []
    for event_start, event_signals in windows:
        by_setup: dict[str, list[ShadowSignal]] = defaultdict(list)
        for signal in event_signals:
            by_setup[signal.setup_family].append(signal)
        for setup_family in sorted(by_setup):
            candidates = by_setup[setup_family]
            setup_clusters.extend(
                _cluster_window(
                    kind=ClusterKind.SETUP_RESEARCH,
                    candidates=candidates,
                    event_start=event_start,
                    threshold=threshold,
                    pair_lookup=pair_lookup,
                    unknown_signal_ids=unknown_signal_ids,
                )
            )
        exposure_clusters.extend(
            _cluster_window(
                kind=ClusterKind.EXPOSURE,
                candidates=event_signals,
                event_start=event_start,
                threshold=threshold,
                pair_lookup=pair_lookup,
                unknown_signal_ids=unknown_signal_ids,
            )
        )
    del signals  # scope is explicit in the signature for auditability.
    # Cluster creation order is part of the frozen complete-linkage rule.
    # ``windows`` and all candidate orders are deterministic, so retaining it
    # also preserves order invariance without inventing a second ordering.
    return tuple(setup_clusters), tuple(exposure_clusters)


def _performance_series(
    observations: Sequence[Decimal | None],
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...], tuple[Decimal, ...]]:
    ordered = tuple(value for value in observations if value is not None)
    equity: list[Decimal] = []
    drawdown: list[Decimal] = []
    cumulative = Decimal()
    peak = Decimal()
    for value in ordered:
        cumulative += value
        peak = max(peak, cumulative)
        equity.append(cumulative)
        drawdown.append(peak - cumulative)
    return ordered, tuple(equity), tuple(drawdown)


def _raw_report(signals: Sequence[ShadowSignal]) -> RawMarketLevelReport:
    observations, equity, drawdown = _performance_series(
        tuple(signal.outcome_r for signal in signals)
    )
    return RawMarketLevelReport(tuple(signals), observations, equity, drawdown)


def _normalized_report(exposure_clusters: Sequence[Cluster]) -> ClusterNormalizedReport:
    members: list[ClusterNormalizedMember] = []
    for cluster in exposure_clusters:
        member_count = len(cluster.members)
        weight = Fraction(1, member_count)
        for signal in cluster.members:
            members.append(
                ClusterNormalizedMember(
                    cluster_id=cluster.cluster_id,
                    shadow_order_id=signal.shadow_order_id,
                    member_weight=weight,
                    weighted_outcome_r=None
                    if signal.outcome_r is None
                    else signal.outcome_r / Decimal(member_count),
                    raw_market_evidence=signal,
                )
            )
    observations, equity, drawdown = _performance_series(
        tuple(member.weighted_outcome_r for member in members)
    )
    return ClusterNormalizedReport(
        tuple(members), len(exposure_clusters), observations, equity, drawdown
    )


def _leader_report(exposure_clusters: Sequence[Cluster]) -> LeaderOnlyReport:
    leaders = tuple(cluster.leader for cluster in exposure_clusters)
    observations, equity, drawdown = _performance_series(
        tuple(leader.outcome_r for leader in leaders)
    )
    return LeaderOnlyReport(leaders, observations, equity, drawdown)


def build_correlation_report(
    signals: Sequence[ShadowSignal],
    observations_by_market: Mapping[str, Sequence[CloseObservation]],
) -> CorrelationReport:
    """Build all frozen research views with one complete-linkage algorithm.

    The primary report uses ``0.80``.  ``0.70`` and ``0.90`` are emitted only
    as sensitivity views; no alternate correlation or clustering algorithm is
    present in this module.
    """
    ordered_signals = _validate_signals(signals)
    returns_by_market: dict[str, tuple[_Return, ...]] = {}
    for market_id, observations in observations_by_market.items():
        if any(item.market_id != market_id for item in observations):
            raise CorrelationEngineError("observation mapping key must match market identity")
        returns_by_market[market_id] = _market_returns(observations)
    signal_markets = {signal.market_id for signal in ordered_signals}
    if signal_markets - returns_by_market.keys():
        raise CorrelationEngineError("every signal market requires supplied closed observations")

    windows = _event_windows(ordered_signals)
    pair_lookup: dict[tuple[datetime, str, str], PairwiseCorrelation] = {}
    unknown_ids: set[str] = set()
    for event_start, event_signals in windows:
        for left, right in combinations(event_signals, 2):
            market_ids = _market_pair_ids(left.market_id, right.market_id)
            key = (event_start, *market_ids)
            if key not in pair_lookup:
                pair_lookup[key] = _pairwise_correlation(
                    first_market_id=market_ids[0],
                    second_market_id=market_ids[1],
                    returns_by_market=returns_by_market,
                    event_start=event_start,
                )
            if pair_lookup[key].status is not CorrelationStatus.COMPUTED:
                unknown_ids.update((left.shadow_order_id, right.shadow_order_id))

    sensitivity: list[SensitivityReport] = []
    primary_setup: tuple[Cluster, ...] = ()
    primary_exposure: tuple[Cluster, ...] = ()
    for threshold in SENSITIVITY_THRESHOLDS:
        setup, exposure = _clusters_for_threshold(
            signals=ordered_signals,
            windows=windows,
            threshold=threshold,
            pair_lookup=pair_lookup,
            unknown_signal_ids=unknown_ids,
        )
        sensitivity.append(SensitivityReport(threshold, setup, exposure))
        if threshold == PRIMARY_THRESHOLD:
            primary_setup, primary_exposure = setup, exposure

    return CorrelationReport(
        raw_market_level=_raw_report(ordered_signals),
        setup_research_clusters=primary_setup,
        exposure_clusters=primary_exposure,
        cluster_normalized=_normalized_report(primary_exposure),
        leader_only=_leader_report(primary_exposure),
        pairwise_correlations=tuple(
            sorted(
                pair_lookup.values(),
                key=lambda item: (item.window_end, item.market_ids),
            )
        ),
        sensitivity=tuple(sensitivity),
        correlation_unknown_count=len(unknown_ids),
    )
