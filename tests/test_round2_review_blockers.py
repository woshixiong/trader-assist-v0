from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import (
    CandidateKindV0,
    DirectionV0,
    EnvironmentV0,
    ExecutionPermitV0,
    HealthStateV0,
    HumanDecisionKindV0,
    HumanReviewDecisionV0,
    InstrumentPrecisionContractV0,
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
    validate_promotion_chain,
)

NOW = datetime(2026, 7, 6, tzinfo=UTC)
H = "a" * 64


def precision() -> InstrumentPrecisionContractV0:
    return InstrumentPrecisionContractV0.bind(
        schema_version="0.1.0",
        contract_id="precision-hl-eth-001",
        contract_version="precision.0.1",
        venue="hyperliquid",
        symbol="ETH",
        price_tick=Decimal("0.1"),
        quantity_step=Decimal("0.01"),
        source_metadata_version="hl-meta.0.1",
        source_snapshot_hash=H,
        created_at=NOW - timedelta(hours=1),
    )


def feed_contract() -> RequiredFeedContractV0:
    return RequiredFeedContractV0.bind(
        schema_version="0.1.0",
        contract_id="feeds-lqs-fr-001",
        playbook_id="LQS-FR",
        contract_version="feeds.0.1",
        mandatory_feed_ids=frozenset({"hl-bbo", "hl-trades"}),
        created_at=NOW - timedelta(hours=1),
    )


def candidate(**updates) -> StrategyCandidateV0:
    feeds = feed_contract()
    status = MandatoryFeedStatusV0(
        playbook_id=feeds.playbook_id,
        required_feed_contract_id=feeds.contract_id,
        required_feed_contract_version=feeds.contract_version,
        required_feed_contract_hash=feeds.contract_hash,
        evaluated_at=NOW,
        valid_until=NOW + timedelta(seconds=30),
        mandatory_feed_ids=feeds.mandatory_feed_ids,
        feed_states={feed: HealthStateV0.LIVE for feed in feeds.mandatory_feed_ids},
    )
    payload = dict(
        schema_version="0.1.0",
        candidate_id="candidate-001",
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        feature_version="features.0.1",
        label_version="labels.0.1",
        required_feed_contract=feeds,
        instrument_precision=precision(),
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        kind=CandidateKindV0.TRADE_SETUP,
        direction=DirectionV0.LONG,
        entry_zone_low=Decimal("3000.1"),
        entry_zone_high=Decimal("3010.1"),
        stop_price=Decimal("2980.1"),
        target_prices=(Decimal("3040.1"),),
        market_snapshot_hash=H,
        account_snapshot_hash=H,
        context_snapshot_hash=H,
        mandatory_feed_status=status,
    )
    payload.update(updates)
    return StrategyCandidateV0.bind(**payload)


def order(**updates) -> OrderPackageV0:
    payload = dict(
        schema_version="0.1.0",
        order_package_id="order-package-001",
        instrument_precision=precision(),
        direction=DirectionV0.LONG,
        order_type=OrderTypeV0.LIMIT,
        quantity=Decimal("1.25"),
        limit_price=Decimal("3000.5"),
        reduce_only=False,
        time_in_force="GTC",
        max_slippage_bps=Decimal("2.5"),
        valid_until=NOW + timedelta(minutes=2),
        stop_policy_hash=H,
        take_profit_policy_hash=H,
        cancellation_policy_hash=H,
        emergency_reduce_only_policy_hash=H,
    )
    payload.update(updates)
    return OrderPackageV0.bind(**payload)


def proposal(package: OrderPackageV0 | None = None, **updates) -> ProposalV0:
    payload = dict(
        schema_version="0.1.0",
        proposal_id="proposal-001",
        candidate_id="candidate-001",
        candidate_hash=H,
        recommendation_id="recommendation-001",
        recommendation_hash=H,
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        risk_policy_version="risk.0.1",
        market_snapshot_hash=H,
        account_snapshot_hash=H,
        context_snapshot_hash=H,
        order_package=package or order(),
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=2),
        invalidation_codes=("regime_change",),
    )
    payload.update(updates)
    return ProposalV0.bind(**payload)


