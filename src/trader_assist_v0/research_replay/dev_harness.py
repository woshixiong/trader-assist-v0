"""Explicit DEV ingress to the single accepted native rc5 replay loop."""

from trader_assist_v0.contracts.common import FiniteDecimal
from trader_assist_v0.nautilus_e4.contracts import AdmittedEvent
from trader_assist_v0.research_data.contracts import DatasetManifest
from trader_assist_v0.vnext_g4.contracts import ExecutionModelConfig

from .contracts import CashFlow, Opportunity, checked_observation, digest
from .dev_contracts import (
    DevAccessAuthority,
    DevEvidenceBundle,
    DevObservation,
    DevRunSpec,
    dev_fingerprint,
)
from .dev_lifecycle import (
    DevPreregistration,
    DevStageResult,
    DevTrial,
    DevTrialLedger,
    DevVisibilityPolicy,
    require_predecessor,
)
from .harness import (
    CandidatePlan,
    ContextFrame,
    _replay_results,
    _validate_replay_evidence,
    _validate_roster,
)
from .lifecycle import BlockPlan


def dev_trial_identity(run: DevRunSpec, candidate: CandidatePlan) -> str:
    """Economic identity excludes operational code/platform and prospective ledger cut."""
    from .dev_contracts import dev_material_identity

    return dev_material_identity(run, candidate.record_hash)


def validate_dev_inputs(
    run: DevRunSpec,
    datasets: tuple[DatasetManifest, ...],
    rows: tuple[DevObservation, ...],
    roster: tuple[Opportunity, ...],
    candidates: tuple[CandidatePlan, ...],
    frames: tuple[ContextFrame, ...],
    ledger: DevTrialLedger,
    blocks: BlockPlan,
    visibility: DevVisibilityPolicy,
    authorities: tuple[DevAccessAuthority, ...],
    *,
    predecessor: DevStageResult | None,
    previous: DevPreregistration | None,
    s0_preparation_hash: str,
) -> None:
    if (
        type(run) is not DevRunSpec
        or type(ledger) is not DevTrialLedger
        or type(visibility) is not DevVisibilityPolicy
    ):
        raise TypeError("concrete DEV run/ledger/visibility required")
    run = DevRunSpec.model_validate_json(run.model_dump_json())
    ledger = DevTrialLedger.model_validate_json(ledger.model_dump_json())
    visibility = DevVisibilityPolicy.model_validate_json(visibility.model_dump_json())
    pre = ledger.preregistration
    if len(datasets) != len(authorities):
        raise PermissionError("one exact authority per dataset required")
    checked = tuple(a.require(ds, pre) for ds, a in zip(datasets, authorities, strict=True))
    if (
        tuple(ds.record_hash for ds in checked) != run.dataset_hashes
        or pre.dataset_hashes != run.dataset_hashes
    ):
        raise ValueError("DEV dataset roster mismatch")
    if ledger.history != "COMPLETE":
        raise PermissionError("incomplete legacy research history cannot execute/select")
    if (
        run.preregistration_hash != pre.record_hash
        or run.trial_ledger_hash != ledger.record_hash
        or run.block_plan_hash != blocks.record_hash
        or run.visibility_hash != visibility.record_hash
        or pre.block_plan_hash != blocks.record_hash
        or pre.visibility_hash != visibility.record_hash
        or run.strategy_hash != pre.strategy_hash
        or run.strategy_version != pre.strategy_version
        or run.cost.record_hash != pre.cost_hash
        or run.horizon_ns > pre.max_horizon_ns
        or run.policy_hashes != pre.candidate_order
        or run.parameter_hashes != pre.parameter_hashes
        or run.taxonomy_hash != pre.taxonomy_hash
        or run.cost.delay_ns > pre.gates.max_delay_ns
    ):
        raise ValueError("DEV frozen execution/preregistration mismatch")
    BlockPlan.model_validate_json(blocks.model_dump_json())
    require_predecessor(pre, predecessor, previous, s0_preparation_hash)
    for ds, a in zip(datasets, authorities, strict=True):
        if a.visibility != visibility.channel or not any(
            b.role == "DEV"
            and b.start <= ds.start_ns
            and ds.end_ns <= b.end
            and set(ds.instruments) <= set(b.instruments)
            for b in blocks.blocks
        ):
            raise PermissionError("DEV visibility/block cut mismatch")
    _validate_roster(run, rows, roster, candidates)
    allowed = {t.semantic_hash: t for t in ledger.entries if type(t) is DevTrial}
    for candidate in candidates:
        trial = allowed.get(dev_trial_identity(run, candidate))
        if trial is None or trial.candidate_hash != candidate.record_hash:
            raise ValueError("unlogged DEV material candidate")
    for candidate in candidates:
        if pre.group == "G2" and candidate.reentry.code != "R0":
            raise ValueError("G2 loss attribution requires R0 before re-entry")
    for row in rows:
        if type(row) is not DevObservation:
            raise TypeError("DEV requires concrete DEV observations")
        checked_observation(row)
        if row.evidence.registry_hash != run.registry_hash:
            raise ValueError("DEV registry identity mismatch")
        if row.authority not in authorities:
            raise PermissionError("row outside current DEV authority")
    _validate_replay_evidence(run, datasets, rows, roster, candidates, frames)
    if not roster or not any(row.evidence.owner == "HL_E4" for row in rows):
        raise ValueError("MORE_EVIDENCE_REQUIRED: retained native E4 opportunities required")
    for op in roster:
        if not op.domain_hashes:
            raise ValueError("MORE_EVIDENCE_REQUIRED: retained original domain lineage required")
        if not any(
            b.role == "DEV"
            and b.start <= op.decision_ns
            and op.decision_ns + run.horizon_ns < b.end
            for b in blocks.blocks
        ):
            raise ValueError("outcome horizon crosses DEV block/reserve embargo")


