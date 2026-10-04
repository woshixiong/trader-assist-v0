"""Bounded DEV diagnostics and fixed aggregate egress; research selection only."""

from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import FiniteDecimal, Sha256Hex, canonical_json_bytes
from trader_assist_v0.research_data.contracts import BoundRecord

from .contracts import decimal80, wire
from .dev_contracts import DevEvidenceBundle, dev_material_identity
from .dev_lifecycle import (
    DevCompletion,
    DevStageResult,
    DevTrial,
    DevTrialLedger,
    DevVisibilityPolicy,
    ResearchDisposition,
)
from .reporting import CandidateResult


def _finite(value: Decimal) -> Decimal:
    return Decimal(wire(value))


class DevCandidateMetrics(BoundRecord):
    candidate_hash: Sha256Hex
    roster_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    thesis_count: int = Field(ge=0)
    cluster_count: int = Field(ge=0)
    cell_count: int = Field(ge=0)
    missing_cells: int = Field(ge=0)
    incomplete_count: int = Field(ge=0)
    ambiguity_count: int = Field(ge=0)
    suppressed_count: int = Field(ge=0)
    false_positive_count: int = Field(ge=0)
    false_negative_count: int = Field(ge=0)
    after_cost_thesis_r: FiniteDecimal | None
    paired_delta_r: FiniteDecimal | None
    median_paired_delta_r: FiniteDecimal | None
    net_cash: FiniteDecimal | None
    fee_cash: FiniteDecimal
    funding_cash: FiniteDecimal | None
    reentry_fee_cash: FiniteDecimal
    drawdown_r: FiniteDecimal | None
    tail_loss_r: FiniteDecimal | None
    winner_concentration: FiniteDecimal | None
    cluster_concentration: FiniteDecimal | None
    coverage: FiniteDecimal
    unavailable_rate: FiniteDecimal
    cost_r: FiniteDecimal
    cluster_delta_lower: FiniteDecimal | None
    cluster_delta_upper: FiniteDecimal | None
    sufficient: bool
    uncertainty_unit: Literal["MARKET_EVENT_THESIS_CLUSTER"] = "MARKET_EVENT_THESIS_CLUSTER"
    uncertainty_method: Literal["DESCRIPTIVE_CLUSTER_RANGE_NO_INFERENTIAL_CLAIM"] = (
        "DESCRIPTIVE_CLUSTER_RANGE_NO_INFERENTIAL_CLAIM"
    )


class DevDiagnosticRow(BoundRecord):
    result: CandidateResult
    original_risk_cash: FiniteDecimal
    net_r_after_cost: FiniteDecimal | None
    setup: str
    mode: str
    side: Literal["LONG", "SHORT"]
    regime: str
    false_positive: bool
    false_negative: bool | None
    counterfactual_result_hash: Sha256Hex | None


class DevDiagnostics(BoundRecord):
    bundle_hash: Sha256Hex
    visibility_hash: Sha256Hex
    rows: tuple[DevDiagnosticRow, ...]
    pairs: tuple["Pair", ...]
    attribution: tuple[str, ...]
    claim: Literal["DEV_RESEARCH_ONLY"] = "DEV_RESEARCH_ONLY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"


class DevSummary(BoundRecord):
    bundle_hash: Sha256Hex
    run_hash: Sha256Hex
    preregistration_hash: Sha256Hex
    ledger_hash: Sha256Hex
    fingerprint: Sha256Hex
    stage: Literal["S1", "S2", "S3", "S4", "S5"]
    disposition: ResearchDisposition
    selected_hash: Sha256Hex | None
    metrics: tuple[DevCandidateMetrics, ...]
    setup_counts: tuple[
        tuple[Literal["SWEEP_RECLAIM", "BREAKOUT_RETEST", "RANGE_EDGE_REJECTION"], int], ...
    ]
    limitation_codes: tuple[
        Literal[
            "SYNTHETIC_ONLY",
            "INCOMPLETE",
            "INSUFFICIENT",
            "RESEARCH_ONLY",
            "NO_INFERENTIAL_ESTIMATOR",
            "DIAGNOSTICS_WITHHELD",
        ],
        ...,
    ]
    attribution: tuple[str, ...]
    claim: Literal["DEV_RESEARCH_ONLY"] = "DEV_RESEARCH_ONLY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"

    @model_validator(mode="after")
    def research_only(self) -> Self:
        if self.selected_hash is not None and self.selected_hash not in {
            m.candidate_hash for m in self.metrics
        }:
            raise ValueError("unregistered selection")
        return self


