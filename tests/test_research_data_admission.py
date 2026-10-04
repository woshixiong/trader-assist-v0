"""External continuity is independent of execution truth."""

import pytest
from test_research_data_contracts import dataset
from test_research_data_mapping import mapping, snapshot

from trader_assist_v0.research_data.admission import (
    AdmissionPolicy,
    ExternalReferenceAdmission,
    ExternalReferenceLedger,
)
from trader_assist_v0.research_data.contracts import (
    CapabilityState,
    ControlReplan,
    ExternalReferenceEvent,
    ProviderCapability,
    SourceMode,
    TimestampProvenance,
    TradePayload,
)
from trader_assist_v0.research_data.mapping import PitReferenceResolver


def capability(**updates):
    values = dict(
        version="synthetic-v1",
        provider="BINANCE",
        venue="BINANCE",
        product="SYNTHETIC_SWAP",
        source_mode="LIVE",
        datatype="TRADE",
        source_exposes=True,
        source_evidence="synthetic://source-exposure",
        adapter_state="AVAILABLE_VERIFIED",
        adapter_owner="NAUTILUS_RC5",
        proof_locator="synthetic://offline-contract",
        enabled=True,
    )
    values.update(updates)
    return ProviderCapability.create(**values)


def admission(
    *,
    provider="BINANCE",
    mode=SourceMode.LIVE,
    datatype="TRADE",
    ds_changes=None,
    policy_changes=None,
):
    maps = snapshot(mapping(provider=provider, venue=provider, valid_to=10**18))
    caps = (
        capability(
            provider=provider,
            venue=provider,
            source_mode=mode,
            datatype=datatype,
            adapter_owner="FREE_FILE"
            if mode == SourceMode.FREE_REFERENCE_IMPORT
            else "NAUTILUS_RC5",
        ),
    )
    ds = dataset(
        source=provider,
        venue=provider,
        instruments=("SYNTH",),
        datatypes=(datatype,),
        mapping_hash=maps.record_hash,
        **(ds_changes or {}),
    )
    policy = AdmissionPolicy.create(
        version="synthetic-v1",
        **{
            "stale_after_ns": 100,
            "sequence_semantics": "CONTIGUOUS",
            "max_observations": 100,
            **(policy_changes or {}),
        },
    )
    return ExternalReferenceAdmission(
        ds, PitReferenceResolver(maps), caps, policy, production=False
    )


def event(bound, *, ts=1000, seq=1, native_id="one", price="10", mode=None):
    ds = bound.dataset
    cap = bound.capabilities[0]
    return ExternalReferenceEvent.create(
        version="synthetic-v1",
        provider=cap.provider,
        venue=cap.venue,
        product=cap.product,
        instrument_id="SYNTH",
        mapping_hash=ds.mapping_hash,
        dataset_hash=ds.record_hash,
        capability_hash=cap.record_hash,
        rights_hash=ds.rights.record_hash,
        source_mode=mode or cap.source_mode,
        native_id=native_id,
        sequence=seq,
        timestamps=TimestampProvenance(
            source_ts=str(ts),
            source_unit="ns",
            ts_event=ts,
            observed_at_ns=ts + 1,
            receive_provenance="NOT_EXPOSED",
        ),
        payload=TradePayload(
            price=price, size="1", native_id=native_id, aggressor="UNKNOWN", trade_semantics="TRADE"
        ),
    )


