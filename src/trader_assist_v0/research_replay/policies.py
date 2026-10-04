"""Authority-qualified finite causal research families; old G4 semantics are untouched."""

from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import FiniteDecimal, Sha256Hex
from trader_assist_v0.research_data.contracts import BoundRecord

from .contracts import Decision, digest

ROOT = "https://github.com/woshixiong/trader-assist-v0/issues/"
EA_AUTHORITY = ROOT + "161#issuecomment-5969358545"
AUTHORITIES = {
    "EA": EA_AUTHORITY,
    "L": ROOT + "150",
    "R": ROOT + "150",
    "A": ROOT + "150",
    "E": ROOT + "85",
    "BASELINE": ROOT + "85",
    "CHAMPION": ROOT + "161#issuecomment-5977723712",
}
BASELINES = (
    "SIMPLE_SWEEP_RECLAIM_BASELINE",
    "SIMPLE_CLOSE_BREAKOUT_BASELINE",
    "DONCHIAN_TURTLE_BREAKOUT_BASELINE",
    "SIMPLE_RANGE_EDGE_REJECTION_BASELINE",
)
FAMILIES = {
    "EA": tuple(f"EA{i}" for i in range(7)),
    "L": tuple(f"L{i}" for i in range(7)),
    "R": tuple(f"R{i}" for i in range(5)),
    "E": tuple(f"E{i}" for i in range(10)),
    "A": tuple(f"A{i}" for i in range(4)),
    "BASELINE": BASELINES,
    "CHAMPION": ("CURRENT_THREE_SETUP_CHAMPION",),
}
REQUIRED = {
    "L1": {"adverse_bps"},
    "L2": {"volatility_multiple"},
    "L3": {"timeout_ns", "min_progress_bps"},
    "E0": {"fixed_r"},
    "E2": {"scale_fraction"},
    "E3": {"trail_bps"},
    "E5": {"giveback_fraction"},
    "R2": {"cooldown_ns"},
    "A1": {"progress_bps", "add_fraction"},
    "A2": {"add_fraction"},
    "A3": {"add_fraction"},
    "EA1": {"room_to_cost"},
    "EA2": {"room_to_cost"},
    "EA3": {"room_to_cost"},
    "EA4": {"room_to_cost"},
    "EA5": {"room_to_cost"},
    "EA6": {"room_to_cost"},
    "L6": {"adverse_bps", "timeout_ns"},
    "E8": {"trail_bps"},
    "E9": {"giveback_fraction"},
}
COMPLEX = {"EA6", "L6", "E9", "A3"}
COMPONENTS = {
    "EA6": {"EA1", "EA2", "EA3", "EA4", "EA5"},
    "L6": {"L0", "L1", "L3", "L4"},
    "E9": {"E1", "E3", "E5", "E6"},
    "A3": {"A0", "A1", "A2"},
}


class PrerequisiteReceipt(BoundRecord):
    components: tuple[str, ...] = Field(min_length=1)
    evidence_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    role: Literal["R0_WIRING_ONLY"]


class PolicySpec(BoundRecord):
    family: Literal["CHAMPION", "BASELINE", "EA", "L", "R", "E", "A"]
    code: str
    authority: str
    semantics: Literal["ISSUE_FAMILIES_B_V1"]
    parameters: tuple[tuple[str, FiniteDecimal], ...]
    prerequisite: PrerequisiteReceipt | None = None

    @model_validator(mode="after")
    def frozen_family(self) -> Self:
        if self.authority != AUTHORITIES[self.family] or self.code not in FAMILIES[self.family]:
            raise ValueError("bare/legacy/unauthorized policy identity")
        params = dict(self.parameters)
        if tuple(sorted(self.parameters)) != self.parameters or len(params) != len(self.parameters):
            raise ValueError("policy parameters must be sorted and unique")
        if not REQUIRED.get(self.code, set()) <= params.keys():
            raise ValueError("explicit registered policy inputs required")
        if any(v < 0 for v in params.values()):
            raise ValueError("policy inputs must be nonnegative")
        for key in {"scale_fraction", "add_fraction", "giveback_fraction"} & params.keys():
            if not 0 < params[key] <= 1:
                raise ValueError("fraction outside registered bounds")
        if self.prerequisite and not COMPONENTS.get(self.code, set()) <= set(
            self.prerequisite.components
        ):
            raise ValueError("named simple-policy prerequisites missing")
        return self

    @property
    def qualified_id(self) -> str:
        return digest(
            "B_POLICY_AUTHORITY", (self.authority, self.semantics, self.family, self.code)
        )