def _authenticate(bundle: DevEvidenceBundle, visibility: DevVisibilityPolicy) -> DevEvidenceBundle:
    if type(bundle) is not DevEvidenceBundle or type(visibility) is not DevVisibilityPolicy:
        raise TypeError("concrete authenticated DEV envelope and visibility required")
    checked = DevEvidenceBundle.model_validate_json(bundle.model_dump_json())
    policy = DevVisibilityPolicy.model_validate_json(visibility.model_dump_json())
    if checked.run.visibility_hash != policy.record_hash:
        raise PermissionError("DEV report visibility binding mismatch")
    if any(a.visibility != policy.channel for a in checked.authorities):
        raise PermissionError("DEV rights visibility mismatch")
    if len(checked.results) > policy.max_rows:
        raise ValueError("bounded DEV diagnostic rows exceeded")
    required = {c for d in checked.datasets if d.rights for c in d.rights.attribution_constraints}
    if not required <= set(policy.attribution):
        raise PermissionError("report attribution constraints unsatisfied")
    return checked


@decimal80
def diagnostics(
    bundle: DevEvidenceBundle, visibility: DevVisibilityPolicy
) -> DevDiagnostics | None:
    checked = _authenticate(bundle, visibility)
    if visibility.channel != "DEV_LOCAL_AND_AGGREGATE":
        return None
    opportunities = {o.record_hash: o for o in checked.roster}
    risks = dict(checked.original_risks)
    counterfactuals = {
        (c.result.opportunity_hash, c.result.candidate_hash): c for c in checked.counterfactuals
    }
    rows = []
    for result in checked.results:
        op = opportunities[result.opportunity_hash]
        risk = risks[op.thesis_id]
        net_r = _finite(result.net_cash / risk) if result.net_cash is not None else None
        cf = counterfactuals.get((result.opportunity_hash, result.candidate_hash))
        rows.append(
            DevDiagnosticRow.create(
                version="DEV_DIAGNOSTIC_ROW_V1",
                result=result,
                original_risk_cash=risk,
                net_r_after_cost=net_r,
                setup=op.setup,
                mode=op.mode,
                side=op.side,
                regime=op.regime,
                false_positive=result.entry_trigger is not None
                and net_r is not None
                and net_r <= 0,
                false_negative=(
                    cf.result.net_cash > 0
                    if cf is not None
                    and cf.status == "RECONSTRUCTABLE"
                    and cf.result.net_cash is not None
                    else None
                ),
                counterfactual_result_hash=cf.record_hash if cf else None,
            )
        )
    artifact = DevDiagnostics.create(
        version="DEV_DIAGNOSTICS_V1",
        bundle_hash=checked.record_hash,
        visibility_hash=visibility.record_hash,
        rows=tuple(rows),
        pairs=checked.pairs,
        attribution=visibility.attribution,
    )
    if len(canonical_json_bytes(artifact.model_dump(mode="json"))) > visibility.max_bytes:
        raise ValueError("bounded DEV diagnostic bytes exceeded")
    return artifact


