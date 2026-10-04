"""Bounded roster identity, actual harness prefix decisions and paired reporting."""

import os
import subprocess
import sys
from decimal import Decimal, localcontext

import pytest
from test_research_data_contracts import dataset
from test_research_replay_contracts import BASE, H, changed, cost, opportunity, raw
from test_research_replay_lifecycle import blocks, ledger, visibility
from test_research_replay_paths import decision
from test_research_replay_policies import context, policy

from trader_assist_v0.research_replay.contracts import Attempt, Fill, ResearchRunSpec, digest
from trader_assist_v0.research_replay.harness import (
    CandidatePlan,
    ContextFrame,
    _canonical_decision_metrics,
    snapshot,
    trial_identity,
    validate_inputs,
)
from trader_assist_v0.research_replay.paths import measure_path
from trader_assist_v0.research_replay.reporting import (
    CandidateResult,
    EntryTrigger,
    bundle_fingerprint,
    pair,
    summarize,
)


def test_derived_decision_metrics_canonicalize_repeating_ratios_before_validation():
    names = (
        "progress_bps",
        "adverse_bps",
        "high_water_bps",
        "giveback_fraction",
        "net_r",
        "cumulative_cost_bps",
    )
    with localcontext() as arithmetic:
        arithmetic.prec = 80
        repeating = Decimal(1) / Decimal(6)
    with pytest.raises(ValueError, match="canonical wire length"):
        context(giveback_fraction=repeating)
    outputs = []
    for precision in (6, 28, 80):
        with localcontext() as ambient:
            ambient.prec = precision
            metrics = _canonical_decision_metrics(**dict.fromkeys(names, repeating))
            assert set(metrics.values()) == {Decimal("0.166666666667")}
            bound = context(**metrics)
            assert type(bound).model_validate_json(bound.model_dump_json()) == bound
            outputs.append((bound.record_hash, bound.model_dump_json()))
    assert outputs[0] == outputs[1] == outputs[2]
    assert _canonical_decision_metrics(
        progress_bps=Decimal("-1.0000000000005"),
        net_r=Decimal("1.0000000000015"),
    ) == {"progress_bps": Decimal("-1.000000000000"), "net_r": Decimal("1.000000000002")}
    with pytest.raises(ValueError, match="nonfinite"):
        _canonical_decision_metrics(net_r=Decimal("NaN"))


def candidate(**updates):
    args = dict(
        version="B_CANDIDATE_V1",
        participation=policy(),
        loss=policy("L", "L0"),
        reentry=policy("R", "R0"),
        exit=policy("E", "E0"),
        add=policy("A", "A0"),
        max_attempts=2,
        max_adds=0,
        cost_budget_bps=Decimal(100),
        winner_progress_bps=Decimal(10),
        role="REFERENCE",
    )
    args.update(updates)
    return CandidatePlan.create(**args)


def run_fixture(*, rows=None, op=None, candidates=None, frames=None, cost_model=None, ds=None):
    ds = ds or dataset(
        source="NAUTILUS_HYPERLIQUID",
        venue="HYPERLIQUID",
        instruments=("SYNTH",),
        datatypes=("BBO",),
        end_ns=10000,
    )
    rows = rows or (raw(ds=ds), raw(150, ds=ds))
    op = op or opportunity(prefix_hashes=(rows[0].record_hash,))
    candidates = candidates or (candidate(),)
    frames = frames or (
        ContextFrame.create(
            version="B_FRAME_V1",
            opportunity_hash=op.record_hash,
            context=context(input_hashes=(rows[0].record_hash,), price_core=True),
            features=(),
        ),
    )
    cost_model = cost_model or cost()
    trial_ledger = ledger(
        tuple(c.record_hash for c in candidates), cost_hash=cost_model.record_hash
    )
    run = ResearchRunSpec.create(
        version="B_RUN_V1",
        package="CAUSAL_RESEARCH_DERIVATION_STRATEGY_REPLAY_FOUNDATION_1",
        base=BASE,
        release=BASE,
        runtime="R0_ENGINEERING_FIXTURE",
        strategy_hash=op.strategy_hash,
        dataset_hashes=(ds.record_hash,),
        feature_hashes=(),
        policy_hashes=tuple(c.record_hash for c in candidates),
        roster_hash=digest("B_ROSTER", (op.record_hash,)),
        cost=cost_model,
        horizon_ns=100,
        max_observations=100,
        max_candidates=4,
        trial_ledger_hash=trial_ledger.record_hash,
        block_plan_hash=blocks().record_hash,
        visibility_hash=visibility().record_hash,
        correlation_method="RETAINED_R0_EPISODE",
        seed=7,
    )
    trial_ledger = changed(
        trial_ledger,
        trials=tuple(
            changed(t, semantic_hash=trial_identity(run, c))
            for t, c in zip(trial_ledger.trials, candidates, strict=True)
        ),
    )
    run = changed(run, trial_ledger_hash=trial_ledger.record_hash)
    return run, (ds,), rows, (op,), candidates, frames, trial_ledger, blocks(), visibility()


