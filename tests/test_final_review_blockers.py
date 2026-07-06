from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, TypeAdapter, ValidationError

from scripts.export_schemas import render
from trader_assist_v0.contracts import (
    DirectionV0,
    EnvironmentV0,
    ExecutionPermitV0,
    HashBoundModel,
    HumanDecisionKindV0,
    HumanReviewDecisionV0,
    InstrumentPrecisionContractV0,
    OrderPackageV0,
    OrderTypeV0,
    PermitActionV0,
    PlaybookIdV0,
    PromotionRecordV0,
    PromotionStateV0,
    ProposalV0,
    RequiredFeedContractV0,
    validate_execution_permit_bindings,
    validate_execution_promotion_authority,
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


def order() -> OrderPackageV0:
    return OrderPackageV0.bind(
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


def proposal() -> ProposalV0:
    return ProposalV0.bind(
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
        order_package=order(),
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=2),
        invalidation_codes=("regime_change",),
    )


def decision(proposed: ProposalV0) -> HumanReviewDecisionV0:
    return HumanReviewDecisionV0.bind(
        schema_version="0.1.0",
        human_decision_id="decision-001",
        proposal_id=proposed.proposal_id,
        proposal_hash=proposed.proposal_hash,
        decision=HumanDecisionKindV0.APPROVE,
        operator_id="operator-001",
        decided_at=NOW + timedelta(seconds=10),
        approved_order_package_hash=proposed.order_package.order_package_hash,
    )


def promotion(
    previous: PromotionRecordV0 | None,
    state: PromotionStateV0,
    environment: EnvironmentV0,
    index: int,
    reviewed_at: datetime,
    activated_at: datetime | None,
) -> PromotionRecordV0:
    feeds = feed_contract()
    return PromotionRecordV0.bind(
        previous=previous,
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


def history() -> tuple[PromotionRecordV0, ...]:
    draft = promotion(
        None,
        PromotionStateV0.DRAFT,
        EnvironmentV0.READ_ONLY,
        0,
        NOW - timedelta(minutes=10),
        None,
    )
    shadow = promotion(
        draft,
        PromotionStateV0.SHADOW,
        EnvironmentV0.SHADOW,
        1,
        NOW - timedelta(minutes=9),
        NOW - timedelta(minutes=8),
    )
    review = promotion(
        shadow,
        PromotionStateV0.HUMAN_REVIEW,
        EnvironmentV0.HUMAN_REVIEW,
        2,
        NOW - timedelta(minutes=7),
        NOW - timedelta(minutes=6),
    )
    testnet = promotion(
        review,
        PromotionStateV0.TESTNET_ELIGIBLE,
        EnvironmentV0.TESTNET,
        3,
        NOW - timedelta(minutes=5),
        NOW - timedelta(minutes=4),
    )
    return (draft, shadow, review, testnet)


def permit(
    proposed: ProposalV0,
    approved: HumanReviewDecisionV0,
    promoted: PromotionRecordV0,
) -> ExecutionPermitV0:
    return ExecutionPermitV0.bind(
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


def test_authority_revalidates_basemodel_copy_bypasses() -> None:
    proposed = proposal()
    approved = decision(proposed)
    chain = history()
    valid = permit(proposed, approved, chain[-1])
    for tampered in (
        BaseModel.model_copy(valid, update={"single_use": False}),
        BaseModel.copy(valid, update={"single_use": False}),
        super(HashBoundModel, valid).model_copy(update={"single_use": False}),
    ):
        with pytest.raises((ValueError, ValidationError), match="single_use|permit_hash|literal"):
            validate_execution_permit_bindings(
                tampered,
                proposed,
                approved,
                chain[-1],
                promotion_history=chain,
            )


def test_authority_revalidates_basemodel_construct_bypass() -> None:
    proposed = proposal()
    approved = decision(proposed)
    chain = history()
    valid = permit(proposed, approved, chain[-1])
    data = valid.model_dump(mode="python")
    data["single_use"] = False
    tampered = BaseModel.model_construct.__func__(ExecutionPermitV0, **data)
    with pytest.raises((ValueError, ValidationError), match="single_use|permit_hash|literal"):
        validate_execution_permit_bindings(
            tampered,
            proposed,
            approved,
            chain[-1],
            promotion_history=chain,
        )


def test_type_adapter_and_json_round_trip_revalidate_hash() -> None:
    package = order()
    payload = package.model_dump(mode="python")
    payload["quantity"] = Decimal("1.26")
    with pytest.raises(ValidationError, match="order_package_hash"):
        TypeAdapter(OrderPackageV0).validate_python(payload)
    stale = BaseModel.model_copy(package, update={"quantity": Decimal("1.26")})
    with pytest.raises(ValidationError, match="order_package_hash"):
        OrderPackageV0.model_validate_json(stale.model_dump_json())


def test_raw_promotion_record_cannot_claim_execution_authority() -> None:
    terminal = history()[-1]
    data = terminal.model_dump(mode="python")
    data.update(
        promotion_record_id="promotion-invented",
        predecessor_record_id="invented-predecessor",
        predecessor_record_hash="b" * 64,
    )
    data.pop("promotion_record_hash")
    forged = HashBoundModel.bind.__func__(PromotionRecordV0, **data)
    direct = PromotionRecordV0.model_validate(forged.model_dump(mode="python"))
    assert direct == forged
    assert direct.execution_enabled_at(NOW) is False
    with pytest.raises(ValueError, match="initial promotion record must be DRAFT"):
        validate_execution_promotion_authority((direct,), at=NOW)


def test_valid_chain_derives_execution_authority() -> None:
    chain = history()
    assert validate_execution_promotion_authority(chain, at=NOW) == chain[-1]


@pytest.mark.parametrize(
    ("field", "valid", "invalid"),
    [
        ("quantity", ("0.1", "+1", ".1", "1."), ("0", "-1", "-0.1", "+", "-", ".")),
        ("max_slippage_bps", ("0", "0.0", "+1", ".1"), ("-1", "-0.1", "+", "-", ".")),
    ],
)
def test_decimal_schema_matches_sign_and_zero_semantics(
    field: str,
    valid: tuple[str, ...],
    invalid: tuple[str, ...],
) -> None:
    schema = json.loads(render(OrderPackageV0))
    validator = Draft202012Validator(
        {"type": "string", "pattern": schema["properties"][field]["pattern"]}
    )
    for value in valid:
        assert validator.is_valid(value), value
    for value in invalid:
        assert not validator.is_valid(value), value


def test_decimal_json_wire_is_string_only() -> None:
    schema = json.loads(render(OrderPackageV0))
    assert schema["properties"]["quantity"]["type"] == "string"
    assert schema["properties"]["max_slippage_bps"]["type"] == "string"
    assert '"quantity":"1.25"' in order().model_dump_json()
