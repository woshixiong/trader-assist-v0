from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal

import pytest

from trader_assist_v0.contracts.common import (
    canonical_json_bytes,
    sha256_hex,
)
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    HyperliquidPublicClient,
)
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
from trader_assist_v0.nautilus_g4.t2_acquisition import (
    EXECUTION_CONTROL_RECORD,
    EXECUTION_MODEL_SOURCE_HASH,
    FEE_CONTROL_RECORD,
    FEE_PROFILE_SOURCE_HASH,
    FRICTION_POLICY_RECORD,
    FRICTION_POLICY_SOURCE_HASH,
    FROZEN_MARKETS,
    LATENCY_CONTROL_RECORD,
    LATENCY_CONTROL_SOURCE_HASH,
    PHASE0C_MARKET_SET_HASH,
    REAL_T2_ACQUISITION_SECONDS,
    FormalSetupObservation,
    RealT2IntegrationError,
    StructuralSourceEvidence,
    admitted_external_5m_to_strategy_input,
    assess_public_funding_history,
    expected_external_bar_type,
    frozen_task5d_prospective_candidate,
    materialize_fixed_markets_from_public_metadata,
    materialize_task5d_g4_manifest,
    materialize_task5d_validation_source,
    provider_instrument_metadata_document,
    select_focal_causal_bbo,
    select_focal_formal_setup,
)
from trader_assist_v0.nautilus_g4.t2_shadow import (
    RoleBoundSourceArtifact,
    T2SourceRole,
)
from trader_assist_v0.nautilus_pilot.strategy_package import StrategyPackageManifest
from trader_assist_v0.vnext_g4.contracts import PositionSide


def _admission(
    *,
    minutes: int = 5,
    ordinal: int = 1,
    ts_event: int = 1_800_000_000_000_000_000,
    ts_init: int | None = None,
    finalized: bool = True,
    context: str | None = None,
    continuity: EvidenceState = EvidenceState.COMPLETE,
    out_of_order: bool = False,
) -> AdmittedEvent:
    market = FROZEN_MARKETS[0]
    duration = minutes * 60_000_000_000
    initialized = ts_event + duration if ts_init is None else ts_init
    source = SourceEvent.create(
        market_id=market.market_id,
        expression_id="task5d-test-expression",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=market.instrument_id,
        data_kind=DataKind.BAR,
        source_event_id=f"bar-{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=context or expected_external_bar_type(market.instrument_id, minutes),
        ts_event=ts_event,
        ts_init=initialized,
        true_network_receive_ts=None,
        payload={
            "open": "100",
            "high": "102",
            "low": "99",
            "close": "101",
            "volume": "12",
            "finalized": finalized,
        },
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-test",
        continuity_epoch="continuity-test",
        admission_epoch="admission-test",
        admission_ordinal=ordinal,
        admission_ts=initialized,
        source_identity=source.replay_identity,
        out_of_order=out_of_order,
        continuity_state=continuity,
        source=source,
    )


def test_fixed_identity_and_duration_are_not_configurable() -> None:
    assert REAL_T2_ACQUISITION_SECONDS == 14_400
    assert len(FROZEN_MARKETS) == 20
    assert PHASE0C_MARKET_SET_HASH == (
        "9044fb1fa5f25d29cea9c42ee5e3f5aa73448db08d26a988f5d0e8df10dd24ca"
    )


def test_exact_5m_external_admission_projects_with_e4_hash() -> None:
    event = _admission()
    package = StrategyPackageManifest.create(
        trade_os_release_sha="830f0e6ab3bfb711cf29b83f41a7c86ed7fae0c2"
    )
    projected = admitted_external_5m_to_strategy_input(
        event, strategy_package_hash=package.manifest_hash
    )
    assert projected.interval == "5m"
    assert projected.provenance_hash == event.admission_hash
    assert projected.closed_bar.provenance_hash == event.admission_hash
    assert projected.closed_bar.received_at.timestamp() == event.admission_ts / 1_000_000_000


