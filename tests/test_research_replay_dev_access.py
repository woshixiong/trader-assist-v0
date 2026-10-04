"""Synthetic DEV access factories and before-I/O firewall matrix."""

from pathlib import Path

import pytest
from test_research_data_contracts import H, dataset, rights
from test_research_replay_contracts import changed, cost
from test_research_replay_harness import candidate

from trader_assist_v0.research_replay.contracts import digest
from trader_assist_v0.research_replay.dev_contracts import DevAccessAuthority
from trader_assist_v0.research_replay.dev_evidence import read_e4_dev
from trader_assist_v0.research_replay.dev_lifecycle import (
    DevGates,
    DevPreregistration,
    DevVisibilityPolicy,
)


def dev_dataset(**updates):
    meta = dict(dataset().metadata)
    meta.update(
        strategy_version_allowed="THREE_SETUP_DEV_V1",
        primary_research_question="core edge",
        current_evidence_role="DEV",
        permitted_output_visibility="DEV_LOCAL_AND_AGGREGATE",
        result_visibility_state="DEV",
        open_reason="SYNTHETIC_ENGINEERING",
    )
    args = dict(
        exposure_state="DEV_EXPOSED",
        metadata=tuple(sorted(meta.items())),
        rights=rights(intended_use="STRATEGY_DEV_RESEARCH"),
        end_ns=10000,
        source="NAUTILUS_HYPERLIQUID",
        venue="HYPERLIQUID",
        instruments=("SYNTH",),
        datatypes=("BBO",),
    )
    args.update(updates)
    return dataset(**args)


def dev_visibility(**updates):
    return DevVisibilityPolicy.create(
        **dict(
            version="DEV_VISIBILITY_V1",
            channel="DEV_LOCAL_AND_AGGREGATE",
            max_rows=100,
            max_bytes=1000000,
            max_buckets=64,
            aggregate_allowed=True,
            attribution=(),
            **updates,
        )
    )


def prereg(ds=None, *, candidates=None, vis=None, **updates):
    ds, vis = ds or dev_dataset(), vis or dev_visibility()
    candidates = candidates or (candidate(), changed(candidate(), role="CHALLENGER"))
    args = dict(
        version="DEV_PREREG_V1",
        authority="ISSUE_280_V1.2",
        r0_ref="synthetic://R0",
        r1_ref="synthetic://R1",
        run_authority_ref="synthetic://frozen-inventory",
        evidence_kind="SYNTHETIC_ENGINEERING",
        stage="S1",
        group="G0",
        predecessor_hash=H,
        hypothesis="after-cost edge",
        failure_mode="no useful edge",
        champion_hash=candidates[0].record_hash,
        challenger_hashes=tuple(c.record_hash for c in candidates[1:]),
        candidate_order=tuple(c.record_hash for c in candidates),
        complexity=tuple(range(len(candidates), 0, -1)),
        parameter_hashes=tuple(H for _ in candidates),
        allowed_changes=("participation", "delay"),
        prohibited_changes=("direction",),
        fixed_components=(),
        primary_metric="THESIS_NET_R_AFTER_COST",
        secondary_metrics=("drawdown", "coverage"),
        taxonomy_hash=H,
        cost_hash=cost().record_hash,
        block_plan_hash=H,
        visibility_hash=vis.record_hash,
        stopping_rule="COMPLETE_FROZEN_ROSTER_NO_PNL_EARLY_STOP",
        failure_rule="COHERENT_AFTER_COST_AND_ALL_GATES",
        selection_rule="PAIRED_INCREMENTAL_R_SIMPLER_ON_EQUIVALENCE",
        gates=DevGates.create(
            version="DEV_GATES_V1",
            minimum_incremental_r="0.1",
            equivalence_tolerance_r="0.05",
            max_drawdown_r="5",
            max_tail_loss_r="3",
            max_winner_concentration="1",
            max_cluster_concentration="1",
            minimum_coverage="0.5",
            max_unavailable_rate="0.1",
            max_cost_r="1",
            max_delay_ns=100,
        ),
        max_trials=4,
        max_research_repairs=1,
        repair_mechanism="bounded causal diagnosis",
        minimum_events=1,
        minimum_clusters=1,
        minimum_cells=1,
        mandatory_cells=("SWEEP_RECLAIM|STANDARD|LONG|R0",),
        max_horizon_ns=100,
        reserve_hashes=(),
        dataset_hashes=(ds.record_hash,),
        strategy_hash=H,
        strategy_version="THREE_SETUP_DEV_V1",
        question="core edge",
        research_plan_hash=H,
        original_risk_hash=digest("DEV_ORIGINAL_THESIS_RISK_V1", (("retained-thesis", "1"),)),
        false_positive_rule="TAKEN_NONPOSITIVE_NET_R",
        false_negative_rule="SUPPRESSED_POSITIVE_REGISTERED_COUNTERFACTUAL_R",
    )
    args.update(updates)
    return DevPreregistration.create(**args)


