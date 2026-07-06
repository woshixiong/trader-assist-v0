from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .common import (
    HashBoundModel,
    HashDomainV0,
    OpaqueId,
    Sha256Hex,
    StrictModel,
    UTCDateTime,
    VersionId,
)


class HealthStateV0(StrEnum):
    INITIALIZING = "INITIALIZING"
    SNAPSHOT_SYNC = "SNAPSHOT_SYNC"
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    GAPPED = "GAPPED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    BACKFILLING = "BACKFILLING"
    RECONCILING = "RECONCILING"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


LEGAL_HEALTH_TRANSITIONS: dict[HealthStateV0, frozenset[HealthStateV0]] = {
    HealthStateV0.INITIALIZING: frozenset(
        {
            HealthStateV0.INITIALIZING,
            HealthStateV0.SNAPSHOT_SYNC,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
            HealthStateV0.UNKNOWN,
        }
    ),
    HealthStateV0.SNAPSHOT_SYNC: frozenset(
        {
            HealthStateV0.SNAPSHOT_SYNC,
            HealthStateV0.LIVE,
            HealthStateV0.DEGRADED,
            HealthStateV0.GAPPED,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.LIVE: frozenset(
        {
            HealthStateV0.LIVE,
            HealthStateV0.DEGRADED,
            HealthStateV0.STALE,
            HealthStateV0.GAPPED,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.DEGRADED: frozenset(
        {
            HealthStateV0.DEGRADED,
            HealthStateV0.LIVE,
            HealthStateV0.STALE,
            HealthStateV0.GAPPED,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.RECONNECTING,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.STALE: frozenset(
        {
            HealthStateV0.STALE,
            HealthStateV0.LIVE,
            HealthStateV0.DEGRADED,
            HealthStateV0.GAPPED,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.RECONNECTING,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.GAPPED: frozenset(
        {
            HealthStateV0.GAPPED,
            HealthStateV0.BACKFILLING,
            HealthStateV0.RECONNECTING,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.DISCONNECTED: frozenset(
        {
            HealthStateV0.DISCONNECTED,
            HealthStateV0.RECONNECTING,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.RECONNECTING: frozenset(
        {
            HealthStateV0.RECONNECTING,
            HealthStateV0.SNAPSHOT_SYNC,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.BACKFILLING: frozenset(
        {
            HealthStateV0.BACKFILLING,
            HealthStateV0.RECONCILING,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.RECONCILING: frozenset(
        {
            HealthStateV0.RECONCILING,
            HealthStateV0.LIVE,
            HealthStateV0.DEGRADED,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
        }
    ),
    HealthStateV0.CONFLICTED: frozenset(
        {
            HealthStateV0.CONFLICTED,
            HealthStateV0.RECONCILING,
            HealthStateV0.DISCONNECTED,
        }
    ),
    HealthStateV0.UNKNOWN: frozenset(
        {
            HealthStateV0.UNKNOWN,
            HealthStateV0.INITIALIZING,
            HealthStateV0.DISCONNECTED,
            HealthStateV0.CONFLICTED,
        }
    ),
}


def is_legal_health_transition(previous: HealthStateV0, current: HealthStateV0) -> bool:
    return current in LEGAL_HEALTH_TRANSITIONS[previous]


class FeedHealthPolicyV0(StrictModel):
    policy_version: VersionId
    feed_id: OpaqueId
    required: bool
    max_age_ms: int = Field(gt=0)
    expected_cadence_ms: int = Field(gt=0)
    max_future_skew_ms: int = Field(ge=0)
    reconnect_limit: int = Field(ge=0)
    gap_policy: str = Field(min_length=1, max_length=200)
    backfill_source: str = Field(min_length=1, max_length=200)
    reconciliation_rule: str = Field(min_length=1, max_length=300)


class RequiredFeedContractV0(HashBoundModel):
    hash_domain = HashDomainV0.REQUIRED_FEED_CONTRACT
    hash_field = "contract_hash"

    schema_version: VersionId
    contract_id: OpaqueId
    contract_hash: Sha256Hex
    playbook_id: OpaqueId
    contract_version: VersionId
    mandatory_feed_ids: frozenset[OpaqueId]
    created_at: UTCDateTime

    @model_validator(mode="after")
    def validate_contract(self) -> RequiredFeedContractV0:
        if not self.mandatory_feed_ids:
            raise ValueError("required feed contract must contain mandatory feeds")
        return self


class DataHealthEventV0(StrictModel):
    health_event_id: OpaqueId
    feed_id: OpaqueId
    policy_version: VersionId
    previous_state: HealthStateV0
    state: HealthStateV0
    observed_at: UTCDateTime
    source_event_time: UTCDateTime | None = None
    age_ms: int | None = Field(default=None, ge=0)
    sequence_gap: bool = False
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_transition(self) -> DataHealthEventV0:
        if not is_legal_health_transition(self.previous_state, self.state):
            raise ValueError(f"illegal health transition: {self.previous_state} -> {self.state}")
        if self.state is not HealthStateV0.LIVE and not self.reason_codes:
            raise ValueError("non-LIVE health state requires reason_codes")
        return self


class MandatoryFeedStatusV0(StrictModel):
    playbook_id: OpaqueId
    required_feed_contract_id: OpaqueId
    required_feed_contract_version: VersionId
    required_feed_contract_hash: Sha256Hex
    evaluated_at: UTCDateTime
    valid_until: UTCDateTime
    mandatory_feed_ids: frozenset[OpaqueId]
    feed_states: dict[OpaqueId, HealthStateV0]

    @model_validator(mode="after")
    def validate_status(self) -> MandatoryFeedStatusV0:
        if self.valid_until < self.evaluated_at:
            raise ValueError("mandatory-feed status valid_until must be >= evaluated_at")
        if not self.mandatory_feed_ids:
            raise ValueError("mandatory_feed_ids must be non-empty")
        if set(self.feed_states) != set(self.mandatory_feed_ids):
            raise ValueError("feed_states must exactly cover mandatory_feed_ids")
        return self

    @property
    def all_live(self) -> bool:
        return all(state is HealthStateV0.LIVE for state in self.feed_states.values())

    def satisfies(self, contract: RequiredFeedContractV0, at: UTCDateTime) -> bool:
        return (
            self.playbook_id == contract.playbook_id
            and self.required_feed_contract_id == contract.contract_id
            and self.required_feed_contract_version == contract.contract_version
            and self.required_feed_contract_hash == contract.contract_hash
            and self.mandatory_feed_ids == contract.mandatory_feed_ids
            and self.evaluated_at <= at <= self.valid_until
            and self.all_live
        )