@pytest.mark.parametrize(
    "event",
    [
        _admission(minutes=1),
        _admission(context=expected_external_bar_type(FROZEN_MARKETS[0].instrument_id, 1)),
        _admission(finalized=False),
        _admission(ts_init=1_800_000_000_000_000_001),
        _admission(ts_event=1_800_000_001_000_000_000),
        _admission(continuity=EvidenceState.GAPPED),
        _admission(out_of_order=True),
    ],
)
def test_5m_seam_fails_closed_on_wrong_route_finality_or_causality(
    event: AdmittedEvent,
) -> None:
    package = StrategyPackageManifest.create(
        trade_os_release_sha="830f0e6ab3bfb711cf29b83f41a7c86ed7fae0c2"
    )
    with pytest.raises((RealT2IntegrationError, ValueError)):
        admitted_external_5m_to_strategy_input(
            event, strategy_package_hash=package.manifest_hash
        )


def test_raw_public_response_bytes_are_retained_losslessly() -> None:
    raw = b'{ "universe" : [1, 2, 3] }\n'
    client = HyperliquidPublicClient(post=lambda _url, _body, _timeout: raw)
    response = client.request_with_raw({"type": "meta"})
    assert response.raw_bytes == raw
    assert response.parsed == {"universe": [1, 2, 3]}
    assert json.dumps(response.parsed, separators=(",", ":")).encode() != raw


def test_metadata_materializer_rejects_missing_frozen_market_without_substitution() -> None:
    universe = [
        {"name": item.provider_coin, "szDecimals": 2, "maxLeverage": 20}
        for item in FROZEN_MARKETS[:-1]
    ]
    contexts = [{} for _ in universe]
    raw = json.dumps([{"universe": universe}, contexts], separators=(",", ":")).encode()
    with pytest.raises(RealT2IntegrationError, match="substitution prohibited"):
        materialize_fixed_markets_from_public_metadata(
            raw_response=raw,
            parsed_response=json.loads(raw),
            observed_at_ns=1_800_000_000_000_000_000,
        )


def test_metadata_materializer_is_exact_20_and_explicit_registry() -> None:
    universe = [
        {"name": item.provider_coin, "szDecimals": 3, "maxLeverage": 20}
        for item in FROZEN_MARKETS
    ]
    contexts = [{} for _ in universe]
    raw = json.dumps([{"universe": universe}, contexts], separators=(",", ":")).encode()
    result = materialize_fixed_markets_from_public_metadata(
        raw_response=raw,
        parsed_response=json.loads(raw),
        observed_at_ns=1_800_000_000_000_000_000,
    )
    assert len(result) == 20
    assert [item.identity.ordinal for item in result] == list(range(1, 21))
    assert all(item.registry_market.identity.dex == "MAIN" for item in result)
    assert all(item.registry_market.asset_class.value == "CRYPTO" for item in result)
    assert all(item.registry_market.lifecycle.value == "ACTIVE" for item in result)
    assert all(item.registry_market.price_max_significant_figures == 5 for item in result)
    assert all(item.registry_market.price_max_decimals == 3 for item in result)


def test_focal_rule_uses_timestamp_then_market_then_admission_then_id() -> None:
    # Construction bypasses Strategy economics only for testing the frozen selector itself.
    def obs(ts: int, market_ordinal: int, admission_ordinal: int, setup_id: str):
        market = FROZEN_MARKETS[market_ordinal - 1]
        structural = StructuralSourceEvidence.model_construct(
            strategy_package_hash="0" * 64,
            market_id=market.market_id,
            exact_market_set_ordinal=market_ordinal,
            formal_setup_admission_ordinal=admission_ordinal,
            formal_setup_admission_ts=ts,
            formal_setup_id=setup_id,
            triggering_admission_hash="1" * 64,
            decision={},
            decision_hash="2" * 64,
        )
        return FormalSetupObservation(
            structural=structural,
            package_id="p-" + setup_id,
            opportunity_id="o-" + setup_id,
            thesis_id="t-" + setup_id,
            continuity_epoch="continuity-test",
            admission_epoch="admission-test",
        )

    later_take_like = obs(101, 1, 1, "later")
    earlier_non_take_like = obs(100, 2, 9, "earlier")
    assert select_focal_formal_setup(
        (later_take_like, earlier_non_take_like)
    ) is earlier_non_take_like