def decision(proposed: ProposalV0, *, decided_at=None) -> HumanReviewDecisionV0:
    return HumanReviewDecisionV0.bind(
        schema_version="0.1.0",
        human_decision_id="decision-001",
        proposal_id=proposed.proposal_id,
        proposal_hash=proposed.proposal_hash,
        decision=HumanDecisionKindV0.APPROVE,
        operator_id="operator-001",
        decided_at=decided_at or NOW + timedelta(seconds=10),
        approved_order_package_hash=proposed.order_package.order_package_hash,
    )


def promotion_record(previous, state, environment, index, reviewed_at, activated_at, **updates):
    feeds = feed_contract()
    payload = dict(
        schema_version="0.1.0",
        promotion_record_id=f"promotion-{index:03d}",
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        feature_version="features.0.1",
        label_version="labels.0.1",
        required_feed_contract_id=feeds.contract_id,
        required_feed_contract_version=feeds.contract_version,
        required_feed_contract_hash=feeds.contract_hash,
        state=state,
        environment=environment,
        evidence_dataset_ids=() if state is PromotionStateV0.DRAFT else (f"dataset-{index:03d}",),
        reviewed_by="reviewer-001",
        reviewed_at=reviewed_at,
        activated_at=activated_at,
        rationale=f"transition to {state.value}",
    )
    payload.update(updates)
    return PromotionRecordV0.bind(previous=previous, **payload)


def _testnet_history(*, terminal_expires_at=None, terminal_revoked_at=None):
    draft = promotion_record(
        None,
        PromotionStateV0.DRAFT,
        EnvironmentV0.READ_ONLY,
        0,
        NOW - timedelta(minutes=10),
        None,
    )
    shadow = promotion_record(
        draft,
        PromotionStateV0.SHADOW,
        EnvironmentV0.SHADOW,
        1,
        NOW - timedelta(minutes=9),
        NOW - timedelta(minutes=8),
    )
    review = promotion_record(
        shadow,
        PromotionStateV0.HUMAN_REVIEW,
        EnvironmentV0.HUMAN_REVIEW,
        2,
        NOW - timedelta(minutes=7),
        NOW - timedelta(minutes=6),
    )
    testnet = promotion_record(
        review,
        PromotionStateV0.TESTNET_ELIGIBLE,
        EnvironmentV0.TESTNET,
        3,
        NOW - timedelta(minutes=5),
        NOW - timedelta(minutes=4),
        expires_at=terminal_expires_at,
        revoked_at=terminal_revoked_at,
    )
    return (draft, shadow, review, testnet)


def permit(proposed, approved, promoted, **updates):
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
        issued_at=NOW + timedelta(seconds=20),
        expires_at=NOW + timedelta(seconds=60),
        permitted_actions=frozenset({PermitActionV0.SUBMIT_ENTRY}),
    )
    payload.update(updates)
    return ExecutionPermitV0.bind(**payload)


def test_external_validation_context_cannot_bypass_hash_verification():
    package = order()
    data = package.model_dump(mode="python")
    data["quantity"] = Decimal("1.26")
    with pytest.raises(ValidationError, match="order_package_hash"):
        OrderPackageV0.model_validate(
            data,
            context={"skip_hash_domain": package.hash_domain.value},
        )


def test_bind_still_produces_self_verifying_hash():
    package = order()
    assert OrderPackageV0.model_validate(package.model_dump(mode="python")) == package


def test_hash_bound_model_copy_rejects_updates():
    package = order()
    with pytest.raises(TypeError, match="cannot be copied with updates"):
        package.model_copy(update={"quantity": Decimal("1.26")})
    assert package.model_copy() == package


def test_hash_bound_legacy_copy_rejects_field_changes():
    package = order()
    with pytest.raises(TypeError, match="cannot be copied with field changes"):
        package.copy(update={"quantity": Decimal("1.26")})
    assert package.copy() == package


def test_hash_bound_model_construct_is_disabled():
    package = order()
    data = package.model_dump(mode="python")
    data["quantity"] = Decimal("1.26")
    with pytest.raises(TypeError, match="cannot bypass validation"):
        OrderPackageV0.model_construct(**data)


@pytest.mark.parametrize(
    ("factory", "updates"),
    [
        (candidate, {"entry_zone_low": Decimal("3000.05")}),
        (candidate, {"target_prices": (Decimal("3040.05"),)}),
        (order, {"quantity": Decimal("1.255")}),
        (order, {"limit_price": Decimal("3000.55")}),
    ],
)
def test_non_aligned_values_are_rejected(factory, updates):
    with pytest.raises(ValidationError, match="precision step"):
        factory(**updates)


