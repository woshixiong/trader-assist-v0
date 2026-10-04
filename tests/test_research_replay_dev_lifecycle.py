"""Prospective history, exact ancestry and S1-S5 subgroup progression."""

import pytest
from test_research_data_contracts import H
from test_research_replay_contracts import changed
from test_research_replay_dev_access import prereg

from trader_assist_v0.research_replay.dev_lifecycle import (
    DevCompletion,
    DevReproduction,
    DevStageResult,
    DevTrial,
    DevTrialLedger,
    require_predecessor,
)


def trial(pre=None, **updates):
    pre = pre or prereg()
    args = dict(
        version="DEV_TRIAL_V1",
        semantic_hash=H,
        preregistration_hash=pre.record_hash,
        candidate_hash=pre.champion_hash,
        dataset_hashes=pre.dataset_hashes,
        strategy_hash=pre.strategy_hash,
        parent_trial_hash=None,
        parent_result_hash=None,
        result_informed=False,
        research_repair=False,
        repair_cause=None,
        changed_variables=(),
        unchanged_hash=H,
        role="PRIMARY",
    )
    args.update(updates)
    return DevTrial.create(**args)


def ledger(pre=None, entries=()):
    return DevTrialLedger.create(
        version="DEV_LEDGER_V1",
        preregistration=pre or prereg(),
        history="COMPLETE",
        entries=entries,
    )


def completion(log, t, **updates):
    args = dict(
        version="DEV_COMPLETION_V1",
        trial_hash=t.record_hash,
        preregistration_hash=log.preregistration.record_hash,
        run_hash=H,
        bundle_hash=H,
        prior_cut_hash=log.cut_hash(len(log.entries)),
    )
    args.update(updates)
    return DevCompletion.create(**args)


def stage(pre=None, **updates):
    pre = pre or prereg()
    args = dict(
        version="DEV_STAGE_RESULT_V1",
        preregistration_hash=pre.record_hash,
        stage=pre.stage,
        group=pre.group,
        ledger_hash=H,
        bundle_hash=H,
        selected_hash=pre.champion_hash,
        fixed_components=pre.fixed_components,
        dataset_hashes=pre.dataset_hashes,
        strategy_hash=pre.strategy_hash,
        disposition="KEEP_CURRENT",
        sufficient=True,
        coherent=True,
        stop=False,
    )
    args.update(updates)
    return DevStageResult.create(**args)


def test_prospective_completion_parent_and_reproduction():
    pre = prereg()
    t = trial(pre)
    original = ledger(pre, (t,))
    done = completion(original, t)
    complete = original.append(done)
    child = trial(
        pre,
        semantic_hash="b" * 64,
        candidate_hash=pre.challenger_hashes[0],
        parent_trial_hash=t.record_hash,
        parent_result_hash=done.record_hash,
        result_informed=True,
        changed_variables=("participation",),
    )
    new = complete.append(child)
    assert original.entries == (t,) and len(new.entries) == 3
    with pytest.raises(ValueError, match="visible result"):
        original.append(child)
    with pytest.raises(ValueError, match="visible result"):
        complete.append(changed(child, parent_result_hash=H))
    with pytest.raises(ValueError, match="prior ledger cut"):
        original.append(changed(done, prior_cut_hash=H))
    rep = DevReproduction.create(
        version="DEV_REPRODUCTION_V1",
        trial_hash=t.record_hash,
        original_completion_hash=done.record_hash,
        run_hash=H,
    )
    assert len(complete.append(rep).entries) == 3
    with pytest.raises(ValueError, match="reproduction"):
        original.append(rep)
    with pytest.raises(ValueError, match="identical reproduction"):
        original.append(t)
    with pytest.raises(ValueError, match="orphan"):
        ledger(pre).append(done)


def test_trial_repair_budget_and_unlogged_changes():
    pre = prereg(max_trials=1, max_research_repairs=0)
    a = trial(pre)
    log = ledger(pre, (a,))
    with pytest.raises(ValueError, match="budget"):
        log.append(trial(pre, semantic_hash="b" * 64))
    with pytest.raises(ValueError, match="budget"):
        ledger(pre, (trial(pre, research_repair=True, repair_cause=pre.repair_mechanism),))
    with pytest.raises(ValueError, match="mechanism"):
        ledger(entries=(trial(research_repair=True, repair_cause="unfrozen"),))
    with pytest.raises(ValueError, match="prohibited"):
        ledger(entries=(trial(changed_variables=("direction",)),))
    with pytest.raises(ValueError):
        changed(ledger(), unlogged_adaptation=True)
    with pytest.raises(ValueError):
        changed(prereg(), stage="S6")
    with pytest.raises(ValueError):
        changed(stage(), disposition="PASS_TO_PRODUCTION")


def test_exact_stage_and_subgroup_order_and_core_stop():
    pre = prereg()
    require_predecessor(pre, None, None, H)
    for group, stage_name in (
        ("G1", "S2"),
        ("G2", "S3"),
        ("G3", "S3"),
        ("G4", "S4"),
        ("G5", "S4"),
        ("G6", "S5"),
    ):
        done = stage(pre)
        next_pre = changed(
            pre,
            group=group,
            stage=stage_name,
            predecessor_hash=done.record_hash,
            fixed_components=(*pre.fixed_components, done.selected_hash),
        )
        require_predecessor(next_pre, done, pre, H)
        with pytest.raises(ValueError):
            require_predecessor(next_pre, None, pre, H)
        with pytest.raises(ValueError):
            require_predecessor(changed(next_pre, predecessor_hash=H), done, pre, H)
        failed = stage(pre, disposition="REJECT", selected_hash=None, coherent=False, stop=True)
        with pytest.raises(ValueError):
            require_predecessor(
                changed(next_pre, predecessor_hash=failed.record_hash), failed, pre, H
            )
        pre = next_pre
    with pytest.raises(ValueError):
        changed(prereg(), stage="S2", group="G0")
    with pytest.raises(ValueError):
        changed(stage(), sufficient=False)
