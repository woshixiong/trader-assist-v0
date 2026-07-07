from __future__ import annotations

import hmac
import re
from collections.abc import Mapping, Set
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.config import ExtraValues

from .common import (
    EnvironmentV0,
    OpaqueId,
    Sha256Hex,
    StrictModel,
    UTCDateTime,
    VersionId,
    canonical_json_bytes,
    sha256_hex,
)

RAW_IDENTITY_VERSION = "trader-assist-v0/raw-observation/v1"
OBSERVATION_SLOT_VERSION = "trader-assist-v0/raw-observation-slot/v1"
MANIFEST_FORMAT_VERSION = "0.1.0"
MANIFEST_HASH_CHAIN_VERSION = "trader-assist-v0/raw-manifest-entry/v1"
REPLAY_REPORT_VERSION = "0.1.0"
REPLAY_REPORT_HASH_VERSION = "trader-assist-v0/bronze-replay-report/v1"
MANIFEST_GENESIS_HASH = "0" * 64
_PAYLOAD_REF_RE = re.compile(
    r"^payloads/sha256/(?P<prefix>[0-9a-f]{2})/(?P<digest>[0-9a-f]{64})\.payload$"
)


class EventTypeV0(StrEnum):
    TRADE = "TradeEventV0"
    BBO = "BboEventV0"
    BOOK_SNAPSHOT = "BookSnapshotEventV0"
    BOOK_DELTA = "BookDeltaEventV0"
    CANDLE = "CandleEventV0"
    ASSET_CONTEXT = "AssetContextEventV0"
    ACCOUNT_STATE = "AccountStateEventV0"
    POSITION = "PositionEventV0"
    OPEN_ORDER = "OpenOrderEventV0"
    ORDER_UPDATE = "OrderUpdateEventV0"
    FILL = "FillEventV0"
    FUNDING = "FundingEventV0"
    LEDGER = "LedgerEventV0"
    MACRO = "MacroEventV0"
    NEWS = "NewsEventV0"
    SOCIAL = "SocialEventV0"
    LIQUIDATION_CONTEXT = "LiquidationContextEventV0"
    LARGE_FLOW = "LargeFlowEventV0"
    DATA_HEALTH = "DataHealthEventV0"


class RawCaptureModeV0(StrEnum):
    WS_TEXT_UTF8_APPLICATION_PAYLOAD = "WS_TEXT_UTF8_APPLICATION_PAYLOAD"
    HTTP_RESPONSE_BODY = "HTTP_RESPONSE_BODY"