def authority(ds=None, pre=None, **updates):
    ds = ds or dev_dataset()
    pre = pre or prereg(ds)
    args = dict(
        version="DEV_ACCESS_V1",
        dataset_hash=ds.record_hash,
        dataset_id=ds.dataset_id,
        cut=(ds.start_ns, ds.end_ns),
        instruments=ds.instruments,
        checksum=ds.checksum,
        mapping_hash=ds.mapping_hash,
        rights_hash=ds.rights.record_hash if ds.rights else H,
        strategy_version=pre.strategy_version,
        strategy_hash=pre.strategy_hash,
        question=pre.question,
        visibility="DEV_LOCAL_AND_AGGREGATE",
        preregistration_hash=pre.record_hash,
        run_authority_ref=pre.run_authority_ref,
        satisfied_constraints=(),
    )
    args.update(updates)
    return DevAccessAuthority.create(**args)


class NeverStore:
    def __getattr__(self, name):
        pytest.fail(f"forbidden pre-authority I/O: {name}")


@pytest.mark.parametrize(
    "state",
    [
        "UNSEEN_SEALED",
        "SACRIFICIAL",
        "VALIDATION_SEALED",
        "VALIDATION_USED",
        "FINAL_LOCKBOX_SEALED",
        "FINAL_LOCKBOX_USED",
        "CONTAMINATED",
        "RETIRED",
    ],
)
def test_every_non_dev_state_fails_before_io(state, monkeypatch):
    ds = dev_dataset(exposure_state=state)
    pre = prereg(ds)
    a = authority(ds, pre)
    monkeypatch.setattr(Path, "resolve", lambda *a, **k: pytest.fail("resolve before authority"))
    with pytest.raises(PermissionError):
        read_e4_dev(NeverStore(), ds, H, H, H, a, pre)


@pytest.mark.parametrize(
    "r",
    [
        None,
        rights(intended_use="STRATEGY_DEV_RESEARCH", eligibility="UNKNOWN"),
        rights(intended_use="STRATEGY_DEV_RESEARCH", eligibility="PROHIBITED"),
        rights(),
        rights(intended_use="STRATEGY_DEV_RESEARCH", attribution_constraints=("credit",)),
        rights(intended_use="STRATEGY_DEV_RESEARCH", retention_constraints=("delete_after_run",)),
    ],
)
def test_rights_fail_before_io(r):
    ds = dev_dataset(rights=r)
    pre = prereg(ds)
    with pytest.raises(PermissionError):
        read_e4_dev(NeverStore(), ds, H, H, H, authority(ds, pre), pre)


def test_exact_authority_and_no_s0_bypass():
    ds = dev_dataset()
    pre = prereg(ds)
    a = authority(ds, pre)
    assert a.require(ds, pre) == ds
    with pytest.raises(PermissionError):
        ds.require_access("PIPELINE_CORRECTNESS_ONLY")
    with pytest.raises(PermissionError):
        ds.require_access("STRATEGY_DEV_RESEARCH")
    for update in (
        dict(strategy_version="UNKNOWN"),
        dict(question="different"),
        dict(rights_hash="b" * 64),
        dict(preregistration_hash="b" * 64),
        dict(run_authority_ref="synthetic://other"),
        dict(cut=(1, 20)),
    ):
        with pytest.raises(PermissionError):
            changed(a, **update).require(ds, pre)
    r = rights(intended_use="STRATEGY_DEV_RESEARCH", attribution_constraints=("credit",))
    ds = dev_dataset(rights=r)
    pre = prereg(ds)
    assert authority(ds, pre, satisfied_constraints=("credit",)).require(ds, pre) == ds


def test_forward_r0_and_metadata_cannot_be_permission():
    for ds in (
        dev_dataset(source_tier="R6"),
        dev_dataset(
            metadata=tuple(
                sorted({**dict(dev_dataset().metadata), "open_reason": "Forward"}.items())
            )
        ),
    ):
        pre = prereg(ds)
        with pytest.raises(PermissionError):
            authority(ds, pre).require(ds, pre)
    ds = dev_dataset()
    pre = prereg(
        ds,
        evidence_kind="RIGHTS_AUTHORIZED_DEV",
        r0_ref="https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-1",
        r1_ref="https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-2",
        run_authority_ref="https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-3",
    )
    with pytest.raises(PermissionError):
        authority(ds, pre).require(ds, pre)
