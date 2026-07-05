from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import (
    CandidateKindV0,
    DirectionV0,
    EnvironmentV0,
    EvidenceBundleManifestV0,
    EvidenceFileV0,
    ExecutionPermitV0,
    HealthStateV0,
    HumanDecisionKindV0,
    HumanReviewDecisionV0,
    MandatoryFeedStatusV0,
    OrderPackageV0,
    OrderTypeV0,
    PermitActionV0,
    PlaybookIdV0,
    PromotionRecordV0,
    PromotionStateV0,
    ProposalV0,
    RequiredFeedContractV0,
    StrategyCandidateV0,
    validate_execution_permit_bindings,
)


def feed_contract(now, feeds=frozenset({"hl-bbo", "hl-trades"})):
    return RequiredFeedContractV0.bind(
        schema_version="0.1.0",
        contract_id="feeds-lqs-fr-001",
        playbook_id="LQS-FR",
        contract_version="feeds.0.1",
        mandatory_feed_ids=feeds,
        created_at=now,
    )


def feed_status(now, contract, *, state=HealthStateV0.LIVE, feeds=None):
    ids = contract.mandatory_feed_ids if feeds is None else frozenset(feeds)
    return MandatoryFeedStatusV0(
        playbook_id=contract.playbook_id,
        required_feed_contract_id=contract.contract_id,
        required_feed_contract_version=contract.contract_version,
        required_feed_contract_hash=contract.contract_hash,
        evaluated_at=now,
        valid_until=now + timedelta(seconds=30),
        mandatory_feed_ids=ids,
        feed_states={feed_id: state for feed_id in ids},
    )


def candidate_payload(now, h, contract, status):
    return dict(
        schema_version="0.1.0",
        candidate_id="candidate-001",
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        feature_version="features.0.1",
        label_version="labels.0.1",
        required_feed_contract=contract,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        kind=CandidateKindV0.TRADE_SETUP,
        direction=DirectionV0.LONG,
        entry_zone_low=Decimal("3000.1"),
        entry_zone_high=Decimal("3010.1"),
        stop_price=Decimal("2980.1"),
        target_prices=(Decimal("3040.1"),),
        market_snapshot_hash=h,
        account_snapshot_hash=h,
        context_snapshot_hash=h,
        mandatory_feed_status=status,
    )


def order(now, h, quantity=Decimal("1.25")):
    return OrderPackageV0.bind(
        schema_version="0.1.0",
        order_package_id="order-package-001",
        direction=DirectionV0.LONG,
        order_type=OrderTypeV0.LIMIT,
        quantity=quantity,
        limit_price=Decimal("3000.5"),
        reduce_only=False,
        time_in_force="GTC",
        max_slippage_bps=Decimal("2.5"),
        valid_until=now + timedelta(minutes=2),
        stop_policy_hash=h,
        take_profit_policy_hash=h,
        cancellation_policy_hash=h,
        emergency_reduce_only_policy_hash=h,
    )


def proposal(now, h, package):
    return ProposalV0.bind(
        schema_version="0.1.0",
        proposal_id="proposal-001",
        candidate_id="candidate-001",
        candidate_hash=h,
        recommendation_id="recommendation-001",
        recommendation_hash=h,
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        risk_policy_version="risk.0.1",
        market_snapshot_hash=h,
        account_snapshot_hash=h,
        context_snapshot_hash=h,
        order_package=package,
        created_at=now,
        expires_at=now + timedelta(minutes=2),
        invalidation_codes=("regime_change",),
    )


def decision(now, proposed):
    return HumanReviewDecisionV0.bind(
        schema_version="0.1.0",
        human_decision_id="decision-001",
        proposal_id=proposed.proposal_id,
        proposal_hash=proposed.proposal_hash,
        decision=HumanDecisionKindV0.APPROVE,
        operator_id="operator-001",
        decided_at=now,
        approved_order_package_hash=proposed.order_package.order_package_hash,
    )


def promotion(now, h, contract, *, state=PromotionStateV0.TESTNET_ELIGIBLE):
    environment = (
        EnvironmentV0.TESTNET
        if state is PromotionStateV0.TESTNET_ELIGIBLE
        else EnvironmentV0.MAINNET_PILOT
    )
    return PromotionRecordV0.bind(
        schema_version="0.1.0",
        promotion_record_id="promotion-001",
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        feature_version="features.0.1",
        label_version="labels.0.1",
        required_feed_contract_id=contract.contract_id,
        required_feed_contract_version=contract.contract_version,
        required_feed_contract_hash=contract.contract_hash,
        state=state,
        environment=environment,
        evidence_dataset_ids=("dataset-001",),
        reviewed_by="reviewer-001",
        reviewed_at=now,
        activated_at=now,
        rationale="reviewed evidence supports this bounded state",
    )


def permit(now, proposed, approved, promoted, **updates):
    payload = dict(
        schema_version="0.1.0",
        permit_id="permit-001",
        environment=promoted.environment,
        playbook_id=proposed.playbook_id,
        strategy_version=proposed.strategy_version,
        parameter_version=proposed.parameter_version,
        risk_policy_version=proposed.risk_policy_version,
        operator_id=approved.operator_id,
        approved_at=approved.decided_at,
        human_decision_id=approved.human_decision_id,
        human_decision_hash=approved.human_decision_hash,
        proposal_id=proposed.proposal_id,
        proposal_hash=proposed.proposal_hash,
        order_package_id=proposed.order_package.order_package_id,
        order_package_hash=proposed.order_package.order_package_hash,
        account_snapshot_hash=proposed.account_snapshot_hash,
        promotion_record_id=promoted.promotion_record_id,
        promotion_record_hash=promoted.promotion_record_hash,
        issued_at=now + timedelta(seconds=1),
        expires_at=now + timedelta(minutes=1),
        permitted_actions=frozenset({PermitActionV0.SUBMIT_ENTRY}),
    )
    payload.update(updates)
    return ExecutionPermitV0.bind(**payload)


