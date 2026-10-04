"""DEV replay seams, material identities and matched real native S0/DEV economics."""

import importlib.util
import os
from decimal import Decimal

import pytest
from test_research_data_contracts import H
from test_research_replay_contracts import changed, raw
from test_research_replay_dev_access import authority, dev_dataset, dev_visibility, prereg
from test_research_replay_dev_lifecycle import completion, ledger, trial
from test_research_replay_harness import candidate, run_fixture

from trader_assist_v0.multi_asset_shadow.shadow_records.records import MarketEvent
from trader_assist_v0.research_replay.contracts import digest
from trader_assist_v0.research_replay.dev_contracts import (
    DevObservation,
    DevRunSpec,
)
from trader_assist_v0.research_replay.dev_evidence import bind_domain_records_dev
from trader_assist_v0.research_replay.dev_harness import (
    dev_trial_identity,
    replay_dev,
    validate_dev_inputs,
)
from trader_assist_v0.research_replay.harness import ContextFrame, validate_inputs
from trader_assist_v0.research_replay.lifecycle import Block, BlockPlan

BASE = "343941250b3b32d1c527a2a419fd4e19e8ff3814"
TREE = "49aca33c51acc0e81d85c0f25ed68a2916e0a750"


def dev_fixture(s0=None, extra_dataset=None, visibility=None, **pre_updates):
    s0 = s0 or run_fixture(candidates=(candidate(), changed(candidate(), role="CHALLENGER")))
    old, datasets, rows, roster, candidates, frames, *_ = s0
    original = datasets[0]
    ds = dev_dataset(
        source=original.source,
        venue=original.venue,
        instruments=original.instruments,
        datatypes=original.datatypes,
        start_ns=original.start_ns,
        end_ns=original.end_ns,
        mapping_hash=original.mapping_hash,
    )
    if visibility is not None:
        metadata = dict(ds.metadata)
        metadata["permitted_output_visibility"] = visibility.channel
        ds = changed(ds, metadata=tuple(sorted(metadata.items())))
    dataset_roster = (ds,) if extra_dataset is None else (ds, extra_dataset)
    instruments = tuple(dict.fromkeys(i for d in dataset_roster for i in d.instruments))
    pre_updates = {**pre_updates, "dataset_hashes": tuple(d.record_hash for d in dataset_roster)}
    vis = visibility or dev_visibility()
    blocks = BlockPlan.create(
        version="B_BLOCKS_V1",
        blocks=(
            Block.create(version="1", role="DEV", start=1, end=10000, instruments=instruments),
            Block.create(version="1", role="OOS", start=11000, end=12000, instruments=instruments),
        ),
        embargo_ns=100,
        embargo_reason="frozen synthetic outcome horizon",
        cluster_policy="PURGE_WHOLE_CLUSTER",
        holdout_instruments=(),
    )
    pre = prereg(
        ds,
        candidates=candidates,
        vis=vis,
        cost_hash=old.cost.record_hash,
        block_plan_hash=blocks.record_hash,
        **pre_updates,
    )
    a = authority(ds, pre, visibility=vis.channel)
    projected = tuple(
        DevObservation.create(
            **{
                **r.model_dump(exclude={"record_hash", "evidence"}),
                "version": "DEV_OBSERVATION_V1",
                "evidence": changed(
                    r.evidence,
                    dataset_hash=ds.record_hash,
                    exposure_state="DEV_EXPOSED",
                    rights_hash=ds.rights.record_hash,
                ),
                "authority": a,
            }
        )
        for r in rows
    )
    mapping = {r.record_hash: p.record_hash for r, p in zip(rows, projected, strict=True)}
    ops = []
    for op in roster:
        record = MarketEvent.create(
            identity={"synthetic": op.market_event_id},
            market_id=op.market_id,
            event_kind="SYNTHETIC",
            event_time=op.decision_ns,
        )
        op = changed(
            op,
            market_event_id=record.record_id,
            prefix_hashes=tuple(mapping[h] for h in op.prefix_hashes),
        )
        ops.append(bind_domain_records_dev(op, (record,), ds, a, pre))
    opmap = {o.record_hash: n.record_hash for o, n in zip(roster, ops, strict=True)}
    frames = tuple(
        changed(
            f,
            opportunity_hash=opmap[f.opportunity_hash],
            context=changed(
                f.context, input_hashes=tuple(mapping[h] for h in f.context.input_hashes)
            ),
        )
        for f in frames
    )
    log = ledger(pre)
    extra = dict(
        version="DEV_RUN_V1",
        package="R2_DEV_RESEARCH_EXECUTION_ENABLEMENT_1",
        base=BASE,
        release=BASE,
        code_tree=TREE,
        claim="DEV_RESEARCH_ONLY",
        strategy_version=pre.strategy_version,
        strategy_package_hash=H,
        dataset_hashes=tuple(d.record_hash for d in dataset_roster),
        parameter_hashes=pre.parameter_hashes,
        roster_hash=digest("B_ROSTER", tuple(o.record_hash for o in ops)),
        trial_ledger_hash=log.record_hash,
        block_plan_hash=blocks.record_hash,
        visibility_hash=vis.record_hash,
        preregistration_hash=pre.record_hash,
        dependency_lock_hash=H,
        config_hash=H,
        python_version="3.12",
        os="SYNTHETIC",
        architecture="SYNTHETIC",
        backtest_version="2.0.0rc5",
        report_code_hash=H,
        universe_hash=H,
        registry_hash=H,
        taxonomy_hash=pre.taxonomy_hash,
        execution_hash=old.cost.fill_model_hash,
        funding_hash=H,
        friction_hash=H,
    )
    run = DevRunSpec.create(**{**old.model_dump(exclude={"record_hash"}), **extra})
    for c in candidates:
        log = log.append(
            trial(pre, semantic_hash=dev_trial_identity(run, c), candidate_hash=c.record_hash)
        )
    run = changed(run, trial_ledger_hash=log.record_hash)
    return (
        run,
        dataset_roster,
        projected,
        tuple(ops),
        candidates,
        frames,
        log,
        blocks,
        vis,
        tuple(authority(d, pre, visibility=vis.channel) for d in dataset_roster),
    )


