from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import CandidateKindV0, DirectionV0, EnvironmentV0, EvidenceBundleManifestV0, EvidenceFileV0, ExecutionPermitV0, HashDomainV0, HealthStateV0, MandatoryFeedStatusV0, OrderPackageV0, OrderTypeV0, PermitActionV0, PlaybookIdV0, PromotionRecordV0, PromotionStateV0, StrategyCandidateV0, contract_hash


def feed_status(now, playbook="LQS-FR", contract="feeds.0.1", state=HealthStateV0.LIVE):
    return MandatoryFeedStatusV0(playbook_id=playbook, required_feed_contract_version=contract, evaluated_at=now, valid_until=now + timedelta(seconds=30), mandatory_feed_ids=frozenset({"hl-bbo", "hl-trades"}), feed_states={"hl-bbo": state, "hl-trades": HealthStateV0.LIVE})


def candidate(now, h, **kwargs):
    data = dict(schema_version="0.1.0", candidate_id="candidate-001", candidate_hash=h, playbook_id=PlaybookIdV0.LQS_FR, strategy_version="lqs-fr.0.1", parameter_version="params.0.1", feature_version="features.0.1", label_version="labels.0.1", required_feed_contract_version="feeds.0.1", created_at=now, expires_at=now + timedelta(minutes=5), kind=CandidateKindV0.TRADE_SETUP, direction=DirectionV0.LONG, entry_zone_low=Decimal("3000.1"), entry_zone_high=Decimal("3010.1"), stop_price=Decimal("2980.1"), target_prices=(Decimal("3040.1"),), market_snapshot_hash=h, account_snapshot_hash=h, context_snapshot_hash=h, mandatory_feed_status=feed_status(now))
    data.update(kwargs)
    return data


def promotion(now, h, **kwargs):
    data = dict(schema_version="0.1.0", promotion_record_id="promotion-001", promotion_record_hash=h, playbook_id=PlaybookIdV0.LQS_FR, strategy_version="lqs-fr.0.1", parameter_version="params.0.1", feature_version="features.0.1", label_version="labels.0.1", required_feed_contract_version="feeds.0.1", state=PromotionStateV0.TESTNET_ELIGIBLE, environment=EnvironmentV0.TESTNET, evidence_dataset_ids=("dataset-001",), reviewed_by="reviewer-001", reviewed_at=now, activated_at=now, rationale="enough evidence for testnet")
    data.update(kwargs)
    return data


def permit(now, h, **kwargs):
    data = dict(schema_version="0.1.0", permit_id="permit-001", permit_hash=h, environment=EnvironmentV0.TESTNET, playbook_id=PlaybookIdV0.LQS_FR, strategy_version="lqs-fr.0.1", parameter_version="params.0.1", risk_policy_version="risk.0.1", operator_id="operator-001", approved_at=now, human_decision_id="decision-001", human_decision_hash=h, proposal_id="proposal-001", proposal_hash=h, order_package_id="order-package-001", order_package_hash=h, account_snapshot_hash=h, promotion_record_id="promotion-001", promotion_record_hash=h, issued_at=now + timedelta(seconds=1), expires_at=now + timedelta(minutes=2), permitted_actions=frozenset({PermitActionV0.SUBMIT_ENTRY}))
    data.update(kwargs)
    return data


def test_candidate_rejects_cross_playbook_feed_status(now, h):
    with pytest.raises(ValidationError, match="playbook"):
        StrategyCandidateV0(**candidate(now, h, mandatory_feed_status=feed_status(now, playbook="BRK-AR")))


def test_candidate_rejects_missing_required_feed_coverage(now):
    with pytest.raises(ValidationError, match="exactly cover"):
        MandatoryFeedStatusV0(playbook_id="LQS-FR", required_feed_contract_version="feeds.0.1", evaluated_at=now, valid_until=now, mandatory_feed_ids=frozenset({"hl-bbo", "hl-trades"}), feed_states={"hl-bbo": HealthStateV0.LIVE})


