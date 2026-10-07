"""Generated external DEV only: real admission/owner seams and omission attacks."""

import builtins
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import pytest
from test_research_data_admission import capability
from test_research_data_contracts import H, rights
from test_research_data_mapping import mapping, snapshot
from test_research_inventory_manifest import item, spec
from test_research_replay_contracts import changed, cost
from test_research_replay_dev_access import authority, dev_dataset, dev_visibility, prereg
from test_research_replay_dev_lifecycle import ledger, trial

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_pilot.strategy_package import StrategyPackageManifest
from trader_assist_v0.research_data.admission import AdmissionPolicy, ExternalReferenceLedger
from trader_assist_v0.research_data.contracts import (
    BarPayload,
    ExternalReferenceEvent,
    SourceMode,
    TimestampProvenance,
)
from trader_assist_v0.research_data.mapping import PitReferenceResolver
from trader_assist_v0.research_data.storage import EvidenceSidecar, ReferenceDatasetStore
from trader_assist_v0.research_inventory.builder import build_inventory_manifest
from trader_assist_v0.research_inventory.contracts import InventoryState
from trader_assist_v0.research_replay import mechanism as pure
from trader_assist_v0.research_replay import mechanism_harness as harness
from trader_assist_v0.research_replay.contracts import Fill
from trader_assist_v0.research_replay.dev_evidence import DevExternalAdmission
from trader_assist_v0.research_replay.lifecycle import Block, BlockPlan
from trader_assist_v0.research_replay.mechanism_contracts import (
    CHAMPION,
    CODES,
    MechanismBundle,
    MechanismCandidate,
    MechanismConfig,
    MechanismDecision,
    MechanismMarket,
    MechanismOpportunity,
    MechanismRunSpec,
    MechanismSource,
    checked,
)
from trader_assist_v0.research_replay.policies import AUTHORITIES, BASELINES, PolicySpec

BASE = "69d100172154a1fe723a3c08166ad6705c1f49d6"
TREE = "fadfdd313def3c8886687b810e862d5e526ed060"
STEP = 300_000_000_000


