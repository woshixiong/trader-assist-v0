from datetime import timedelta

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import (
    EnvironmentV0,
    ExecutionPermitV0,
    HumanDecisionKindV0,
    HumanReviewDecisionV0,
    PermitActionV0,
)


def test_approve_requires_exact_order_package_hash(now, h):
    with pytest.raises(ValidationError, match="exact approved"):
        HumanReviewDecisionV0(
            schema_version="0.1.0",
            human_decision_id="decision-001",
            human_decision_hash=h,
            proposal_id="proposal-001",
            proposal_hash=h,
            decision=HumanDecisionKindV0.APPROVE,
            operator_id="operator-001",
            decided_at=now,
        )


def test_modify_requires_new_proposal(now, h):
    with pytest.raises(ValidationError, match="new proposal"):
        HumanReviewDecisionV0(
            schema_version="0.1.0",
            human_decision_id="decision-002",
            human_decision_hash=h,
            proposal_id="proposal-001",
            proposal_hash=h,
            decision=HumanDecisionKindV0.MODIFY,
            operator_id="operator-001",
            decided_at=now,
        )


def permit(now, h, environment):
    return dict(
        schema_version="0.1.0",
        permit_id="permit-001",
        permit_hash=h,
        environment=environment,
        human_decision_id="decision-001",
        human_decision_hash=h,
        proposal_id="proposal-001",
        proposal_hash=h,
        order_package_id="order-package-001",
        order_package_hash=h,
        account_snapshot_hash=h,
        promotion_record_id="promotion-001",
        promotion_record_hash=h,
        issued_at=now,
        expires_at=now + timedelta(minutes=2),
        permitted_actions=frozenset({PermitActionV0.SUBMIT_ENTRY}),
    )


def test_permit_rejects_non_execution_environment(now, h):
    with pytest.raises(ValidationError, match="TESTNET or MAINNET_PILOT"):
        ExecutionPermitV0(**permit(now, h, EnvironmentV0.SHADOW))


def test_mainnet_permit_requires_two_explicit_gates(now, h):
    with pytest.raises(ValidationError, match="pre-pilot review"):
        ExecutionPermitV0(**permit(now, h, EnvironmentV0.MAINNET_PILOT))


def test_testnet_permit_contract_is_single_use(now, h):
    result = ExecutionPermitV0(**permit(now, h, EnvironmentV0.TESTNET))
    assert result.single_use is True