@decimal80
def _metrics(bundle: DevEvidenceBundle, candidate: str) -> DevCandidateMetrics:
    pre = bundle.preregistration
    risks = dict(bundle.original_risks)
    ops = {o.record_hash: o for o in bundle.roster}
    rows = tuple(r for r in bundle.results if r.candidate_hash == candidate)
    baseline = {
        r.opportunity_hash: r for r in bundle.results if r.candidate_hash == pre.champion_hash
    }
    thesis: dict[str, Decimal] = {}
    clusters: dict[str, Decimal] = {}
    deltas: dict[str, Decimal] = {}
    cluster_deltas: dict[str, Decimal] = {}
    cells: set[str] = set()
    events: set[str] = set()
    good_clusters: set[str] = set()
    incomplete = ambiguity = suppressed = fp = fn = 0
    cost_r = reentry_fees = Decimal(0)
    for row in rows:
        op = ops[row.opportunity_hash]
        ref = baseline[row.opportunity_hash]
        risk = risks[op.thesis_id]
        ambiguous = (
            row.trigger_path.same_bar_ambiguous or row.trigger_path.status != "RECONSTRUCTABLE"
        )
        complete = (
            row.net_cash is not None
            and row.outstanding_size == 0
            and not ambiguous
            and not row.trigger_path.censored
        )
        ambiguity += ambiguous
        incomplete += not complete
        suppressed += row.terminal in {"SUPPRESSED", "NO_SUBMIT", "NONFILL"}
        cost_r += row.fee_cash / risk
        reentry_fees += sum(
            (f.fee for a in row.attempts[1:] for f in (a.fill, a.exit_fill) if f), Decimal(0)
        )
        if complete and row.net_cash is not None:
            r = row.net_cash / risk
            thesis[op.thesis_id] = thesis.get(op.thesis_id, Decimal(0)) + r
            clusters[op.cluster_id] = clusters.get(op.cluster_id, Decimal(0)) + r
            events.add(op.market_event_id)
            good_clusters.add(op.cluster_id)
            cells.add(f"{op.setup}|{op.mode}|{op.side}|{op.regime}")
            fp += row.entry_trigger is not None and r <= 0
            if (
                ref.net_cash is not None
                and ref.trigger_path.status == "RECONSTRUCTABLE"
                and not ref.trigger_path.same_bar_ambiguous
                and not ref.trigger_path.censored
            ):
                delta = (row.net_cash - ref.net_cash) / risk
                deltas[op.thesis_id] = deltas.get(op.thesis_id, Decimal(0)) + delta
                cluster_deltas[op.cluster_id] = (
                    cluster_deltas.get(op.cluster_id, Decimal(0)) + delta
                )
        for cf in bundle.counterfactuals:
            if (cf.result.opportunity_hash, cf.result.candidate_hash) == (
                row.opportunity_hash,
                candidate,
            ):
                fn += (
                    cf.status == "RECONSTRUCTABLE"
                    and cf.result.net_cash is not None
                    and cf.result.net_cash > 0
                )
    all_complete = incomplete == 0 and len(thesis) == len({o.thesis_id for o in bundle.roster})
    equity = peak = drawdown = Decimal(0)
    # Report each Thesis once, ordered by its last opportunity decision.
    order = sorted(
        thesis, key=lambda key: max(o.decision_ns for o in bundle.roster if o.thesis_id == key)
    )
    for key in order:
        equity += thesis[key]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    positive = sum((max(Decimal(0), r) for r in thesis.values()), Decimal(0))
    cluster_positive = sum((max(Decimal(0), r) for r in clusters.values()), Decimal(0))
    delta_values = sorted(deltas.values())
    median = (
        (delta_values[(len(delta_values) - 1) // 2] + delta_values[len(delta_values) // 2]) / 2
        if delta_values
        else None
    )
    missing = len(set(pre.mandatory_cells) - cells)
    sufficient = (
        len(events) >= pre.minimum_events
        and len(good_clusters) >= pre.minimum_clusters
        and len(cells) >= pre.minimum_cells
        and missing == 0
    )
    return DevCandidateMetrics.create(
        version="DEV_METRICS_V1",
        candidate_hash=candidate,
        roster_count=len(rows),
        event_count=len(events),
        thesis_count=len(thesis),
        cluster_count=len(good_clusters),
        cell_count=len(cells),
        missing_cells=missing,
        incomplete_count=incomplete,
        ambiguity_count=ambiguity,
        suppressed_count=suppressed,
        false_positive_count=fp,
        false_negative_count=fn,
        after_cost_thesis_r=_finite(equity / len(thesis)) if all_complete and thesis else None,
        paired_delta_r=_finite(sum(deltas.values(), Decimal(0)) / len(deltas))
        if all_complete and len(deltas) == len(thesis) and deltas
        else None,
        median_paired_delta_r=_finite(median) if median is not None else None,
        net_cash=sum((r.net_cash for r in rows if r.net_cash is not None), Decimal(0))
        if all_complete
        else None,
        fee_cash=sum((r.fee_cash for r in rows), Decimal(0)),
        funding_cash=sum((r.funding_cash for r in rows if r.funding_cash is not None), Decimal(0))
        if all(r.funding_cash is not None for r in rows)
        else None,
        reentry_fee_cash=reentry_fees,
        drawdown_r=_finite(drawdown) if all_complete else None,
        tail_loss_r=_finite(max((max(Decimal(0), -r) for r in thesis.values()), default=Decimal(0)))
        if all_complete
        else None,
        winner_concentration=_finite(max(thesis.values()) / positive)
        if positive and all_complete
        else None,
        cluster_concentration=_finite(max(clusters.values()) / cluster_positive)
        if cluster_positive and all_complete
        else None,
        coverage=_finite(Decimal(len(rows) - suppressed) / len(rows)) if rows else Decimal(0),
        unavailable_rate=_finite(Decimal(incomplete) / len(rows)) if rows else Decimal(1),
        cost_r=_finite(cost_r),
        sufficient=sufficient,
        cluster_delta_lower=_finite(min(cluster_deltas.values())) if cluster_deltas else None,
        cluster_delta_upper=_finite(max(cluster_deltas.values())) if cluster_deltas else None,
    )


def _completed_cut(bundle: DevEvidenceBundle, completed: DevTrialLedger) -> DevTrialLedger:
    if type(completed) is not DevTrialLedger:
        raise TypeError("exact completed DEV ledger required")
    completed = DevTrialLedger.model_validate_json(completed.model_dump_json())
    if (
        completed.preregistration != bundle.preregistration
        or completed.history != "COMPLETE"
        or completed.entries[: len(bundle.ledger.entries)] != bundle.ledger.entries
    ):
        raise ValueError("final ledger must extend exact prereplay cut")
    current_identities = {dev_material_identity(bundle.run, c) for c in bundle.run.policy_hashes}
    registered = {
        e.record_hash
        for e in bundle.ledger.entries
        if type(e) is DevTrial and e.semantic_hash in current_identities
    }
    receipts = {
        e.trial_hash
        for e in completed.entries
        if type(e) is DevCompletion
        and e.run_hash == bundle.run.record_hash
        and e.bundle_hash == bundle.record_hash
    }
    if not registered <= receipts:
        raise ValueError("selection requires exact completed visible result receipts")
    return completed


def summarize_dev(
    bundle: DevEvidenceBundle, visibility: DevVisibilityPolicy, completed: DevTrialLedger
) -> DevSummary:
    bundle = _authenticate(bundle, visibility)
    completed = _completed_cut(bundle, completed)
    pre = bundle.preregistration
    metrics = tuple(_metrics(bundle, c) for c in pre.candidate_order)
    gates = pre.gates

    def eligible(m: DevCandidateMetrics) -> bool:
        return (
            m.sufficient
            and m.after_cost_thesis_r is not None
            and m.after_cost_thesis_r > 0
            and m.drawdown_r is not None
            and m.drawdown_r <= gates.max_drawdown_r
            and m.tail_loss_r is not None
            and m.tail_loss_r <= gates.max_tail_loss_r
            and m.winner_concentration is not None
            and m.winner_concentration <= gates.max_winner_concentration
            and m.cluster_concentration is not None
            and m.cluster_concentration <= gates.max_cluster_concentration
            and m.coverage >= gates.minimum_coverage
            and m.unavailable_rate <= gates.max_unavailable_rate
            and m.cost_r <= gates.max_cost_r
            and m.incomplete_count == 0
        )

    selected: str | None = None
    if not all(m.sufficient for m in metrics):
        disposition = ResearchDisposition.INSUFFICIENT
    elif any(m.after_cost_thesis_r is None or m.paired_delta_r is None for m in metrics):
        disposition = ResearchDisposition.MORE_EVIDENCE_REQUIRED
    else:
        baseline = metrics[0]
        qualified = [(i, m) for i, m in enumerate(metrics) if eligible(m)]
        if not qualified:
            disposition = ResearchDisposition.REJECT
        else:
            best_i, best = max(
                qualified, key=lambda item: (item[1].after_cost_thesis_r or Decimal(0), -item[0])
            )
            # Equivalence is prospective: prefer the lowest registered complexity.
            near = [
                (i, m)
                for i, m in qualified
                if (best.after_cost_thesis_r or Decimal(0)) - (m.after_cost_thesis_r or Decimal(0))
                <= gates.equivalence_tolerance_r
            ]
            chosen_i, chosen = min(near, key=lambda item: (pre.complexity[item[0]], item[0]))
            if (
                chosen_i != 0
                and (chosen.paired_delta_r or Decimal(0)) < gates.minimum_incremental_r
                and pre.complexity[chosen_i] >= pre.complexity[0]
            ):
                selected = baseline.candidate_hash if eligible(baseline) else None
            else:
                selected = chosen.candidate_hash
            disposition = (
                ResearchDisposition.KEEP_CURRENT
                if selected == pre.champion_hash
                else ResearchDisposition.RESEARCH_LEADER
                if selected
                else ResearchDisposition.REJECT
            )
    setups: dict[str, int] = {}
    for op in bundle.roster:
        setups[op.setup] = setups.get(op.setup, 0) + 1
    limitations = ["RESEARCH_ONLY", "NO_INFERENTIAL_ESTIMATOR"]
    if pre.evidence_kind == "SYNTHETIC_ENGINEERING":
        limitations.append("SYNTHETIC_ONLY")
    if any(m.incomplete_count for m in metrics):
        limitations.append("INCOMPLETE")
    if disposition == ResearchDisposition.INSUFFICIENT:
        limitations.append("INSUFFICIENT")
    if visibility.channel == "DEV_AGGREGATE_ONLY":
        limitations.append("DIAGNOSTICS_WITHHELD")
    return DevSummary.create(
        version="DEV_SUMMARY_V1",
        bundle_hash=bundle.record_hash,
        run_hash=bundle.run.record_hash,
        preregistration_hash=pre.record_hash,
        ledger_hash=completed.record_hash,
        fingerprint=bundle.fingerprint,
        stage=pre.stage,
        disposition=disposition,
        selected_hash=selected,
        metrics=metrics,
        setup_counts=tuple(sorted(setups.items())),
        limitation_codes=tuple(limitations),
        attribution=visibility.attribution,
    )


def canonical_summary(
    bundle: DevEvidenceBundle, visibility: DevVisibilityPolicy, completed: DevTrialLedger
) -> dict[str, object] | None:
    summary = summarize_dev(bundle, visibility, completed)
    if not visibility.aggregate_allowed:
        return None
    if len(summary.metrics) > visibility.max_buckets:
        raise ValueError("canonical bucket bound exceeded")
    payload = summary.model_dump(mode="json")
    if len(canonical_json_bytes(payload)) > visibility.max_bytes:
        raise ValueError("canonical summary byte bound exceeded")
    return payload


def stage_result(
    bundle: DevEvidenceBundle, visibility: DevVisibilityPolicy, completed: DevTrialLedger
) -> DevStageResult:
    summary = summarize_dev(bundle, visibility, completed)
    success = summary.disposition in {
        ResearchDisposition.KEEP_CURRENT,
        ResearchDisposition.RESEARCH_LEADER,
    }
    return DevStageResult.create(
        version="DEV_STAGE_RESULT_V1",
        preregistration_hash=bundle.preregistration.record_hash,
        stage=bundle.preregistration.stage,
        group=bundle.preregistration.group,
        ledger_hash=completed.record_hash,
        bundle_hash=bundle.record_hash,
        selected_hash=summary.selected_hash,
        fixed_components=bundle.preregistration.fixed_components,
        dataset_hashes=bundle.run.dataset_hashes,
        strategy_hash=bundle.run.strategy_hash,
        disposition=summary.disposition,
        sufficient=all(m.sufficient for m in summary.metrics),
        coherent=success,
        stop=not success,
    )


from .reporting import Pair  # noqa: E402

DevDiagnostics.model_rebuild()
