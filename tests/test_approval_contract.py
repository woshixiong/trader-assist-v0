from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import (
    EnvironmentV0,
    ExecutionPermitV0,
    HumanDecisionKindV0,
    HumanReviewDecisionV0,
    OrderPackageV0,
    OrderTypeV0,
    PermitActionV0,
    PlaybookIdV0,
)


def order(now, h):
    return OrderPackageV0.bind(
        schema_version="0.1.0",
        order_package_id="order-package-001",
        direction="LONG",
        order_type=OrderTypeV0.LIMIT,
        quantity=Decimal("1.25"),
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


def test_approve_requires_exact_order_package_hash(now, h):
    with pytest.raises(ValidationError, match="exact approved"):
        HumanReviewDecisionV0.bind(
            schema_version="0.1.0",
            human_decision_id="decision-001",
            proposal_id="proposal-001",
            proposal_hash=h,
            decision=HumanDecisionKindV0.APPROVE,
            operator_id="operator-001",
            decided_at=now,
        )


def test_modify_requires_new_proposal(now, h):
    with pytest.raises(ValidationError, match="new proposal"):
        HumanReviewDecisionV0.bind(
            schema_version="0.1.0",
            human_decision_id="decision-002",
            proposal_id="proposal-001",
            proposal_hash=h,
            decision=HumanDecisionKindV0.MODIFY,
            operator_id="operator-001",
            decided_at=now,
        )


def permit_payload(now, h, environment):
    return dict(
        schema_version="0.1.0",
        permit_id="permit-001",
        environment=environment,
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        risk_policy_version="risk.0.1",
        operator_id="operator-001",
        approved_at=now,
        human_decision_id="decision-001",
        human_decision_hash=h,
        proposal_id="proposal-001",
        proposal_hash=h,
        order_package_id=order(now, h).order_package_id,
        order_package_hash=order(now, h).order_package_hash,
        account_snapshot_hash=h,
        promotion_record_id="promotion-001",
        promotion_record_hash=h,
        issued_at=now + timedelta(seconds=1),
        expires_at=now + timedelta(minutes=2),
        permitted_actions=frozenset({PermitActionV0.SUBMIT_ENTRY}),
    )


def test_permit_rejects_non_execution_environment(now, h):
    with pytest.raises(ValidationError, match="TESTNET or MAINNET_PILOT"):
        ExecutionPermitV0.bind(**permit_payload(now, h, EnvironmentV0.SHADOW))


def test_mainnet_permit_requires_two_explicit_gates(now, h):
    with pytest.raises(ValidationError, match="pre-pilot review"):
        ExecutionPermitV0.bind(**permit_payload(now, h, EnvironmentV0.MAINNET_PILOT))


def test_testnet_permit_contract_is_single_use(now, h):
    result = ExecutionPermitV0.bind(**permit_payload(now, h, EnvironmentV0.TESTNET))
    assert result.single_use is True
