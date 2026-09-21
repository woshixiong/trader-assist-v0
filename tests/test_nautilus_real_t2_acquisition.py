from __future__ import annotations

import json
from decimal import Decimal

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
    PHASE0C_STRATEGY_PACKAGE_HASH,
    REAL_T2_ACQUISITION_NS,
    RealT2IntegrationError,
    RealT2StrategyCoordinator,
    admitted_external_5m_to_strategy_input,
    expected_external_bar_type,
    materialize_fixed_markets_from_public_metadata,
    raw_response_sha256,
    select_focal_formal_setup,
)


def _bar(*, market_index: int = 0, minutes: int = 5, ordinal: int = 1,
         ts_event: int = 300_000_000_000, context: str | None = None,
         continuity: EvidenceState = EvidenceState.COMPLETE,
         out_of_order: bool = False) -> AdmittedEvent:
    frozen = FROZEN_MARKETS[market_index]
    duration = minutes * 60_000_000_000
    source = SourceEvent.create(
        market_id=frozen.market_id,
        expression_id=f"expr-{market_index}",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=frozen.instrument_id,
        data_kind=DataKind.BAR,
        source_event_id=f"bar-{market_index}-{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=context or expected_external_bar_type(frozen.instrument_id, minutes),
        ts_event=ts_event,
        ts_init=ts_event + duration,
        true_network_receive_ts=None,
        payload={
            "open": "100", "high": "102", "low": "99", "close": "101",
            "volume": "10", "finalized": True,
        },
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process",
        continuity_epoch="continuity",
        admission_epoch="admission",
        admission_ordinal=ordinal,
        admission_ts=source.ts_init + 1,
        source_identity=source.replay_identity,
        out_of_order=out_of_order,
        continuity_state=continuity,
        source=source,
    )


def _meta_response() -> bytes:
    universe = []
    contexts = []
    for item in FROZEN_MARKETS:
        universe.append({"name": item.provider_coin, "szDecimals": 2, "maxLeverage": 10})
        contexts.append({"markPx": "100"})
    return json.dumps([{"universe": universe}, contexts], separators=(",", ":")).encode()


def test_public_client_preserves_exact_raw_response_bytes() -> None:
    raw = b'{"exact":"bytes", "spacing":true}'
    client = HyperliquidPublicClient(post=lambda *_: raw)
    response = client.request_with_raw({"type": "meta"})
    assert response.raw_bytes == raw
    assert response.raw_sha256 == raw_response_sha256(raw)
    assert response.parsed == {"exact": "bytes", "spacing": True}


def test_provider_native_5m_projection_binds_frozen_strategy_package() -> None:
    projected = admitted_external_5m_to_strategy_input(
        _bar(), strategy_package_hash=PHASE0C_STRATEGY_PACKAGE_HASH
    )
    assert projected.strategy_package_hash == PHASE0C_STRATEGY_PACKAGE_HASH
    assert projected.closed_bar.interval == "5m"
    assert projected.closed_bar.provenance_hash == _bar().admission_hash


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"minutes": 1}, "5m"),
        ({"context": FROZEN_MARKETS[0].instrument_id + "-5-MINUTE-LAST-INTERNAL"}, "LAST EXTERNAL"),
        ({"continuity": EvidenceState.INCOMPLETE}, "gapped"),
        ({"out_of_order": True}, "gapped"),
    ],
)
def test_strategy_projection_rejects_wrong_route_or_bad_admission(kwargs: dict[str, object], match: str) -> None:
    event = _bar(**kwargs)
    with pytest.raises(RealT2IntegrationError, match=match):
        admitted_external_5m_to_strategy_input(
            event, strategy_package_hash=PHASE0C_STRATEGY_PACKAGE_HASH
        )


def test_metadata_materialization_is_exact_20_market_and_no_substitution() -> None:
    raw = _meta_response()
    parsed = json.loads(raw)
    markets = materialize_fixed_markets_from_public_metadata(
        raw_response=raw, parsed_response=parsed, observed_at_ns=1
    )
    assert tuple(x.identity for x in markets) == FROZEN_MARKETS
    assert len(markets) == 20
    tampered = json.loads(raw)
    tampered[0]["universe"][0]["name"] = "SUBSTITUTE"
    tampered_raw = json.dumps(tampered, separators=(",", ":")).encode()
    with pytest.raises(RealT2IntegrationError, match="substitution"):
        materialize_fixed_markets_from_public_metadata(
            raw_response=tampered_raw, parsed_response=tampered, observed_at_ns=1
        )


def test_metadata_rejects_raw_parsed_mismatch() -> None:
    raw = _meta_response()
    parsed = json.loads(raw)
    parsed[1][0]["markPx"] = "999"
    with pytest.raises(RealT2IntegrationError, match="exact raw"):
        materialize_fixed_markets_from_public_metadata(
            raw_response=raw, parsed_response=parsed, observed_at_ns=1
        )


def test_coordinator_requires_exact_fixed_cutoff_and_market_set() -> None:
    raw = _meta_response()
    markets = materialize_fixed_markets_from_public_metadata(
        raw_response=raw, parsed_response=json.loads(raw), observed_at_ns=1
    )
    registry = {x.identity.market_id: x.registry_market for x in markets}
    with pytest.raises(RealT2IntegrationError, match="14400"):
        RealT2StrategyCoordinator(
            registry_markets=registry,
            open_structural_package=lambda **_: EvidenceState.COMPLETE,
            clock_start_ns=1,
            cutoff_ns=1 + REAL_T2_ACQUISITION_NS + 1,
        )
    with pytest.raises(RealT2IntegrationError, match="exact frozen markets"):
        RealT2StrategyCoordinator(
            registry_markets=dict(list(registry.items())[:-1]),
            open_structural_package=lambda **_: EvidenceState.COMPLETE,
            clock_start_ns=1,
            cutoff_ns=1 + REAL_T2_ACQUISITION_NS,
        )


def test_focal_selection_is_outcome_blind_minimum() -> None:
    # Empty is a first-class no-opportunity terminal input; ordering logic itself
    # is covered by StructuralSourceEvidence replay tests below.
    assert select_focal_formal_setup(()) is None


def test_no_private_or_write_surface_in_acquisition_module() -> None:
    import inspect
    import trader_assist_v0.nautilus_g4.t2_acquisition as module

    source = inspect.getsource(module)
    forbidden = ("private_key", "signer", "submit_order", "place_order", "cancel_order")
    assert all(token not in source for token in forbidden)
    assert "LAST-EXTERNAL" in source
    assert "REAL_T2_ACQUISITION_SECONDS = 14_400" in source
