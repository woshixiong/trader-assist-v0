"""Metadata-only #280 planning. No transition here opens or relabels raw evidence."""

from typing import Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex
from trader_assist_v0.research_data.contracts import BoundRecord


class Block(BoundRecord):
    role: Literal["DEV", "OOS", "VALIDATION_RESERVE", "LOCKBOX_RESERVE"]
    start: int = Field(gt=0)
    end: int = Field(gt=0)
    instruments: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.start >= self.end or len(set(self.instruments)) != len(self.instruments):
            raise ValueError("invalid half-open chronological block")
        return self


class BlockPlan(BoundRecord):
    blocks: tuple[Block, ...] = Field(min_length=2)
    embargo_ns: int = Field(ge=0)
    embargo_reason: str = Field(min_length=1)
    cluster_policy: Literal["PURGE_WHOLE_CLUSTER"]
    holdout_instruments: tuple[str, ...]

    @model_validator(mode="after")
    def chronology(self) -> Self:
        for first, second in zip(self.blocks, self.blocks[1:], strict=False):
            if first.end > second.start:
                raise ValueError("blocks must be chronological and nonoverlapping")
        for block in self.blocks:
            if block.role == "DEV" and set(block.instruments) & set(self.holdout_instruments):
                raise ValueError("held-out instruments cannot enter DEV")
        if not any(b.role == "DEV" for b in self.blocks) or not any(
            b.role == "OOS" for b in self.blocks
        ):
            raise ValueError("DEV and chronological OOS required")
        return self


class LabelSpan(BoundRecord):
    thesis_id: str = Field(min_length=1)
    cluster_id: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    start: int = Field(gt=0)
    outcome_end: int = Field(gt=0)

    @model_validator(mode="after")
    def forward(self) -> Self:
        if self.outcome_end < self.start:
            raise ValueError("outcome end precedes observation")
        return self


def purge(plan: BlockPlan, spans: tuple[LabelSpan, ...]) -> tuple[str, ...]:
    """Return excluded DEV Theses; endpoints include suppressed counterfactual tails."""
    plan = BlockPlan.model_validate_json(plan.model_dump_json())
    spans = tuple(LabelSpan.model_validate_json(s.model_dump_json()) for s in spans)
    dev = tuple(b for b in plan.blocks if b.role == "DEV")
    oos = tuple(b for b in plan.blocks if b.role == "OOS")
    excluded_clusters: set[str] = set()
    for span in spans:
        if not any(b.start <= span.start < b.end and span.instrument in b.instruments for b in dev):
            continue
        if any(span.start < b.end and span.outcome_end >= b.start - plan.embargo_ns for b in oos):
            excluded_clusters.add(span.cluster_id)
    # Whole-cluster leakage: a cluster touching either side cannot train on its other member.
    oos_clusters = {
        s.cluster_id
        for s in spans
        if any(b.start <= s.start < b.end and s.instrument in b.instruments for b in oos)
    }
    excluded_clusters |= oos_clusters
    return tuple(
        sorted(
            {
                s.thesis_id
                for s in spans
                if s.cluster_id in excluded_clusters
                and any(b.start <= s.start < b.end for b in dev)
            }
        )
    )


class Preregistration(BoundRecord):
    authority: Literal["ISSUE_280_V1.2"]
    stage: Literal["S0", "S1", "S2", "S3", "S4", "S5"]
    predecessor_hash: Sha256Hex | None
    hypothesis: str = Field(min_length=1)
    failure_mode: str = Field(min_length=1)
    champion_hash: Sha256Hex
    challenger_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    allowed_changes: tuple[str, ...] = Field(min_length=1)
    prohibited_changes: tuple[str, ...] = Field(min_length=1)
    metrics: tuple[str, ...] = Field(min_length=1)
    taxonomy_hash: Sha256Hex
    cost_hash: Sha256Hex
    block_plan_hash: Sha256Hex
    visibility_hash: Sha256Hex
    stopping_rule: str = Field(min_length=1)
    failure_rule: str = Field(min_length=1)
    selection_rule: Literal["NO_SELECTION_PIPELINE_ONLY"]
    max_trials: int = Field(gt=0, le=64)
    max_research_repairs: int = Field(ge=0, le=20)
    minimum_events: int = Field(gt=0)
    minimum_clusters: int = Field(gt=0)
    minimum_cells: int = Field(gt=0)
    max_horizon_ns: int = Field(gt=0)
    reserve_hashes: tuple[Sha256Hex, ...]
    diagnostics: Literal["SACRIFICIAL_ONLY"]
    promotion: Literal["PROHIBITED"]
    claim: Literal["PIPELINE_CORRECTNESS_ONLY"]

    @model_validator(mode="after")
    def sequence(self) -> Self:
        if self.stage != "S0" and self.predecessor_hash is None:
            raise ValueError("frozen sequencing predecessor required")
        return self