class PolicyContext(BoundRecord):
    at: int = Field(gt=0)
    source_cutoff: int = Field(gt=0)
    input_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    feature_hashes: tuple[Sha256Hex, ...]
    evaluable: bool
    thesis_valid: bool
    champion_take: bool
    price_core: bool
    failed_auction: bool
    profile_confirmation: bool
    binance_confirmation: bool
    okx_confirmation: bool
    economics_improvable: bool
    room_to_cost: FiniteDecimal = Field(ge=0)
    adverse_bps: FiniteDecimal = Field(ge=0)
    progress_bps: FiniteDecimal
    volatility_bps: FiniteDecimal = Field(gt=0)
    elapsed_ns: int = Field(ge=0)
    structure_failed: bool
    structural_stop_hit: bool
    microstructure_failed: bool
    structural_target: bool
    fresh_structure: bool
    structural_level: FiniteDecimal | None
    fresh_condition_ns: int | None = Field(default=None, gt=0)
    fresh_setup: bool
    fresh_microstructure: bool
    reversal: bool
    retest: bool
    high_water_bps: FiniteDecimal = Field(ge=0)
    giveback_fraction: FiniteDecimal = Field(ge=0)
    net_r: FiniteDecimal
    attempts: int = Field(ge=0)
    max_attempts: int = Field(gt=0, le=20)
    cumulative_cost_bps: FiniteDecimal = Field(ge=0)
    cost_budget_bps: FiniteDecimal = Field(ge=0)
    since_scratch_ns: int = Field(ge=0)
    winner: bool
    regime_trending: bool
    continuation: bool
    sweep: bool
    close_breakout: bool
    donchian_breakout: bool
    range_rejection: bool

    @model_validator(mode="after")
    def causal(self) -> Self:
        if self.source_cutoff > self.at:
            raise ValueError("policy context contains future source")
        if self.fresh_condition_ns is not None and self.fresh_condition_ns > self.source_cutoff:
            raise ValueError("fresh condition is in the future")
        return self


class PolicyAction(BoundRecord):
    policy_hash: Sha256Hex
    context_hash: Sha256Hex
    participation: Decision
    action: Literal["HOLD", "ENTER", "SCRATCH", "REENTER", "EXIT", "SCALE_OUT", "ADD", "RATCHET"]
    fraction: FiniteDecimal = Field(ge=0, le=1)
    reason: str