def result(*, op=None, policy_hash=H, cash=Decimal(0), participation="PASS", **updates):
    op = op or opportunity()
    snap = changed(
        decision(op),
        decision=participation,
        policy_hash=policy_hash,
        cost_hash=updates.get("cost_hash", cost().record_hash),
    )
    path = measure_path(snap, op, (raw(150),), as_of=200)
    args = dict(
        version="B_CANDIDATE_RESULT_V1",
        candidate_hash=policy_hash,
        opportunity_hash=op.record_hash,
        market_event_id=op.market_event_id,
        thesis_id=op.thesis_id,
        cluster_id=op.cluster_id,
        setup=op.setup,
        regime=op.regime,
        snapshots=(snap,),
        trigger_path=path,
        fill_path=None,
        attempt_hashes=(),
        fill_hashes=(),
        policy_action_hashes=(),
        cost_hash=cost().record_hash,
        net_cash=cash,
        net_r=cash,
        fee_cash=Decimal(0),
        funding_cash=Decimal(0),
        outstanding_size=Decimal(0),
        limitations=(),
        terminal="SUPPRESSED",
    )
    args.update(updates)
    return CandidateResult.create(**args)


def test_fixed_roster_prefix_boundaries_and_no_network(monkeypatch):
    import socket

    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("network forbidden")
    )
    args = run_fixture()
    validate_inputs(*args)
    run, _, _, roster, candidates, frames, *_ = args
    first = snapshot(run, roster[0], candidates[0], frames[0])
    assert first.decision == "TAKE"
    future = raw(210, ds=args[1][0])
    expanded = (*args[:2], args[2] + (future,), *args[3:])
    validate_inputs(*expanded)
    assert snapshot(run, roster[0], candidates[0], frames[0]).record_hash == first.record_hash
    bad_frame = changed(
        frames[0], context=changed(frames[0].context, input_hashes=(future.record_hash,))
    )
    with pytest.raises(ValueError, match="future"):
        validate_inputs(*expanded[:5], (bad_frame,), *expanded[6:])
    with pytest.raises(ValueError, match="bounded"):
        validate_inputs(changed(run, max_observations=1), *args[1:])
    with pytest.raises(ValueError, match="candidate roster"):
        validate_inputs(changed(run, policy_hashes=(H,)), *args[1:])


def test_wait_pass_nonfill_denominator_and_matched_costs():
    left = result(participation="PASS")
    right = result(policy_hash="b" * 64, participation="WAIT")
    paired = pair(left, right)
    assert paired.comparable and paired.delta_cash == 0
    missing = changed(right, net_cash=None, terminal="NONFILL")
    assert not pair(left, missing).comparable
    summary = summarize((left,), (paired, pair(left, missing)))
    assert summary.roster_count == 1 and summary.paired_count == 1 and summary.unmatched_count == 1
    with pytest.raises(ValueError, match="matched-cost"):
        pair(left, result(policy_hash="b" * 64, participation="WAIT", cost_hash="c" * 64))
    with pytest.raises(ValueError, match="one candidate"):
        summarize((left, right), ())