def fixture(
    tmp_path,
    tier="R3",
    *,
    channel="DEV_LOCAL_AND_AGGREGATE",
    count=54,
    config_updates=None,
    dataset_updates=None,
    state="AVAILABLE",
    source_mode=SourceMode.HISTORY,
    observed_at_ns=None,
    mapping_known_at=1,
):
    config = MechanismConfig.create(
        version="MECHANISM_CONFIG_V1",
        model="BAR_NEXT_OPEN_STOP_FIRST_V1",
        cost=changed(cost(), size=Decimal(1), delay_ns=0, slippage_bps=Decimal(1)),
        resolution_ns=STEP,
        horizon_ns=STEP * 2,
        decision_start_ns=STEP * 44,
        expiry_ns=STEP * 2,
        spread_bps=Decimal(2),
        funding_applicable=False,
        funding_bps=None,
        funding_interval_ns=STEP * 96,
        funding_anchor_ns=0,
        scanner_liquidity_healthy=True,
        scanner_assumption_ref="synthetic://registered-spread-liquidity",
        donchian_bars=5,
        baseline_stop="SIGNAL_EXTREME_PLUS_TICK",
        baseline_target_r=Decimal(2),
        original_risk_cash=Decimal(10),
        capital_cash=Decimal(1000),
        cluster_window_ns=STEP * 10,
        episode_rule="CAUSAL_FAMILY_SIDE_BOUNDARY_NONOVERLAP_V1",
        regime_method="FIXED_SYNTHETIC",
        markets=(
            MechanismMarket.create(
                version="1",
                instrument="SYNTH",
                expression="SYNTH",
                minimum_tick=Decimal("0.01"),
                cluster="cluster",
                regime="R0",
            ),
        ),
        pit_qa_hash=None,
        pit_qa_ref=None,
    )
    if config_updates:
        config = changed(config, **config_updates)
    candidates = tuple(
        MechanismCandidate.create(
            version="MECHANISM_CANDIDATE_V1",
            participation=PolicySpec.create(
                version="B_POLICY_V1",
                family="CHAMPION" if code == CHAMPION else "BASELINE",
                code=code,
                authority=AUTHORITIES["CHAMPION" if code == CHAMPION else "BASELINE"],
                semantics="ISSUE_FAMILIES_B_V1",
                parameters=(),
            ),
            config_hash=config.record_hash,
            risk_hash=config.risk_hash,
            role="REFERENCE" if code == CHAMPION else "BASELINE",
        )
        for code in CODES
    )
    maps = snapshot(
        mapping(
            valid_from=1,
            valid_to=STEP * 1000,
            known_at=mapping_known_at,
            recorded_at=mapping_known_at,
        )
    )
    cap = capability(datatype="BAR_5M", source_mode=source_mode)
    policy = AdmissionPolicy.create(
        version="1", stale_after_ns=STEP, sequence_semantics="CONTIGUOUS", max_observations=1000
    )
    ds = dev_dataset(
        source="BINANCE",
        venue="BINANCE",
        source_tier=tier,
        start_ns=STEP,
        end_ns=STEP * 100,
        datatypes=("BAR_5M",),
        resolution="5m",
        mapping_hash=maps.record_hash,
        **(dataset_updates or {}),
    )
    metadata = dict(ds.metadata)
    metadata.update(
        strategy_version_allowed="FL-MA-PRICE-ACTION-v0.1", permitted_output_visibility=channel
    )
    ds = changed(ds, metadata=tuple(sorted(metadata.items())))
    vis = changed(dev_visibility(), channel=channel, max_rows=1000, max_bytes=4_000_000)
    blocks = BlockPlan.create(
        version="1",
        blocks=(
            Block.create(version="1", role="DEV", start=1, end=STEP * 100, instruments=("SYNTH",)),
            Block.create(
                version="1", role="OOS", start=STEP * 110, end=STEP * 120, instruments=("SYNTH",)
            ),
        ),
        embargo_ns=STEP * 2,
        embargo_reason="frozen horizon",
        cluster_policy="PURGE_WHOLE_CLUSTER",
        holdout_instruments=(),
    )
    inv = build_inventory_manifest(
        datasets=(ds,),
        allocation=spec(
            item(
                ds,
                inventory_state=InventoryState(state),
                limitations=() if state == "AVAILABLE" else ("MISSING",),
            ),
            strategy_version="FL-MA-PRICE-ACTION-v0.1",
            primary_research_question="core edge",
        ),
    )
    manifest = StrategyPackageManifest.create(trade_os_release_sha=BASE)
    pre = prereg(
        ds,
        candidates=candidates,
        vis=vis,
        strategy_version=manifest.strategy_version,
        strategy_hash=manifest.manifest_hash,
        parameter_hashes=(config.record_hash,) * 5,
        cost_hash=config.cost.record_hash,
        block_plan_hash=blocks.record_hash,
        max_horizon_ns=config.horizon_ns,
        max_trials=5,
        original_risk_hash=config.risk_hash,
        mandatory_cells=("BREAKOUT_RETEST|UNCONFIRMED|LONG|R0",),
    )
    a = authority(ds, pre, visibility=channel)
    admission = DevExternalAdmission(ds, PitReferenceResolver(maps), (cap,), policy, a, pre)
    log = ExternalReferenceLedger(admission)
    for index in range(count):
        start = (index + 1) * STEP
        observed = start + STEP if observed_at_ns is None else observed_at_ns
        price = Decimal(100) + index * 2
        payload = BarPayload(
            interval_minutes=5,
            start_ns=start,
            end_ns=start + STEP,
            timestamp_meaning="OPEN",
            aggregation_origin="SYNTHETIC_GENERATED",
            finalized=True,
            open=str(price),
            high=str(price + 1),
            low=str(price - 1),
            close=str(price + Decimal("0.5")),
            volume="100",
        )
        event = ExternalReferenceEvent.create(
            version="1",
            provider="BINANCE",
            venue="BINANCE",
            product="SYNTHETIC_SWAP",
            instrument_id="SYNTH",
            mapping_hash=maps.record_hash,
            dataset_hash=ds.record_hash,
            capability_hash=cap.record_hash,
            rights_hash=ds.rights.record_hash,
            source_mode=source_mode,
            native_id=str(index),
            sequence=index + 1,
            timestamps=TimestampProvenance(
                source_ts=str(start),
                source_unit="ns",
                ts_event=start,
                observed_at_ns=observed,
                receive_provenance="NOT_EXPOSED",
            ),
            payload=payload,
        )
        log.observe(event, evaluated_at_ns=observed)
    sidecar = EvidenceSidecar.create(
        version="1",
        dataset_hash=ds.record_hash,
        mapping_hash=maps.record_hash,
        capability_hashes=(cap.record_hash,),
        policy_hash=policy.record_hash,
        observations=tuple(log.observations),
        source_bytes_hex=(b"generated fixture".hex(),),
        raw_semantics="SYNTHETIC",
        catalog_files=(),
    )
    path = tmp_path / "fixture.reference.json"
    data = canonical_json_bytes(sidecar.model_dump(mode="json"))
    path.write_bytes(data)
    source = MechanismSource.create(
        version="1",
        dataset=ds,
        authority=a,
        mapping=maps,
        capabilities=(cap,),
        policy=policy,
        registry_hash=H,
        root=str(tmp_path),
        path=str(path),
        checksum=sha256_hex(data),
    )
    log = ledger(pre)
    run = MechanismRunSpec.create(
        version="MECHANISM_RUN_V1",
        package="C_G0_EXTERNAL_MECHANISM_REPLAY_1",
        stage="S1",
        group="G0",
        base=BASE,
        code_commit=BASE,
        code_tree=TREE,
        manifest=manifest,
        strategy_hash=manifest.manifest_hash,
        dataset_hashes=(ds.record_hash,),
        source_hashes=(source.record_hash,),
        candidate_hashes=tuple(c.record_hash for c in candidates),
        inventory_hash=inv.record_hash,
        preregistration_hash=pre.record_hash,
        ledger_hash=log.record_hash,
        block_hash=blocks.record_hash,
        visibility_hash=vis.record_hash,
        config_hash=config.record_hash,
        registry_hash=H,
        taxonomy_hash=H,
        s0_preparation_hash=H,
        dependency_lock_hash=H,
        module_hashes=tuple(
            (name, H) for name in ("mechanism.py", "mechanism_contracts.py", "mechanism_harness.py")
        ),
        runtime="PURE_PYTHON_SYNTHETIC",
        python_version="3.12",
        os_arch="SYNTHETIC",
        max_observations=1000,
        max_events=1000,
        evidence_kind="SYNTHETIC_ENGINEERING",
    )
    for c in candidates:
        log = log.append(
            trial(
                pre,
                candidate_hash=c.record_hash,
                semantic_hash=harness.mechanism_trial_identity(run, c, config),
            )
        )
    run = changed(run, ledger_hash=log.record_hash)
    return run, (source,), inv, log, blocks, vis, config, candidates