class _ProviderInstrument:
    def __init__(self, *, size_increment: str = "0.001") -> None:
        self.id = FROZEN_MARKETS[0].instrument_id
        self.price_increment = Decimal("0.1")
        self.size_precision = 3
        self.size_increment = Decimal(size_increment)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "price_increment": str(self.price_increment),
            "size_precision": self.size_precision,
            "size_increment": str(self.size_increment),
        }


def _fixed_materialization():
    universe = [
        {
            "name": item.provider_coin,
            "szDecimals": 3,
            "maxLeverage": 20,
        }
        for item in FROZEN_MARKETS
    ]
    contexts = [{} for _ in universe]
    raw = json.dumps(
        [{"universe": universe}, contexts],
        separators=(",", ":"),
    ).encode()
    markets = materialize_fixed_markets_from_public_metadata(
        raw_response=raw,
        parsed_response=json.loads(raw),
        observed_at_ns=1_800_000_000_000_000_000,
    )
    return raw, markets[0]


def _focal_for_validation() -> FormalSetupObservation:
    market = FROZEN_MARKETS[0]
    structural = StructuralSourceEvidence.model_construct(
        strategy_package_hash="0" * 64,
        market_id=market.market_id,
        exact_market_set_ordinal=1,
        formal_setup_admission_ordinal=1,
        formal_setup_admission_ts=1_800_000_000_000_000_000,
        formal_setup_id="setup-validation",
        triggering_admission_hash="1" * 64,
        decision={},
        decision_hash="2" * 64,
    )
    return FormalSetupObservation(
        structural=structural,
        package_id="package-validation",
        opportunity_id="opportunity-validation",
        thesis_id="thesis-validation",
        continuity_epoch="continuity-test",
        admission_epoch="admission-test",
    )


def _bbo_for_validation(
    *, ordinal: int = 2, ask_size: str = "1.000"
) -> AdmittedEvent:
    market = FROZEN_MARKETS[0]
    source = SourceEvent.create(
        market_id=market.market_id,
        expression_id="task5d-test-expression",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=market.instrument_id,
        data_kind=DataKind.BBO,
        source_event_id=f"bbo-{ordinal}-{ask_size}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=f"block-time-{ordinal}",
        ts_event=1_800_000_000_000_000_000 + ordinal,
        ts_init=1_800_000_000_000_000_100 + ordinal,
        true_network_receive_ts=None,
        payload={
            "bid_price": "99.9",
            "ask_price": "100.1",
            "bid_size": "1.000",
            "ask_size": ask_size,
        },
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-test",
        continuity_epoch="continuity-test",
        admission_epoch="admission-test",
        admission_ordinal=ordinal,
        admission_ts=1_800_000_000_000_000_200 + ordinal,
        source_identity=source.replay_identity,
        out_of_order=False,
        continuity_state=EvidenceState.COMPLETE,
        source=source,
    )