def first_entry_result():
    run, _, rows, (op,), (plan,), _, *_ = run_fixture()
    wait_context = context(price_core=False)
    take_context = context(
        at=150,
        source_cutoff=150,
        input_hashes=(rows[1].record_hash,),
        price_core=True,
    )
    snaps = tuple(
        snapshot(
            run,
            op,
            plan,
            ContextFrame.create(
                version="B_FRAME_V1",
                opportunity_hash=op.record_hash,
                context=c,
                features=(),
            ),
        )
        for c in (wait_context, take_context)
    )
    from trader_assist_v0.research_replay.policies import evaluate

    action = evaluate(plan.participation, take_context)
    receipt = EntryTrigger.create(
        version="B_ENTRY_TRIGGER_V1",
        snapshot=snaps[1],
        context=take_context,
        action=action,
    )
    fill = Fill(
        ts=170,
        price=Decimal(103),
        size=Decimal(1),
        direction="BUY",
        fee=Decimal(0),
        source_hash=rows[1].record_hash,
    )
    attempt = Attempt.create(
        version="B_ATTEMPT_V1",
        thesis_id=op.thesis_id,
        policy_hash=plan.record_hash,
        index=1,
        trigger_ns=150,
        fill=fill,
        exit_fill=None,
        state="PROBE_OPEN",
        fresh_condition_hash=take_context.record_hash,
        reason=action.reason,
    )
    forward = (*rows, raw(170), raw(190))
    return result(
        op=op,
        policy_hash=plan.record_hash,
        snapshots=snaps,
        entry_trigger=receipt,
        actions=(action,),
        policy_action_hashes=(action.record_hash,),
        fills=(fill,),
        fill_hashes=(digest("B_NATIVE_FILL", fill.model_dump(mode="json")),),
        attempts=(attempt,),
        attempt_hashes=(attempt.record_hash,),
        trigger_path=measure_path(snaps[1], op, forward, as_of=200),
        fill_path=measure_path(snaps[1], op, forward, as_of=200, fill=fill),
        terminal="UNFINISHED",
        outstanding_size=Decimal(1),
    )


def test_first_entry_contract_retains_wait_history_and_rejects_false_lineage():
    observed = first_entry_result()
    wait, take = observed.snapshots
    assert (wait.decision, take.decision) == ("WAIT", "TAKE")
    assert observed.entry_trigger.snapshot == take
    assert (
        observed.trigger_path.snapshot_hash == observed.fill_path.snapshot_hash == take.record_hash
    )
    assert observed.fills[0].ts > take.decision_ns
    assert CandidateResult.model_validate_json(observed.model_dump_json()) == observed
    unfilled = changed(
        observed,
        fills=(),
        fill_hashes=(),
        attempts=(),
        attempt_hashes=(),
        fill_path=None,
        terminal="NO_SUBMIT",
        outstanding_size=Decimal(0),
    )
    assert unfilled.entry_trigger == observed.entry_trigger and unfilled.fill_path is None
    mutations = (
        {"entry_trigger": None},
        {"snapshots": (take, wait)},
        {"snapshots": (wait,)},
        {"trigger_path": changed(observed.trigger_path, snapshot_hash=wait.record_hash)},
        {"fill_path": changed(observed.fill_path, snapshot_hash=wait.record_hash)},
        {"fill_path": None},
        {"terminal": "SUPPRESSED"},
        {"actions": (), "policy_action_hashes": ()},
    )
    for mutation in mutations:
        with pytest.raises(ValueError):
            changed(observed, **mutation)
    wrong_attempt = changed(observed.attempts[0], trigger_ns=151)
    with pytest.raises(ValueError, match="first native fill"):
        changed(observed, attempts=(wrong_attempt,), attempt_hashes=(wrong_attempt.record_hash,))
    receipt = observed.entry_trigger
    for mutation in (
        {"snapshot": wait},
        {"context": changed(receipt.context, at=151)},
        {"action": changed(receipt.action, context_hash=H)},
        {"action": changed(receipt.action, action="HOLD")},
    ):
        with pytest.raises(ValueError, match="lineage"):
            changed(receipt, **mutation)
    suppressed = result(participation="WAIT")
    assert suppressed.entry_trigger is None and suppressed.fill_path is None
    with pytest.raises(ValueError):
        changed(suppressed, entry_trigger=receipt)


