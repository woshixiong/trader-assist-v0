"""Prospective DEV preregistration and append-only adaptation receipts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import FiniteDecimal, Sha256Hex
from trader_assist_v0.research_data.contracts import BoundRecord

from .contracts import digest


class ResearchDisposition(StrEnum):
    RESEARCH_LEADER = "RESEARCH_LEADER"
    KEEP_CURRENT = "KEEP_CURRENT"
    REJECT = "REJECT"
    INSUFFICIENT = "INSUFFICIENT"
    MORE_EVIDENCE_REQUIRED = "MORE_EVIDENCE_REQUIRED"


class DevVisibilityPolicy(BoundRecord):
    channel: Literal["DEV_LOCAL_AND_AGGREGATE", "DEV_AGGREGATE_ONLY"]
    max_rows: int = Field(gt=0, le=100_000)
    max_bytes: int = Field(gt=0, le=4_000_000)
    max_buckets: int = Field(gt=0, le=64)
    aggregate_allowed: bool
    attribution: tuple[str, ...]
    sealed_access: Literal[False] = False
    promotion: Literal["PROHIBITED"] = "PROHIBITED"


class DevGates(BoundRecord):
    minimum_incremental_r: FiniteDecimal = Field(ge=0)
    equivalence_tolerance_r: FiniteDecimal = Field(ge=0)
    max_drawdown_r: FiniteDecimal = Field(gt=0)
    max_tail_loss_r: FiniteDecimal = Field(gt=0)
    max_winner_concentration: FiniteDecimal = Field(gt=0, le=1)
    max_cluster_concentration: FiniteDecimal = Field(gt=0, le=1)
    minimum_coverage: FiniteDecimal = Field(gt=0, le=1)
    max_unavailable_rate: FiniteDecimal = Field(ge=0, lt=1)
    max_cost_r: FiniteDecimal = Field(gt=0)
    max_delay_ns: int = Field(ge=0)


class DevPreregistration(BoundRecord):
    authority: Literal["ISSUE_280_V1.2"]
    r0_ref: str = Field(min_length=1)
    r1_ref: str = Field(min_length=1)
    run_authority_ref: str = Field(min_length=1)
    evidence_kind: Literal["SYNTHETIC_ENGINEERING", "RIGHTS_AUTHORIZED_DEV"]
    stage: Literal["S1", "S2", "S3", "S4", "S5"]
    group: Literal["G0", "G1", "G2", "G3", "G4", "G5", "G6"]
    predecessor_hash: Sha256Hex
    hypothesis: str = Field(min_length=1)
    failure_mode: str = Field(min_length=1)
    champion_hash: Sha256Hex
    challenger_hashes: tuple[Sha256Hex, ...] = Field(min_length=1, max_length=63)
    candidate_order: tuple[Sha256Hex, ...] = Field(min_length=2, max_length=64)
    complexity: tuple[int, ...]
    parameter_hashes: tuple[Sha256Hex, ...]
    allowed_changes: tuple[str, ...] = Field(min_length=1)
    prohibited_changes: tuple[str, ...] = Field(min_length=1)
    fixed_components: tuple[Sha256Hex, ...]
    primary_metric: Literal["THESIS_NET_R_AFTER_COST"]
    secondary_metrics: tuple[str, ...] = Field(min_length=1)
    taxonomy_hash: Sha256Hex
    cost_hash: Sha256Hex
    block_plan_hash: Sha256Hex
    visibility_hash: Sha256Hex
    stopping_rule: Literal["COMPLETE_FROZEN_ROSTER_NO_PNL_EARLY_STOP"]
    failure_rule: Literal["COHERENT_AFTER_COST_AND_ALL_GATES"]
    selection_rule: Literal["PAIRED_INCREMENTAL_R_SIMPLER_ON_EQUIVALENCE"]
    gates: DevGates
    max_trials: int = Field(gt=0, le=64)
    max_research_repairs: int = Field(ge=0, le=1)
    repair_mechanism: str = Field(min_length=1)
    minimum_events: int = Field(gt=0)
    minimum_clusters: int = Field(gt=0)
    minimum_cells: int = Field(gt=0)
    mandatory_cells: tuple[str, ...] = Field(min_length=1, max_length=64)
    max_horizon_ns: int = Field(gt=0)
    reserve_hashes: tuple[Sha256Hex, ...]
    dataset_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    strategy_hash: Sha256Hex
    strategy_version: str = Field(min_length=1)
    question: str = Field(min_length=1)
    research_plan_hash: Sha256Hex
    original_risk_hash: Sha256Hex
    false_positive_rule: Literal["TAKEN_NONPOSITIVE_NET_R"]
    false_negative_rule: Literal["SUPPRESSED_POSITIVE_REGISTERED_COUNTERFACTUAL_R"]
    promotion: Literal["PROHIBITED"] = "PROHIBITED"

    @model_validator(mode="after")
    def frozen_order(self) -> Self:
        groups = {"S1": {"G0"}, "S2": {"G1"}, "S3": {"G2", "G3"}, "S4": {"G4", "G5"}, "S5": {"G6"}}
        if self.group not in groups[self.stage]:
            raise ValueError("stage/subgroup mismatch")
        if self.candidate_order != (self.champion_hash, *self.challenger_hashes):
            raise ValueError("candidate order must match frozen champion/challengers")
        if len(set(self.candidate_order)) != len(self.candidate_order):
            raise ValueError("duplicate candidate")
        if len(self.complexity) != len(self.candidate_order) or any(x < 0 for x in self.complexity):
            raise ValueError("exact prespecified complexity required")
        if len(self.parameter_hashes) != len(self.candidate_order):
            raise ValueError("exact candidate parameter sets required")
        if set(self.dataset_hashes) & set(self.reserve_hashes):
            raise PermissionError("reserve cannot be executable DEV")
        if len(set(self.mandatory_cells)) != len(self.mandatory_cells) or self.minimum_cells > len(
            self.mandatory_cells
        ):
            raise ValueError("exact mandatory cells required")
        if self.evidence_kind == "RIGHTS_AUTHORIZED_DEV" and any(
            not ref.startswith("https://github.com/woshixiong/trader-assist-v0/issues/")
            or "#issuecomment-" not in ref
            for ref in (self.r0_ref, self.r1_ref, self.run_authority_ref)
        ):
            raise PermissionError("exact canonical authority locators required for real DEV")
        return self


class DevStageResult(BoundRecord):
    preregistration_hash: Sha256Hex
    stage: Literal["S1", "S2", "S3", "S4", "S5"]
    group: Literal["G0", "G1", "G2", "G3", "G4", "G5", "G6"]
    ledger_hash: Sha256Hex
    bundle_hash: Sha256Hex
    selected_hash: Sha256Hex | None
    fixed_components: tuple[Sha256Hex, ...]
    dataset_hashes: tuple[Sha256Hex, ...]
    strategy_hash: Sha256Hex
    disposition: ResearchDisposition
    sufficient: bool
    coherent: bool
    stop: bool
    claim: Literal["DEV_RESEARCH_ONLY"] = "DEV_RESEARCH_ONLY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"

    @model_validator(mode="after")
    def eligible(self) -> Self:
        success = self.disposition in {
            ResearchDisposition.KEEP_CURRENT,
            ResearchDisposition.RESEARCH_LEADER,
        }
        if success and (
            not self.sufficient or not self.coherent or self.stop or self.selected_hash is None
        ):
            raise ValueError("success requires sufficient coherent research evidence")
        if not success and not self.stop:
            raise ValueError("failed/incomplete stage must stop progression")
        return self


def require_predecessor(
    pre: DevPreregistration,
    predecessor: DevStageResult | None,
    previous: DevPreregistration | None,
    s0_preparation_hash: str,
) -> None:
    pre = DevPreregistration.model_validate_json(pre.model_dump_json())
    if pre.group == "G0":
        if (
            predecessor is not None
            or previous is not None
            or pre.predecessor_hash != s0_preparation_hash
        ):
            raise ValueError("S1 requires exact accepted S0 preparation receipt")
        return
    if type(predecessor) is not DevStageResult or type(previous) is not DevPreregistration:
        raise ValueError("exact completed predecessor and prior preregistration required")
    result = DevStageResult.model_validate_json(predecessor.model_dump_json())
    prior = DevPreregistration.model_validate_json(previous.model_dump_json())
    order = ("G0", "G1", "G2", "G3", "G4", "G5", "G6")
    if order.index(pre.group) != order.index(prior.group) + 1:
        raise ValueError("skipped/reversed research group")
    if (
        result.preregistration_hash != prior.record_hash
        or pre.predecessor_hash != result.record_hash
        or result.group != prior.group
        or result.stage != prior.stage
        or result.stop
        or not result.coherent
        or not result.sufficient
        or result.disposition
        not in {ResearchDisposition.KEEP_CURRENT, ResearchDisposition.RESEARCH_LEADER}
        or result.dataset_hashes != pre.dataset_hashes
        or result.strategy_hash != pre.strategy_hash
        or result.selected_hash not in pre.fixed_components
        or not set(result.fixed_components) <= set(pre.fixed_components)
    ):
        raise ValueError("failed/incomplete/wrong-lineage predecessor")


class DevTrial(BoundRecord):
    kind: Literal["REGISTER"] = "REGISTER"
    semantic_hash: Sha256Hex
    preregistration_hash: Sha256Hex
    candidate_hash: Sha256Hex
    dataset_hashes: tuple[Sha256Hex, ...]
    strategy_hash: Sha256Hex
    parent_trial_hash: Sha256Hex | None
    parent_result_hash: Sha256Hex | None
    result_informed: bool
    research_repair: bool
    repair_cause: str | None
    changed_variables: tuple[str, ...]
    unchanged_hash: Sha256Hex
    role: Literal["PRIMARY", "SENSITIVITY"]


class DevCompletion(BoundRecord):
    kind: Literal["COMPLETE"] = "COMPLETE"
    trial_hash: Sha256Hex
    preregistration_hash: Sha256Hex
    run_hash: Sha256Hex
    bundle_hash: Sha256Hex
    prior_cut_hash: Sha256Hex
    visible: Literal[True] = True


class DevReproduction(BoundRecord):
    kind: Literal["REPRODUCE"] = "REPRODUCE"
    trial_hash: Sha256Hex
    original_completion_hash: Sha256Hex
    run_hash: Sha256Hex


class DevTrialLedger(BoundRecord):
    preregistration: DevPreregistration
    history: Literal["COMPLETE", "UNKNOWN_LEGACY_INCOMPLETE"]
    unlogged_adaptation: Literal[False] = False
    entries: tuple[DevTrial | DevCompletion | DevReproduction, ...] = Field(max_length=192)

    def cut_hash(self, count: int) -> str:
        return digest(
            "DEV_LEDGER_CUT_V1",
            (self.preregistration.record_hash, tuple(e.record_hash for e in self.entries[:count])),
        )

    @model_validator(mode="after")
    def prospective(self) -> Self:
        pre = self.preregistration
        trials: dict[str, DevTrial] = {}
        completed: dict[str, DevCompletion] = {}
        variants: set[str] = set()
        candidate_seen: set[str] = set()
        repairs = 0
        for index, entry in enumerate(self.entries):
            if type(entry) is DevTrial:
                if (
                    entry.preregistration_hash != pre.record_hash
                    or entry.candidate_hash not in pre.candidate_order
                ):
                    raise ValueError("unregistered candidate/preregistration")
                if (
                    entry.dataset_hashes != pre.dataset_hashes
                    or entry.strategy_hash != pre.strategy_hash
                ):
                    raise ValueError("trial changed dataset/Strategy identity")
                if entry.candidate_hash not in candidate_seen:
                    if entry.candidate_hash != pre.candidate_order[len(candidate_seen)]:
                        raise ValueError("trial registration violated frozen candidate order")
                    candidate_seen.add(entry.candidate_hash)
                if entry.semantic_hash in variants:
                    raise ValueError("identical reproduction must not debit a material trial")
                if not set(entry.changed_variables) <= set(pre.allowed_changes) or set(
                    entry.changed_variables
                ) & set(pre.prohibited_changes):
                    raise ValueError("unlogged/prohibited adaptation")
                if entry.parent_trial_hash is not None:
                    parent = trials.get(entry.parent_trial_hash)
                    if parent is None:
                        raise ValueError("missing/future parent trial")
                if entry.result_informed:
                    result = completed.get(entry.parent_trial_hash or "")
                    if result is None or result.record_hash != entry.parent_result_hash:
                        raise ValueError(
                            "result-informed child requires exact prior visible result"
                        )
                elif entry.parent_result_hash is not None:
                    raise ValueError("undeclared result-informed adaptation")
                if entry.research_repair and entry.repair_cause != pre.repair_mechanism:
                    raise ValueError("unregistered research repair mechanism")
                repairs += entry.research_repair
                trials[entry.record_hash] = entry
                variants.add(entry.semantic_hash)
            elif type(entry) is DevCompletion:
                if entry.trial_hash not in trials or entry.trial_hash in completed:
                    raise ValueError("orphan/duplicate trial completion")
                if (
                    entry.preregistration_hash != pre.record_hash
                    or entry.prior_cut_hash != self.cut_hash(index)
                ):
                    raise ValueError("completion wrong prior ledger cut/preregistration")
                completed[entry.trial_hash] = entry
            elif type(entry) is DevReproduction:
                original = completed.get(entry.trial_hash)
                if original is None or original.record_hash != entry.original_completion_hash:
                    raise ValueError("unlogged reproduction")
            else:
                raise TypeError("closed DEV ledger entry types required")
        if len(variants) > pre.max_trials or repairs > pre.max_research_repairs:
            raise ValueError("DEV trial/research-repair budget exhausted")
        return self

    def append(self, entry: DevTrial | DevCompletion | DevReproduction) -> DevTrialLedger:
        return DevTrialLedger.create(
            **{
                **self.model_dump(exclude={"record_hash", "entries"}),
                "entries": (*self.entries, entry),
            }
        )