def _validation_materialization(
    *,
    ordinal: int = 2,
    ask_size: str = "1.000",
    size_increment: str = "0.001",
    hip3: bool = False,
):
    raw, market = _fixed_materialization()
    if hip3:
        market = replace(
            market,
            registry_market=market.registry_market.model_copy(
                update={"is_hip3": True}
            ),
        )
    focal = _focal_for_validation()
    bbo = _bbo_for_validation(
        ordinal=ordinal,
        ask_size=ask_size,
    )
    causal = select_focal_causal_bbo(
        admissions=(bbo,),
        focal=focal,
        side=PositionSide.LONG,
    )
    assert causal is not None
    provider = _ProviderInstrument(
        size_increment=size_increment
    )
    metadata_document = provider_instrument_metadata_document(
        raw_provider_response=raw,
        materialization=market,
        provider_instrument=provider,
    )
    metadata_artifact = RoleBoundSourceArtifact.create(
        role=T2SourceRole.INSTRUMENT_METADATA,
        name="instrument-metadata-01",
        exact_bytes=metadata_document,
    )
    bbo_artifact = RoleBoundSourceArtifact.create(
        role=T2SourceRole.E4_ADMISSION,
        name=f"bbo-{ordinal}",
        exact_bytes=canonical_json_bytes(
            bbo.model_dump(mode="json")
        ),
    )
    structural_artifact = RoleBoundSourceArtifact.create(
        role=T2SourceRole.STRUCTURAL_SOURCE,
        name="structural",
        exact_bytes=b"structural",
    )
    prospective = frozen_task5d_prospective_candidate()
    prospective_artifact = RoleBoundSourceArtifact.create(
        role=(
            T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY
        ),
        name="prospective",
        exact_bytes=canonical_json_bytes(
            prospective.model_dump(mode="json")
        ),
    )
    candidate = prospective.materialize_candidate_manifest(
        structural_component_manifest_hash=(
            structural_artifact.artifact_hash
        )
    )
    g4 = materialize_task5d_g4_manifest(
        exact_source_git_head="a" * 40,
        exact_source_git_tree="b" * 40,
        e4_manifest_hash="3" * 64,
        pit_snapshot_hash="4" * 64,
        structural_artifact=structural_artifact,
        candidate=candidate,
        e4_admission_artifacts=(bbo_artifact,),
    )
    g4_artifact = RoleBoundSourceArtifact.create(
        role=T2SourceRole.G4_RUN_MANIFEST,
        name="g4-run",
        exact_bytes=canonical_json_bytes(
            g4.model_dump(mode="json")
        ),
    )
    validation = materialize_task5d_validation_source(
        clock_start_ns=1_800_000_000_000_000_000,
        exact_source_git_head="a" * 40,
        exact_source_git_tree="b" * 40,
        focal=focal,
        side=PositionSide.LONG,
        causal_bbo=causal,
        provider_instrument=provider,
        registry_market=market.registry_market,
        instrument_metadata_version=(
            market.expression.instrument_metadata_version
        ),
        instrument_metadata_artifact=metadata_artifact,
        e4_admission_artifact=bbo_artifact,
        prospective_candidate_artifact=prospective_artifact,
        prospective_candidate=prospective,
        g4_run_manifest_artifact=g4_artifact,
        g4_run_manifest=g4,
    )
    return validation, causal, metadata_artifact


def test_frozen_validation_static_hashes_match_authority() -> None:
    assert (
        sha256_hex(canonical_json_bytes(FEE_CONTROL_RECORD))
        == FEE_PROFILE_SOURCE_HASH
    )
    assert (
        sha256_hex(canonical_json_bytes(FRICTION_POLICY_RECORD))
        == FRICTION_POLICY_SOURCE_HASH
    )
    assert (
        sha256_hex(canonical_json_bytes(EXECUTION_CONTROL_RECORD))
        == EXECUTION_MODEL_SOURCE_HASH
    )
    assert (
        sha256_hex(canonical_json_bytes(LATENCY_CONTROL_RECORD))
        == LATENCY_CONTROL_SOURCE_HASH
    )