def replay_dev(
    run: DevRunSpec,
    datasets: tuple[DatasetManifest, ...],
    rows: tuple[DevObservation, ...],
    roster: tuple[Opportunity, ...],
    candidates: tuple[CandidatePlan, ...],
    frames: tuple[ContextFrame, ...],
    ledger: DevTrialLedger,
    blocks: BlockPlan,
    visibility: DevVisibilityPolicy,
    authorities: tuple[DevAccessAuthority, ...],
    *,
    predecessor: DevStageResult | None,
    previous: DevPreregistration | None,
    s0_preparation_hash: str,
    original_risks: tuple[tuple[str, FiniteDecimal], ...],
    events: tuple[AdmittedEvent, ...],
    instruments: dict[str, object],
    execution: ExecutionModelConfig,
    cashflows: tuple[CashFlow, ...] = (),
    funding_complete: bool,
    funding_applicable: bool,
) -> DevEvidenceBundle:
    validate_dev_inputs(
        run,
        datasets,
        rows,
        roster,
        candidates,
        frames,
        ledger,
        blocks,
        visibility,
        authorities,
        predecessor=predecessor,
        previous=previous,
        s0_preparation_hash=s0_preparation_hash,
    )
    if digest("B_NATIVE_EXECUTION", execution.model_dump(mode="json")) != run.execution_hash:
        raise ValueError("DEV execution identity mismatch")
    source_hashes = {r.evidence.source_hash for r in rows if r.evidence.owner == "HL_E4"}
    if source_hashes != {e.admission_hash for e in events}:
        raise ValueError("DEV native admission/projection roster mismatch")
    if any(
        op.market_id not in instruments
        or not any(e.source.market_id == op.market_id for e in events)
        for op in roster
    ):
        raise ValueError("MORE_EVIDENCE_REQUIRED: native market prerequisites unavailable")
    if not events:
        raise ValueError("MORE_EVIDENCE_REQUIRED: retained admitted E4 events required")
    if (
        digest("DEV_ORIGINAL_THESIS_RISK_V1", original_risks)
        != ledger.preregistration.original_risk_hash
    ):
        raise ValueError("matched original risk identity mismatch")
    if (
        len(dict(original_risks)) != len(original_risks)
        or any(r <= 0 for _, r in original_risks)
        or not {o.thesis_id for o in roster} <= dict(original_risks).keys()
    ):
        raise ValueError("positive matched original risk required before native invocation")
    results, pairs, counterfactuals = _replay_results(
        run,
        rows,
        roster,
        candidates,
        frames,
        events=events,
        instruments=instruments,
        execution=execution,
        cashflows=cashflows,
        funding_complete=funding_complete,
        funding_applicable=funding_applicable,
    )
    artifacts = tuple(
        sorted(
            (
                ("inputs", digest("B_INPUTS", tuple(r.record_hash for r in rows))),
                ("frames", digest("B_FRAMES", tuple(f.record_hash for f in frames))),
                ("admissions", digest("DEV_ADMISSIONS", tuple(e.admission_hash for e in events))),
                ("results", digest("B_RESULTS", tuple(r.record_hash for r in results))),
                ("pairs", digest("B_PAIRS", tuple(p.record_hash for p in pairs))),
                (
                    "counterfactuals",
                    digest("B_COUNTERFACTUALS", tuple(c.record_hash for c in counterfactuals)),
                ),
            )
        )
    )
    values = dict(
        version="DEV_BUNDLE_V1",
        run=run,
        preregistration=ledger.preregistration,
        ledger=ledger,
        datasets=datasets,
        authorities=authorities,
        roster=roster,
        original_risks=original_risks,
        results=results,
        pairs=pairs,
        counterfactuals=counterfactuals,
        artifacts=artifacts,
        claim="DEV_RESEARCH_ONLY",
        promotion="PROHIBITED",
    )
    # Normalize models exactly as the bound fingerprint validator does.
    import json

    from trader_assist_v0.contracts.common import canonical_json_bytes

    normalized = json.loads(canonical_json_bytes(values))
    return DevEvidenceBundle.create(**values, fingerprint=dev_fingerprint(normalized))
