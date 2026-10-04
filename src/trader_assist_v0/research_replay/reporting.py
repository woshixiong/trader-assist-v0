"""Thesis/cluster summaries and a strict summary-only disclosure channel."""

from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import FiniteDecimal, Sha256Hex
from trader_assist_v0.research_data.contracts import BoundRecord

from .contracts import Attempt, CashFlow, DecisionSnapshot, Fill, PathResult, digest
from .lifecycle import VisibilityPolicy
from .policies import PolicyAction


class CandidateResult(BoundRecord):
    candidate_hash: Sha256Hex
    opportunity_hash: Sha256Hex
    market_event_id: str
    thesis_id: str
    cluster_id: str
    setup: str
    regime: str
    snapshots: tuple[DecisionSnapshot, ...] = Field(min_length=1)
    trigger_path: PathResult
    fill_path: PathResult | None
    attempt_hashes: tuple[Sha256Hex, ...]
    fill_hashes: tuple[Sha256Hex, ...]
    policy_action_hashes: tuple[Sha256Hex, ...]
    cost_hash: Sha256Hex
    net_cash: FiniteDecimal | None
    net_r: FiniteDecimal | None
    fee_cash: FiniteDecimal
    funding_cash: FiniteDecimal | None
    outstanding_size: FiniteDecimal
    limitations: tuple[str, ...]
    terminal: Literal["COMPLETE", "UNFINISHED", "NONFILL", "NO_SUBMIT", "SUPPRESSED"]
    attempts: tuple[Attempt, ...] = ()
    fills: tuple[Fill, ...] = ()
    actions: tuple[PolicyAction, ...] = ()
    cashflows: tuple[CashFlow, ...] = ()

    @model_validator(mode="after")
    def evidence_binding(self) -> Self:
        if (
            self.attempt_hashes != tuple(a.record_hash for a in self.attempts)
            or self.fill_hashes
            != tuple(digest("B_NATIVE_FILL", f.model_dump(mode="json")) for f in self.fills)
            or self.policy_action_hashes != tuple(a.record_hash for a in self.actions)
        ):
            raise ValueError("candidate result evidence binding mismatch")
        if self.trigger_path.snapshot_hash != self.snapshots[0].record_hash:
            raise ValueError("path bound to wrong decision snapshot")
        return self


class CounterfactualPathRef(BoundRecord):
    snapshot_hash: Sha256Hex
    scenario: Literal["REGISTERED_REFERENCE_TIME_NATIVE_TAKE"]
    cost_hash: Sha256Hex
    result: CandidateResult
    status: Literal["RECONSTRUCTABLE", "PARTIAL", "NOT_RECONSTRUCTABLE"]
    reason: str


class Pair(BoundRecord):
    opportunity_hash: Sha256Hex
    left_hash: Sha256Hex
    right_hash: Sha256Hex
    comparable: bool
    reason: str
    delta_cash: FiniteDecimal | None
    thesis_id: str
    cluster_id: str


def pair(left: CandidateResult, right: CandidateResult) -> Pair:
    left = CandidateResult.model_validate_json(left.model_dump_json())
    right = CandidateResult.model_validate_json(right.model_dump_json())
    if (left.opportunity_hash, left.thesis_id, left.cluster_id, left.cost_hash) != (
        right.opportunity_hash,
        right.thesis_id,
        right.cluster_id,
        right.cost_hash,
    ):
        raise ValueError("same-opportunity matched-cost identity required")
    comparable = (
        left.net_cash is not None
        and right.net_cash is not None
        and not (
            left.trigger_path.status != "RECONSTRUCTABLE"
            or right.trigger_path.status != "RECONSTRUCTABLE"
        )
    )
    return Pair.create(
        version="B_PAIR_V1",
        opportunity_hash=left.opportunity_hash,
        left_hash=left.record_hash,
        right_hash=right.record_hash,
        comparable=comparable,
        reason="MATCHED" if comparable else "INCOMPLETE_PATH_COST_OR_POSITION",
        delta_cash=right.net_cash - left.net_cash
        if comparable and right.net_cash is not None and left.net_cash is not None
        else None,
        thesis_id=left.thesis_id,
        cluster_id=left.cluster_id,
    )


