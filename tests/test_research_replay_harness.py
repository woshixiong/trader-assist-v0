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

from trader_assist_v0.research_replay.contracts import ResearchRunSpec, digest
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
    bundle_fingerprint,
    pair,
    summarize,
)


def test_derived_decision_metrics_canonicalize_repeating_ratios_before_validation():
    names = (
        "progress_bps", "adverse_bps", "high_water_bps", "giveback_fraction",
        "net_r", "cumulative_cost_bps",
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


def result(*, policy_hash=H, cash=Decimal(0), participation="PASS", **updates):
    op = opportunity()
    snap = changed(decision(op), decision=participation)
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
        pair(left, changed(right, cost_hash="c" * 64))
    with pytest.raises(ValueError, match="one candidate"):
        summarize((left, right), ())


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
