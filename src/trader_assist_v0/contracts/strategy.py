from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

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
from .precision import InstrumentPrecisionContractV0, require_step_aligned


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


LEGAL_PROMOTION_TRANSITIONS: dict[PromotionStateV0, frozenset[PromotionStateV0]] = {
    PromotionStateV0.DRAFT: frozenset({PromotionStateV0.SHADOW}),
    PromotionStateV0.SHADOW: frozenset(
        {
            PromotionStateV0.HUMAN_REVIEW,
            PromotionStateV0.QUARANTINED,
            PromotionStateV0.RETIRED,
        }
    ),
    PromotionStateV0.HUMAN_REVIEW: frozenset(
        {
            PromotionStateV0.TESTNET_ELIGIBLE,
            PromotionStateV0.QUARANTINED,
            PromotionStateV0.RETIRED,
        }
    ),
    PromotionStateV0.TESTNET_ELIGIBLE: frozenset(
        {
            PromotionStateV0.MAINNET_PILOT_ELIGIBLE,
            PromotionStateV0.QUARANTINED,
            PromotionStateV0.RETIRED,
        }
    ),
    PromotionStateV0.MAINNET_PILOT_ELIGIBLE: frozenset(
        {
            PromotionStateV0.MAINNET_PILOT_ACTIVE,
            PromotionStateV0.QUARANTINED,
            PromotionStateV0.RETIRED,
        }
    ),
    PromotionStateV0.MAINNET_PILOT_ACTIVE: frozenset(
        {PromotionStateV0.QUARANTINED, PromotionStateV0.RETIRED}
    ),
    PromotionStateV0.QUARANTINED: frozenset(
        {PromotionStateV0.SHADOW, PromotionStateV0.RETIRED}
    ),
    PromotionStateV0.RETIRED: frozenset(),
}


class StrategyCandidateV0(HashBoundModel):
    hash_domain = HashDomainV0.STRATEGY_CANDIDATE
    hash_field = "candidate_hash"

    schema_version: VersionId
    candidate_id: OpaqueId
    candidate_hash: Sha256Hex
    symbol: Literal["ETH"] = "ETH"
    playbook_id: PlaybookIdV0
    strategy_version: VersionId
    parameter_version: VersionId
    feature_version: VersionId
    label_version: VersionId
    required_feed_contract: RequiredFeedContractV0
    instrument_precision: InstrumentPrecisionContractV0
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
        if self.instrument_precision.symbol != self.symbol:
            raise ValueError("instrument precision symbol must match candidate symbol")
        if self.expires_at <= self.created_at:
            raise ValueError("candidate expiry must be after creation")
        price_fields = (
            ("entry_zone_low", self.entry_zone_low),
            ("entry_zone_high", self.entry_zone_high),
            ("stop_price", self.stop_price),
        )
        for field_name, value in price_fields:
            if value is not None:
                require_step_aligned(value, self.instrument_precision.price_tick, field_name)
        for index, target in enumerate(self.target_prices):
            require_step_aligned(
                target,
                self.instrument_precision.price_tick,
                f"target_prices[{index}]",
            )
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
    predecessor_record_id: OpaqueId | None = None
    predecessor_record_hash: Sha256Hex | None = None
    predecessor_state: PromotionStateV0 | None = None
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
        predecessor_values = (
            self.predecessor_record_id,
            self.predecessor_record_hash,
            self.predecessor_state,
        )
        if self.state is PromotionStateV0.DRAFT:
            if any(item is not None for item in predecessor_values):
                raise ValueError("initial DRAFT must not declare a predecessor")
            if self.activated_at is not None:
                raise ValueError("initial DRAFT must not be activated")
        else:
            if any(item is None for item in predecessor_values):
                raise ValueError("non-DRAFT promotion requires complete predecessor binding")
            if not self.evidence_dataset_ids:
                raise ValueError("non-DRAFT promotion requires transition-specific evidence")
            if self.activated_at is None:
                raise ValueError("non-DRAFT promotion requires activated_at")
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

    @classmethod
    def bind(
        cls,
        *,
        previous: PromotionRecordV0 | None = None,
        **payload: Any,
    ) -> PromotionRecordV0:
        state = PromotionStateV0(payload["state"])
        predecessor_fields = {
            "predecessor_record_id",
            "predecessor_record_hash",
            "predecessor_state",
        }
        if predecessor_fields.intersection(payload):
            raise ValueError(
                "predecessor fields are derived from previous and must not be supplied"
            )
        if previous is None:
            if state is not PromotionStateV0.DRAFT:
                raise ValueError("initial promotion record must be DRAFT")
        else:
            payload.update(
                predecessor_record_id=previous.promotion_record_id,
                predecessor_record_hash=previous.promotion_record_hash,
                predecessor_state=previous.state,
            )
        current = super().bind(**payload)
        validate_promotion_transition(previous, current)
        return current

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