def evaluate(policy: PolicySpec, context: PolicyContext) -> PolicyAction:
    policy = PolicySpec.model_validate_json(policy.model_dump_json())
    c = PolicyContext.model_validate_json(context.model_dump_json())
    p, code = dict(policy.parameters), policy.code

    def action(
        kind: str, reason: str, decision: Decision = "TAKE", fraction: Decimal = Decimal(1)
    ) -> PolicyAction:
        return PolicyAction.create(
            version="B_ACTION_V1",
            policy_hash=policy.record_hash,
            context_hash=c.record_hash,
            participation=decision,
            action=kind,
            fraction=fraction,
            reason=reason,
        )

    if not c.evaluable:
        return action("HOLD", "MISSING_FEATURE_OR_PATH", "NOT_EVALUABLE", Decimal(0))
    if not c.thesis_valid:
        return action("EXIT", "THESIS_INVALIDATED", "BLOCKED")
    if code in COMPLEX and policy.prerequisite is None:
        return action("HOLD", "SIMPLE_COMPONENT_EVIDENCE_REQUIRED", "BLOCKED", Decimal(0))
    if policy.family in {"EA", "CHAMPION", "BASELINE"}:
        ready = c.champion_take
        if policy.family == "BASELINE":
            ready = {
                BASELINES[0]: c.sweep,
                BASELINES[1]: c.close_breakout,
                BASELINES[2]: c.donchian_breakout,
                BASELINES[3]: c.range_rejection,
            }[code]
        elif code != "EA0" and policy.family == "EA":
            ready = (
                c.price_core
                and {
                    "EA1": True,
                    "EA2": c.failed_auction,
                    "EA3": c.profile_confirmation,
                    "EA4": c.binance_confirmation,
                    "EA5": c.okx_confirmation,
                    "EA6": c.failed_auction
                    and c.profile_confirmation
                    and c.binance_confirmation
                    and c.okx_confirmation,
                }[code]
            )
        if not ready:
            return action("HOLD", "ACTIVATION_PENDING", "WAIT", Decimal(0))
        if c.room_to_cost < p.get("room_to_cost", Decimal(0)):
            return action(
                "HOLD", "ROOM_TO_COST", "WAIT" if c.economics_improvable else "PASS", Decimal(0)
            )
        return action("ENTER", "CAUSAL_ACTIVATION")
    if policy.family == "L":
        failed = {
            "L0": c.structural_stop_hit,
            "L1": c.adverse_bps >= p.get("adverse_bps", Decimal("Infinity")),
            "L2": c.adverse_bps
            >= c.volatility_bps * p.get("volatility_multiple", Decimal("Infinity")),
            "L3": c.elapsed_ns >= p.get("timeout_ns", Decimal("Infinity"))
            and c.progress_bps < p.get("min_progress_bps", Decimal(0)),
            "L4": c.structure_failed,
            "L5": c.microstructure_failed,
            "L6": c.adverse_bps >= p.get("adverse_bps", Decimal("Infinity"))
            or c.elapsed_ns >= p.get("timeout_ns", Decimal("Infinity"))
            or c.structure_failed,
        }[code]
        return action(
            "SCRATCH" if failed else "HOLD", "ATTEMPT_FAILURE" if failed else "ATTEMPT_VALID"
        )
    if policy.family == "R":
        allowed = c.attempts < c.max_attempts and c.cumulative_cost_bps < c.cost_budget_bps
        allowed &= {
            "R0": False,
            "R1": True,
            "R2": c.since_scratch_ns >= p.get("cooldown_ns", Decimal("Infinity")),
            "R3": c.fresh_setup
            and c.fresh_condition_ns is not None
            and c.fresh_condition_ns > c.at - c.since_scratch_ns,
            "R4": c.fresh_microstructure
            and c.fresh_condition_ns is not None
            and c.fresh_condition_ns > c.at - c.since_scratch_ns,
        }[code]
        return action(
            "REENTER" if allowed else "HOLD",
            "FRESH_REENTRY" if allowed else "REENTRY_BLOCKED",
            "TAKE" if allowed else "WAIT",
        )
    if policy.family == "A":
        allowed = c.winner and c.progress_bps > 0 and c.cumulative_cost_bps < c.cost_budget_bps
        allowed &= {
            "A0": False,
            "A1": c.progress_bps >= p.get("progress_bps", Decimal("Infinity")),
            "A2": c.fresh_structure and c.retest,
            "A3": c.continuation,
        }[code]
        return action(
            "ADD" if allowed else "HOLD",
            "WINNER_ADD" if allowed else "NO_ADD",
            fraction=p.get("add_fraction", Decimal(0)) if allowed else Decimal(0),
        )
    hit = {
        "E0": c.net_r >= p.get("fixed_r", Decimal("Infinity")),
        "E1": c.structural_target,
        "E2": c.structural_target,
        "E3": c.high_water_bps - c.progress_bps >= p.get("trail_bps", Decimal("Infinity")),
        "E4": c.fresh_structure,
        "E5": c.giveback_fraction >= p.get("giveback_fraction", Decimal("Infinity")),
        "E6": c.reversal,
        "E7": (c.reversal and c.retest) or c.structure_failed,
        "E8": (not c.regime_trending and c.structural_target)
        or c.high_water_bps - c.progress_bps >= p.get("trail_bps", Decimal("Infinity")),
        "E9": not c.continuation
        or c.giveback_fraction >= p.get("giveback_fraction", Decimal("Infinity")),
    }[code]
    kind = "RATCHET" if code == "E4" else "SCALE_OUT" if code == "E2" else "EXIT"
    return action(
        kind if hit else "HOLD",
        "CAUSAL_EXIT" if hit else "HOLD_WINNER",
        fraction=p.get("scale_fraction", Decimal(1)) if hit else Decimal(0),
    )