class Summary(BoundRecord):
    claim: Literal["PIPELINE_CORRECTNESS_ONLY"]
    status: Literal["COMPLETE", "INCOMPLETE", "LEGACY_UNKNOWN"]
    roster_count: int = Field(ge=0)
    thesis_count: int = Field(ge=0)
    cluster_count: int = Field(ge=0)
    paired_count: int = Field(ge=0)
    unmatched_count: int = Field(ge=0)
    participation_counts: tuple[tuple[str, int], ...]
    setup_counts: tuple[tuple[str, int], ...]
    net_expectancy: FiniteDecimal | None
    cost_burden: FiniteDecimal
    maximum_drawdown: FiniteDecimal | None
    tail_concentration: FiniteDecimal | None
    ambiguity_count: int = Field(ge=0)
    uncertainty_unit: Literal["CORRELATION_CLUSTER_THESIS"]
    sufficiency_claim: Literal[False] = False


def summarize(results: tuple[CandidateResult, ...], pairs: tuple[Pair, ...]) -> Summary:
    results = tuple(CandidateResult.model_validate_json(r.model_dump_json()) for r in results)
    if len({r.candidate_hash for r in results}) > 1:
        raise ValueError("summaries must describe one candidate, not pool alternative policies")
    participation: dict[str, int] = {}
    setups: dict[str, int] = {}
    thesis_cash: dict[str, Decimal] = {}
    for row in results:
        key = row.snapshots[-1].decision
        participation[key] = participation.get(key, 0) + 1
        setups[row.setup] = setups.get(row.setup, 0) + 1
        if row.net_cash is not None:
            thesis_cash[row.thesis_id] = thesis_cash.get(row.thesis_id, Decimal(0)) + row.net_cash
    complete = all(r.net_cash is not None for r in results)
    # Deterministic chronological rows provided by the harness; no ranking/selection.
    equity = peak = drawdown = Decimal(0)
    for row in results:
        if row.net_cash is not None:
            equity += row.net_cash
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
    positive = sum((max(Decimal(0), x) for x in thesis_cash.values()), Decimal(0))
    return Summary.create(
        version="B_SUMMARY_V1",
        claim="PIPELINE_CORRECTNESS_ONLY",
        status="COMPLETE" if complete else "INCOMPLETE",
        roster_count=len({r.opportunity_hash for r in results}),
        thesis_count=len({r.thesis_id for r in results}),
        cluster_count=len({r.cluster_id for r in results}),
        paired_count=sum(p.comparable for p in pairs),
        unmatched_count=sum(not p.comparable for p in pairs),
        participation_counts=tuple(sorted(participation.items())),
        setup_counts=tuple(sorted(setups.items())),
        net_expectancy=equity / len(thesis_cash) if complete and thesis_cash else None,
        cost_burden=sum((r.fee_cash for r in results), Decimal(0)),
        maximum_drawdown=drawdown if complete else None,
        tail_concentration=max(thesis_cash.values()) / positive if positive and complete else None,
        ambiguity_count=sum(r.trigger_path.same_bar_ambiguous for r in results),
        uncertainty_unit="CORRELATION_CLUSTER_THESIS",
    )


def summary_only(summary: Summary, visibility: VisibilityPolicy) -> dict[str, object]:
    """Never accept dictionaries containing raw IDs, timestamps or event diagnostics."""
    summary = Summary.model_validate_json(summary.model_dump_json())
    VisibilityPolicy.model_validate_json(visibility.model_dump_json())
    return summary.model_dump(mode="json", exclude={"record_hash", "version"})


def bundle_fingerprint(run_hash: str, artifacts: tuple[tuple[str, str], ...]) -> str:
    if tuple(sorted(artifacts)) != artifacts or len(dict(artifacts)) != len(artifacts):
        raise ValueError("artifact names must be sorted and unique")
    if any(name == "fingerprint" for name, _ in artifacts):
        raise ValueError("noncircular artifact manifest required")
    return digest("B_EVIDENCE_BUNDLE_V1", (run_hash, artifacts))
