"""R0-only factories and adversarial identity checks."""

from decimal import Decimal

import pytest
from test_research_data_contracts import H, dataset

from trader_assist_v0.research_replay.contracts import (
    CostModel,
    EvidenceRef,
    FeatureSpec,
    Observation,
    Opportunity,
)
from trader_assist_v0.research_replay.evidence import require_pipeline

BASE = "ba7c1424b8beb06b15f4254b6864e8d87b93531b"


def changed(value, **updates):
    return type(value).create(**{**value.model_dump(exclude={"record_hash"}), **updates})


def raw(
    ts=100,
    *,
    provider="NAUTILUS_HYPERLIQUID",
    kind="BBO",
    values=None,
    known=None,
    receive=None,
    quality=("COMPLETE",),
    ordinal=None,
    ds=None,
    **updates,
):
    ds = ds or dataset(
        source=provider, venue=provider, instruments=("SYNTH",), datatypes=(kind,), end_ns=10000
    )
    ref = EvidenceRef.create(
        version="B_INPUT_V1",
        owner="HL_E4" if provider == "NAUTILUS_HYPERLIQUID" else "EXTERNAL_REFERENCE",
        source_hash=f"{ts:064x}",
        dataset_hash=ds.record_hash,
        mapping_hash=ds.mapping_hash,
        interval_hash=H,
        registry_hash=H,
        provider=provider,
        instrument="SYNTH",
        expression="SYNTH",
        price_unit="USD",
        size_unit="BASE",
        source_mode="LIVE",
        source_tier="R0",
        exposure_state=ds.exposure_state,
        source_locator="synthetic://R0",
        rights_hash=ds.rights.record_hash,
        valid_from=1,
        valid_to=10000,
        mapping_known_at=1,
        mapping_recorded_at=1,
        coverage_start=ds.start_ns,
        coverage_end=ds.end_ns,
    )
    values = values or {"bid": "99", "ask": "101", "bid_size": "2", "ask_size": "1"}
    return Observation.create(
        version="B_OBSERVATION_V1",
        evidence=ref,
        kind=kind,
        ts_event=ts,
        known_at=known or ts,
        ts_init=known or ts,
        ts_receive=receive,
        ordinal=ordinal if ordinal is not None else ts,
        continuity_epoch="R0",
        quality=quality,
        values=tuple(sorted(values.items())),
        bar_end=ts if kind == "BAR" else None,
        receive_provenance="PROVIDER_EXPOSED" if receive else "NOT_EXPOSED",
        **updates,
    )


def spec(kind="BBO", family="BBO_TRADES", **updates):
    args = dict(
        version="B_SPEC_V1",
        name="R0 toy",
        family=family,
        algorithm="R0_V1",
        implementation=BASE,
        parameters=(),
        required_kinds=(kind,),
        clock="EVENT",
        window_ns=100,
        warmup_ns=0,
        stale_ns=100,
        skew_ns=100,
        unit="USD_BASE",
    )
    args.update(updates)
    return FeatureSpec.create(**args)


def cost(**updates):
    args = dict(
        version="B_COST_V1",
        maker_bps=Decimal(2),
        taker_bps=Decimal(5),
        slippage_bps=Decimal(0),
        delay_ns=1,
        quote_age_ns=100,
        size=Decimal("0.01"),
        fill_model_hash=H,
        fee_profile="R0_configured",
        funding_profile="R0_signed",
    )
    args.update(updates)
    return CostModel.create(**args)


def opportunity(**updates):
    args = dict(
        version="B_OPPORTUNITY_V1",
        opportunity_id=H,
        market_event_id="retained-event",
        thesis_id="retained-thesis",
        market_id="SYNTH",
        setup="SWEEP_RECLAIM",
        mode="STANDARD",
        side="LONG",
        decision_ns=100,
        knowledge_ns=100,
        expiry_ns=1000,
        entry=Decimal(100),
        stop=Decimal(95),
        target=Decimal(105),
        registry_hash=H,
        strategy_hash=H,
        parameter_hash=H,
        prefix_hashes=(raw().record_hash,),
        absence_reason="R0_SUPPRESSED",
        cluster_id="R0-episode",
        regime="R0",
    )
    args.update(updates)
    return Opportunity.create(**args)


def test_hash_tamper_feature_identity_cost_and_no_fourth_setup():
    value = spec()
    payload = value.model_dump(mode="json")
    payload["window_ns"] = 50
    with pytest.raises(ValueError, match="hash"):
        FeatureSpec.model_validate(payload)
    assert changed(value, clock="OBSERVED").record_hash != value.record_hash
    assert changed(cost(), delay_ns=20).record_hash != cost().record_hash
    with pytest.raises(ValueError):
        opportunity(setup="FOURTH_SETUP")
    with pytest.raises(ValueError):
        cost(taker_bps=Decimal("NaN"))
    with pytest.raises(ValueError, match="ownership"):
        changed(raw(provider="OKX").evidence, owner="HL_E4")


@pytest.mark.parametrize("tier", [f"R{i}" for i in range(7)])
@pytest.mark.parametrize(
    "state",
    [
        "UNSEEN_SEALED",
        "DEV_EXPOSED",
        "VALIDATION_SEALED",
        "VALIDATION_USED",
        "FINAL_LOCKBOX_SEALED",
        "FINAL_LOCKBOX_USED",
        "RETIRED",
    ],
)
def test_quality_never_grants_access(tier, state):
    with pytest.raises(PermissionError):
        require_pipeline(dataset(source_tier=tier, exposure_state=state))


def test_e4_sealed_gate_precedes_store_methods_and_output_cannot_be_e4():
    from trader_assist_v0.nautilus_e4.contracts import SourceEvent
    from trader_assist_v0.research_replay.evidence import read_e4

    class NeverRead:
        def load_manifest(self):
            pytest.fail("sealed manifest I/O")

    with pytest.raises(PermissionError):
        read_e4(NeverRead(), dataset(exposure_state="FINAL_LOCKBOX_SEALED"), H, H, H)
    with pytest.raises(ValueError):
        SourceEvent.model_validate(raw(provider="OKX").model_dump())


def test_lawful_retained_domain_ids_are_bound_not_manufactured():
    from trader_assist_v0.multi_asset_shadow.shadow_records.records import MarketEvent
    from trader_assist_v0.research_replay.evidence import bind_domain_records

    record = MarketEvent.create(
        identity={"R0": "toy"}, market_id="SYNTH", event_kind="R0", event_time=100
    )
    op = opportunity(market_event_id=record.record_id)
    bound = bind_domain_records(op, (record,), dataset())
    assert bound.market_event_id == record.record_id and bound.formal_signal_id is None
    assert bound.domain_hashes == (record.canonical_hash,)
    with pytest.raises(ValueError, match="do not fabricate"):
        bind_domain_records(op, (), dataset())


def test_revalidate_constructed_manifest_before_access():
    ds = dataset()
    forged = ds.model_copy(update={"exposure_state": "SACRIFICIAL", "checksum": "b" * 64})
    with pytest.raises(ValueError, match="hash"):
        require_pipeline(forged)
