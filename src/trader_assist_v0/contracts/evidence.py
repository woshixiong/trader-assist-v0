from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator, model_validator

from .common import EnvironmentV0, OpaqueId, Sha256Hex, StrictModel, UTCDateTime, VersionId


class CorrelationChainV0(StrictModel):
    source_event_id: OpaqueId
    normalized_event_id: OpaqueId
    market_snapshot_id: OpaqueId
    account_snapshot_id: OpaqueId
    context_snapshot_id: OpaqueId
    feature_snapshot_id: OpaqueId
    regime_decision_id: OpaqueId
    strategy_candidate_id: OpaqueId
    recommendation_id: OpaqueId
    proposal_id: OpaqueId
    human_decision_id: OpaqueId | None = None
    execution_permit_id: OpaqueId | None = None
    order_package_id: OpaqueId | None = None
    client_order_id: OpaqueId | None = None
    exchange_order_id: OpaqueId | None = None
    fill_id: OpaqueId | None = None
    position_episode_id: OpaqueId | None = None
    outcome_id: OpaqueId | None = None
    review_id: OpaqueId | None = None


class EvidenceFileV0(StrictModel):
    relative_path: str = Field(min_length=1, max_length=500)
    sha256: Sha256Hex
    size_bytes: int = Field(ge=0)
    row_count: int | None = Field(default=None, ge=0)
    min_event_time: UTCDateTime | None = None
    max_event_time: UTCDateTime | None = None

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        parts = Path(value).parts
        if value.startswith("/") or ".." in parts:
            raise ValueError("relative_path must not be absolute or traverse parents")
        return value

    @model_validator(mode="after")
    def validate_time_bounds(self) -> EvidenceFileV0:
        if (
            self.min_event_time is not None
            and self.max_event_time is not None
            and self.min_event_time > self.max_event_time
        ):
            raise ValueError("min_event_time must be <= max_event_time")
        return self


class EvidenceBundleManifestV0(StrictModel):
    bundle_schema_version: VersionId
    dataset_id: OpaqueId
    environment: EnvironmentV0
    account_alias: OpaqueId
    instrument: str = Field(pattern=r"^ETH$")
    start_time: UTCDateTime
    end_time: UTCDateTime
    source_versions: dict[str, VersionId]
    collector_versions: dict[str, VersionId]
    normalizer_version: VersionId
    strategy_versions: dict[str, VersionId]
    parameter_versions: dict[str, VersionId]
    risk_policy_version: VersionId
    model_versions: dict[str, VersionId]
    prompt_versions: dict[str, VersionId]
    code_commit_sha: Sha256Hex
    quality_status: str = Field(min_length=1, max_length=80)
    known_gaps: tuple[str, ...]
    files: tuple[EvidenceFileV0, ...]
    created_at: UTCDateTime

    @model_validator(mode="after")
    def validate_bundle(self) -> EvidenceBundleManifestV0:
        if self.end_time <= self.start_time:
            raise ValueError("bundle end_time must be after start_time")
        paths = [item.relative_path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("evidence file paths must be unique")
        return self
