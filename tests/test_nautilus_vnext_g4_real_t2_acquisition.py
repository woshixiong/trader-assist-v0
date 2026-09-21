from __future__ import annotations

import json

import pytest

from trader_assist_v0.multi_asset_shadow.hyperliquid_public import HyperliquidPublicClient
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
from trader_assist_v0.nautilus_g4.t2_acquisition import (
    FROZEN_MARKETS,
    PHASE0C_MARKET_SET_HASH,
    REAL_T2_ACQUISITION_SECONDS,
    FormalSetupObservation,
    RealT2IntegrationError,
    StructuralSourceEvidence,
    admitted_external_5m_to_strategy_input,
    expected_external_bar_type,
    materialize_fixed_markets_from_public_metadata,
    select_focal_formal_setup,
)
from trader_assist_v0.nautilus_pilot.strategy_package import StrategyPackageManifest


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
        process_epoch="p",
        continuity_epoch="c",
        admission_epoch="a",
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
            continuity_epoch="c",
            admission_epoch="a",
        )

    later_take_like = obs(101, 1, 1, "later")
    earlier_non_take_like = obs(100, 2, 9, "earlier")
    assert select_focal_formal_setup(
        (later_take_like, earlier_non_take_like)
    ) is earlier_non_take_like
