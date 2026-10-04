"""Synthetic selection gates, independent denominators and canonical disclosure."""

import json
from decimal import Decimal

import pytest
from test_research_replay_contracts import H, changed
from test_research_replay_dev_harness import completed, dev_fixture
from test_research_replay_harness import result

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.research_replay.contracts import digest
from trader_assist_v0.research_replay.dev_contracts import DevEvidenceBundle, dev_fingerprint
from trader_assist_v0.research_replay.dev_reporting import (
    canonical_summary,
    diagnostics,
    stage_result,
    summarize_dev,
)
from trader_assist_v0.research_replay.paths import measure_path
from trader_assist_v0.research_replay.reporting import pair


def bundle_fixture(
    *,
    cash=(Decimal(1), Decimal(2)),
    fees=Decimal(0),
    incomplete=False,
    ambiguous=False,
    suppressed=False,
    **pre_updates,
):
    args = dev_fixture(**pre_updates)
    run, datasets, rows, ops, candidates, frames, log, blocks, vis, authorities = args
    op = ops[0]
    results = []
    for c, value in zip(candidates, cash, strict=True):
        r = result(
            op=op,
            policy_hash=c.record_hash,
            cash=value,
            cost_hash=run.cost.record_hash,
            terminal="SUPPRESSED" if suppressed else "COMPLETE",
            fee_cash=fees,
        )
        path = measure_path(r.snapshots[0], op, rows, as_of=op.decision_ns + run.horizon_ns)
        r = changed(
            r,
            trigger_path=changed(path, same_bar_ambiguous=ambiguous),
            net_cash=None if incomplete else value,
        )
        results.append(r)
    pairs = (pair(*results),)
    artifacts = tuple(
        sorted(
            (
                ("inputs", digest("B_INPUTS", tuple(r.record_hash for r in rows))),
                ("frames", digest("B_FRAMES", tuple(f.record_hash for f in frames))),
                ("results", digest("B_RESULTS", tuple(r.record_hash for r in results))),
                ("pairs", digest("B_PAIRS", tuple(p.record_hash for p in pairs))),
                ("counterfactuals", digest("B_COUNTERFACTUALS", ())),
            )
        )
    )
    values = dict(
        version="DEV_BUNDLE_V1",
        run=run,
        preregistration=log.preregistration,
        ledger=log,
        datasets=datasets,
        authorities=authorities,
        roster=ops,
        original_risks=((op.thesis_id, Decimal(1)),),
        results=tuple(results),
        pairs=pairs,
        counterfactuals=(),
        artifacts=artifacts,
        claim="DEV_RESEARCH_ONLY",
        promotion="PROHIBITED",
    )
    bundle = DevEvidenceBundle.create(
        **values, fingerprint=dev_fingerprint(json.loads(canonical_json_bytes(values)))
    )
    return bundle, vis


def summary_for(**kwargs):
    bundle, vis = bundle_fixture(**kwargs)
    return summarize_dev(bundle, vis, completed(bundle))


def test_bounded_diagnostics_and_canonical_no_raw_ids_timestamps_or_paths():
    bundle, vis = bundle_fixture()
    detail = diagnostics(bundle, vis)
    assert detail.rows[0].original_risk_cash == 1 and detail.rows[0].net_r_after_cost == 1
    final = completed(bundle)
    summary = canonical_summary(bundle, vis, final)
    assert summary["disposition"] == "RESEARCH_LEADER" and summary["promotion"] == "PROHIBITED"
    serialized = json.dumps(summary)
    for forbidden in (
        "source_bytes_hex",
        "synthetic://",
        "retained-thesis",
        "source_locator",
        "ts_event",
        "market_event_id",
        "known_at",
        "instrument",
        "payload",
        "THREE_SETUP_DEV_V1",
    ):
        assert forbidden not in serialized
    with pytest.raises(ValueError, match="completed visible"):
        summarize_dev(bundle, vis, bundle.ledger)
    with pytest.raises(TypeError):
        diagnostics(bundle.model_dump(), vis)
    with pytest.raises(ValueError):
        diagnostics(bundle.model_copy(update={"fingerprint": H}), vis)
    with pytest.raises(ValueError):
        changed(stage_result(bundle, vis, final), promotion="ALLOWED")