def test_aligned_values_and_decimal_equivalents_are_deterministic():
    first = order(quantity=Decimal("1.250"), limit_price=Decimal("3000.500"))
    second = order(quantity=Decimal("1.25"), limit_price=Decimal("3000.5"))
    assert first.order_package_hash == second.order_package_hash


def test_direct_promotion_jump_is_rejected():
    draft = _testnet_history()[0]
    with pytest.raises(ValueError, match="does not permit"):
        promotion_record(
            draft,
            PromotionStateV0.MAINNET_PILOT_ACTIVE,
            EnvironmentV0.MAINNET_PILOT,
            99,
            NOW - timedelta(minutes=9),
            NOW - timedelta(minutes=8),
        )


def test_complete_promotion_chain_passes():
    validate_promotion_chain(_testnet_history())


def test_execution_requires_exact_terminal_complete_promotion_chain():
    proposed = proposal()
    approved = decision(proposed)
    history = _testnet_history()
    execution_permit = permit(proposed, approved, history[-1])
    with pytest.raises(ValueError, match="invalid promotion chain|terminal"):
        validate_execution_permit_bindings(
            execution_permit,
            proposed,
            approved,
            history[-1],
            promotion_history=(history[-1],),
        )


def test_valid_temporal_authority_passes():
    proposed = proposal()
    approved = decision(proposed)
    history = _testnet_history(terminal_expires_at=NOW + timedelta(seconds=90))
    execution_permit = permit(proposed, approved, history[-1])
    validate_execution_permit_bindings(
        execution_permit,
        proposed,
        approved,
        history[-1],
        promotion_history=history,
    )


def test_decision_at_proposal_expiry_is_rejected():
    proposed = proposal()
    approved = decision(proposed, decided_at=proposed.expires_at)
    history = _testnet_history()
    execution_permit = permit(
        proposed,
        approved,
        history[-1],
        issued_at=proposed.expires_at + timedelta(seconds=1),
        expires_at=proposed.expires_at + timedelta(seconds=2),
    )
    with pytest.raises(ValueError, match="decision is outside|issued at or after"):
        validate_execution_permit_bindings(
            execution_permit,
            proposed,
            approved,
            history[-1],
            promotion_history=history,
        )


def test_permit_issued_at_order_expiry_is_rejected():
    package = order(valid_until=NOW + timedelta(seconds=40))
    proposed = proposal(package=package)
    approved = decision(proposed)
    history = _testnet_history()
    execution_permit = permit(
        proposed,
        approved,
        history[-1],
        issued_at=package.valid_until,
        expires_at=package.valid_until + timedelta(seconds=1),
    )
    with pytest.raises(ValueError, match="issued at or after"):
        validate_execution_permit_bindings(
            execution_permit,
            proposed,
            approved,
            history[-1],
            promotion_history=history,
        )


@pytest.mark.parametrize("boundary", ["proposal", "order", "promotion_expiry", "revocation"])
def test_permit_expiry_cannot_exceed_any_authority_boundary(boundary):
    order_deadline = NOW + timedelta(seconds=80)
    proposal_deadline = NOW + timedelta(seconds=100)
    promotion_expiry = NOW + timedelta(seconds=90)
    revocation = NOW + timedelta(seconds=70)
    package = order(valid_until=order_deadline)
    proposed = proposal(package=package, expires_at=proposal_deadline)
    approved = decision(proposed)
    history = _testnet_history(
        terminal_expires_at=promotion_expiry if boundary == "promotion_expiry" else None,
        terminal_revoked_at=revocation if boundary == "revocation" else None,
    )
    endpoints = {
        "proposal": proposal_deadline,
        "order": order_deadline,
        "promotion_expiry": promotion_expiry,
        "revocation": revocation,
    }
    execution_permit = permit(
        proposed,
        approved,
        history[-1],
        expires_at=endpoints[boundary] + timedelta(seconds=1),
    )
    with pytest.raises(ValueError, match="earliest authority boundary"):
        validate_execution_permit_bindings(
            execution_permit,
            proposed,
            approved,
            history[-1],
            promotion_history=history,
        )