def test_validation_source_materializes_exact_control_profile() -> None:
    validation, causal, _metadata = _validation_materialization()
    reference = validation.validation_reference
    assert reference.fully_materialized is True
    assert reference.fee_bps == Decimal("4.5")
    assert reference.all_in_friction_bps == Decimal("9.0")
    assert reference.actual_user_fee_rate_claim is False
    assert reference.production_account_fee_authority is False
    assert reference.latency_ms == 0
    assert reference.latency_evidence_role.value == "CONTROL_ONLY"
    document = json.loads(
        validation.validation_source_artifact.exact_bytes()
    )
    assert (
        document["attempt_binding"]["focal_bbo_admission_hash"]
        == causal.admission.admission_hash
    )
    friction = document["friction_control"]["record"]
    assert (
        friction["spread_state"]
        == "NOT_APPLICABLE_AS_SEPARATE_DEBIT"
    )
    assert friction["slippage_extra_control_bps"] == "0"
    assert friction["all_in_friction_bps"] == "9.0"
    assert FRICTION_POLICY_RECORD["slippage_zero_scope"] == (
        "CONTROL_ONLY"
    )


def test_causal_bbo_uses_latest_complete_same_lineage_at_cutoff() -> None:
    focal = _focal_for_validation()
    first = _bbo_for_validation(ordinal=2)
    later = _bbo_for_validation(ordinal=3)
    binding = select_focal_causal_bbo(
        admissions=(later, first),
        focal=focal,
        side=PositionSide.LONG,
    )
    assert binding is not None
    assert binding.admission.admission_hash == later.admission_hash
    assert binding.executable_price == Decimal("100.1")
    assert binding.opposite_l1_size == Decimal("1.000")


def test_quantity_over_causal_opposite_l1_fails_closed() -> None:
    with pytest.raises(
        RealT2IntegrationError,
        match="exceeds causal opposite L1",
    ):
        _validation_materialization(ask_size="0.0005")


def test_missing_or_invalid_provider_increment_fails_closed() -> None:
    with pytest.raises(
        RealT2IntegrationError,
        match="size increment is invalid",
    ):
        _validation_materialization(size_increment="0")


def test_hip3_validation_profile_is_not_guessed() -> None:
    with pytest.raises(
        RealT2IntegrationError,
        match="MAIN non-HIP3",
    ):
        _validation_materialization(hip3=True)


def test_dynamic_hashes_bind_causal_source_identity() -> None:
    first, _causal_first, _ = _validation_materialization(
        ordinal=2
    )
    second, _causal_second, _ = _validation_materialization(
        ordinal=3
    )
    assert first.quantity_source_hash != second.quantity_source_hash
    assert first.friction_source_hash != second.friction_source_hash


def test_funding_history_no_event_event_and_missing_are_distinct() -> None:
    no_event = assess_public_funding_history(
        raw_response=b"[]",
        parsed_response=[],
        coin="BTC",
        start_time_ms=1_000,
        end_time_ms=2_000,
    )
    assert no_event.state == "NOT_APPLICABLE"
    assert no_event.source_hash == sha256_hex(b"[]")
    event_raw = (
        b'[{"coin":"BTC","fundingRate":"0.0001",'
        b'"premium":"0","time":1500}]'
    )
    event = assess_public_funding_history(
        raw_response=event_raw,
        parsed_response=json.loads(event_raw),
        coin="BTC",
        start_time_ms=1_000,
        end_time_ms=2_000,
    )
    assert event.state == "NOT_EVALUABLE"
    assert event.reason == "FUNDING_EVENT_PRESENT_V1"
    missing = assess_public_funding_history(
        raw_response=None,
        parsed_response=None,
        coin="BTC",
        start_time_ms=1_000,
        end_time_ms=2_000,
    )
    assert missing.state == "NOT_EVALUABLE"
    assert missing.source_hash is None


def test_missing_bbo_is_not_evaluable_and_not_synthesized() -> None:
    assert (
        select_focal_causal_bbo(
            admissions=(),
            focal=_focal_for_validation(),
            side=PositionSide.LONG,
        )
        is None
    )

