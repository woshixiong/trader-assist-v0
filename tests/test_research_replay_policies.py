"""Synthetic semantic scenarios for every authority-qualified required family."""

from decimal import Decimal

import pytest
from test_research_replay_contracts import H, changed, raw

from trader_assist_v0.research_replay.policies import (
    AUTHORITIES,
    BASELINES,
    COMPLEX,
    COMPONENTS,
    FAMILIES,
    REQUIRED,
    PolicyContext,
    PolicySpec,
    PrerequisiteReceipt,
    evaluate,
)


def policy(family="EA", code="EA1", *, prerequisite=False, **updates):
    parameters = {
        key: Decimal("0.5") if "fraction" in key else Decimal(10)
        for key in REQUIRED.get(code, set())
    }
    receipt = (
        PrerequisiteReceipt.create(
            version="B_R0_PREREQUISITE_V1",
            components=tuple(sorted(COMPONENTS.get(code, {"R0"}))),
            evidence_hashes=(H,),
            role="R0_WIRING_ONLY",
        )
        if prerequisite
        else None
    )
    return PolicySpec.create(
        version="B_POLICY_V1",
        family=family,
        code=code,
        authority=AUTHORITIES[family],
        semantics="ISSUE_FAMILIES_B_V1",
        parameters=tuple(sorted(parameters.items())),
        prerequisite=receipt,
        **updates,
    )


def context(**updates):
    flags = (
        "evaluable thesis_valid champion_take price_core failed_auction profile_confirmation "
        "binance_confirmation okx_confirmation economics_improvable structure_failed "
        "structural_stop_hit microstructure_failed structural_target fresh_structure fresh_setup "
        "fresh_microstructure reversal retest winner regime_trending continuation sweep "
        "close_breakout donchian_breakout range_rejection"
    ).split()
    args = {key: False for key in flags}
    args.update(
        version="B_CONTEXT_V1",
        at=100,
        source_cutoff=100,
        input_hashes=(raw().record_hash,),
        feature_hashes=(),
        evaluable=True,
        thesis_valid=True,
        room_to_cost=Decimal(20),
        adverse_bps=Decimal(0),
        progress_bps=Decimal(0),
        volatility_bps=Decimal(1),
        elapsed_ns=0,
        high_water_bps=Decimal(0),
        giveback_fraction=Decimal(0),
        net_r=Decimal(0),
        attempts=0,
        max_attempts=2,
        cumulative_cost_bps=Decimal(0),
        cost_budget_bps=Decimal(100),
        since_scratch_ns=0,
        structural_level=None,
    )
    args.update(updates)
    return PolicyContext.create(**args)


@pytest.mark.parametrize("code", FAMILIES["EA"])
def test_activation_semantics_and_wait_pass(code):
    p = policy(code=code, prerequisite=True)
    ready = context(
        champion_take=True,
        price_core=True,
        failed_auction=True,
        profile_confirmation=True,
        binance_confirmation=True,
        okx_confirmation=True,
    )
    assert evaluate(p, ready).action == "ENTER"
    if code != "EA0":
        assert evaluate(p, changed(ready, room_to_cost=Decimal(1))).participation == "PASS"
        assert (
            evaluate(
                p, changed(ready, room_to_cost=Decimal(1), economics_improvable=True)
            ).participation
            == "WAIT"
        )
    assert evaluate(p, context()).participation == "WAIT"


@pytest.mark.parametrize("code", FAMILIES["L"])
def test_loss_semantics(code):
    p = policy("L", code, prerequisite=True)
    hit = context(
        structural_stop_hit=True,
        structure_failed=True,
        microstructure_failed=True,
        adverse_bps=Decimal(20),
        elapsed_ns=20,
        progress_bps=Decimal(-1),
    )
    assert evaluate(p, hit).action == "SCRATCH"
    assert evaluate(p, context()).action == "HOLD"
    if code == "L0":
        assert evaluate(p, context(structure_failed=True)).action == "HOLD"


@pytest.mark.parametrize("code", FAMILIES["R"])
def test_reentry_family_semantics_and_budget(code):
    p = policy("R", code)
    ready = context(
        fresh_setup=True,
        fresh_microstructure=True,
        since_scratch_ns=20,
        attempts=1,
        fresh_condition_ns=90,
    )
    assert evaluate(p, ready).action == ("HOLD" if code == "R0" else "REENTER")
    assert evaluate(p, changed(ready, attempts=2)).action == "HOLD"
    assert evaluate(p, changed(ready, thesis_valid=False)).participation == "BLOCKED"
    if code in {"R2", "R3", "R4"}:
        assert evaluate(p, context()).action == "HOLD"


@pytest.mark.parametrize("code", FAMILIES["E"])
def test_all_exit_rules_are_causal_finite_rules(code):
    p = policy("E", code, prerequisite=True)
    ready = context(
        structural_target=True,
        fresh_structure=True,
        structural_level=Decimal(101),
        reversal=True,
        retest=True,
        high_water_bps=Decimal(30),
        progress_bps=Decimal(0),
        giveback_fraction=Decimal("0.75"),
        net_r=Decimal(20),
        continuation=False,
    )
    assert evaluate(p, ready).action == (
        "SCALE_OUT" if code == "E2" else "RATCHET" if code == "E4" else "EXIT"
    )
    quiet = context(continuation=True)
    assert evaluate(p, quiet).action == "HOLD"


@pytest.mark.parametrize("code", FAMILIES["A"])
def test_add_only_winners_with_budget(code):
    p = policy("A", code, prerequisite=True)
    ready = context(
        winner=True, progress_bps=Decimal(20), fresh_structure=True, retest=True, continuation=True
    )
    assert evaluate(p, ready).action == ("HOLD" if code == "A0" else "ADD")
    assert evaluate(p, changed(ready, progress_bps=Decimal(-1))).action == "HOLD"
    assert evaluate(p, changed(ready, cumulative_cost_bps=Decimal(100))).action == "HOLD"


@pytest.mark.parametrize("code", BASELINES)
def test_simple_baselines_and_current_champion(code):
    p = policy("BASELINE", code)
    ready = context(sweep=True, close_breakout=True, donchian_breakout=True, range_rejection=True)
    assert evaluate(p, ready).action == "ENTER" and evaluate(p, context()).action == "HOLD"
    champion = policy("CHAMPION", "CURRENT_THREE_SETUP_CHAMPION")
    assert evaluate(champion, context(champion_take=True)).action == "ENTER"


@pytest.mark.parametrize("code", sorted(COMPLEX))
def test_complex_requires_named_incremental_prerequisites(code):
    p = policy(code[0] if code[0] != "E" or not code.startswith("EA") else "EA", code)
    assert evaluate(p, context()).participation == "BLOCKED"


def test_authority_collision_future_context_and_missing_feature():
    p = policy(code="EA2")
    with pytest.raises(ValueError, match="unauthorized"):
        changed(p, authority="VNEXT_G4_V1")
    with pytest.raises(ValueError, match="future"):
        context(source_cutoff=101)
    assert evaluate(p, context(evaluable=False)).participation == "NOT_EVALUABLE"
    assert p.qualified_id != "EA2" and "VNEXT_G4" not in p.semantics