class ReplayStatusV0(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


def _validate_relative_path_text(value: str) -> str:
    if not value:
        raise ValueError("relative path must be non-empty")
    if "\x00" in value:
        raise ValueError("relative path must not contain NUL")
    if "\\" in value or re.match(r"^[A-Za-z]:", value):
        raise ValueError("relative path must use portable POSIX syntax")
    if value.startswith("/"):
        raise ValueError("relative path must not be absolute")
    components = value.split("/")
    if any(component in {"", ".", ".."} for component in components):
        raise ValueError("relative path contains a forbidden component")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError("relative path must be canonical POSIX syntax")
    return value


def compute_observation_slot_id(
    *,
    source_catalog_version: str,
    source_id: str,
    endpoint_id: str,
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
) -> str:
    material = canonical_json_bytes(
        {
            "slot_version": OBSERVATION_SLOT_VERSION,
            "source_catalog_version": source_catalog_version,
            "source_id": source_id,
            "endpoint_id": endpoint_id,
            "connection_id": connection_id,
            "subscription_id": subscription_id,
            "receive_sequence": receive_sequence,
        }
    )
    return sha256_hex(OBSERVATION_SLOT_VERSION.encode() + b"\0" + material)


def compute_raw_observation_id(
    *,
    source_catalog_version: str,
    source_id: str,
    endpoint_id: str,
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
    payload_sha256: str,
) -> str:
    material = canonical_json_bytes(
        {
            "identity_version": RAW_IDENTITY_VERSION,
            "source_catalog_version": source_catalog_version,
            "source_id": source_id,
            "endpoint_id": endpoint_id,
            "connection_id": connection_id,
            "subscription_id": subscription_id,
            "receive_sequence": receive_sequence,
            "payload_sha256": payload_sha256,
        }
    )
    return sha256_hex(RAW_IDENTITY_VERSION.encode() + b"\0" + material)


class _A0AuthorityModel(StrictModel):
    model_config = ConfigDict(revalidate_instances="always")

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if isinstance(obj, BaseModel):
            if type(obj) is not cls:
                raise ValueError(f"expected exact {cls.__name__} authority object")
            obj = BaseModel.model_dump(obj, mode="python", round_trip=True)
        return super().model_validate(
            obj,
            strict=strict,
            extra=extra,
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            raise TypeError("A0 authority models cannot be copied with updates")
        return super().model_copy(deep=deep)

    def copy(
        self,
        *,
        include: Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None = None,
        exclude: Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None = None,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if include is not None or exclude is not None or update is not None:
            raise TypeError("A0 authority models cannot be copied with field changes")
        return self.model_copy(deep=deep)

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        raise TypeError("A0 authority models cannot bypass validation with model_construct")


class RawEventV0(_A0AuthorityModel):
    schema_version: VersionId
    source_event_id: Sha256Hex
    observation_slot_id: Sha256Hex
    source_id: OpaqueId
    source_catalog_version: VersionId
    endpoint_id: OpaqueId
    connection_id: OpaqueId
    subscription_id: OpaqueId
    receive_sequence: int = Field(ge=0)
    source_native_id: str | None = Field(default=None, max_length=300)
    source_native_cursor: str | None = Field(default=None, max_length=300)
    collector_version: VersionId
    environment: Literal[EnvironmentV0.READ_ONLY]
    capture_mode: RawCaptureModeV0
    content_type: str = Field(min_length=1, max_length=120)
    payload_sha256: Sha256Hex
    payload_size_bytes: int = Field(ge=0)
    payload_encoding: str = Field(min_length=1, max_length=40)
    payload_ref: str = Field(min_length=1, max_length=500)
    source_event_time: UTCDateTime | None = None
    source_publish_time: UTCDateTime | None = None
    first_observed_time: UTCDateTime
    collector_receive_time: UTCDateTime
    collector_monotonic_ns: int = Field(ge=0)
    revision_time: UTCDateTime | None = None

    @field_validator("payload_ref")
    @classmethod
    def validate_payload_ref(cls, value: str) -> str:
        return _validate_relative_path_text(value)

    @model_validator(mode="after")
    def validate_authority(self) -> Self:
        if type(self) is not RawEventV0:
            raise ValueError("expected exact RawEventV0 authority object")
        if self.first_observed_time > self.collector_receive_time:
            raise ValueError("first_observed_time must be <= collector_receive_time")
        match = _PAYLOAD_REF_RE.fullmatch(self.payload_ref)
        if match is None:
            raise ValueError("payload_ref must use the content-addressed payload layout")
        if match.group("digest") != self.payload_sha256:
            raise ValueError("payload_ref digest must equal payload_sha256")
        if match.group("prefix") != self.payload_sha256[:2]:
            raise ValueError("payload_ref prefix must match payload_sha256")
        expected_slot = compute_observation_slot_id(
            source_catalog_version=self.source_catalog_version,
            source_id=self.source_id,
            endpoint_id=self.endpoint_id,
            connection_id=self.connection_id,
            subscription_id=self.subscription_id,
            receive_sequence=self.receive_sequence,
        )
        if not hmac.compare_digest(self.observation_slot_id, expected_slot):
            raise ValueError("observation_slot_id does not match collector receive identity")
        expected = compute_raw_observation_id(
            source_catalog_version=self.source_catalog_version,
            source_id=self.source_id,
            endpoint_id=self.endpoint_id,
            connection_id=self.connection_id,
            subscription_id=self.subscription_id,
            receive_sequence=self.receive_sequence,
            payload_sha256=self.payload_sha256,
        )
        if not hmac.compare_digest(self.source_event_id, expected):
            raise ValueError("source_event_id does not match raw observation identity")
        return self

    @classmethod
    def bind_observation(cls, **payload: Any) -> RawEventV0:
        if "source_event_id" in payload or "observation_slot_id" in payload:
            raise ValueError("authority identities must not be supplied to bind_observation()")
        slot = compute_observation_slot_id(
            source_catalog_version=str(payload["source_catalog_version"]),
            source_id=str(payload["source_id"]),
            endpoint_id=str(payload["endpoint_id"]),
            connection_id=str(payload["connection_id"]),
            subscription_id=str(payload["subscription_id"]),
            receive_sequence=int(payload["receive_sequence"]),
        )
        identity = compute_raw_observation_id(
            source_catalog_version=str(payload["source_catalog_version"]),
            source_id=str(payload["source_id"]),
            endpoint_id=str(payload["endpoint_id"]),
            connection_id=str(payload["connection_id"]),
            subscription_id=str(payload["subscription_id"]),
            receive_sequence=int(payload["receive_sequence"]),
            payload_sha256=str(payload["payload_sha256"]),
        )
        return cls.model_validate(
            {**payload, "observation_slot_id": slot, "source_event_id": identity}
        )


ModelT = TypeVar("ModelT", bound=BaseModel)


def _revalidate_exact(value: Any, expected_type: type[ModelT]) -> ModelT:
    if isinstance(value, BaseModel):
        if type(value) is not expected_type:
            raise ValueError(f"expected exact {expected_type.__name__} authority object")
        value = BaseModel.model_dump(value, mode="python", round_trip=True)
    validated = expected_type.model_validate(value)
    if type(validated) is not expected_type:
        raise ValueError(f"expected exact {expected_type.__name__} authority object")
    return validated


class RawManifestEntryV0(_A0AuthorityModel):
    schema_version: VersionId
    manifest_format_version: VersionId = MANIFEST_FORMAT_VERSION
    hash_chain_version: VersionId = MANIFEST_HASH_CHAIN_VERSION
    segment_id: OpaqueId
    entry_index: int = Field(ge=0)
    previous_entry_hash: Sha256Hex
    entry_hash: Sha256Hex
    raw_event: RawEventV0

    @field_validator("raw_event", mode="before")
    @classmethod
    def validate_raw_event(cls, value: Any) -> RawEventV0:
        return _revalidate_exact(value, RawEventV0)

    @model_validator(mode="after")
    def validate_entry(self) -> Self:
        if type(self) is not RawManifestEntryV0:
            raise ValueError("expected exact RawManifestEntryV0 authority object")
        if type(self.raw_event) is not RawEventV0:
            raise ValueError("manifest entry requires exact RawEventV0")
        if self.entry_index == 0 and self.previous_entry_hash != MANIFEST_GENESIS_HASH:
            raise ValueError("first manifest entry must use the genesis previous hash")
        if self.entry_index > 0 and self.previous_entry_hash == MANIFEST_GENESIS_HASH:
            raise ValueError("non-first manifest entry cannot use the genesis previous hash")
        expected = compute_manifest_entry_hash(
            schema_version=self.schema_version,
            manifest_format_version=self.manifest_format_version,
            hash_chain_version=self.hash_chain_version,
            segment_id=self.segment_id,
            entry_index=self.entry_index,
            previous_entry_hash=self.previous_entry_hash,
            raw_event=self.raw_event,
        )
        if not hmac.compare_digest(self.entry_hash, expected):
            raise ValueError("entry_hash does not match canonical manifest entry")
        return self

    @classmethod
    def bind(
        cls,
        *,
        schema_version: str,
        segment_id: str,
        entry_index: int,
        previous_entry_hash: str,
        raw_event: RawEventV0,
    ) -> RawManifestEntryV0:
        exact_event = _revalidate_exact(raw_event, RawEventV0)
        digest = compute_manifest_entry_hash(
            schema_version=schema_version,
            manifest_format_version=MANIFEST_FORMAT_VERSION,
            hash_chain_version=MANIFEST_HASH_CHAIN_VERSION,
            segment_id=segment_id,
            entry_index=entry_index,
            previous_entry_hash=previous_entry_hash,
            raw_event=exact_event,
        )
        return cls.model_validate(
            {
                "schema_version": schema_version,
                "manifest_format_version": MANIFEST_FORMAT_VERSION,
                "hash_chain_version": MANIFEST_HASH_CHAIN_VERSION,
                "segment_id": segment_id,
                "entry_index": entry_index,
                "previous_entry_hash": previous_entry_hash,
                "entry_hash": digest,
                "raw_event": exact_event,
            }
        )


def compute_manifest_entry_hash(
    *,
    schema_version: str,
    manifest_format_version: str,
    hash_chain_version: str,
    segment_id: str,
    entry_index: int,
    previous_entry_hash: str,
    raw_event: RawEventV0,
) -> str:
    exact_event = _revalidate_exact(raw_event, RawEventV0)
    material = canonical_json_bytes(
        {
            "schema_version": schema_version,
            "manifest_format_version": manifest_format_version,
            "hash_chain_version": hash_chain_version,
            "segment_id": segment_id,
            "entry_index": entry_index,
            "previous_entry_hash": previous_entry_hash,
            "raw_event": BaseModel.model_dump(exact_event, mode="python", round_trip=True),
        }
    )
    return sha256_hex(MANIFEST_HASH_CHAIN_VERSION.encode() + b"\0" + material)


class BronzeReplayReportV0(_A0AuthorityModel):
    schema_version: VersionId
    replay_report_version: VersionId = REPLAY_REPORT_VERSION
    manifest_segment_id: OpaqueId
    source_catalog_version: VersionId
    entries_checked: int = Field(ge=0)
    unique_payload_blobs: int = Field(ge=0)
    duplicate_payload_observations: int = Field(ge=0)
    idempotent_event_observations: int = Field(ge=0)
    conflicting_event_identities: int = Field(ge=0)
    missing_payload_count: int = Field(ge=0)
    corrupt_payload_count: int = Field(ge=0)
    orphan_payload_count: int = Field(ge=0)
    partial_manifest_count: int = Field(ge=0)
    first_receive_time: UTCDateTime | None = None
    last_receive_time: UTCDateTime | None = None
    manifest_terminal_hash: Sha256Hex
    status: ReplayStatusV0
    reason_codes: tuple[str, ...]
    report_hash: Sha256Hex

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))):
            raise ValueError("reason_codes must be sorted and unique")
        return value

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        if type(self) is not BronzeReplayReportV0:
            raise ValueError("expected exact BronzeReplayReportV0 authority object")
        failures = (
            self.conflicting_event_identities
            + self.missing_payload_count
            + self.corrupt_payload_count
            + self.orphan_payload_count
            + self.partial_manifest_count
            + self.idempotent_event_observations
        )
        if self.status is ReplayStatusV0.PASS and (failures or self.reason_codes):
            raise ValueError("PASS replay report cannot contain integrity failures")
        if self.status is ReplayStatusV0.FAIL and not self.reason_codes:
            raise ValueError("FAIL replay report requires reason_codes")
        expected = compute_replay_report_hash(self)
        if not hmac.compare_digest(self.report_hash, expected):
            raise ValueError("report_hash does not match canonical replay report")
        return self

    @classmethod
    def bind(cls, **payload: Any) -> BronzeReplayReportV0:
        if "report_hash" in payload:
            raise ValueError("report_hash must not be supplied to bind()")
        normalized = {"replay_report_version": REPLAY_REPORT_VERSION, **payload}
        digest = compute_replay_report_hash_from_payload(normalized)
        return cls.model_validate({**normalized, "report_hash": digest})


def compute_replay_report_hash_from_payload(payload: Mapping[str, Any]) -> str:
    material = canonical_json_bytes(dict(payload))
    return sha256_hex(REPLAY_REPORT_HASH_VERSION.encode() + b"\0" + material)


def compute_replay_report_hash(report: BronzeReplayReportV0) -> str:
    payload = BaseModel.model_dump(report, mode="python", round_trip=True)
    payload.pop("report_hash", None)
    return compute_replay_report_hash_from_payload(payload)


class NormalizedEventV0(StrictModel):
    schema_version: VersionId
    normalized_event_id: OpaqueId
    source_event_id: OpaqueId
    event_type: EventTypeV0
    normalized_time: UTCDateTime
    normalized_payload_sha256: Sha256Hex
    units: dict[str, str] = Field(default_factory=dict)
    precision: dict[str, int] = Field(default_factory=dict)
    payload: dict[str, Any]