def replay(args):
    return harness.replay_mechanism(*args, s0_preparation_hash=H, as_of_ns=STEP * 100)


def read(args):
    return harness.read_mechanism_sources(*args, s0_preparation_hash=H)


@pytest.mark.parametrize("tier", ["R1", "R2", "R3"])
def test_real_admission_external_replay_no_native_e4(tier, tmp_path):
    args = fixture(tmp_path, tier)
    bundle = replay(args)
    assert bundle.run.manifest.parameter_version == "2026-08-03-r1"
    assert bundle.run.manifest.scanner_version == "SESSION-MOMENTUM-R3"
    assert bundle.claim == "MECHANISM_VALIDATION" and bundle.economics == "SYNTHETIC_VENUE_OVERLAY"
    assert not bundle.summary.performance_evidence
    assert bundle.summary.disposition not in {"KEEP_CURRENT", "RESEARCH_LEADER"}
    assert bundle.roster and len(bundle.results) == len(bundle.roster) * 5
    assert any(r.entry is not None for r in bundle.results)
    assert all(r.evidence.owner == "EXTERNAL_REFERENCE" for r in bundle.observations)
    assert all(
        f.mode == "SYNTHETIC_VENUE_OVERLAY" for r in bundle.results for f in (r.entry, r.exit) if f
    )
    assert bundle.fingerprint == replay(args).fingerprint
    assert bundle.model_dump_json() == replay(args).model_dump_json()


@pytest.mark.parametrize(
    "field,value",
    [
        *(("source_tier", t) for t in ("R0", "R4", "R5", "R6")),
        *(
            ("exposure_state", t)
            for t in (
                "UNSEEN_SEALED",
                "SACRIFICIAL",
                "VALIDATION_SEALED",
                "VALIDATION_USED",
                "FINAL_LOCKBOX_SEALED",
                "FINAL_LOCKBOX_USED",
                "CONTAMINATED",
                "RETIRED",
            )
        ),
    ],
)
def test_whole_batch_firewall_before_any_io(tmp_path, monkeypatch, field, value):
    args = fixture(tmp_path, count=1)
    good = args[1][0]
    bad = changed(good, dataset=changed(good.dataset, **{field: value}))

    def never(*args, **kwargs):
        pytest.fail("source/outcome I/O before whole-batch authority")

    monkeypatch.setattr(builtins, "open", never)
    monkeypatch.setattr(Path, "resolve", never)
    monkeypatch.setattr(Path, "stat", never)
    monkeypatch.setattr(Path, "open", never)
    monkeypatch.setattr(ReferenceDatasetStore, "__init__", never)
    monkeypatch.setattr(harness, "read_external_dev", never)
    with pytest.raises(PermissionError):
        read((args[0], (good, bad), *args[2:]))


@pytest.mark.parametrize(
    "update",
    [
        {"rights_hash": "b" * 64},
        {"cut": (1, 2)},
        {"question": "wrong"},
        {"strategy_version": "wrong"},
        {"visibility": "DEV_AGGREGATE_ONLY"},
        {"mapping_hash": "b" * 64},
        {"checksum": "b" * 64},
    ],
)
def test_authority_mismatch_before_reader(tmp_path, monkeypatch, update):
    args = fixture(tmp_path, count=1)
    s = args[1][0]
    bad = changed(s, authority=changed(s.authority, **update))
    run = changed(args[0], source_hashes=(bad.record_hash,))
    monkeypatch.setattr(
        harness, "read_external_dev", lambda *a, **k: pytest.fail("reader before gate")
    )
    with pytest.raises((PermissionError, ValueError)):
        read((run, (bad,), *args[2:]))


def test_forward_rights_reserve_ledger_and_pit_fail_closed(tmp_path, monkeypatch):
    args = fixture(tmp_path, count=1)
    monkeypatch.setattr(
        harness, "read_external_dev", lambda *a, **k: pytest.fail("reader before gate")
    )
    s = args[1][0]
    for ds in (
        changed(s.dataset, rights=None),
        changed(
            s.dataset, rights=rights(intended_use="STRATEGY_DEV_RESEARCH", eligibility="PROHIBITED")
        ),
        changed(
            s.dataset,
            metadata=tuple(sorted({**dict(s.dataset.metadata), "open_reason": "FORWARD"}.items())),
        ),
        changed(s.dataset, asset_class="EQUITY"),
    ):
        bad = changed(s, dataset=ds)
        with pytest.raises((ValueError, PermissionError)):
            read((args[0], (bad,), *args[2:]))
    for index, replacement in (
        (3, changed(args[3], history="UNKNOWN_LEGACY_INCOMPLETE")),
        (0, changed(args[0], s0_preparation_hash="b" * 64)),
    ):
        changed_args = list(args)
        changed_args[index] = replacement
        with pytest.raises((ValueError, PermissionError)):
            read(tuple(changed_args))
    bad_inv = args[2].model_copy(update={"entries": ()})
    with pytest.raises((ValueError, TypeError)):
        read((*args[:2], bad_inv, *args[3:]))
    with pytest.raises(ValueError):
        changed(args[6], cost=changed(args[6].cost, size=Decimal(2)))


