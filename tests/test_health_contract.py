from datetime import timedelta

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import DataHealthEventV0, HealthStateV0, MandatoryFeedStatusV0


def test_disconnect_must_reconnect_before_snapshot(now):
    with pytest.raises(ValidationError, match="illegal health transition"):
        DataHealthEventV0(health_event_id="health-001", feed_id="hl-bbo", policy_version="v0.1", previous_state=HealthStateV0.DISCONNECTED, state=HealthStateV0.LIVE, observed_at=now, reason_codes=())


def test_reconnect_snapshot_reconcile_live_path(now):
    path = [(HealthStateV0.DISCONNECTED, HealthStateV0.RECONNECTING), (HealthStateV0.RECONNECTING, HealthStateV0.SNAPSHOT_SYNC), (HealthStateV0.SNAPSHOT_SYNC, HealthStateV0.LIVE)]
    for index, (previous, current) in enumerate(path):
        event = DataHealthEventV0(health_event_id=f"health-{index}", feed_id="hl-bbo", policy_version="v0.1", previous_state=previous, state=current, observed_at=now + timedelta(seconds=index), reason_codes=() if current is HealthStateV0.LIVE else ("recovery",))
        assert event.state is current


def test_non_live_requires_reason(now):
    with pytest.raises(ValidationError, match="reason_codes"):
        DataHealthEventV0(health_event_id="health-002", feed_id="hl-bbo", policy_version="v0.1", previous_state=HealthStateV0.LIVE, state=HealthStateV0.STALE, observed_at=now)


def test_mandatory_feed_status_all_live(now):
    live = MandatoryFeedStatusV0(playbook_id="LQS-FR", required_feed_contract_version="feeds.0.1", evaluated_at=now, valid_until=now, mandatory_feed_ids=frozenset({"hl-bbo"}), feed_states={"hl-bbo": HealthStateV0.LIVE})
    stale = MandatoryFeedStatusV0(playbook_id="LQS-FR", required_feed_contract_version="feeds.0.1", evaluated_at=now, valid_until=now, mandatory_feed_ids=frozenset({"hl-bbo"}), feed_states={"hl-bbo": HealthStateV0.STALE})
    assert live.all_live is True
    assert stale.all_live is False