class Trial(BoundRecord):
    semantic_hash: Sha256Hex
    preregistration_hash: Sha256Hex
    parent_trial_hash: Sha256Hex | None
    result_informed: bool
    research_repair: bool
    result_hash: Sha256Hex | None
    visibility: Literal["PIPELINE", "SUMMARY_SCENARIO"]


class TrialLedger(BoundRecord):
    preregistration: Preregistration
    history: Literal["COMPLETE", "UNKNOWN_LEGACY_INCOMPLETE"]
    trials: tuple[Trial, ...]
    reproductions: tuple[Sha256Hex, ...]

    @model_validator(mode="after")
    def budgets(self) -> Self:
        seen: set[str] = set()
        variants: set[str] = set()
        repairs = 0
        for trial in self.trials:
            if trial.preregistration_hash != self.preregistration.record_hash:
                raise ValueError("trial changed certification identity")
            if trial.semantic_hash in variants:
                raise ValueError("identical reproduction must not consume material trial")
            if trial.parent_trial_hash is not None and trial.parent_trial_hash not in seen:
                raise ValueError("missing adaptation ancestry")
            if trial.result_informed and trial.parent_trial_hash is None:
                raise ValueError("result-informed variant requires parent")
            if (
                trial.parent_trial_hash
                and trial.result_informed
                and not any(
                    t.record_hash == trial.parent_trial_hash and t.result_hash for t in self.trials
                )
            ):
                raise ValueError("adaptation requires a recorded visible result")
            variants.add(trial.semantic_hash)
            seen.add(trial.record_hash)
            repairs += trial.research_repair
        if (
            len(variants) > self.preregistration.max_trials
            or repairs > self.preregistration.max_research_repairs
        ):
            raise ValueError("research trial/repair budget exceeded")
        if not set(self.reproductions) <= variants:
            raise ValueError("unlogged reproduction")
        return self


class VisibilityPolicy(BoundRecord):
    channel: Literal["PIPELINE", "VALIDATION_SUMMARY_SCENARIO", "LOCKBOX_SUMMARY_SCENARIO"]
    granularity: Literal["AGGREGATE_ONLY"]
    diagnostics: Literal[False] = False
    real_sealed_access: Literal[False] = False


class ReserveScenario(BoundRecord):
    """Synthetic metadata exercise only: this is not an evidence access receipt."""

    reserve_hash: Sha256Hex
    configuration_hash: Sha256Hex
    state: Literal["UNOPENED", "SUMMARY_CONSUMED", "DIAGNOSTICALLY_CONTAMINATED"]
    source: Literal["SYNTHETIC_DESCRIPTOR"]

    def summary_request(self, configuration_hash: str) -> "ReserveScenario":
        checked = ReserveScenario.model_validate_json(self.model_dump_json())
        if checked.state != "UNOPENED" or configuration_hash != checked.configuration_hash:
            raise PermissionError("consumed/contaminated/adapted reserve scenario refused")
        return ReserveScenario.create(
            **{
                **checked.model_dump(exclude={"record_hash"}),
                "state": "SUMMARY_CONSUMED",
            }
        )


def require_real_sealed_access() -> None:
    raise PermissionError("CONTROL_REPLAN: no sealed opener or diagnostic unlock in Package B")