def test_concrete_contract_and_claim_tamper(tmp_path):
    args = fixture(tmp_path, count=1)

    class OtherRun(MechanismRunSpec):
        pass

    with pytest.raises(TypeError):
        checked(OtherRun.model_construct(**args[0].__dict__), MechanismRunSpec)
    with pytest.raises(ValueError):
        checked(args[0].model_copy(update={"config_hash": "b" * 64}), MechanismRunSpec)
    for update in (
        {"claim": "HYPERLIQUID_VENUE_TRANSLATION"},
        {"stage": "S2"},
        {"promotion": "PRODUCTION"},
    ):
        with pytest.raises(ValueError):
            changed(args[0], **update)


def opportunity(
    args, rows, *, side="LONG", code=BASELINES[2], stop=Decimal(97), target=Decimal(110)
):
    # A retained causal test episode: one signal, two whole forward bars.
    at = STEP * 2
    d = MechanismDecision.create(
        version="1",
        code=code,
        at=at,
        prefix_hashes=(rows[0].record_hash,),
        participation="TAKE",
        reason="SYNTHETIC_SIGNAL",
        mode="UNCONFIRMED",
        entry_low=None,
        entry_high=None,
        chase=None,
        stop=stop,
        target=target,
        owner_hash=H,
    )
    c = args[6]
    op = MechanismOpportunity.create(
        version="1",
        market_event_id="synthetic-event",
        thesis_id="synthetic-thesis",
        expression="SYNTH",
        dataset_hash=args[1][0].dataset.record_hash,
        family="BREAKOUT_RETEST",
        mode="UNCONFIRMED",
        side=side,
        cluster_id="cluster",
        regime="R0",
        start_ns=at,
        expiry_ns=at + c.expiry_ns,
        horizon_end=at + c.horizon_ns,
        kernel_event=False,
        availability="AVAILABLE",
        reasons=(),
        original_risk_cash=c.original_risk_cash,
        risk_hash=c.risk_hash,
        config_hash=c.record_hash,
        scan_hashes=(),
        decisions=(d,),
    )
    return op


def evaluate(args, rows, op):
    candidate = next(c for c in args[7] if c.participation.code == op.decisions[0].code)
    return pure.evaluate_mechanism_candidate(
        op, candidate, op.decisions, rows, args[6], as_of_ns=STEP * 100
    )


def test_modeled_risk_friction_short_gap_and_ambiguity(tmp_path):
    args = fixture(tmp_path, count=4, config_updates={"decision_start_ns": STEP * 2})
    rows = read(args)
    op = opportunity(args, rows)
    result = evaluate(args, rows, op)
    assert result.terminal == "COMPLETE"
    assert result.entry.ts >= op.decisions[0].at
    assert result.entry.source_hash != rows[0].record_hash
    assert result.entry.size != args[6].cost.size
    expected = (
        (result.exit.price - result.entry.price) * result.entry.size
        - result.entry.fee
        - result.exit.fee
        - result.additional_cash
    )
    assert abs(result.net_cash - expected) < Decimal("0.0000001")
    assert abs(result.net_r - result.net_cash / op.original_risk_cash) < Decimal("0.0000001")
    with pytest.raises(ValueError):
        Fill.model_validate(result.entry.model_dump(mode="json"))
    short = opportunity(args, rows, side="SHORT", stop=Decimal(110), target=Decimal(90))
    short_result = evaluate(args, rows, short)
    assert short_result.entry.price < rows[1].number("open")
    assert short_result.exit.price > rows[2].number("close")
    ambiguous = opportunity(args, rows, stop=Decimal("101.5"), target=Decimal("102.5"))
    amb = evaluate(args, rows, ambiguous)
    assert amb.path.ambiguous and amb.net_r < 0
    gap = opportunity(args, rows, side="SHORT", stop=Decimal("103.5"), target=Decimal(90))
    g = evaluate(args, rows, gap)
    assert g.exit.price >= rows[2].number("open")


def test_missing_future_mapping_delay_and_path_cannot_improve(tmp_path):
    args = fixture(tmp_path, count=4, config_updates={"decision_start_ns": STEP * 2})
    rows = read(args)
    op = opportunity(args, rows)
    assert evaluate(args, rows[:-2], op).net_r is None
    gapped = (*rows[:1], changed(rows[1], quality=("GAP",)), *rows[2:])
    assert evaluate(args, gapped, op).net_r is None
    late = changed(rows[0], evidence=changed(rows[0].evidence, mapping_recorded_at=STEP * 50))
    bad_op = opportunity(args, (late, *rows[1:]))
    with pytest.raises(ValueError, match="future"):
        evaluate(args, (late, *rows[1:]), bad_op)
    with pytest.raises(ValueError):
        pure.evaluate_mechanism_candidate(op, args[7][3], (), rows, args[6], as_of_ns=STEP * 100)
    with pytest.raises(ValueError):
        pure.bar_view(
            changed(
                rows[0], values=tuple(sorted({**dict(rows[0].values), "start_ns": "1"}.items()))
            ),
            args[6],
        )