def test_r1_missing_binance_loss_only_cost_and_concentration_adversaries():
    assert summary_for(incomplete=True).disposition == "INSUFFICIENT"
    assert summary_for(cash=(Decimal(1), Decimal("0.9"))).disposition == "KEEP_CURRENT"
    assert summary_for(cash=(Decimal(1), Decimal("-1")), fees=Decimal(3)).disposition == "REJECT"
    b, v = bundle_fixture()
    gates = changed(
        b.preregistration.gates,
        max_winner_concentration=Decimal("0.5"),
        max_cluster_concentration=Decimal("0.5"),
    )
    assert summary_for(gates=gates).disposition == "REJECT"
    assert summary_for(cash=(Decimal(1), Decimal(0))).disposition == "KEEP_CURRENT"
    assert (
        summary_for(cash=(Decimal(1), Decimal("1.01"))).disposition == "RESEARCH_LEADER"
    )  # simpler equivalence
    assert summary_for(cash=(Decimal(-1), Decimal(-2))).disposition == "REJECT"
    assert (
        summary_for(mandatory_cells=("RANGE_EDGE_REJECTION|STANDARD|SHORT|R0",)).disposition
        == "INSUFFICIENT"
    )
    assert summary_for(minimum_events=2).disposition == "INSUFFICIENT"
    assert summary_for(minimum_clusters=2).disposition == "INSUFFICIENT"
    assert summary_for(ambiguous=True).disposition == "INSUFFICIENT"
    assert summary_for(suppressed=True).disposition == "REJECT"


def test_risk_is_original_thesis_denominator_and_all_attempt_fees_stay_visible():
    b, v = bundle_fixture(fees=Decimal("0.1"))
    s = summarize_dev(b, v, completed(b))
    assert s.metrics[1].after_cost_thesis_r == 2 and s.metrics[1].fee_cash == Decimal("0.1")
    assert s.metrics[1].cost_r == Decimal("0.1")
    with pytest.raises(ValueError, match="risk denominator"):
        changed(b, original_risks=(("retained-thesis", Decimal("0.1")),))
    failed_bundle, failed_visibility = bundle_fixture(cash=(Decimal(-1), Decimal(-2)))
    failed = stage_result(failed_bundle, failed_visibility, completed(failed_bundle))
    assert failed.stop and not failed.coherent


@pytest.mark.parametrize(
    "field,value",
    [
        ("strategy_package_hash", "b" * 64),
        ("release", "b" * 40),
        ("code_tree", "b" * 40),
        ("dependency_lock_hash", "b" * 64),
        ("config_hash", "b" * 64),
        ("python_version", "3.12.1"),
        ("os", "Linux"),
        ("architecture", "x86_64"),
        ("report_code_hash", "b" * 64),
        ("universe_hash", "b" * 64),
        ("registry_hash", "b" * 64),
        ("funding_hash", "b" * 64),
        ("friction_hash", "b" * 64),
        ("execution_hash", "b" * 64),
        ("seed", 9),
    ],
)
def test_fingerprint_changes_for_each_code_environment_execution_identity(field, value):
    b, _ = bundle_fixture()
    modified = changed(b.run, **{field: value})
    with pytest.raises(ValueError):
        changed(b, run=modified)
    payload = b.model_dump(mode="json", exclude={"fingerprint", "record_hash"})
    payload["run"] = modified.model_dump(mode="json")
    assert dev_fingerprint(payload) != b.fingerprint


def test_rights_visibility_withholds_channels_and_enforces_bounds():
    from test_research_replay_dev_access import dev_visibility

    vis = changed(dev_visibility(), channel="DEV_AGGREGATE_ONLY", aggregate_allowed=False)
    bundle, policy = bundle_fixture(visibility=vis)
    assert diagnostics(bundle, policy) is None
    assert canonical_summary(bundle, policy, completed(bundle)) is None
    bundle, policy = bundle_fixture(visibility=changed(dev_visibility(), max_rows=1))
    with pytest.raises(ValueError, match="rows"):
        diagnostics(bundle, policy)
    bundle, policy = bundle_fixture(visibility=changed(dev_visibility(), max_bytes=1))
    with pytest.raises(ValueError, match="byte"):
        canonical_summary(bundle, policy, completed(bundle))
