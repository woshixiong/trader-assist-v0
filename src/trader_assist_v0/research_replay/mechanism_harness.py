"""Whole-batch before-I/O authorization, matched G0 diagnostics and bounded egress."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.research_data.mapping import PitReferenceResolver
from trader_assist_v0.research_inventory.builder import validate_inventory_manifest
from trader_assist_v0.research_inventory.contracts import DatasetInventoryManifest, InventoryRole

from .contracts import decimal80, digest, wire
from .dev_contracts import DevAccessAuthority, DevObservation
from .dev_evidence import DevExternalAdmission, read_external_dev
from .dev_lifecycle import (
    DevPreregistration,
    DevTrial,
    DevTrialLedger,
    DevVisibilityPolicy,
    require_predecessor,
)
from .dev_reporting import ProspectiveSelectionCandidate, select_prospective_candidate
from .lifecycle import BlockPlan
from .mechanism import (
    _evaluate_mechanism_candidate,
    admitted_rows,
    applicable,
    derive_mechanism_opportunities,
)
from .mechanism_contracts import (
    CHAMPION,
    CODES,
    MechanismBundle,
    MechanismCandidate,
    MechanismConfig,
    MechanismMetrics,
    MechanismOpportunity,
    MechanismPair,
    MechanismResult,
    MechanismRunSpec,
    MechanismSource,
    MechanismSummary,
    checked,
    mechanism_fingerprint,
)

ZERO = Decimal(0)


def mechanism_trial_identity(
    run: MechanismRunSpec, candidate: MechanismCandidate, config: MechanismConfig
) -> str:
    return digest(
        "MECHANISM_MATERIAL_TRIAL_V1",
        (
            candidate.record_hash,
            config.record_hash,
            run.strategy_hash,
            run.dataset_hashes,
            run.taxonomy_hash,
            config.markets,
            config.episode_rule,
            config.risk_hash,
        ),
    )


def validate_mechanism_access(
    run: MechanismRunSpec,
    sources: tuple[MechanismSource, ...],
    inventory: DatasetInventoryManifest,
    ledger: DevTrialLedger,
    blocks: BlockPlan,
    visibility: DevVisibilityPolicy,
    config: MechanismConfig,
    candidates: tuple[MechanismCandidate, ...],
    *,
    s0_preparation_hash: str,
) -> None:
    run = checked(run, MechanismRunSpec)
    config = checked(config, MechanismConfig)
    sources = tuple(checked(s, MechanismSource) for s in sources)
    # Entire batch firewall precedes source admission/store/path/checksum work.
    for source in sources:
        ds = source.dataset
        if ds.source_tier not in {"R1", "R2", "R3"} or ds.exposure_state != "DEV_EXPOSED":
            raise PermissionError("R1/R2/R3 DEV_EXPOSED only")
        if "HYPERLIQUID" in (ds.source + ds.venue).upper() or any(
            "FORWARD" in v.upper()
            for k, v in ds.metadata
            if k in {"open_reason", "current_evidence_role", "result_visibility_state"}
        ):
            raise PermissionError("native/forward evidence prohibited")
    checked(inventory, DatasetInventoryManifest)
    inventory = validate_inventory_manifest(inventory)
    ledger = checked(ledger, DevTrialLedger)
    blocks = checked(blocks, BlockPlan)
    visibility = checked(visibility, DevVisibilityPolicy)
    pre = checked(ledger.preregistration, DevPreregistration)
    candidates = tuple(checked(c, MechanismCandidate) for c in candidates)
    if pre.stage != "S1" or pre.group != "G0" or ledger.history != "COMPLETE":
        raise PermissionError("complete prospective S1/G0 ledger required")
    require_predecessor(pre, None, None, s0_preparation_hash)
    if run.s0_preparation_hash != s0_preparation_hash:
        raise ValueError("S0 receipt mismatch")
    bindings = (
        (run.config_hash, config.record_hash),
        (run.inventory_hash, inventory.record_hash),
        (run.preregistration_hash, pre.record_hash),
        (run.ledger_hash, ledger.record_hash),
        (run.block_hash, blocks.record_hash),
        (pre.block_plan_hash, blocks.record_hash),
        (run.visibility_hash, visibility.record_hash),
        (pre.visibility_hash, visibility.record_hash),
        (pre.strategy_hash, run.strategy_hash),
        (pre.strategy_version, run.manifest.strategy_version),
        (run.taxonomy_hash, pre.taxonomy_hash),
        (pre.cost_hash, config.cost.record_hash),
        (pre.original_risk_hash, config.risk_hash),
        (run.evidence_kind, pre.evidence_kind),
    )
    if any(left != right for left, right in bindings):
        raise ValueError("frozen run/preregistration identity mismatch")
    if config.horizon_ns > pre.max_horizon_ns or config.cost.delay_ns > pre.gates.max_delay_ns:
        raise ValueError("horizon/delay exceeds frozen gates")
    if tuple(c.participation.code for c in candidates) != CODES:
        raise ValueError("exact ordered five-candidate G0 roster required")
    if (
        tuple(c.record_hash for c in candidates) != run.candidate_hashes
        or pre.candidate_order != run.candidate_hashes
    ):
        raise ValueError("candidate roster mismatch")
    if pre.parameter_hashes != (config.record_hash,) * len(candidates):
        raise ValueError("exact mechanism config parameter binding required")
    if any(
        (c.config_hash, c.risk_hash) != (config.record_hash, config.risk_hash) for c in candidates
    ):
        raise ValueError("matched candidate config/risk required")
    if (
        run.dataset_hashes != tuple(s.dataset.record_hash for s in sources)
        or pre.dataset_hashes != run.dataset_hashes
    ):
        raise ValueError("dataset roster mismatch")
    if (
        len(set(run.dataset_hashes)) != len(sources)
        or tuple(s.record_hash for s in sources) != run.source_hashes
    ):
        raise ValueError("duplicate/changed source roster")
    if set(m.instrument for m in config.markets) != {
        i for s in sources for i in s.dataset.instruments
    }:
        raise ValueError("full frozen universe required")
    reserves = tuple(
        sorted(
            e.dataset.record_hash
            for e in inventory.entries
            if e.allocation.role
            in {
                InventoryRole.FUTURE_DEV_RESERVE,
                InventoryRole.CERTIFICATION_RESERVE,
                InventoryRole.SEALED_VALIDATION,
                InventoryRole.FINAL_LOCKBOX,
            }
        )
    )
    if tuple(sorted(pre.reserve_hashes)) != reserves:
        raise PermissionError("exact inventory reserve roster required")
    entries = {e.dataset.record_hash: e for e in inventory.entries}
    if {
        e.dataset.record_hash
        for e in inventory.entries
        if e.allocation.role == InventoryRole.CURRENT_DEV
    } != set(run.dataset_hashes):
        raise PermissionError("CURRENT_DEV allocation must exhaust executable roster")
    if (
        inventory.allocation_spec.strategy_version != pre.strategy_version
        or inventory.allocation_spec.primary_research_question != pre.question
    ):
        raise PermissionError("inventory Strategy/question mismatch")
    required_attribution: set[str] = set()
    for s in sources:
        ds = s.dataset
        entry = entries.get(ds.record_hash)
        if (
            entry is None
            or entry.dataset != ds
            or entry.allocation.role != InventoryRole.CURRENT_DEV
        ):
            raise PermissionError("exact CURRENT_DEV inventory binding required")
        checked(s.authority, DevAccessAuthority).require(ds, pre)
        if s.authority.visibility != visibility.channel:
            raise PermissionError("visibility mismatch")
        if s.mapping.record_hash != ds.mapping_hash or s.registry_hash != run.registry_hash:
            raise PermissionError("mapping/registry/checksum mismatch")
        for cap in s.capabilities:
            cap.require_core_proof()
            if not cap.enabled or cap.adapter_state.value != "AVAILABLE_VERIFIED":
                raise PermissionError("source capability must be enabled and verified")
        expected_mapping = {
            m.instrument: m.expression for m in config.markets if m.instrument in ds.instruments
        }
        mapped = {
            r.instrument_id: r.association or r.instrument_id
            for r in s.mapping.records
            if r.instrument_id in ds.instruments and r.venue == ds.venue
        }
        if mapped != expected_mapping:
            raise PermissionError("exact external universe mapping required")
        if {m.instrument for m in config.markets if m.instrument in ds.instruments} != set(
            ds.instruments
        ):
            raise PermissionError("universe source mismatch")
        if ds.asset_class.upper() in {"EQUITY", "EQUITIES", "RWA", "STOCK", "STOCKS"} and (
            config.pit_qa_hash is None
            or not config.pit_qa_ref
            or not config.pit_qa_ref.startswith("https://github.com/woshixiong/trader-assist-v0/")
        ):
            raise PermissionError("accepted PIT historical QA required")
        if not any(
            b.role == "DEV"
            and b.start <= ds.start_ns
            and ds.end_ns <= b.end
            and set(ds.instruments) <= set(b.instruments)
            for b in blocks.blocks
        ):
            raise PermissionError("exact DEV block cut required")
        for reserved in inventory.entries:
            r = reserved.dataset
            if reserved.allocation.role not in {
                InventoryRole.CURRENT_DEV,
                InventoryRole.METADATA_ONLY_EXCLUDED,
            }:
                if (
                    ds.source == r.source
                    and ds.venue == r.venue
                    and set(ds.instruments) & set(r.instruments)
                    and max(ds.start_ns, r.start_ns) < min(ds.end_ns, r.end_ns)
                ):
                    raise PermissionError("requested cut overlaps reserve")
        assert ds.rights is not None
        required_attribution.update(ds.rights.attribution_constraints)
        if not set(entry.allocation.satisfied_constraints) <= set(
            s.authority.satisfied_constraints
        ):
            raise PermissionError("inventory rights constraints mismatch")
    if not required_attribution <= set(visibility.attribution):
        raise PermissionError("report attribution required before I/O")
    material = {t.semantic_hash: t for t in ledger.entries if type(t) is DevTrial}
    for c in candidates:
        t = material.get(mechanism_trial_identity(run, c, config))
        if t is None or t.candidate_hash != c.record_hash:
            raise PermissionError("unlogged mechanism material trial")


def read_mechanism_sources(
    run: MechanismRunSpec,
    sources: tuple[MechanismSource, ...],
    inventory: DatasetInventoryManifest,
    ledger: DevTrialLedger,
    blocks: BlockPlan,
    visibility: DevVisibilityPolicy,
    config: MechanismConfig,
    candidates: tuple[MechanismCandidate, ...],
    *,
    s0_preparation_hash: str,
) -> tuple[DevObservation, ...]:
    validate_mechanism_access(
        run,
        sources,
        inventory,
        ledger,
        blocks,
        visibility,
        config,
        candidates,
        s0_preparation_hash=s0_preparation_hash,
    )
    states = {e.dataset.record_hash: e.inventory_state.value for e in inventory.entries}
    rows: list[DevObservation] = []
    for s in sources:
        if states[s.dataset.record_hash] != "AVAILABLE":
            continue  # remains an unavailable cohort, never a substitute source
        s.authority.require(s.dataset, ledger.preregistration)
        admission = DevExternalAdmission(
            s.dataset,
            PitReferenceResolver(s.mapping),
            s.capabilities,
            s.policy,
            s.authority,
            ledger.preregistration,
        )
        rows.extend(
            read_external_dev(
                Path(s.root),
                Path(s.path),
                s.checksum,
                s.registry_hash,
                admission,
                max_bytes=visibility.max_bytes,
            )
        )
    if len(rows) > min(run.max_observations, visibility.max_rows):
        raise ValueError("bounded observations exceeded")
    return admitted_rows(tuple(rows))


def pair_results(
    roster: tuple[MechanismOpportunity, ...],
    results: tuple[MechanismResult, ...],
    candidates: tuple[MechanismCandidate, ...],
) -> tuple[MechanismPair, ...]:
    result_by_key = {(r.opportunity_hash, r.code): r for r in results}
    expected = {(o.record_hash, c.participation.code) for o in roster for c in candidates}
    if set(result_by_key) != expected or len(results) != len(expected):
        raise ValueError("incomplete/duplicate five-candidate denominator")
    pairs = []
    for op in roster:
        left = result_by_key[(op.record_hash, CHAMPION)]
        for c in candidates[1:]:
            if not applicable(op, c.participation.code):
                continue
            right = result_by_key[(op.record_hash, c.participation.code)]
            if (left.config_hash, left.risk_hash, left.thesis_id, left.cluster_id) != (
                right.config_hash,
                right.risk_hash,
                right.thesis_id,
                right.cluster_id,
            ):
                raise ValueError("unmatched comparison")
            comparable = left.net_r is not None and right.net_r is not None
            pairs.append(
                MechanismPair.create(
                    version="MECHANISM_PAIR_V1",
                    opportunity_hash=op.record_hash,
                    left_hash=left.record_hash,
                    right_hash=right.record_hash,
                    comparable=comparable,
                    reason="MATCHED" if comparable else "INCOMPLETE_ECONOMICS",
                    delta_r=wire(right.net_r - left.net_r)
                    if right.net_r is not None and left.net_r is not None
                    else None,
                    delta_cash=wire(right.net_cash - left.net_cash)
                    if right.net_cash is not None and left.net_cash is not None
                    else None,
                )
            )
    return tuple(pairs)


def _cell(op: MechanismOpportunity) -> str:
    return f"{op.family}|{op.mode}|{op.side}|{op.regime}"


@decimal80
def summarize_mechanism(
    roster: tuple[MechanismOpportunity, ...],
    results: tuple[MechanismResult, ...],
    pairs: tuple[MechanismPair, ...],
    pre: DevPreregistration,
    inventory: DatasetInventoryManifest,
    *,
    run: MechanismRunSpec,
    candidates: tuple[MechanismCandidate, ...],
) -> MechanismSummary:
    if (
        pre.candidate_order != run.candidate_hashes
        or run.candidate_hashes != tuple(c.record_hash for c in candidates)
        or len(pre.complexity) != len(candidates)
        or tuple(c.participation.code for c in candidates) != CODES
        or pre.champion_hash != candidates[0].record_hash
        or any(
            (c.config_hash, c.risk_hash) != (run.config_hash, pre.original_risk_hash)
            for c in candidates
        )
    ):
        raise ValueError("exact prospective candidate/order/complexity binding required")
    identities = {
        c.participation.code: (c.record_hash, i, pre.complexity[i])
        for i, c in enumerate(candidates)
    }
    ops = {o.record_hash: o for o in roster}
    by_cell: dict[tuple[str, str], list[MechanismResult]] = defaultdict(list)
    for r in results:
        if applicable(ops[r.opportunity_hash], r.code):
            by_cell[(_cell(ops[r.opportunity_hash]), r.code)].append(r)
    paired = {p.right_hash: p for p in pairs}
    known_cells = {_cell(o) for o in roster if o.availability == "AVAILABLE"}
    missing_cells = tuple(sorted(set(pre.mandatory_cells) - known_cells))
    metrics = []
    for (cell, code), values in sorted(by_cell.items()):
        values.sort(
            key=lambda r: (
                r.exit.ts if r.exit else ops[r.opportunity_hash].horizon_end,
                r.thesis_id,
            )
        )
        total = len(values)
        incomplete = sum(r.net_r is None for r in values)
        complete = incomplete == 0
        risks = [r.net_r for r in values if r.net_r is not None]
        event_count = len(
            {
                ops[r.opportunity_hash].market_event_id
                for r in values
                if ops[r.opportunity_hash].availability == "AVAILABLE"
            }
        )
        clusters = {
            r.cluster_id for r in values if ops[r.opportunity_hash].availability == "AVAILABLE"
        }
        equity = peak = drawdown = ZERO
        streak = longest = 0
        for value in risks:
            equity += value
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
            streak = streak + 1 if value < 0 else 0
            longest = max(longest, streak)
        winners = [v for v in risks if v > 0]
        winner_total = sum(winners, ZERO)
        winner_conc = max(winners) / winner_total if winner_total else None
        contributions: dict[str, Decimal] = defaultdict(Decimal)
        deltas: dict[str, list[Decimal]] = defaultdict(list)
        for r in values:
            if r.net_r is not None:
                contributions[r.cluster_id] += max(ZERO, r.net_r)
            p = paired.get(r.record_hash)
            if p and p.delta_r is not None:
                deltas[r.cluster_id].append(p.delta_r)
        contribution_total = sum(contributions.values(), ZERO)
        cluster_conc = (
            max(contributions.values()) / contribution_total if contribution_total else None
        )
        observed_pairs = [paired[r.record_hash] for r in values if r.record_hash in paired]
        delta_values = [p.delta_r for p in observed_pairs if p.delta_r is not None]
        cluster_means = [sum(v, ZERO) / len(v) for v in deltas.values()]
        legs = [f for r in values for f in (r.entry, r.exit) if f is not None]
        fees = sum((f.fee for f in legs), ZERO)
        friction = sum((f.friction_cash for f in legs), ZERO)
        funding = sum((r.funding_cash or ZERO for r in values), ZERO) if complete else None
        additional = sum((r.additional_cash for r in values), ZERO)
        costs = (
            sum(
                (
                    (
                        sum((f.fee + f.friction_cash for f in (r.entry, r.exit) if f), ZERO)
                        + r.additional_cash
                        + max(ZERO, -(r.funding_cash or ZERO))
                    )
                    / r.original_risk_cash
                    for r in values
                ),
                ZERO,
            )
            / total
        )
        unavailable = Decimal(incomplete) / total
        coverage = Decimal(sum(r.terminal == "COMPLETE" for r in values)) / total
        sufficient = (
            event_count >= pre.minimum_events
            and len(clusters) >= pre.minimum_clusters
            and not missing_cells
        )
        tail = max((max(ZERO, -v) for v in risks), default=ZERO) if complete else None
        mae_values = [
            abs(r.path.mae) * r.entry.size / r.original_risk_cash
            for r in values
            if r.path.mae is not None and r.entry
        ]
        mean = sum(risks, ZERO) / total if complete else None
        coherent = bool(
            sufficient
            and complete
            and mean is not None
            and mean > 0
            and drawdown <= pre.gates.max_drawdown_r
            and tail is not None
            and tail <= pre.gates.max_tail_loss_r
            and coverage >= pre.gates.minimum_coverage
            and unavailable <= pre.gates.max_unavailable_rate
            and costs <= pre.gates.max_cost_r
            and (winner_conc or ZERO) <= pre.gates.max_winner_concentration
            and (cluster_conc or ZERO) <= pre.gates.max_cluster_concentration
        )
        metrics.append(
            MechanismMetrics.create(
                version="MECHANISM_METRICS_V1",
                cell=cell,
                code=code,
                roster_count=total,
                event_count=event_count,
                thesis_count=len({r.thesis_id for r in values}),
                cluster_count=len(clusters),
                incomplete_count=incomplete,
                participation=tuple(sorted(Counter(r.terminal for r in values).items())),
                after_cost_thesis_r=wire(mean) if mean is not None else None,
                paired_delta_r=wire(sum(delta_values, ZERO) / len(delta_values))
                if delta_values and len(delta_values) == total
                else None,
                median_delta_r=wire(median(delta_values)) if delta_values else None,
                drawdown_r=wire(drawdown) if complete else None,
                tail_loss_r=tail,
                tail_mae_r=max(mae_values) if mae_values and complete else None,
                longest_losing_streak=longest,
                winner_concentration=wire(winner_conc) if winner_conc is not None else None,
                cluster_concentration=wire(cluster_conc) if cluster_conc is not None else None,
                coverage=wire(coverage),
                unavailable_rate=wire(unavailable),
                cost_r=wire(costs),
                turnover_cash=sum((f.price * f.size for f in legs), ZERO),
                fee_cash=fees,
                friction_cash=friction,
                funding_cash=funding,
                additional_cash=additional,
                per_leg_cost_cash=wire((fees + friction + additional) / len(legs))
                if legs
                else None,
                missed_count=sum(
                    r.terminal in {"SUPPRESSED", "NONFILL", "NO_SUBMIT"} for r in values
                ),
                false_positive_count=sum(
                    r.entry is not None and r.net_r is not None and r.net_r <= 0 for r in values
                ),
                false_negative_count=sum(
                    r.counterfactual_r is not None and r.counterfactual_r > 0 for r in values
                ),
                ambiguous_count=sum(r.path.ambiguous for r in values),
                comparable_count=len(delta_values),
                unmatched_count=len(observed_pairs) - len(delta_values),
                cluster_delta_lower=wire(min(cluster_means)) if cluster_means else None,
                cluster_delta_upper=wire(max(cluster_means)) if cluster_means else None,
                sufficient=sufficient,
                coherent=coherent,
            )
        )
    performance = pre.evidence_kind == "RIGHTS_AUTHORIZED_DEV"
    unavailable_cohorts = sum(
        e.inventory_state.value != "AVAILABLE"
        for e in inventory.entries
        if e.allocation.role == InventoryRole.CURRENT_DEV
    )
    sufficient = (
        bool(metrics)
        and not missing_cells
        and unavailable_cohorts == 0
        and all(m.sufficient for m in metrics)
    )
    champion = [m for m in metrics if m.code == CHAMPION]
    coherent = any(m.coherent for m in champion)
    selections = []
    for cell in sorted({m.cell for m in metrics}):
        cell_ops = [o for o in roster if _cell(o) == cell]
        edge_candidates = [c for c in candidates if applicable(cell_ops[0], c.participation.code)]
        cell_metrics = {m.code: m for m in metrics if m.cell == cell}
        if len(cell_metrics) != sum(m.cell == cell for m in metrics) or set(cell_metrics) != {
            c.participation.code for c in edge_candidates
        }:
            raise ValueError("complete unique applicable comparison edge required")
        rows = []
        for c in edge_candidates:
            code = c.participation.code
            m = cell_metrics[code]
            candidate_hash, order, complexity = identities[code]
            rows.append(
                ProspectiveSelectionCandidate(
                    candidate_hash=candidate_hash,
                    preregistered_order=order,
                    complexity=complexity,
                    sufficient=m.sufficient,
                    eligible=m.coherent,
                    after_cost_thesis_r=m.after_cost_thesis_r,
                    paired_delta_r=ZERO if code == CHAMPION else m.paired_delta_r,
                )
            )
        selections.append(
            select_prospective_candidate(
                tuple(rows),
                champion_hash=pre.champion_hash,
                equivalence_tolerance_r=pre.gates.equivalence_tolerance_r,
                minimum_incremental_r=pre.gates.minimum_incremental_r,
            )
        )
    leader = any(s.disposition == "RESEARCH_LEADER" for s in selections)
    keep = any(s.disposition == "KEEP_CURRENT" for s in selections)
    disposition = (
        "MORE_EVIDENCE_REQUIRED"
        if unavailable_cohorts or any(m.incomplete_count for m in metrics)
        else "INSUFFICIENT"
        if not sufficient or not performance
        else "RESEARCH_LEADER"
        if leader
        else "KEEP_CURRENT"
        if keep
        else "REJECT"
    )
    stop = performance and sufficient and not coherent and not leader
    return MechanismSummary.create(
        version="MECHANISM_SUMMARY_V1",
        metrics=tuple(metrics),
        missing_cells=missing_cells,
        cohort_count=sum(e.allocation.role == InventoryRole.CURRENT_DEV for e in inventory.entries),
        unavailable_cohort_count=unavailable_cohorts,
        event_count=len({o.market_event_id for o in roster if o.availability == "AVAILABLE"}),
        disposition=disposition,
        stop_broad_optimization=stop,
        next_action="DIAGNOSE_SCANNER_SETUP_ENTRY_COST_LAYER" if stop else "RESEARCH_ONLY_NO_S2_S5",
        performance_evidence=performance,
    )


def _allocate_capital(
    roster: tuple[MechanismOpportunity, ...],
    results: tuple[MechanismResult, ...],
    config: MechanismConfig,
) -> tuple[MechanismResult, ...]:
    """Chronological admission without profit sorting; mode portfolios are separate."""
    ops = {o.record_hash: o for o in roster}
    output = list(results)
    occupied: dict[tuple[str, str], list[tuple[int, Decimal]]] = defaultdict(list)

    def admission_order(index: int) -> tuple[int, str, str, str]:
        result = results[index]
        return (
            result.entry.ts if result.entry is not None else 2**100,
            result.thesis_id,
            result.opportunity_hash,
            result.code,
        )

    for index in sorted(
        range(len(results)),
        key=admission_order,
    ):
        result = results[index]
        if result.entry is None or result.exit is None:
            continue
        key = (result.code, ops[result.opportunity_hash].mode)
        current = [(end, cash) for end, cash in occupied[key] if end > result.entry.ts]
        notional = result.entry.price * result.entry.size
        if sum((cash for _, cash in current), ZERO) + notional > config.capital_cash:
            output[index] = MechanismResult.create(
                **{
                    **result.model_dump(exclude={"record_hash"}),
                    "entry": None,
                    "exit": None,
                    "net_cash": ZERO,
                    "net_r": ZERO,
                    "funding_cash": ZERO,
                    "additional_cash": ZERO,
                    "terminal": "NO_SUBMIT",
                    "counterfactual_r": result.net_r,
                    "reasons": ("MATCHED_CAPITAL_BUSY",),
                }
            )
        else:
            current.append((result.exit.ts, notional))
        occupied[key] = current
    return tuple(output)


def _outputs(
    rows: tuple[DevObservation, ...],
    run: MechanismRunSpec,
    config: MechanismConfig,
    candidates: tuple[MechanismCandidate, ...],
    *,
    as_of_ns: int,
) -> tuple[
    tuple[MechanismOpportunity, ...], tuple[MechanismResult, ...], tuple[MechanismPair, ...]
]:
    roster = derive_mechanism_opportunities(rows, run.manifest, config)
    if len({o.market_event_id for o in roster}) > run.max_events:
        raise ValueError("bounded event roster exceeded")
    results = tuple(
        _evaluate_mechanism_candidate(o, c, o.decisions, rows, config, as_of_ns=as_of_ns)
        for o in roster
        for c in candidates
    )
    results = _allocate_capital(roster, results, config)
    return roster, results, pair_results(roster, results, candidates)


def _artifacts(
    rows: object, roster: object, results: object, pairs: object, summary: object
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, digest("MECHANISM_ARTIFACT_" + name.upper(), value))
        for name, value in (
            ("observations", rows),
            ("pairs", pairs),
            ("results", results),
            ("roster", roster),
            ("summary", summary),
        )
    )


def authenticate_bundle(bundle: MechanismBundle) -> None:
    """Recompute pure outputs: rehashing a pruned/tampered result cannot authenticate it."""
    validate_mechanism_access(
        bundle.run,
        bundle.sources,
        bundle.inventory,
        bundle.ledger,
        bundle.blocks,
        bundle.visibility,
        bundle.config,
        bundle.candidates,
        s0_preparation_hash=bundle.run.s0_preparation_hash,
    )
    sources = {s.dataset.record_hash: s for s in bundle.sources}
    for row in admitted_rows(bundle.observations):
        source = sources.get(row.evidence.dataset_hash)
        if (
            source is None
            or row.authority != source.authority
            or row.evidence.registry_hash != bundle.run.registry_hash
        ):
            raise PermissionError("observation outside admitted source authority")
        row.authority.require(source.dataset, bundle.ledger.preregistration)
        if (row.evidence.mapping_hash, row.evidence.rights_hash) != (
            source.dataset.mapping_hash,
            source.authority.rights_hash,
        ):
            raise PermissionError("observation provenance mismatch")
    if len(bundle.observations) > bundle.run.max_observations:
        raise ValueError("observation bound exceeded")
    roster, results, pairs = _outputs(
        bundle.observations, bundle.run, bundle.config, bundle.candidates, as_of_ns=bundle.as_of_ns
    )
    if (bundle.roster, bundle.results, bundle.pairs) != (roster, results, pairs):
        raise ValueError("incomplete/forged causal denominator or modeled economics")
    expected = summarize_mechanism(
        roster,
        results,
        pairs,
        bundle.ledger.preregistration,
        bundle.inventory,
        run=bundle.run,
        candidates=bundle.candidates,
    )
    if bundle.summary != expected or bundle.artifacts != _artifacts(
        bundle.observations, roster, results, pairs, expected
    ):
        raise ValueError("summary/artifact mismatch")
    payload = bundle.model_dump(mode="json", exclude={"record_hash", "fingerprint"})
    if bundle.fingerprint != mechanism_fingerprint(payload):
        raise ValueError("mechanism fingerprint mismatch")


def replay_mechanism(
    run: MechanismRunSpec,
    sources: tuple[MechanismSource, ...],
    inventory: DatasetInventoryManifest,
    ledger: DevTrialLedger,
    blocks: BlockPlan,
    visibility: DevVisibilityPolicy,
    config: MechanismConfig,
    candidates: tuple[MechanismCandidate, ...],
    *,
    s0_preparation_hash: str,
    as_of_ns: int,
) -> MechanismBundle:
    rows = read_mechanism_sources(
        run,
        sources,
        inventory,
        ledger,
        blocks,
        visibility,
        config,
        candidates,
        s0_preparation_hash=s0_preparation_hash,
    )
    roster, results, pairs = _outputs(rows, run, config, candidates, as_of_ns=as_of_ns)
    summary = summarize_mechanism(
        roster, results, pairs, ledger.preregistration, inventory, run=run, candidates=candidates
    )
    values: dict[str, Any] = dict(
        version="MECHANISM_BUNDLE_V1",
        run=run,
        config=config,
        sources=sources,
        inventory=inventory,
        ledger=ledger,
        blocks=blocks,
        visibility=visibility,
        candidates=candidates,
        observations=rows,
        roster=roster,
        results=results,
        pairs=pairs,
        summary=summary,
        as_of_ns=as_of_ns,
        artifacts=_artifacts(rows, roster, results, pairs, summary),
        claim="MECHANISM_VALIDATION",
        economics="SYNTHETIC_VENUE_OVERLAY",
        promotion="PROHIBITED",
    )
    import json

    payload = json.loads(canonical_json_bytes(values))
    return MechanismBundle.create(**values, fingerprint=mechanism_fingerprint(payload))


def mechanism_summary_bytes(bundle: MechanismBundle, visibility: DevVisibilityPolicy) -> bytes:
    checked(visibility, DevVisibilityPolicy)
    checked(bundle, MechanismBundle)
    if visibility != bundle.visibility or not visibility.aggregate_allowed:
        raise PermissionError("authorized aggregate visibility required")
    if len(bundle.summary.metrics) > visibility.max_buckets:
        raise ValueError("bounded summary buckets exceeded")
    # Explicit output allowlist: no source paths, event receipts, locators or raw rows.
    output = canonical_json_bytes(
        dict(
            claim=bundle.claim,
            economics=bundle.economics,
            promotion=bundle.promotion,
            fingerprint=bundle.fingerprint,
            run_hash=bundle.run.record_hash,
            preregistration_hash=bundle.ledger.preregistration.record_hash,
            summary=bundle.summary.model_dump(mode="json"),
            attribution=visibility.attribution,
            diagnostics_withheld=visibility.channel == "DEV_AGGREGATE_ONLY",
        )
    )
    if len(output) > visibility.max_bytes:
        raise ValueError("bounded summary bytes exceeded")
    return output