def test_candidate_rejects_self_declared_subset_of_required_feeds(now, h):
    contract = feed_contract(now)
    subset = feed_status(now, contract, feeds={"hl-bbo"})
    with pytest.raises(ValidationError, match="exact playbook contract"):
        StrategyCandidateV0.bind(**candidate_payload(now, h, contract, subset))


def test_required_feed_contract_hash_tampering_is_rejected(now):
    contract = feed_contract(now)
    data = contract.model_dump(mode="python")
    data["mandatory_feed_ids"] = frozenset({"fake-live-feed"})
    with pytest.raises(ValidationError, match="contract_hash"):
        RequiredFeedContractV0.model_validate(data)


def test_promotion_rejects_shadow_in_mainnet(now, h):
    contract = feed_contract(now)
    with pytest.raises(ValidationError, match="environment"):
        PromotionRecordV0.bind(
            schema_version="0.1.0",
            promotion_record_id="promotion-001",
            playbook_id=PlaybookIdV0.LQS_FR,
            strategy_version="lqs-fr.0.1",
            parameter_version="params.0.1",
            feature_version="features.0.1",
            label_version="labels.0.1",
            required_feed_contract_id=contract.contract_id,
            required_feed_contract_version=contract.contract_version,
            required_feed_contract_hash=contract.contract_hash,
            state=PromotionStateV0.SHADOW,
            environment=EnvironmentV0.MAINNET_PILOT,
            evidence_dataset_ids=("dataset-001",),
            reviewed_by="reviewer-001",
            reviewed_at=now,
            activated_at=now,
            rationale="invalid combination",
        )


def test_mainnet_eligible_is_not_execution_enabled(now, h):
    contract = feed_contract(now)
    record = promotion(now, h, contract, state=PromotionStateV0.MAINNET_PILOT_ELIGIBLE)
    assert record.active_at(now) is False
    assert record.execution_enabled_at(now) is False


def test_git_commit_oid_accepts_current_sha1(now, h):
    item = EvidenceFileV0(relative_path="gold/events.parquet", sha256=h, size_bytes=1)
    bundle = EvidenceBundleManifestV0(
        bundle_schema_version="0.1.0",
        dataset_id="dataset-001",
        environment=EnvironmentV0.SHADOW,
        account_alias="account-redacted",
        instrument="ETH",
        start_time=now,
        end_time=now + timedelta(hours=1),
        source_versions={"hl": "v1"},
        collector_versions={"hl": "v1"},
        normalizer_version="v1",
        strategy_versions={"LQS-FR": "v1"},
        parameter_versions={"LQS-FR": "v1"},
        risk_policy_version="v1",
        model_versions={"explain": "none"},
        prompt_versions={"explain": "none"},
        code_commit_oid="46f53dba95b0f5e83d73f406d752754bad939539",
        quality_status="PASS",
        known_gaps=(),
        files=(item,),
        created_at=now,
    )
    assert len(bundle.code_commit_oid) == 40


def test_hash_normalizes_decimal_and_set_order(now, h):
    first = order(now, h, Decimal("1.250"))
    second = order(now, h, Decimal("1.25"))
    assert first.order_package_hash == second.order_package_hash

    contract_a = feed_contract(now, frozenset({"hl-bbo", "hl-trades"}))
    contract_b = feed_contract(now, frozenset({"hl-trades", "hl-bbo"}))
    assert contract_a.contract_hash == contract_b.contract_hash


def test_hash_tampering_is_rejected(now, h):
    package = order(now, h)
    data = package.model_dump(mode="python")
    data["quantity"] = Decimal("1.26")
    with pytest.raises(ValidationError, match="order_package_hash"):
        OrderPackageV0.model_validate(data)


def test_order_rejects_non_finite_or_negative_numbers(now, h):
    with pytest.raises(ValidationError):
        order(now, h, Decimal("NaN"))
    contract = feed_contract(now)
    status = feed_status(now, contract)
    invalid_candidate = candidate_payload(now, h, contract, status)
    invalid_candidate["target_prices"] = (Decimal("-1"),)
    with pytest.raises(ValidationError):
        StrategyCandidateV0.bind(**invalid_candidate)


def test_permit_cross_object_bindings_pass(now, h):
    contract = feed_contract(now)
    package = order(now, h)
    proposed = proposal(now, h, package)
    approved = decision(now, proposed)
    promoted = promotion(now, h, contract)
    execution_permit = permit(now, proposed, approved, promoted)
    validate_execution_permit_bindings(execution_permit, proposed, approved, promoted)


def test_permit_cross_object_mismatch_is_rejected(now, h):
    contract = feed_contract(now)
    package = order(now, h)
    proposed = proposal(now, h, package)
    approved = decision(now, proposed)
    promoted = promotion(now, h, contract)
    execution_permit = permit(
        now,
        proposed,
        approved,
        promoted,
        risk_policy_version="risk.other",
    )
    with pytest.raises(ValueError, match="risk policy"):
        validate_execution_permit_bindings(execution_permit, proposed, approved, promoted)
