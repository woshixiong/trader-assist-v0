from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .common import EnvironmentV0, OpaqueId, Sha256Hex, StrictModel, UTCDateTime, VersionId
from .health import MandatoryFeedStatusV0


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


class StrategyCandidateV0(StrictModel):
    schema_version: VersionId
    candidate_id: OpaqueId
    candidate_hash: Sha256Hex
    playbook_id: PlaybookIdV0
    strategy_version: VersionId
    parameter_version: VersionId
    feature_version: VersionId
    label_version: VersionId
    created_at: UTCDateTime
    expires_at: UTCDateTime
    kind: CandidateKindV0
    direction: DirectionV0 | None = None
    entry_zone_low: float | None = Field(default=None, gt=0)
    entry_zone_high: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    target_prices: tuple[float, ...] = ()
    reason_codes: tuple[str, ...] = ()
    invalidation_codes: tuple[str, ...] = ()
    market_snapshot_hash: Sha256Hex
    account_snapshot_hash: Sha256Hex
    context_snapshot_hash: Sha256Hex
    mandatory_feed_status: MandatoryFeedStatusV0

    @model_validator(mode="after")
    def validate_candidate(self) -> StrategyCandidateV0:
        if self.expires_at <= self.created_at:
            raise ValueError("candidate expiry must be after creation")
        if self.kind is CandidateKindV0.TRADE_SETUP:
            if not self.mandatory_feed_status.all_live:
                raise ValueError("trade setup requires all mandatory feeds LIVE")
            required = (self.direction, self.entry_zone_low, self.entry_zone_high, self.stop_price)
            if any(item is None for item in required) or not self.target_prices:
                raise ValueError("trade setup requires direction, entry zone, stop, and targets")
            assert self.entry_zone_low is not None and self.entry_zone_high is not None
            if self.entry_zone_low > self.entry_zone_high:
                raise ValueError("entry_zone_low must be <= entry_zone_high")
        return self


class PromotionRecordV0(StrictModel):
    schema_version: VersionId
    promotion_record_id: OpaqueId
    promotion_record_hash: Sha256Hex
    playbook_id: PlaybookIdV0
    strategy_version: VersionId
    parameter_version: VersionId
    feature_version: VersionId
    label_version: VersionId
    required_feed_contract_version: VersionId
    state: PromotionStateV0
    environment: EnvironmentV0
    evidence_dataset_ids: tuple[OpaqueId, ...]
    reviewed_by: OpaqueId
    reviewed_at: UTCDateTime
    activated_at: UTCDateTime | None = None
    expires_at: UTCDateTime | None = None
    revoked_at: UTCDateTime | None = None
    rationale: str = Field(min_length=1, max_length=2000)

    def active_at(self, at: UTCDateTime) -> bool:
        if self.revoked_at is not None and self.revoked_at <= at:
            return False
        if self.activated_at is not None and at < self.activated_at:
            return False
        if self.expires_at is not None and at >= self.expires_at:
            return False
        return self.state not in {
            PromotionStateV0.DRAFT,
            PromotionStateV0.QUARANTINED,
            PromotionStateV0.RETIRED,
        }
