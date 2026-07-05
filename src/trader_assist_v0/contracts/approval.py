from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .common import EnvironmentV0, OpaqueId, Sha256Hex, StrictModel, UTCDateTime, VersionId
from .strategy import DirectionV0, PlaybookIdV0


class HumanDecisionKindV0(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"
    OBSERVE = "OBSERVE"


class OrderTypeV0(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    TRIGGER = "TRIGGER"


class PermitActionV0(StrEnum):
    SUBMIT_ENTRY = "SUBMIT_ENTRY"
    CANCEL_ENTRY = "CANCEL_ENTRY"
    PLACE_PROTECTION = "PLACE_PROTECTION"
    EMERGENCY_REDUCE_ONLY = "EMERGENCY_REDUCE_ONLY"


class AIRecommendationV0(StrictModel):
    schema_version: VersionId
    recommendation_id: OpaqueId
    recommendation_hash: Sha256Hex
    candidate_id: OpaqueId
    candidate_hash: Sha256Hex
    model_id: VersionId
    prompt_version: VersionId
    created_at: UTCDateTime
    supporting_evidence_ids: tuple[OpaqueId, ...]
    opposing_evidence_ids: tuple[OpaqueId, ...]
    missing_evidence: tuple[str, ...] = ()
    narrative: str = Field(min_length=1, max_length=8000)
    can_authorize: Literal[False] = False


class OrderPackageV0(StrictModel):
    schema_version: VersionId
    order_package_id: OpaqueId
    order_package_hash: Sha256Hex
    symbol: Literal["ETH"] = "ETH"
    direction: DirectionV0
    order_type: OrderTypeV0
    quantity: float = Field(gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    reduce_only: bool
    time_in_force: str = Field(min_length=1, max_length=40)
    max_slippage_bps: float = Field(ge=0)
    valid_until: UTCDateTime
    stop_policy_hash: Sha256Hex
    take_profit_policy_hash: Sha256Hex
    cancellation_policy_hash: Sha256Hex
    emergency_reduce_only_policy_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_order_type(self) -> OrderPackageV0:
        if self.order_type is OrderTypeV0.LIMIT and self.limit_price is None:
            raise ValueError("LIMIT order requires limit_price")
        return self


class ProposalV0(StrictModel):
    schema_version: VersionId
    proposal_id: OpaqueId
    proposal_hash: Sha256Hex
    candidate_id: OpaqueId
    candidate_hash: Sha256Hex
    recommendation_id: OpaqueId
    recommendation_hash: Sha256Hex
    playbook_id: PlaybookIdV0
    strategy_version: VersionId
    parameter_version: VersionId
    risk_policy_version: VersionId
    market_snapshot_hash: Sha256Hex
    account_snapshot_hash: Sha256Hex
    context_snapshot_hash: Sha256Hex
    order_package: OrderPackageV0
    created_at: UTCDateTime
    expires_at: UTCDateTime
    invalidation_codes: tuple[str, ...]

    @model_validator(mode="after")
    def validate_expiry(self) -> ProposalV0:
        if self.expires_at <= self.created_at:
            raise ValueError("proposal expiry must be after creation")
        if self.order_package.valid_until > self.expires_at:
            raise ValueError("order package cannot outlive proposal")
        return self


class HumanReviewDecisionV0(StrictModel):
    schema_version: VersionId
    human_decision_id: OpaqueId
    human_decision_hash: Sha256Hex
    proposal_id: OpaqueId
    proposal_hash: Sha256Hex
    decision: HumanDecisionKindV0
    operator_id: OpaqueId
    decided_at: UTCDateTime
    approved_order_package_hash: Sha256Hex | None = None
    superseding_proposal_id: OpaqueId | None = None
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_decision(self) -> HumanReviewDecisionV0:
        if self.decision is HumanDecisionKindV0.APPROVE:
            if self.approved_order_package_hash is None or self.superseding_proposal_id is not None:
                raise ValueError(
                    "APPROVE requires exact approved order-package hash and no superseding proposal"
                )
        elif self.decision is HumanDecisionKindV0.MODIFY:
            if self.superseding_proposal_id is None or self.approved_order_package_hash is not None:
                raise ValueError(
                    "MODIFY requires a new proposal and cannot approve the old package"
                )
        elif self.approved_order_package_hash is not None:
            raise ValueError("non-APPROVE decision cannot approve an order package")
        return self


class ExecutionPermitV0(StrictModel):
    schema_version: VersionId
    permit_id: OpaqueId
    permit_hash: Sha256Hex
    environment: EnvironmentV0
    human_decision_id: OpaqueId
    human_decision_hash: Sha256Hex
    proposal_id: OpaqueId
    proposal_hash: Sha256Hex
    order_package_id: OpaqueId
    order_package_hash: Sha256Hex
    account_snapshot_hash: Sha256Hex
    promotion_record_id: OpaqueId
    promotion_record_hash: Sha256Hex
    issued_at: UTCDateTime
    expires_at: UTCDateTime
    permitted_actions: frozenset[PermitActionV0]
    single_use: Literal[True] = True
    pre_pilot_review_id: OpaqueId | None = None
    human_mainnet_authorization_id: OpaqueId | None = None

    @model_validator(mode="after")
    def validate_permit(self) -> ExecutionPermitV0:
        if self.environment not in {EnvironmentV0.TESTNET, EnvironmentV0.MAINNET_PILOT}:
            raise ValueError("execution permit is valid only for TESTNET or MAINNET_PILOT")
        if self.expires_at <= self.issued_at:
            raise ValueError("permit expiry must be after issue time")
        if not self.permitted_actions:
            raise ValueError("permit must contain at least one action")
        if self.environment is EnvironmentV0.MAINNET_PILOT:
            if self.pre_pilot_review_id is None or self.human_mainnet_authorization_id is None:
                raise ValueError(
                    "Mainnet pilot permit requires pre-pilot review and human authorization"
                )
        return self
