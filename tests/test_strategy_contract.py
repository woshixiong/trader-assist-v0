from datetime import timedelta

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import CandidateKindV0, DirectionV0, HealthStateV0, MandatoryFeedStatusV0, PlaybookIdV0, StrategyCandidateV0


def candidate(now, h, state=HealthStateV0.LIVE):
    return dict(schema_version="0.1.0", candidate_id="candidate-001", candidate_hash=h, playbook_id=PlaybookIdV0.LQS_FR, strategy_version="lqs-fr.0.1", parameter_version="params.0.1", feature_version="features.0.1", label_version="labels.0.1", required_feed_contract_version="feeds.0.1", created_at=now, expires_at=now + timedelta(minutes=5), kind=CandidateKindV0.TRADE_SETUP, direction=DirectionV0.LONG, entry_zone_low=3000, entry_zone_high=3010, stop_price=2980, target_prices=(3040,), reason_codes=("sweep_reclaim",), invalidation_codes=("lose_reclaim",), market_snapshot_hash=h, account_snapshot_hash=h, context_snapshot_hash=h, mandatory_feed_status=MandatoryFeedStatusV0(playbook_id="LQS-FR", required_feed_contract_version="feeds.0.1", evaluated_at=now, valid_until=now + timedelta(seconds=10), mandatory_feed_ids=frozenset({"hl-bbo"}), feed_states={"hl-bbo": state}))


def test_trade_candidate_requires_live_mandatory_feeds(now, h):
    with pytest.raises(ValidationError, match="mandatory feeds LIVE"):
        StrategyCandidateV0(**candidate(now, h, HealthStateV0.STALE))


def test_trade_candidate_requires_complete_levels(now, h):
    data = candidate(now, h)
    data["stop_price"] = None
    with pytest.raises(ValidationError, match="requires direction"):
        StrategyCandidateV0(**data)


def test_watch_candidate_can_exist_during_degraded_state(now, h):
    data = candidate(now, h, HealthStateV0.DEGRADED)
    data.update(kind=CandidateKindV0.WATCH, direction=None, entry_zone_low=None, entry_zone_high=None, stop_price=None, target_prices=())
    result = StrategyCandidateV0(**data)
    assert result.kind is CandidateKindV0.WATCH