def test_free_reference_import_replays_at_historical_finality_without_backdating(tmp_path):
    late_observation = STEP * 90
    late_mapping = STEP * 80
    args = fixture(
        tmp_path,
        count=4,
        config_updates={"decision_start_ns": STEP * 2},
        source_mode=SourceMode.FREE_REFERENCE_IMPORT,
        observed_at_ns=late_observation,
        mapping_known_at=late_mapping,
    )
    rows = read(args)
    first, next_bar = rows[:2]
    assert first.known_at == late_observation
    assert first.evidence.mapping_known_at == late_mapping
    assert first.evidence.mapping_recorded_at == late_mapping
    assert pure._bar_replay_clock(first) == first.bar_end
    assert pure.healthy(first, first.bar_end)
    assert not pure.healthy(next_bar, first.bar_end)

    op = opportunity(args, rows)
    candidate = next(c for c in args[7] if c.participation.code == op.decisions[0].code)
    assert next_bar.bar_end is not None
    early = pure.evaluate_mechanism_candidate(
        op,
        candidate,
        op.decisions,
        rows,
        args[6],
        as_of_ns=next_bar.bar_end - 1,
    )
    assert early.net_r is None

    result = pure.evaluate_mechanism_candidate(
        op,
        candidate,
        op.decisions,
        rows,
        args[6],
        as_of_ns=STEP * 100,
    )
    assert result.terminal == "COMPLETE"
    assert result.entry is not None
    assert result.entry.ts == int(dict(next_bar.values)["start_ns"])
    assert result.entry.source_hash == next_bar.record_hash
    assert result.entry.ts < first.known_at


def test_non_import_replay_clock_keeps_knowledge_and_mapping_causality(tmp_path):
    late_observation = STEP * 90
    late_mapping = STEP * 80
    args = fixture(
        tmp_path,
        count=1,
        source_mode=SourceMode.HISTORY,
        observed_at_ns=late_observation,
        mapping_known_at=late_mapping,
    )
    row = read(args)[0]
    assert pure._bar_replay_clock(row) == late_observation
    assert not pure.healthy(row, row.bar_end)
    assert pure.healthy(row, late_observation)

    live = changed(row, evidence=changed(row.evidence, source_mode=SourceMode.LIVE))
    assert pure._bar_replay_clock(live) == late_observation
    assert not pure.healthy(live, live.bar_end)
    assert pure.healthy(live, late_observation)


def test_owner_composition_causal_prefix_and_baseline_only(tmp_path, monkeypatch):
    args = fixture(tmp_path)
    rows = read(args)
    calls = []
    original = pure.engine.evaluate_strategy

    def owner(inputs, ledger):
        result = original(inputs, ledger)
        calls.append((asdict(inputs), asdict(result)))
        return result

    monkeypatch.setattr(pure.engine, "evaluate_strategy", owner)
    roster = pure.derive_mechanism_opportunities(rows, args[0].manifest, args[6])
    assert calls and roster
    assert any(
        not o.kernel_event and any(d.code == BASELINES[2] for d in o.decisions) for o in roster
    )
    early = pure.derive_mechanism_opportunities(rows[:-4], args[0].manifest, args[6])
    # Compare completed earlier episodes; future continuation cannot rewrite their receipts.
    last = rows[-5].bar_end
    assert [o for o in early if o.expiry_ns < last] == [o for o in roster if o.expiry_ns < last]
    assert {o.mode for o in roster if o.family == "BREAKOUT_RETEST"} == {
        "MICRO_FAST",
        "STANDARD",
        "UNCONFIRMED",
    }


def test_denominator_fingerprint_and_visibility_attacks(tmp_path):
    args = fixture(tmp_path, channel="DEV_AGGREGATE_ONLY")
    bundle = replay(args)
    with pytest.raises(ValueError, match="denominator"):
        harness.pair_results(bundle.roster, bundle.results[:-1], bundle.candidates)
    with pytest.raises(ValueError):
        changed(bundle, results=bundle.results[:-1])
    with pytest.raises(ValueError):
        checked(bundle.model_copy(update={"fingerprint": "b" * 64}), MechanismBundle)
    output = harness.mechanism_summary_bytes(bundle, args[5])
    parsed = json.loads(output)
    assert parsed["diagnostics_withheld"]
    assert b"fixture.reference" not in output and b"source_locator" not in output
    assert b"SUPPRESSED" in output and b"NOT_EVALUABLE" in output
    with pytest.raises(PermissionError):
        harness.mechanism_summary_bytes(bundle, changed(args[5], aggregate_allowed=False))
    changed_run = changed(args[0], code_tree="1" * 40)
    assert harness.mechanism_trial_identity(
        changed_run, args[7][0], args[6]
    ) == harness.mechanism_trial_identity(args[0], args[7][0], args[6])
    assert changed_run.record_hash != args[0].record_hash


def test_native_external_only_guard_remains_real_owner(tmp_path):
    from test_research_replay_dev_harness import checked as native_checked
    from test_research_replay_dev_harness import dev_fixture

    args = dev_fixture()
    # Native owner refuses a retained roster after all HL_E4 evidence is removed.
    with pytest.raises(ValueError):
        native_checked((*args[:2], (), *args[3:]))