def test_candidate_rejects_stale_feed_status_time(now, h):
    stale_status = MandatoryFeedStatusV0(playbook_id="LQS-FR", required_feed_contract_version="feeds.0.1", evaluated_at=now - timedelta(minutes=2), valid_until=now - timedelta(minutes=1), mandatory_feed_ids=frozenset({"hl-bbo"}), feed_states={"hl-bbo": HealthStateV0.LIVE})
    with pytest.raises(ValidationError, match="LIVE"):
        StrategyCandidateV0(**candidate(now, h, mandatory_feed_status=stale_status))


def test_promotion_rejects_shadow_in_mainnet(now, h):
    with pytest.raises(ValidationError, match="environment"):
        PromotionRecordV0(**promotion(now, h, state=PromotionStateV0.SHADOW, environment=EnvironmentV0.MAINNET_PILOT))


def test_promotion_requires_evidence_and_activation(now, h):
    with pytest.raises(ValidationError, match="evidence"):
        PromotionRecordV0(**promotion(now, h, evidence_dataset_ids=()))
    with pytest.raises(ValidationError, match="activated_at"):
        PromotionRecordV0(**promotion(now, h, activated_at=None))


def test_git_commit_oid_accepts_current_sha1(now, h):
    file = EvidenceFileV0(relative_path="gold/events.parquet", sha256=h, size_bytes=1)
    bundle = EvidenceBundleManifestV0(bundle_schema_version="0.1.0", dataset_id="dataset-001", environment=EnvironmentV0.SHADOW, account_alias="account-redacted", instrument="ETH", start_time=now, end_time=now + timedelta(hours=1), source_versions={"hl": "v1"}, collector_versions={"hl": "v1"}, normalizer_version="v1", strategy_versions={"LQS-FR": "v1"}, parameter_versions={"LQS-FR": "v1"}, risk_policy_version="v1", model_versions={"explain": "none"}, prompt_versions={"explain": "none"}, code_commit_oid="46f53dba95b0f5e83d73f406d752754bad939539", quality_status="PASS", known_gaps=(), files=(file,), created_at=now)
    assert bundle.code_commit_oid.startswith("46f53d")


def test_order_rejects_non_finite_or_negative_numbers(now, h):
    with pytest.raises(ValidationError):
        OrderPackageV0(schema_version="0.1.0", order_package_id="order-package-001", order_package_hash=h, direction=DirectionV0.LONG, order_type=OrderTypeV0.LIMIT, quantity=Decimal("NaN"), limit_price=Decimal("3000"), reduce_only=False, time_in_force="GTC", max_slippage_bps=Decimal("0"), valid_until=now, stop_policy_hash=h, take_profit_policy_hash=h, cancellation_policy_hash=h, emergency_reduce_only_policy_hash=h)
    with pytest.raises(ValidationError):
        StrategyCandidateV0(**candidate(now, h, target_prices=(Decimal("-1"),)))


def test_contract_hash_excludes_hash_field_and_detects_mutation(now, h):
    order = OrderPackageV0(schema_version="0.1.0", order_package_id="order-package-001", order_package_hash=h, direction=DirectionV0.LONG, order_type=OrderTypeV0.LIMIT, quantity=Decimal("1.25"), limit_price=Decimal("3000.5"), reduce_only=False, time_in_force="GTC", max_slippage_bps=Decimal("2.5"), valid_until=now, stop_policy_hash=h, take_profit_policy_hash=h, cancellation_policy_hash=h, emergency_reduce_only_policy_hash=h)
    different_hash_field = order.model_copy(update={"order_package_hash": "b" * 64})
    mutated_quantity = order.model_copy(update={"quantity": Decimal("1.26")})
    assert contract_hash(HashDomainV0.ORDER_PACKAGE, order) == contract_hash(HashDomainV0.ORDER_PACKAGE, different_hash_field)
    assert contract_hash(HashDomainV0.ORDER_PACKAGE, order) != contract_hash(HashDomainV0.ORDER_PACKAGE, mutated_quantity)


def test_permit_requires_full_subject_binding(now, h):
    result = ExecutionPermitV0(**permit(now, h))
    assert result.playbook_id is PlaybookIdV0.LQS_FR
    assert result.strategy_version == "lqs-fr.0.1"
    assert result.parameter_version == "params.0.1"
    assert result.risk_policy_version == "risk.0.1"
    assert result.operator_id == "operator-001"
    assert result.approved_at == now