def checked(args):
    validate_dev_inputs(*args, predecessor=None, previous=None, s0_preparation_hash=H)


def completed(bundle):
    log = bundle.ledger
    for t in tuple(e for e in log.entries if e.kind == "REGISTER"):
        log = log.append(
            completion(log, t, run_hash=bundle.run.record_hash, bundle_hash=bundle.record_hash)
        )
    return log


def test_composed_dev_validate_exact_identity_and_s0_refusal():
    args = dev_fixture()
    checked(args)
    with pytest.raises(TypeError):
        validate_inputs(*args[:9])
    for field, value in (
        ("cost", changed(args[0].cost, delay_ns=3)),
        ("seed", 99),
        ("parameter_hashes", ("b" * 64, "b" * 64)),
    ):
        bad = (changed(args[0], **{field: value}), *args[1:])
        with pytest.raises((ValueError, PermissionError)):
            checked(bad)
    with pytest.raises(PermissionError):
        checked((*args[:6], changed(args[6], history="UNKNOWN_LEGACY_INCOMPLETE"), *args[7:]))
    missing = (
        args[0],
        args[1],
        args[2],
        args[3],
        args[4],
        tuple(changed(f, context=changed(f.context, at=99, source_cutoff=99)) for f in args[5]),
        *args[6:],
    )
    with pytest.raises(ValueError):
        checked(missing)
    with pytest.raises(TypeError):
        checked((*args[:2], (raw(),), *args[3:]))
    with pytest.raises(ValueError):
        checked(
            (
                changed(args[0], trial_ledger_hash=ledger(args[6].preregistration).record_hash),
                *args[1:6],
                ledger(args[6].preregistration),
                *args[7:],
            )
        )


def test_native_missing_prerequisites_fail_before_engine(monkeypatch):
    from trader_assist_v0.research_replay import harness
    from trader_assist_v0.vnext_g4.contracts import ExecutionModelConfig

    args = dev_fixture()
    monkeypatch.setattr(
        harness,
        "_native_candidate",
        lambda *a, **k: pytest.fail("engine before native evidence gate"),
    )
    with pytest.raises(ValueError, match="execution identity"):
        replay_dev(
            *args,
            predecessor=None,
            previous=None,
            s0_preparation_hash=H,
            original_risks=(("retained-thesis", Decimal(1)),),
            events=(),
            instruments={},
            execution=ExecutionModelConfig(
                book_type="L1_MBP",
                order_primitive="MARKETABLE",
                prob_fill_on_limit=Decimal(0),
                prob_slippage=Decimal(0),
                trade_execution=False,
                queue_position=False,
                liquidity_consumption=True,
                fill_limit_at_price=False,
                fill_stop_at_price=False,
                random_seed=7,
                execution_model_limited=True,
            ),
            funding_complete=False,
            funding_applicable=False,
        )