def test_missing_inventory_is_retained_without_reader(tmp_path, monkeypatch):
    args = fixture(tmp_path, count=1, state="INCOMPLETE")
    monkeypatch.setattr(
        harness, "read_external_dev", lambda *a, **k: pytest.fail("missing source opened")
    )
    result = replay(args)
    assert result.summary.unavailable_cohort_count == 1
    assert result.summary.disposition == "MORE_EVIDENCE_REQUIRED"
    assert result.summary.event_count == 0


def test_funding_delay_expiry_and_capital_authority(tmp_path):
    args = fixture(
        tmp_path,
        count=4,
        config_updates={
            "decision_start_ns": STEP * 2,
            "funding_applicable": True,
            "funding_bps": None,
        },
    )
    rows = read(args)
    assert evaluate(args, rows, opportunity(args, rows)).reasons == ("MISSING_APPLICABLE_FUNDING",)
    args = fixture(
        tmp_path,
        count=4,
        config_updates={
            "decision_start_ns": STEP * 2,
            "funding_applicable": True,
            "funding_bps": Decimal(10),
            "funding_interval_ns": STEP,
        },
    )
    rows = read(args)
    op = opportunity(args, rows)
    r = evaluate(args, rows, op)
    assert r.funding_cash < 0
    # Same original risk, strictly earlier capacity admission, no profitable sorting.
    second = changed(op, market_event_id="other", thesis_id="later")
    second_r = evaluate(args, rows, second)
    low_cap = changed(args[6], capital_cash=Decimal(200))
    # Allocation itself uses only declared capital and chronological fill receipts.
    allocated = harness._allocate_capital((op, second), (r, second_r), low_cap)
    assert sum(x.terminal == "NO_SUBMIT" for x in allocated) >= 1
    assert all(x.net_r == 0 for x in allocated if x.terminal == "NO_SUBMIT")
    delayed = changed(args[6], cost=changed(args[6].cost, delay_ns=STEP * 2))
    candidate = changed(args[7][3], config_hash=delayed.record_hash)
    delayed_op = changed(op, config_hash=delayed.record_hash)
    result = pure.evaluate_mechanism_candidate(
        delayed_op, candidate, delayed_op.decisions, rows, delayed, as_of_ns=STEP * 100
    )
    assert result.terminal == "NONFILL" and result.net_r == 0


def test_no_public_champion_boolean_bypass_and_pit_qa(tmp_path):
    args = fixture(tmp_path, count=4, config_updates={"decision_start_ns": STEP * 2})
    rows = read(args)
    forged = opportunity(args, rows, code=CHAMPION)
    with pytest.raises(ValueError, match="Champion receipt"):
        pure.evaluate_mechanism_candidate(
            forged, args[7][0], forged.decisions, rows, args[6], as_of_ns=STEP * 100
        )
    args = fixture(tmp_path, count=1, dataset_updates={"asset_class": "EQUITY"})
    with pytest.raises(PermissionError, match="PIT"):
        read(args)


def test_precise_baseline_matching_and_unavailable_pair_retention(tmp_path):
    args = fixture(tmp_path, count=4, config_updates={"decision_start_ns": STEP * 2})
    rows = read(args)
    op = opportunity(args, rows)
    results = tuple(
        pure.evaluate_mechanism_candidate(op, c, op.decisions, rows, args[6], as_of_ns=STEP * 100)
        if c.participation.code != CHAMPION
        else pure._evaluate_mechanism_candidate(
            op, c, op.decisions, rows, args[6], as_of_ns=STEP * 100
        )
        for c in args[7]
    )
    assert results[1].terminal == "NOT_APPLICABLE" and results[4].terminal == "NOT_APPLICABLE"
    pairs = harness.pair_results((op,), results, args[7])
    assert len(pairs) == 2
    assert pairs[1].delta_r == results[3].net_r - results[0].net_r
    incomplete = pure._evaluate_mechanism_candidate(
        op, args[7][3], op.decisions, rows[:-2], args[6], as_of_ns=STEP * 100
    )
    pairs = harness.pair_results((op,), (*results[:3], incomplete, results[4]), args[7])
    assert not pairs[1].comparable and pairs[1].delta_r is None


def test_source_checksum_fingerprint_trial_config_and_egress_limits(tmp_path):
    args = fixture(tmp_path)
    bad = changed(args[1][0], checksum="b" * 64)
    run = changed(args[0], source_hashes=(bad.record_hash,))
    with pytest.raises(ValueError, match="checksum"):
        read((run, (bad,), *args[2:]))
    changed_config = changed(args[6], spread_bps=Decimal(3))
    assert harness.mechanism_trial_identity(
        args[0], args[7][0], changed_config
    ) != harness.mechanism_trial_identity(args[0], args[7][0], args[6])
    bundle = replay(args)
    forged_result = bundle.results[-1].model_copy(update={"net_r": Decimal(99)})
    with pytest.raises(ValueError):
        changed(bundle, results=(*bundle.results[:-1], forged_result))
    bounded = changed(args[5], max_bytes=1)
    # A changed bound must first match run/preregistration; never disclose on mismatch.
    with pytest.raises(PermissionError):
        harness.mechanism_summary_bytes(bundle, bounded)


