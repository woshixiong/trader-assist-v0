from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .common import (
    EnvironmentV0,
    HashBoundModel,
    HashDomainV0,
    OpaqueId,
    PositiveFiniteDecimal,
    Sha256Hex,
    UTCDateTime,
    VersionId,
)
from .health import MandatoryFeedStatusV0, RequiredFeedContractV0


class PlaybookIdV0(StrEnum):
    LQS_FR = "LQS-FR"
    BRK_AR = "BRK-AR"
    TRD_PB = "TRD-PB"
    BAL_RV = "BAL-RV"
    MACRO_RP = "MACRO-RP"


class DirectionV0(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class CandidateKindV0(StrEnum):
    NO_TRADE = "NO_TRADE"
    WATCH = "WATCH"
    TRADE_SETUP = "TRADE_SETUP"


class PromotionStateV0(StrEnum):
    DRAFT = "DRAFT"
    SHADOW = "SHADOW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    TESTNET_ELIGIBLE = "TESTNET_ELIGIBLE"
    MAINNET_PILOT_ELIGIBLE = "MAINNET_PILOT_ELIGIBLE"
    MAINNET_PILOT_ACTIVE = "MAINNET_PILOT_ACTIVE"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


ALLOWED_PROMOTION_ENVIRONMENTS: dict[PromotionStateV0, frozenset[EnvironmentV0]] = {
    PromotionStateV0.DRAFT: frozenset({EnvironmentV0.READ_ONLY, EnvironmentV0.SHADOW}),
    PromotionStateV0.SHADOW: frozenset({EnvironmentV0.SHADOW}),
    PromotionStateV0.HUMAN_REVIEW: frozenset({EnvironmentV0.HUMAN_REVIEW}),
    PromotionStateV0.TESTNET_ELIGIBLE: frozenset({EnvironmentV0.TESTNET}),
    PromotionStateV0.MAINNET_PILOT_ELIGIBLE: frozenset({EnvironmentV0.MAINNET_PILOT}),
    PromotionStateV0.MAINNET_PILOT_ACTIVE: frozenset({EnvironmentV0.MAINNET_PILOT}),
    PromotionStateV0.QUARANTINED: frozenset(set(EnvironmentV0)),
    PromotionStateV0.RETIRED: frozenset(set(EnvironmentV0)),
}


class StrategyCandidateV0(HashBoundModel):
    hash_domain = HashDomainV0.STRATEGY_CANDIDATE
    hash_field = "candidate_hash"

    schema_version: VersionId
    candidate_id: OpaqueId
    candidate_hash: Sha256Hex
    playbook_id: PlaybookIdV0
    strategy_version: VersionId
    parameter_version: VersionId
    feature_version: VersionId
    label_version: VersionId
    required_feed_contract: RequiredFeedContractV0
    created_at: UTCDateTime
    expires_at: UTCDateTime
    kind: CandidateKindV0
    direction: DirectionV0 | None = None
    entry_zone_low: PositiveFiniteDecimal | None = None
    entry_zone_high: PositiveFiniteDecimal | None = None
    stop_price: PositiveFiniteDecimal | None = None
    target_prices: tuple[PositiveFiniteDecimal, ...] = ()
    reason_codes: tuple[str, ...] = ()
    invalidation_codes: tuple[str, ...] = ()
    market_snapshot_hash: Sha256Hex
    account_snapshot_hash: Sha256Hex
    context_snapshot_hash: Sha256Hex
    mandatory_feed_status: MandatoryFeedStatusV0

    @model_validator(mode="after")
    def validate_candidate(self) -> StrategyCandidateV0:
        if self.required_feed_contract.playbook_id != self.playbook_id.value:
            raise ValueError("required feed contract playbook must match candidate playbook")
        if self.expires_at <= self.created_at:
            raise ValueError("candidate expiry must be after creation")
        if self.kind is CandidateKindV0.TRADE_SETUP:
            if not self.mandatory_feed_status.satisfies(
                self.required_feed_contract,
                at=self.created_at,
            ):
                raise ValueError(
                    "mandatory feeds LIVE and match the exact playbook contract, coverage, and time"
                )
            required = (self.direction, self.entry_zone_low, self.entry_zone_high, self.stop_price)
            if any(item is None for item in required) or not self.target_prices:
                raise ValueError("trade setup requires direction, entry zone, stop, and targets")
            assert self.entry_zone_low is not None and self.entry_zone_high is not None
            if self.entry_zone_low > self.entry_zone_high:
                raise ValueError("entry_zone_low must be <= entry_zone_high")
        return self


class PromotionRecordV0(HashBoundModel):
    hash_domain = HashDomainV0.PROMOTION_RECORD
    hash_field = "promotion_record_hash"

    schema_version: VersionId
    promotion_record_id: OpaqueId
    promotion_record_hash: Sha256Hex
    playbook_id: PlaybookIdV0
    strategy_version: VersionId
    parameter_version: VersionId
    feature_version: VersionId
    label_version: VersionId
    required_feed_contract_id: OpaqueId
    required_feed_contract_version: VersionId
    required_feed_contract_hash: Sha256Hex
    state: PromotionStateV0
    environment: EnvironmentV0
    evidence_dataset_ids: tuple[OpaqueId, ...]
    reviewed_by: OpaqueId
    reviewed_at: UTCDateTime
    activated_at: UTCDateTime | None = None
    expires_at: UTCDateTime | None = None
    revoked_at: UTCDateTime | None = None
    rationale: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_promotion(self) -> PromotionRecordV0:
        if self.environment not in ALLOWED_PROMOTION_ENVIRONMENTS[self.state]:
            raise ValueError("promotion state is not valid for environment")
        if self.state not in {PromotionStateV0.DRAFT, PromotionStateV0.RETIRED}:
            if not self.evidence_dataset_ids:
                raise ValueError("non-draft promotion requires evidence_dataset_ids")
            if self.activated_at is None:
                raise ValueError("non-draft promotion requires activated_at")
        if self.activated_at is not None and self.activated_at < self.reviewed_at:
            raise ValueError("promotion cannot activate before review")
        if (
            self.expires_at is not None
            and self.activated_at is not None
            and self.expires_at <= self.activated_at
        ):
            raise ValueError("promotion expiry must be after activation")
        if (
            self.revoked_at is not None
            and self.activated_at is not None
            and self.revoked_at < self.activated_at
        ):
            raise ValueError("revocation cannot predate activation")
        return self

    def active_at(self, at: UTCDateTime) -> bool:
        if self.activated_at is None or at < self.activated_at:
            return False
        if self.revoked_at is not None and self.revoked_at <= at:
            return False
        if self.expires_at is not None and at >= self.expires_at:
            return False
        return self.state in {
            PromotionStateV0.SHADOW,
            PromotionStateV0.HUMAN_REVIEW,
            PromotionStateV0.TESTNET_ELIGIBLE,
            PromotionStateV0.MAINNET_PILOT_ACTIVE,
        }

    def execution_enabled_at(self, at: UTCDateTime) -> bool:
        if not self.active_at(at):
            return False
        return (
            self.environment is EnvironmentV0.TESTNET
            and self.state is PromotionStateV0.TESTNET_ELIGIBLE
        ) or (
            self.environment is EnvironmentV0.MAINNET_PILOT
            and self.state is PromotionStateV0.MAINNET_PILOT_ACTIVE
        )