@pytest.mark.skipif(
    importlib.util.find_spec("nautilus_trader") is None
    and os.environ.get("NAUTILUS_G4_REQUIRED") != "1",
    reason="authoritative native rc5 is required in existing CI",
)
def test_matched_s0_dev_real_native_results_and_fingerprints():
    from test_nautilus_vnext_g4_catalog_bridge import MARKET, NATIVE_INSTRUMENT, replay_admitted
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument
    from test_research_data_contracts import dataset
    from test_research_replay_contracts import cost, opportunity
    from test_research_replay_policies import context, policy

    from trader_assist_v0.nautilus_e4.contracts import DataKind
    from trader_assist_v0.research_replay.harness import replay
    from trader_assist_v0.vnext_g4.contracts import ExecutionModelConfig, OrderPrimitive

    quotes = (
        ("1999.0", "2001.0"),
        ("2000.0", "2002.0"),
        ("2001.0", "2003.0"),
        ("2009.0", "2011.0"),
        ("2008.0", "2010.0"),
        ("2007.0", "2009.0"),
    )
    events = tuple(
        replay_admitted(
            i,
            DataKind.BBO,
            payload={"bid_price": bid, "ask_price": ask, "bid_size": "2.000", "ask_size": "3.000"},
        )
        for i, (bid, ask) in enumerate(quotes, 1)
    )
    ds = dataset(
        source="NAUTILUS_HYPERLIQUID",
        venue="HYPERLIQUID",
        instruments=(NATIVE_INSTRUMENT,),
        datatypes=("BBO",),
        end_ns=10000,
    )
    rows = tuple(
        changed(
            raw(
                e.source.ts_event,
                known=e.admission_ts,
                ordinal=e.admission_ordinal,
                ds=ds,
                values={
                    "bid": e.source.payload["bid_price"],
                    "ask": e.source.payload["ask_price"],
                    "bid_size": "2.000",
                    "ask_size": "3.000",
                },
            ),
            ts_init=e.source.ts_init,
            evidence=changed(
                raw(e.source.ts_event, ds=ds).evidence,
                source_hash=e.admission_hash,
                instrument=NATIVE_INSTRUMENT,
                expression=MARKET,
            ),
        )
        for e in events
    )
    op = opportunity(
        market_id=MARKET,
        decision_ns=12,
        knowledge_ns=12,
        entry=Decimal(2000),
        stop=Decimal(1900),
        target=Decimal(2005),
        prefix_hashes=(rows[0].record_hash,),
    )
    ref = candidate(exit=policy("E", "E1"))
    challenger = changed(ref, participation=policy("EA", "EA3"), role="CHALLENGER")
    frames = tuple(
        ContextFrame.create(
            version="B_FRAME_V1",
            opportunity_hash=op.record_hash,
            context=context(
                at=r.known_at,
                source_cutoff=r.known_at,
                input_hashes=(r.record_hash,),
                price_core=True,
            ),
            features=(),
        )
        for r in rows
    )
    execution = ExecutionModelConfig(
        book_type="L1_MBP",
        order_primitive=OrderPrimitive.MARKETABLE,
        prob_fill_on_limit=Decimal(0),
        prob_slippage=Decimal(0),
        trade_execution=False,
        queue_position=False,
        liquidity_consumption=True,
        fill_limit_at_price=False,
        fill_stop_at_price=False,
        random_seed=7,
        execution_model_limited=True,
    )
    cm = cost(
        delay_ns=15, fill_model_hash=digest("B_NATIVE_EXECUTION", execution.model_dump(mode="json"))
    )
    s0 = run_fixture(
        rows=rows, op=op, candidates=(ref, challenger), frames=frames, cost_model=cm, ds=ds
    )
    kwargs = dict(
        events=events,
        instruments={MARKET: native_hyperliquid_instrument()},
        execution=execution,
        funding_complete=False,
        funding_applicable=False,
    )
    old = replay(*s0, **kwargs)
    again = replay(*s0, **kwargs)
    assert old.model_dump_json() == again.model_dump_json()
    args = dev_fixture(s0)
    dev = replay_dev(
        *args,
        predecessor=None,
        previous=None,
        s0_preparation_hash=H,
        original_risks=(("retained-thesis", Decimal(1)),),
        **kwargs,
    )
    repeated = replay_dev(
        *args,
        predecessor=None,
        previous=None,
        s0_preparation_hash=H,
        original_risks=(("retained-thesis", Decimal(1)),),
        **kwargs,
    )
    assert dev.fingerprint == repeated.fingerprint

    def fill_values(fill):
        return fill.model_dump(exclude={"source_hash"}) if fill else None

    for left, right in zip(old.results, dev.results, strict=True):
        assert tuple(fill_values(f) for f in left.fills) == tuple(
            fill_values(f) for f in right.fills
        )
        assert tuple(
            f.model_dump(exclude={"source_hash", "input_hashes"}) for f in left.cashflows
        ) == tuple(f.model_dump(exclude={"source_hash", "input_hashes"}) for f in right.cashflows)
        assert (left.net_cash, left.net_r, left.fee_cash, left.funding_cash, left.terminal) == (
            right.net_cash,
            right.net_r,
            right.fee_cash,
            right.funding_cash,
            right.terminal,
        )
        assert [
            (a.trigger_ns, fill_values(a.fill), fill_values(a.exit_fill), a.state)
            for a in left.attempts
        ] == [
            (a.trigger_ns, fill_values(a.fill), fill_values(a.exit_fill), a.state)
            for a in right.attempts
        ]
        assert left.trigger_path.model_dump(
            exclude={"record_hash", "snapshot_hash", "input_hashes"}
        ) == right.trigger_path.model_dump(exclude={"record_hash", "snapshot_hash", "input_hashes"})
    from trader_assist_v0.research_replay.dev_reporting import (
        canonical_summary,
        diagnostics,
        stage_result,
    )

    assert diagnostics(dev, args[8]) is not None
    final = completed(dev)
    assert canonical_summary(dev, args[8], final)["claim"] == "DEV_RESEARCH_ONLY"
    assert stage_result(dev, args[8], final).promotion == "PROHIBITED"