def test_registered_risk_diagnostics_and_hard_stop(tmp_path):
    args = fixture(tmp_path, count=4, config_updates={"decision_start_ns": STEP * 2})
    rows = read(args)
    op = opportunity(args, rows, side="SHORT", stop=Decimal(110), target=Decimal(90))
    results = tuple(
        pure._evaluate_mechanism_candidate(op, c, op.decisions, rows, args[6], as_of_ns=STEP * 100)
        for c in args[7]
    )
    pairs = harness.pair_results((op,), results, args[7])
    canonical = "https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-1"
    pre = changed(
        args[3].preregistration,
        evidence_kind="RIGHTS_AUTHORIZED_DEV",
        mandatory_cells=("BREAKOUT_RETEST|UNCONFIRMED|SHORT|R0",),
        r0_ref=canonical,
        r1_ref=canonical,
        run_authority_ref=canonical,
    )
    summary = harness.summarize_mechanism(
        (op,), results, pairs, pre, args[2], run=args[0], candidates=args[7]
    )
    baseline = next(m for m in summary.metrics if m.code == BASELINES[2])
    assert baseline.drawdown_r > 0 and baseline.tail_loss_r > 0
    assert baseline.longest_losing_streak == 1 and baseline.fee_cash > 0
    assert summary.stop_broad_optimization
    assert summary.next_action == "DIAGNOSE_SCANNER_SETUP_ENTRY_COST_LAYER"
    # Synthetic fixture cannot be put in a real evidence bundle by changing the label.
    real_run = changed(args[0], evidence_kind="RIGHTS_AUTHORIZED_DEV")
    with pytest.raises(ValueError):
        read((real_run, *args[1:]))


def selection_fixture(tmp_path, edges, *, complexity=(3, 1, 1, 1, 1), empirical=True):
    """In-memory reporting evidence; never admitted as an empirical replay bundle."""
    args = fixture(tmp_path, count=4, config_updates={"decision_start_ns": STEP * 2})
    rows = read(args)
    prototype = opportunity(args, rows)
    ops, results = [], []
    for i, (family, mode, scores) in enumerate(edges):
        op = changed(
            prototype,
            family=family,
            mode=mode,
            market_event_id=f"event-{i}",
            thesis_id=f"thesis-{i}",
            cluster_id=f"cluster-{i}",
        )
        ops.append(op)
        for c in args[7]:
            r = pure._evaluate_mechanism_candidate(
                op, c, op.decisions, rows, args[6], as_of_ns=STEP * 100
            )
            value = Decimal(scores.get(c.participation.code, "0"))
            if pure.applicable(op, c.participation.code):
                r = changed(
                    r,
                    entry=None,
                    exit=None,
                    terminal="COMPLETE",
                    net_r=value,
                    net_cash=value * r.original_risk_cash,
                    funding_cash=Decimal(0),
                    additional_cash=Decimal(0),
                )
            results.append(r)
    pairs = harness.pair_results(tuple(ops), tuple(results), args[7])
    canonical = "https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-1"
    pre = changed(
        args[3].preregistration,
        complexity=complexity,
        mandatory_cells=tuple(sorted({harness._cell(o) for o in ops})),
        gates=changed(
            args[3].preregistration.gates,
            equivalence_tolerance_r=Decimal("0.1"),
            minimum_incremental_r=Decimal("0.2"),
        ),
        **(
            {
                "evidence_kind": "RIGHTS_AUTHORIZED_DEV",
                "r0_ref": canonical,
                "r1_ref": canonical,
                "run_authority_ref": canonical,
            }
            if empirical
            else {}
        ),
    )
    return args, tuple(ops), tuple(results), pairs, pre


def selection_summary(data, **updates):
    args, ops, results, pairs, pre = data
    return harness.summarize_mechanism(
        ops,
        results,
        pairs,
        updates.pop("pre", pre),
        args[2],
        run=updates.pop("run", args[0]),
        candidates=updates.pop("candidates", args[7]),
        **updates,
    )


@pytest.mark.parametrize("baseline_r", ["1.05", "0.95", "0.9"])
def test_edge_simpler_equivalence_beats_old_threshold(tmp_path, baseline_r):
    data = selection_fixture(
        tmp_path, [("SWEEP_RECLAIM", "NOT_APPLICABLE", {CHAMPION: "1", BASELINES[0]: baseline_r})]
    )
    summary = selection_summary(data)
    assert summary.disposition == "RESEARCH_LEADER" and not summary.stop_broad_optimization
    metric = next(m for m in summary.metrics if m.code == BASELINES[0])
    assert metric.paired_delta_r < max(
        data[-1].gates.minimum_incremental_r, data[-1].gates.equivalence_tolerance_r
    )
    assert summary == selection_summary(data)


@pytest.mark.parametrize(
    "baseline_r,expected", [("1.05", "KEEP_CURRENT"), ("1.2", "RESEARCH_LEADER")]
)
def test_edge_complex_challenger_minimum_boundary(tmp_path, baseline_r, expected):
    data = selection_fixture(
        tmp_path,
        [("SWEEP_RECLAIM", "NOT_APPLICABLE", {CHAMPION: "1", BASELINES[0]: baseline_r})],
        complexity=(1, 3, 3, 3, 3),
    )
    assert selection_summary(data).disposition == expected