def test_first_entry_contract_cannot_rebind_top_level_paths_to_later_reentry():
    first = first_entry_result()
    receipt = first.entry_trigger
    later_context = changed(receipt.context, at=190, source_cutoff=190)
    later_action = changed(receipt.action, action="REENTER", context_hash=later_context.record_hash)
    later_snapshot = changed(receipt.snapshot, decision_ns=190)
    later_receipt = EntryTrigger.create(
        version="B_ENTRY_TRIGGER_V1",
        snapshot=later_snapshot,
        context=later_context,
        action=later_action,
    )
    history = changed(
        first,
        snapshots=(*first.snapshots, later_snapshot),
        actions=(*first.actions, later_action),
        policy_action_hashes=(*first.policy_action_hashes, later_action.record_hash),
    )
    assert history.entry_trigger == receipt
    with pytest.raises(ValueError, match="first entry"):
        changed(
            history,
            entry_trigger=later_receipt,
            trigger_path=changed(history.trigger_path, snapshot_hash=later_snapshot.record_hash),
        )


def test_fresh_process_prefix_and_fingerprint_reproduction():
    code = """
from test_research_replay_harness import run_fixture
from trader_assist_v0.research_replay.harness import validate_inputs, snapshot
from trader_assist_v0.research_replay.reporting import bundle_fingerprint
args = run_fixture()
validate_inputs(*args)
run, _, _, roster, candidates, frames, *_ = args
decision = snapshot(run, roster[0], candidates[0], frames[0])
print(bundle_fingerprint(run.record_hash, (("decision", decision.record_hash),)))
"""
    env = {**os.environ, "PYTHONPATH": "src:tests"}
    outputs = tuple(
        subprocess.check_output([sys.executable, "-c", code], env=env, text=True).strip()
        for _ in range(2)
    )
    assert outputs[0] == outputs[1]
    run = run_fixture()[0]
    assert bundle_fingerprint(run.record_hash, (("decision", H),)) != bundle_fingerprint(
        changed(run, seed=8).record_hash, (("decision", H),)
    )
    with pytest.raises(ValueError, match="noncircular"):
        bundle_fingerprint(H, (("fingerprint", H),))


