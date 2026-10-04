"""Chronology, adaptivity and disclosure are separate from raw access."""

import pytest
from test_research_replay_contracts import H, changed, cost

from trader_assist_v0.research_replay.lifecycle import (
    Block,
    BlockPlan,
    LabelSpan,
    Preregistration,
    ReserveScenario,
    Trial,
    TrialLedger,
    VisibilityPolicy,
    purge,
    require_real_sealed_access,
)
from trader_assist_v0.research_replay.reporting import Summary, summary_only


def blocks():
    return BlockPlan.create(
        version="B_BLOCK_PLAN_V1",
        blocks=(
            Block.create(
                version="B_BLOCK_V1", role="DEV", start=1, end=100, instruments=("SYNTH",)
            ),
            Block.create(
                version="B_BLOCK_V1", role="OOS", start=100, end=1000, instruments=("SYNTH",)
            ),
        ),
        embargo_ns=5,
        embargo_reason="R0_residual_dependency",
        cluster_policy="PURGE_WHOLE_CLUSTER",
        holdout_instruments=(),
    )


def visibility():
    return VisibilityPolicy.create(
        version="B_VISIBILITY_V1", channel="PIPELINE", granularity="AGGREGATE_ONLY"
    )


def prereg(candidates=(H,), **updates):
    args = dict(
        version="B_PREREG_V1",
        authority="ISSUE_280_V1.2",
        stage="S0",
        predecessor_hash=None,
        hypothesis="R0 engineering correctness",
        failure_mode="causal leakage",
        champion_hash=candidates[0],
        challenger_hashes=candidates,
        allowed_changes=("FROZEN_B1_B5",),
        prohibited_changes=("PROMOTION",),
        metrics=("PIPELINE_CORRECTNESS",),
        taxonomy_hash=H,
        cost_hash=cost().record_hash,
        block_plan_hash=blocks().record_hash,
        visibility_hash=visibility().record_hash,
        stopping_rule="FROZEN_R0_FIXTURE_END",
        failure_rule="FAIL_CLOSED",
        selection_rule="NO_SELECTION_PIPELINE_ONLY",
        max_trials=64,
        max_research_repairs=2,
        minimum_events=1,
        minimum_clusters=1,
        minimum_cells=1,
        max_horizon_ns=1000,
        reserve_hashes=(),
        diagnostics="SACRIFICIAL_ONLY",
        promotion="PROHIBITED",
        claim="PIPELINE_CORRECTNESS_ONLY",
    )
    args.update(updates)
    return Preregistration.create(**args)


def ledger(candidates=(H,), **updates):
    registration = prereg(candidates, **updates)
    trials = tuple(
        Trial.create(
            version="B_TRIAL_V1",
            semantic_hash=h,
            preregistration_hash=registration.record_hash,
            parent_trial_hash=None,
            result_informed=False,
            research_repair=False,
            result_hash=None,
            visibility="PIPELINE",
        )
        for h in candidates
    )
    return TrialLedger.create(
        version="B_LEDGER_V1",
        preregistration=registration,
        history="COMPLETE",
        trials=trials,
        reproductions=(),
    )


def test_forward_tail_purge_embargo_cluster_and_holdout():
    spans = tuple(
        LabelSpan.create(
            version="B_LABEL_SPAN_V1",
            thesis_id=t,
            cluster_id=c,
            instrument="SYNTH",
            start=s,
            outcome_end=e,
        )
        for t, c, s, e in (
            ("safe", "safe", 20, 90),
            ("tail", "shared", 90, 105),
            ("nested", "shared", 30, 40),
            ("embargo", "other", 90, 97),
        )
    )
    assert purge(blocks(), spans) == ("embargo", "nested", "tail")
    with pytest.raises(ValueError, match="held-out"):
        changed(blocks(), holdout_instruments=("SYNTH",))
    with pytest.raises(ValueError):
        prereg(stage="S6")
    with pytest.raises(ValueError, match="predecessor"):
        prereg(stage="S2")


def test_trial_reproduction_adaptivity_ancestry_budget_and_unknown_history():
    value = ledger()
    assert changed(value, reproductions=(H,)).trials == value.trials
    with pytest.raises(ValueError, match="reproduction"):
        changed(value, trials=value.trials + value.trials)
    with pytest.raises(ValueError, match="parent"):
        changed(value, trials=(changed(value.trials[0], result_informed=True),))
    with pytest.raises(ValueError, match="budget"):
        ledger((H, "b" * 64), max_trials=1)
    assert (
        changed(value, history="UNKNOWN_LEGACY_INCOMPLETE").history == "UNKNOWN_LEGACY_INCOMPLETE"
    )


def test_synthetic_reserve_one_shot_no_relabel_no_sealed_opener():
    scenario = ReserveScenario.create(
        version="B_RESERVE_SCENARIO_V1",
        reserve_hash=H,
        configuration_hash=H,
        state="UNOPENED",
        source="SYNTHETIC_DESCRIPTOR",
    )
    used = scenario.summary_request(H)
    assert scenario.state == "UNOPENED" and used.state == "SUMMARY_CONSUMED"
    for reserve, config in ((used, H), (scenario, "b" * 64)):
        with pytest.raises(PermissionError):
            reserve.summary_request(config)
    with pytest.raises(PermissionError, match="CONTROL_REPLAN"):
        require_real_sealed_access()
    with pytest.raises(ValueError):
        changed(visibility(), real_sealed_access=True)


def test_summary_projection_rejects_raw_fields():
    value = Summary.create(
        version="B_SUMMARY_V1",
        claim="PIPELINE_CORRECTNESS_ONLY",
        status="COMPLETE",
        roster_count=1,
        thesis_count=1,
        cluster_count=1,
        paired_count=0,
        unmatched_count=0,
        participation_counts=(("PASS", 1),),
        setup_counts=(("SWEEP_RECLAIM", 1),),
        net_expectancy=0,
        cost_burden=0,
        maximum_drawdown=0,
        tail_concentration=None,
        ambiguity_count=0,
        uncertainty_unit="CORRELATION_CLUSTER_THESIS",
    )
    projection = summary_only(value, visibility())
    assert "record_hash" not in projection and "timestamps" not in projection
    with pytest.raises(ValueError):
        Summary.model_validate({**value.model_dump(), "extreme_event_ids": [H]})