def test_edge_ineligible_champion_no_unproven_alternate(tmp_path):
    data = selection_fixture(
        tmp_path,
        [
            (
                "BREAKOUT_RETEST",
                "STANDARD",
                {CHAMPION: "-0.01", BASELINES[1]: "0.05", BASELINES[2]: "0.04"},
            )
        ],
        complexity=(1, 2, 3, 3, 3),
    )
    summary = selection_summary(data)
    assert summary.disposition == "REJECT" and summary.stop_broad_optimization


def test_complete_edges_isolated_and_global_aggregation(tmp_path, monkeypatch):
    observed = []
    owner = harness.select_prospective_candidate

    def spy(rows, **kwargs):
        decision = owner(rows, **kwargs)
        observed.append((rows, decision))
        return decision

    monkeypatch.setattr(harness, "select_prospective_candidate", spy)
    edges = [
        (
            "BREAKOUT_RETEST",
            "MICRO_FAST",
            {CHAMPION: "1", BASELINES[1]: "0.95", BASELINES[2]: "0.9"},
        ),
        ("BREAKOUT_RETEST", "STANDARD", {CHAMPION: "1", BASELINES[1]: "0.1", BASELINES[2]: "0.1"}),
        ("RANGE_EDGE_REJECTION", "NOT_APPLICABLE", {CHAMPION: "1", BASELINES[3]: "0.1"}),
    ]
    data = selection_fixture(tmp_path, edges)
    assert selection_summary(data).disposition == "RESEARCH_LEADER"
    candidates = data[0][7]
    breakout_hashes = {candidates[i].record_hash for i in (0, 2, 3)}
    breakout = [d for rows, d in observed if {r.candidate_hash for r in rows} == breakout_hashes]
    assert len(breakout) == 2
    assert {d.disposition for d in breakout} == {"KEEP_CURRENT", "RESEARCH_LEADER"}
    original_micro = next(d for d in breakout if d.disposition == "RESEARCH_LEADER")
    observed.clear()
    altered = selection_fixture(
        tmp_path,
        [
            edges[0],
            ("BREAKOUT_RETEST", "STANDARD", {CHAMPION: "1", BASELINES[1]: "9", BASELINES[2]: "10"}),
            edges[2],
        ],
        complexity=(3, 1, 1, 1, 0),
    )
    assert selection_summary(altered).disposition == "RESEARCH_LEADER"
    assert observed[0][1] == original_micro  # Sorted MICRO_FAST edge is unaffected.
    assert {r.candidate_hash for r in observed[0][0]} == breakout_hashes
    assert (
        selection_summary(selection_fixture(tmp_path, [edges[1], edges[2]])).disposition
        == "KEEP_CURRENT"
    )


@pytest.mark.parametrize("attack", ["reorder", "run_hashes", "duplicate", "complexity"])
def test_summary_exact_prospective_binding(tmp_path, attack):
    data = selection_fixture(
        tmp_path, [("SWEEP_RECLAIM", "NOT_APPLICABLE", {CHAMPION: "1", BASELINES[0]: "0.95"})]
    )
    args = data[0]
    kwargs = {}
    if attack == "reorder":
        kwargs["candidates"] = (args[7][0], *reversed(args[7][1:]))
    elif attack == "run_hashes":
        kwargs["run"] = args[0].model_copy(
            update={"candidate_hashes": tuple(reversed(args[0].candidate_hashes))}
        )
    elif attack == "duplicate":
        kwargs["candidates"] = (args[7][0],) * 5
    else:
        kwargs["pre"] = data[-1].model_copy(update={"complexity": (1,)})
    with pytest.raises(ValueError, match="binding"):
        selection_summary(data, **kwargs)


def test_synthetic_insufficient_incomplete_reject_and_revalidation(tmp_path):
    edges = [("SWEEP_RECLAIM", "NOT_APPLICABLE", {CHAMPION: "1", BASELINES[0]: "0.95"})]
    data = selection_fixture(tmp_path, edges, empirical=False)
    summary = selection_summary(data)
    assert (
        summary.disposition == "INSUFFICIENT"
        and not summary.performance_evidence
        and not summary.stop_broad_optimization
    )
    real = selection_fixture(tmp_path, edges)
    assert (
        selection_summary(real, pre=changed(real[-1], minimum_events=2)).disposition
        == "INSUFFICIENT"
    )
    args, ops, results, pairs, pre = real
    missing = tuple(
        changed(r, terminal="NOT_EVALUABLE", net_cash=None, net_r=None)
        if r.code == BASELINES[0]
        else r
        for r in results
    )
    incomplete = (args, ops, missing, harness.pair_results(ops, missing, args[7]), pre)
    assert selection_summary(incomplete).disposition == "MORE_EVIDENCE_REQUIRED"
    assert (
        selection_summary(
            selection_fixture(
                tmp_path,
                [("SWEEP_RECLAIM", "NOT_APPLICABLE", {CHAMPION: "-1", BASELINES[0]: "-2"})],
            )
        ).disposition
        == "REJECT"
    )
    bundle = replay(args)
    assert bundle.fingerprint == replay(args).fingerprint
    forged = changed(
        bundle.summary,
        disposition="RESEARCH_LEADER"
        if bundle.summary.disposition != "RESEARCH_LEADER"
        else "REJECT",
    )
    with pytest.raises(ValueError):
        changed(bundle, summary=forged)
