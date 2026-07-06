from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import (
    CandidateKindV0,
    DirectionV0,
    HealthStateV0,
    InstrumentPrecisionContractV0,
    MandatoryFeedStatusV0,
    PlaybookIdV0,
    RequiredFeedContractV0,
    StrategyCandidateV0,
)


def contract(now):
    return RequiredFeedContractV0.bind(
        schema_version="0.1.0",
        contract_id="feeds-lqs-fr-001",
        playbook_id="LQS-FR",
        contract_version="feeds.0.1",
        mandatory_feed_ids=frozenset({"hl-bbo"}),
        created_at=now,
    )


def precision(now, h):
    return InstrumentPrecisionContractV0.bind(
        schema_version="0.1.0",
        contract_id="precision-hl-eth-001",
        contract_version="precision.0.1",
        venue="hyperliquid",
        symbol="ETH",
        price_tick=Decimal("0.1"),
        quantity_step=Decimal("0.01"),
        source_metadata_version="hl-meta.0.1",
        source_snapshot_hash=h,
        created_at=now,
    )


def candidate(now, h, state=HealthStateV0.LIVE, kind=CandidateKindV0.TRADE_SETUP):
    required = contract(now)
    status = MandatoryFeedStatusV0(
        playbook_id="LQS-FR",
        required_feed_contract_id=required.contract_id,
        required_feed_contract_version=required.contract_version,
        required_feed_contract_hash=required.contract_hash,
        evaluated_at=now,
        valid_until=now + timedelta(seconds=10),
        mandatory_feed_ids=required.mandatory_feed_ids,
        feed_states={"hl-bbo": state},
    )
    payload = dict(
        schema_version="0.1.0",
        candidate_id="candidate-001",
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        feature_version="features.0.1",
        label_version="labels.0.1",
        required_feed_contract=required,
        instrument_precision=precision(now, h),
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        kind=kind,
        direction=DirectionV0.LONG,
        entry_zone_low=Decimal("3000"),
        entry_zone_high=Decimal("3010"),
        stop_price=Decimal("2980"),
        target_prices=(Decimal("3040"),),
        reason_codes=("sweep_reclaim",),
        invalidation_codes=("lose_reclaim",),
        market_snapshot_hash=h,
        account_snapshot_hash=h,
        context_snapshot_hash=h,
        mandatory_feed_status=status,
    )
    if kind is not CandidateKindV0.TRADE_SETUP:
        payload.update(
            direction=None,
            entry_zone_low=None,
            entry_zone_high=None,
            stop_price=None,
            target_prices=(),
        )
    return payload


def test_trade_candidate_requires_live_mandatory_feeds(now, h):
    with pytest.raises(ValidationError, match="mandatory feeds LIVE"):
        StrategyCandidateV0.bind(**candidate(now, h, HealthStateV0.STALE))


def test_trade_candidate_requires_complete_levels(now, h):
    data = candidate(now, h)
    data["stop_price"] = None
    with pytest.raises(ValidationError, match="requires direction"):
        StrategyCandidateV0.bind(**data)


def test_watch_candidate_can_exist_during_degraded_state(now, h):
    result = StrategyCandidateV0.bind(
        **candidate(now, h, HealthStateV0.DEGRADED, CandidateKindV0.WATCH)
    )
    assert result.kind is CandidateKindV0.WATCH


def test_candidate_hash_is_self_verified(now, h):
    result = StrategyCandidateV0.bind(**candidate(now, h))
    data = result.model_dump(mode="python")
    data["target_prices"] = (Decimal("3050"),)
    with pytest.raises(ValidationError, match="candidate_hash"):
        StrategyCandidateV0.model_validate(data)