def test_absent_stale_gap_duplicate_late_and_no_silent_current_replace():
    bound = admission()
    ledger = ExternalReferenceLedger(bound)
    assert ledger.current("BINANCE", "SYNTH", "TRADE", evaluated_at_ns=1000).states == (
        CapabilityState.RUNTIME_UNAVAILABLE,
    )
    first = event(bound)
    assert ledger.observe(first, evaluated_at_ns=1001).admitted
    assert ledger.observe(first, evaluated_at_ns=1002).duplicate
    gap = ledger.observe(event(bound, ts=1050, seq=3, native_id="three"), evaluated_at_ns=1051)
    assert CapabilityState.GAP in gap.quality.states
    late = ledger.observe(event(bound, ts=1020, seq=2, native_id="two"), evaluated_at_ns=1052)
    assert late.out_of_order and late.admitted
    assert (
        CapabilityState.STALE
        not in ledger.current("BINANCE", "SYNTH", "TRADE", evaluated_at_ns=1140).states
    )
    states = ledger.current("BINANCE", "SYNTH", "TRADE", evaluated_at_ns=1200).states
    assert CapabilityState.STALE in states and CapabilityState.GAP in states
    assert len(ledger.observations) == 4


def test_identity_conflict_missing_receive_unknown_sequence():
    bound = admission()
    ledger = ExternalReferenceLedger(bound)
    ledger.observe(event(bound), evaluated_at_ns=1001)
    with pytest.raises(ValueError, match="INVALID_EVIDENCE"):
        ledger.observe(event(bound, price="11"), evaluated_at_ns=1001)
    result = ledger.observe(event(bound, seq=None, native_id="unknown"), evaluated_at_ns=1001)
    assert CapabilityState.CONTINUITY_UNKNOWN in result.quality.states
    assert result.event.timestamps.true_network_receive_ts is None


def test_disagreement_preserves_provider_facts():
    left, right = admission(), admission(provider="OKX")
    a = ExternalReferenceLedger(left).observe(event(left, price="10"), evaluated_at_ns=1001)
    b = ExternalReferenceLedger(right).observe(event(right, price="11"), evaluated_at_ns=1001)
    assert a.event.provider != b.event.provider and a.event.payload.price != b.event.payload.price
    with pytest.raises(ValueError):
        left.validate(b.event, 1001)


@pytest.mark.parametrize(
    "state",
    [
        "ADAPTER_UNSUPPORTED",
        "CAPABILITY_UNPROVEN",
        "CONFIG_DISABLED",
        "RUNTIME_UNAVAILABLE",
        "DISCONNECTED",
        "STALE",
        "GAP",
        "INVALID_EVIDENCE",
        "CONTINUITY_UNKNOWN",
    ],
)
def test_required_core_not_downgraded(state):
    with pytest.raises(ControlReplan):
        capability(adapter_state=state).require_core_proof()


def test_source_absence_optional_disabled_and_unknown_exposure_distinct():
    capability(
        source_exposes=False, adapter_state="SOURCE_NOT_AVAILABLE", enabled=False
    ).require_core_proof()
    for values in (
        dict(source_exposes=None),
        dict(source_exposes=False),
        dict(source_exposes=False, adapter_state="SOURCE_NOT_AVAILABLE", source_evidence=""),
    ):
        with pytest.raises(ControlReplan):
            capability(**values).require_core_proof()
    capability(
        datatype="DEPTH10", enabled=False, adapter_state="CONFIG_DISABLED"
    ).require_core_proof()
    assert len(CapabilityState) == 11


def test_history_keeps_mode_not_live_freshness_or_original_receive():
    bound = admission(mode=SourceMode.HISTORY)
    result = ExternalReferenceLedger(bound).observe(event(bound), evaluated_at_ns=10_000)
    assert CapabilityState.STALE not in result.quality.states
    assert result.event.source_mode == SourceMode.HISTORY
    assert result.event.timestamps.true_network_receive_ts is None


def test_binding_tamper_future_and_bound_limit():
    bound = admission(policy_changes={"max_observations": 1})
    ledger = ExternalReferenceLedger(bound)
    with pytest.raises(ValueError):
        ledger.observe(event(bound).model_copy(update={"provider": "OKX"}), evaluated_at_ns=1001)
    with pytest.raises(ValueError):
        ledger.observe(event(bound), evaluated_at_ns=999)
    ledger.observe(event(bound), evaluated_at_ns=1001)
    with pytest.raises(ValueError, match="limit"):
        ledger.observe(event(bound), evaluated_at_ns=1001)