# Captured before factoring, rebound base:
# 343941250b3b32d1c527a2a419fd4e19e8ff3814.
S0_FROZEN_WIRE = {
    "DatasetManifest": {
        "asset_class": "CRYPTO",
        "checksum": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "dataset_id": "toy",
        "datatypes": ["OI"],
        "end_ns": 1000000000000000000,
        "exposure_state": "SACRIFICIAL",
        "instruments": ["ETH-USDT-SWAP"],
        "mapping_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "metadata": [
            ["bad_tick_policy", "UNKNOWN_SYNTHETIC"],
            ["corporate_action_policy", "UNKNOWN_SYNTHETIC"],
            ["correlation_cluster_method", "UNKNOWN_SYNTHETIC"],
            ["current_evidence_role", "UNKNOWN_SYNTHETIC"],
            ["data_revision_status", "UNKNOWN_SYNTHETIC"],
            ["delisting_status", "UNKNOWN_SYNTHETIC"],
            ["dividend_policy", "UNKNOWN_SYNTHETIC"],
            ["duplicate_policy", "UNKNOWN_SYNTHETIC"],
            ["fee_profile_version", "UNKNOWN_SYNTHETIC"],
            ["first_opened_at", "UNKNOWN_SYNTHETIC"],
            ["friction_profile_version", "UNKNOWN_SYNTHETIC"],
            ["known_gaps", "UNKNOWN_SYNTHETIC"],
            ["missing_bar_policy", "UNKNOWN_SYNTHETIC"],
            ["open_reason", "UNKNOWN_SYNTHETIC"],
            ["oracle_basis_model_version", "UNKNOWN_SYNTHETIC"],
            ["permitted_output_visibility", "UNKNOWN_SYNTHETIC"],
            ["point_in_time_universe", "UNKNOWN_SYNTHETIC"],
            ["primary_research_question", "UNKNOWN_SYNTHETIC"],
            ["provider_disagreement_policy", "UNKNOWN_SYNTHETIC"],
            ["regime_tag_method", "UNKNOWN_SYNTHETIC"],
            ["result_visibility_state", "UNKNOWN_SYNTHETIC"],
            ["session_calendar_version", "UNKNOWN_SYNTHETIC"],
            ["split_adjustment_policy", "UNKNOWN_SYNTHETIC"],
            ["strategy_version_allowed", "UNKNOWN_SYNTHETIC"],
            ["survivorship_limits", "UNKNOWN_SYNTHETIC"],
            ["symbol_mapping", "UNKNOWN_SYNTHETIC"],
            ["timezone_dst_policy", "UNKNOWN_SYNTHETIC"],
            ["trading_halt_status", "UNKNOWN_SYNTHETIC"],
        ],
        "record_hash": "b146ab88fef73234698744d9edf54d71b1bc266dd9160bdbf4ab6ce0597a1c93",
        "resolution": "SNAPSHOT",
        "rights": {
            "attribution_constraints": [],
            "decision_locator": "synthetic://decision",
            "eligibility": "ALLOWED",
            "intended_use": "PIPELINE_CORRECTNESS_ONLY",
            "observed_date": "2026-10-04",
            "observed_version": "v1",
            "record_hash": "8a891b444078aa3c2c7523e56c4bbce31966a95d743ff1174752af78528ef20b",
            "retention_constraints": [],
            "synthetic": True,
            "terms_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "terms_locator": "synthetic://terms",
            "version": "synthetic-v1",
        },
        "session_semantics": "24x7",
        "source": "OKX",
        "source_locator": "synthetic://response",
        "source_tier": "R0",
        "start_ns": 1,
        "timezone": "UTC",
        "venue": "OKX",
        "version": "synthetic-v1",
    },
    "Observation": {
        "bar_end": None,
        "continuity_epoch": "R0",
        "evidence": {
            "capability_hash": None,
            "coverage_end": 10000,
            "coverage_start": 1,
            "dataset_hash": "538a08b441e76ee93084c8467fa0edf8032c7e5fc793ab313069dc3810fc357e",
            "exposure_state": "SACRIFICIAL",
            "expression": "SYNTH",
            "instrument": "SYNTH",
            "interval_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "mapping_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "mapping_known_at": 1,
            "mapping_recorded_at": 1,
            "owner": "HL_E4",
            "price_unit": "USD",
            "provider": "NAUTILUS_HYPERLIQUID",
            "record_hash": "4b9d155eda512043853caa0d5f090de174ccbabba610a508e0f4784d3f7b546a",
            "registry_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "rights_hash": "8a891b444078aa3c2c7523e56c4bbce31966a95d743ff1174752af78528ef20b",
            "size_unit": "BASE",
            "source_hash": "0000000000000000000000000000000000000000000000000000000000000064",
            "source_locator": "synthetic://R0",
            "source_mode": "LIVE",
            "source_tier": "R0",
            "valid_from": 1,
            "valid_to": 10000,
            "version": "B_INPUT_V1",
        },
        "kind": "BBO",
        "known_at": 100,
        "ordinal": 100,
        "quality": ["COMPLETE"],
        "receive_provenance": "NOT_EXPOSED",
        "record_hash": "ae1954ff4ad439df4b345b1242d819be314b2e16d0d640f1e787861c303b51b5",
        "ts_event": 100,
        "ts_init": 100,
        "ts_receive": None,
        "values": [["ask", "101"], ["ask_size", "1"], ["bid", "99"], ["bid_size", "2"]],
        "version": "B_OBSERVATION_V1",
    },
    "Preregistration": {
        "allowed_changes": ["FROZEN_B1_B5"],
        "authority": "ISSUE_280_V1.2",
        "block_plan_hash": "4109b5e7c35d3770d23ecfa06b6fe9971187ee995dcb6211a8f74044587d552b",
        "challenger_hashes": ["a0bfd00a3308af86b3f2d5ead2a2517f7fbecd81aa7b7ccad30a34850848b388"],
        "champion_hash": "a0bfd00a3308af86b3f2d5ead2a2517f7fbecd81aa7b7ccad30a34850848b388",
        "claim": "PIPELINE_CORRECTNESS_ONLY",
        "cost_hash": "71f08450e749c6819da8d99f4a1a3d11165a2ae154fc1f5c821a1602a4486613",
        "diagnostics": "SACRIFICIAL_ONLY",
        "failure_mode": "causal leakage",
        "failure_rule": "FAIL_CLOSED",
        "hypothesis": "R0 engineering correctness",
        "max_horizon_ns": 1000,
        "max_research_repairs": 2,
        "max_trials": 64,
        "metrics": ["PIPELINE_CORRECTNESS"],
        "minimum_cells": 1,
        "minimum_clusters": 1,
        "minimum_events": 1,
        "predecessor_hash": None,
        "prohibited_changes": ["PROMOTION"],
        "promotion": "PROHIBITED",
        "record_hash": "646bfa5013513557561203e648930b7b9d5a9d96be5861e1e0b7a22528ccb422",
        "reserve_hashes": [],
        "selection_rule": "NO_SELECTION_PIPELINE_ONLY",
        "stage": "S0",
        "stopping_rule": "FROZEN_R0_FIXTURE_END",
        "taxonomy_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "version": "B_PREREG_V1",
        "visibility_hash": "ce82a95e81477179875338653361ce52971bc1cf63196e8649ae43400f4cb47c",
    },
    "ResearchRunSpec": {
        "ambiguity": "CONSERVATIVE_STOP_FIRST",
        "base": "ba7c1424b8beb06b15f4254b6864e8d87b93531b",
        "block_plan_hash": "4109b5e7c35d3770d23ecfa06b6fe9971187ee995dcb6211a8f74044587d552b",
        "claim": "PIPELINE_CORRECTNESS_ONLY",
        "consumption": "REPLAY",
        "correlation_method": "RETAINED_R0_EPISODE",
        "cost": {
            "additional_cost_bps": "0",
            "delay_ns": 1,
            "fee_profile": "R0_configured",
            "fill_model_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "funding_profile": "R0_signed",
            "maker_bps": "2",
            "passive_touch_equals_fill": False,
            "quote_age_ns": 100,
            "record_hash": "71f08450e749c6819da8d99f4a1a3d11165a2ae154fc1f5c821a1602a4486613",
            "size": "0.01",
            "slippage_bps": "0",
            "taker_bps": "5",
            "trigger_equals_fill": False,
            "version": "B_COST_V1",
        },
        "dataset_hashes": ["982140a47dd519290c0d29d6fd64299a7382ee644af11cfbc6333d88d8837ea4"],
        "feature_hashes": [],
        "horizon_ns": 100,
        "max_candidates": 4,
        "max_observations": 100,
        "package": ("CAUSAL_RESEARCH_DERIVATION_STRATEGY_REPLAY_FOUNDATION_1"),
        "policy_hashes": ["a0bfd00a3308af86b3f2d5ead2a2517f7fbecd81aa7b7ccad30a34850848b388"],
        "record_hash": "db5e09f7292fdf8db95920388ee3e057c8aa1f83bca6d440b5b60e4971204f3e",
        "release": "ba7c1424b8beb06b15f4254b6864e8d87b93531b",
        "roster_hash": "aecc95e8ab75e7e059600605ee56483539b53ab2563ad471311d1b736b96ac20",
        "runtime": "R0_ENGINEERING_FIXTURE",
        "seed": 7,
        "strategy_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "trial_ledger_hash": "e5a4faab510b756a08dc44a007ad9c23d9a1abc874fe2ad9ed3eb2c401b8d81a",
        "version": "B_RUN_V1",
        "visibility_hash": "ce82a95e81477179875338653361ce52971bc1cf63196e8649ae43400f4cb47c",
    },
    "Summary": {
        "ambiguity_count": 0,
        "claim": "PIPELINE_CORRECTNESS_ONLY",
        "cluster_count": 1,
        "cost_burden": "0",
        "maximum_drawdown": "0",
        "net_expectancy": "0",
        "paired_count": 0,
        "participation_counts": [["PASS", 1]],
        "record_hash": "68d1b2929d9e36edde12652adaf6c5f4aa1dea428858ae1b1b48f68d6434a979",
        "roster_count": 1,
        "setup_counts": [["SWEEP_RECLAIM", 1]],
        "status": "COMPLETE",
        "sufficiency_claim": False,
        "tail_concentration": None,
        "thesis_count": 1,
        "uncertainty_unit": "CORRELATION_CLUSTER_THESIS",
        "unmatched_count": 0,
        "version": "B_SUMMARY_V1",
    },
    "TrialLedger": {
        "history": "COMPLETE",
        "preregistration": {
            "allowed_changes": ["FROZEN_B1_B5"],
            "authority": "ISSUE_280_V1.2",
            "block_plan_hash": "4109b5e7c35d3770d23ecfa06b6fe9971187ee995dcb6211a8f74044587d552b",
            "challenger_hashes": [
                "a0bfd00a3308af86b3f2d5ead2a2517f7fbecd81aa7b7ccad30a34850848b388"
            ],
            "champion_hash": "a0bfd00a3308af86b3f2d5ead2a2517f7fbecd81aa7b7ccad30a34850848b388",
            "claim": "PIPELINE_CORRECTNESS_ONLY",
            "cost_hash": "71f08450e749c6819da8d99f4a1a3d11165a2ae154fc1f5c821a1602a4486613",
            "diagnostics": "SACRIFICIAL_ONLY",
            "failure_mode": "causal leakage",
            "failure_rule": "FAIL_CLOSED",
            "hypothesis": "R0 engineering correctness",
            "max_horizon_ns": 1000,
            "max_research_repairs": 2,
            "max_trials": 64,
            "metrics": ["PIPELINE_CORRECTNESS"],
            "minimum_cells": 1,
            "minimum_clusters": 1,
            "minimum_events": 1,
            "predecessor_hash": None,
            "prohibited_changes": ["PROMOTION"],
            "promotion": "PROHIBITED",
            "record_hash": "646bfa5013513557561203e648930b7b9d5a9d96be5861e1e0b7a22528ccb422",
            "reserve_hashes": [],
            "selection_rule": "NO_SELECTION_PIPELINE_ONLY",
            "stage": "S0",
            "stopping_rule": "FROZEN_R0_FIXTURE_END",
            "taxonomy_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "version": "B_PREREG_V1",
            "visibility_hash": "ce82a95e81477179875338653361ce52971bc1cf63196e8649ae43400f4cb47c",
        },
        "record_hash": "e5a4faab510b756a08dc44a007ad9c23d9a1abc874fe2ad9ed3eb2c401b8d81a",
        "reproductions": [],
        "trials": [
            {
                "parent_trial_hash": None,
                "preregistration_hash": (
                    "646bfa5013513557561203e648930b7b9d5a9d96be5861e1e0b7a22528ccb422"
                ),
                "record_hash": "89e70a01c3596a9c812b5500ae50f5aea4b905635cac77913951dd83bebcdfa4",
                "research_repair": False,
                "result_hash": None,
                "result_informed": False,
                "semantic_hash": "a3052cae8646f996a01877e489fd72c058daeff658ae8520d66ee62fe9ebaedf",
                "version": "B_TRIAL_V1",
                "visibility": "PIPELINE",
            }
        ],
        "version": "B_LEDGER_V1",
    },
    "VisibilityPolicy": {
        "channel": "PIPELINE",
        "diagnostics": False,
        "granularity": "AGGREGATE_ONLY",
        "real_sealed_access": False,
        "record_hash": "ce82a95e81477179875338653361ce52971bc1cf63196e8649ae43400f4cb47c",
        "version": "B_VISIBILITY_V1",
    },
}


def test_s0_pre_refactor_wire_and_hash_identities_are_exact():
    args = run_fixture()
    values = (
        dataset(),
        raw(),
        args[0],
        args[6].preregistration,
        args[6],
        args[8],
        summarize((result(),), ()),
    )
    assert {
        type(value).__name__: value.model_dump(mode="json") for value in values
    } == S0_FROZEN_WIRE


def test_native_candidate_algorithm_ast_is_unchanged_from_frozen_base():
    import ast
    import hashlib
    import inspect

    from trader_assist_v0.research_replay.harness import _native_candidate

    node = ast.parse(inspect.getsource(_native_candidate)).body[0]
    # The native loop only renames its snapshot call to the neutral helper;
    # normalize that explicit extraction, retaining the frozen algorithm digest.
    for item in ast.walk(node):
        if isinstance(item, ast.Name) and item.id == "_snapshot":
            item.id = "snapshot"
    body = ast.dump(ast.Module(body=node.body, type_ignores=[]), include_attributes=False)
    assert (
        hashlib.sha256(body.encode()).hexdigest()
        == "73cf8fdf272d1efa479fccdb615cda81cabe72bbd1e6b2c4db83fa21c21e493f"
    )