_PROMOTION_SUBJECT_FIELDS = (
    "playbook_id",
    "strategy_version",
    "parameter_version",
    "feature_version",
    "label_version",
    "required_feed_contract_id",
    "required_feed_contract_version",
    "required_feed_contract_hash",
)


def _revalidate_promotion(record: PromotionRecordV0) -> PromotionRecordV0:
    if type(record) is not PromotionRecordV0:
        raise ValueError("expected exact PromotionRecordV0 authority object")
    return PromotionRecordV0.model_validate(record.model_dump(mode="python", round_trip=True))


def validate_promotion_transition(
    previous: PromotionRecordV0 | None,
    current: PromotionRecordV0,
) -> None:
    current = _revalidate_promotion(current)
    if previous is not None:
        previous = _revalidate_promotion(previous)
    failures: list[str] = []
    if previous is None:
        if current.state is not PromotionStateV0.DRAFT:
            failures.append("initial promotion record must be DRAFT")
        if any(
            item is not None
            for item in (
                current.predecessor_record_id,
                current.predecessor_record_hash,
                current.predecessor_state,
            )
        ):
            failures.append("initial DRAFT must not bind a predecessor")
    else:
        if previous.state is PromotionStateV0.RETIRED:
            failures.append("RETIRED is terminal")
        if current.promotion_record_id == previous.promotion_record_id:
            failures.append("promotion transition must create a new record")
        if current.predecessor_record_id != previous.promotion_record_id:
            failures.append("wrong predecessor ID")
        if current.predecessor_record_hash != previous.promotion_record_hash:
            failures.append("wrong predecessor hash")
        if current.predecessor_state is not previous.state:
            failures.append("declared predecessor state mismatch")
        if current.state not in LEGAL_PROMOTION_TRANSITIONS[previous.state]:
            failures.append("declared predecessor state does not permit this transition")
        for field_name in _PROMOTION_SUBJECT_FIELDS:
            if getattr(current, field_name) != getattr(previous, field_name):
                failures.append(f"promotion subject mismatch: {field_name}")
        previous_effective_at = previous.activated_at or previous.reviewed_at
        if current.reviewed_at < previous_effective_at:
            failures.append("transition review predates predecessor")
    if failures:
        raise ValueError("; ".join(failures))


def validate_promotion_chain(
    records: tuple[PromotionRecordV0, ...],
) -> tuple[PromotionRecordV0, ...]:
    if not records:
        raise ValueError("promotion chain must not be empty")
    validated = tuple(_revalidate_promotion(record) for record in records)
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    previous: PromotionRecordV0 | None = None
    for record in validated:
        if record.promotion_record_id in seen_ids:
            raise ValueError("promotion chain contains duplicate record ID")
        if record.promotion_record_hash in seen_hashes:
            raise ValueError("promotion chain contains duplicate record hash")
        validate_promotion_transition(previous, record)
        seen_ids.add(record.promotion_record_id)
        seen_hashes.add(record.promotion_record_hash)
        previous = record
    return validated


def validate_execution_promotion_authority(
    records: tuple[PromotionRecordV0, ...],
    *,
    at: UTCDateTime,
) -> PromotionRecordV0:
    """Derive execution authority only from a complete, validated promotion chain."""
    validated = validate_promotion_chain(records)
    terminal = validated[-1]
    if not terminal.active_at(at):
        raise ValueError("terminal promotion is not active at authority time")
    execution_enabled = (
        terminal.environment is EnvironmentV0.TESTNET
        and terminal.state is PromotionStateV0.TESTNET_ELIGIBLE
    ) or (
        terminal.environment is EnvironmentV0.MAINNET_PILOT
        and terminal.state is PromotionStateV0.MAINNET_PILOT_ACTIVE
    )
    if not execution_enabled:
        raise ValueError("terminal promotion is not execution-enabled")
    return terminal