def test_external_dev_reader_to_causal_feature_and_shared_policy_composition(tmp_path):
    from test_research_data_admission import capability, event
    from test_research_data_mapping import mapping, snapshot
    from test_research_replay_contracts import spec

    from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
    from trader_assist_v0.research_data.admission import AdmissionPolicy, ExternalReferenceLedger
    from trader_assist_v0.research_data.contracts import BboPayload
    from trader_assist_v0.research_data.mapping import PitReferenceResolver
    from trader_assist_v0.research_data.storage import EvidenceSidecar
    from trader_assist_v0.research_replay.dev_evidence import (
        DevExternalAdmission,
        read_external_dev,
    )
    from trader_assist_v0.research_replay.microstructure import bbo_features

    maps = snapshot(mapping(valid_from=1, valid_to=10000, known_at=1, recorded_at=1))
    ds = dev_dataset(source="BINANCE", venue="BINANCE", mapping_hash=maps.record_hash)
    args = dev_fixture(extra_dataset=ds)
    pre = args[6].preregistration
    cap = capability(datatype="BBO")
    policy = AdmissionPolicy.create(
        version="1", stale_after_ns=100, sequence_semantics="CONTIGUOUS", max_observations=100
    )
    admitted = DevExternalAdmission(ds, PitReferenceResolver(maps), (cap,), policy, args[9][1], pre)
    log = ExternalReferenceLedger(admitted)
    for i, t in enumerate((98, 99), 1):
        ev = changed(
            event(admitted, ts=t, seq=i, native_id=str(i)),
            payload=BboPayload(bid="99", ask="101", bid_size="2", ask_size="3"),
        )
        log.observe(ev, evaluated_at_ns=100)
    sidecar = EvidenceSidecar.create(
        version="1",
        dataset_hash=ds.record_hash,
        mapping_hash=maps.record_hash,
        capability_hashes=(cap.record_hash,),
        policy_hash=policy.record_hash,
        observations=tuple(log.observations),
        source_bytes_hex=(),
        raw_semantics="SYNTHETIC",
        catalog_files=(),
    )
    data = canonical_json_bytes(sidecar.model_dump(mode="json"))
    path = tmp_path / "dev.reference.json"
    path.write_bytes(data)
    external = read_external_dev(tmp_path, path, sha256_hex(data), H, admitted)
    feature = bbo_features(external, spec(window_ns=10), 100, 100)
    assert feature.status == "AVAILABLE" and feature.input_hashes == tuple(
        r.record_hash for r in external
    )
    run = changed(args[0], feature_hashes=(feature.spec_hash,))
    frames = tuple(
        changed(
            f,
            context=changed(
                f.context,
                input_hashes=(*f.context.input_hashes, *feature.input_hashes),
                feature_hashes=(feature.record_hash,),
            ),
            features=(feature,),
        )
        for f in args[5]
    )
    prospective = ledger(pre)
    for c in args[4]:
        prospective = prospective.append(
            trial(pre, semantic_hash=dev_trial_identity(run, c), candidate_hash=c.record_hash)
        )
    run = changed(run, trial_ledger_hash=prospective.record_hash)
    composed = (
        run,
        args[1],
        (*args[2], *external),
        args[3],
        args[4],
        frames,
        prospective,
        *args[7:],
    )
    checked(composed)
    assert all(r.evidence.owner == "EXTERNAL_REFERENCE" for r in external)
    forged = external[0].model_copy(update={"known_at": 1000})
    with pytest.raises(ValueError):
        checked(
            (run, args[1], (*args[2], forged), args[3], args[4], frames, prospective, *args[7:])
        )
