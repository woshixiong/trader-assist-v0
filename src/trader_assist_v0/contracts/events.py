from __future__ import annotations

import hmac
import re
from collections.abc import Mapping, Set
from datetime import date
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal, Self

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
from .source_catalog import (
    SOURCE_CATALOG_HASH,
    SOURCE_CATALOG_VERSION,
    SOURCE_ID,
    catalog_entry_hash,
    endpoint_kind,
    get_entry,
    validate_public_selection,
)

A0_SCHEMA_VERSION = "0.1.0"
RAW_IDENTITY_VERSION = "trader-assist-v0/raw-observation/v2"
OBSERVATION_SLOT_VERSION = "trader-assist-v0/raw-observation-slot/v2"
MANIFEST_FORMAT_VERSION = "0.1.0"
MANIFEST_HASH_CHAIN_VERSION = "trader-assist-v0/raw-manifest-entry/v1"
MANIFEST_CHECKPOINT_VERSION = "0.1.0"
MANIFEST_CHECKPOINT_HASH_VERSION = "trader-assist-v0/raw-manifest-checkpoint/v1"
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


def _selection_material(
    *,
    source_catalog_version: str,
    source_catalog_hash: str,
    catalog_entry_hash_value: str,
    source_id: str,
    endpoint_id: str,
    operation_type: str,
    coin: str | None,
    candle_interval: str | None,
    capture_mode: str,
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
) -> dict[str, Any]:
    return {
        "source_catalog_version": source_catalog_version,
        "source_catalog_hash": source_catalog_hash,
        "catalog_entry_hash": catalog_entry_hash_value,
        "source_id": source_id,
        "endpoint_id": endpoint_id,
        "operation_type": operation_type,
        "coin": coin,
        "candle_interval": candle_interval,
        "capture_mode": capture_mode,
        "connection_id": connection_id,
        "subscription_id": subscription_id,
        "receive_sequence": receive_sequence,
    }


def compute_observation_slot_id(
    *,
    source_catalog_version: str,
    source_catalog_hash: str,
    catalog_entry_hash_value: str,
    source_id: str,
    endpoint_id: str,
    operation_type: str,
    coin: str | None,
    candle_interval: str | None,
    capture_mode: str,
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
) -> str:
    material = canonical_json_bytes(
        {
            "slot_version": OBSERVATION_SLOT_VERSION,
            **_selection_material(
                source_catalog_version=source_catalog_version,
                source_catalog_hash=source_catalog_hash,
                catalog_entry_hash_value=catalog_entry_hash_value,
                source_id=source_id,
                endpoint_id=endpoint_id,
                operation_type=operation_type,
                coin=coin,
                candle_interval=candle_interval,
                capture_mode=capture_mode,
                connection_id=connection_id,
                subscription_id=subscription_id,
                receive_sequence=receive_sequence,
            ),
        }
    )
    return sha256_hex(OBSERVATION_SLOT_VERSION.encode() + b"\0" + material)


def compute_raw_observation_id(
    *,
    source_catalog_version: str,
    source_catalog_hash: str,
    catalog_entry_hash_value: str,
    source_id: str,
    endpoint_id: str,
    operation_type: str,
    coin: str | None,
    candle_interval: str | None,
    capture_mode: str,
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
    payload_sha256: str,
) -> str:
    material = canonical_json_bytes(
        {
            "identity_version": RAW_IDENTITY_VERSION,
            **_selection_material(
                source_catalog_version=source_catalog_version,
                source_catalog_hash=source_catalog_hash,
                catalog_entry_hash_value=catalog_entry_hash_value,
                source_id=source_id,
                endpoint_id=endpoint_id,
                operation_type=operation_type,
                coin=coin,
                candle_interval=candle_interval,
                capture_mode=capture_mode,
                connection_id=connection_id,
                subscription_id=subscription_id,
                receive_sequence=receive_sequence,
            ),
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
    schema_version: Literal["0.1.0"] = "0.1.0"
    source_event_id: Sha256Hex
    observation_slot_id: Sha256Hex
    source_id: Literal["hyperliquid-public-mainnet"] = "hyperliquid-public-mainnet"
    source_catalog_version: Literal["hyperliquid-public-mainnet.0.1.0"] = (
        "hyperliquid-public-mainnet.0.1.0"
    )
    source_catalog_hash: Literal[
        "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
    ] = "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
    catalog_entry_hash: Sha256Hex
    endpoint_id: OpaqueId
    operation_type: OpaqueId
    coin: Literal["BTC", "ETH"] | None
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"] | None
    capture_mode: RawCaptureModeV0
    connection_id: OpaqueId
    subscription_id: OpaqueId
    receive_sequence: int = Field(ge=0)
    source_native_id: Literal[None] = None
    source_native_cursor: Literal[None] = None
    collector_version: str = Field(min_length=1, max_length=80)
    environment: Literal[EnvironmentV0.READ_ONLY]
    content_type: str = Field(min_length=1, max_length=120)
    payload_sha256: Sha256Hex
    payload_size_bytes: int = Field(ge=0)
    payload_encoding: str = Field(min_length=1, max_length=40)
    payload_ref: str = Field(min_length=1, max_length=500)
    source_event_time: Literal[None] = None
    source_publish_time: Literal[None] = None
    first_observed_time: UTCDateTime
    collector_receive_time: UTCDateTime
    collector_monotonic_ns: int = Field(ge=0)
    revision_time: Literal[None] = None

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
        entry = validate_public_selection(
            self.endpoint_id,
            self.operation_type,
            coin=self.coin,
            interval=self.candle_interval,
        )
        if get_entry(self.endpoint_id, self.operation_type) is not entry:
            raise ValueError("source catalog selection is not canonical")
        expected_entry_hash = catalog_entry_hash(entry)
        if not hmac.compare_digest(self.catalog_entry_hash, expected_entry_hash):
            raise ValueError("catalog_entry_hash does not match selected source catalog entry")
        expected_mode = (
            RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD
            if endpoint_kind(self.endpoint_id) == "WEBSOCKET"
            else RawCaptureModeV0.HTTP_RESPONSE_BODY
        )
        if self.capture_mode is not expected_mode:
            raise ValueError("capture_mode does not match source endpoint kind")
        match = _PAYLOAD_REF_RE.fullmatch(self.payload_ref)
        if match is None:
            raise ValueError("payload_ref must use the content-addressed payload layout")
        if match.group("digest") != self.payload_sha256:
            raise ValueError("payload_ref digest must equal payload_sha256")
        if match.group("prefix") != self.payload_sha256[:2]:
            raise ValueError("payload_ref prefix must match payload_sha256")
        expected_slot = compute_observation_slot_id(
            source_catalog_version=self.source_catalog_version,
            source_catalog_hash=self.source_catalog_hash,
            catalog_entry_hash_value=self.catalog_entry_hash,
            source_id=self.source_id,
            endpoint_id=self.endpoint_id,
            operation_type=self.operation_type,
            coin=self.coin,
            candle_interval=self.candle_interval,
            capture_mode=self.capture_mode.value,
            connection_id=self.connection_id,
            subscription_id=self.subscription_id,
            receive_sequence=self.receive_sequence,
        )
        if not hmac.compare_digest(self.observation_slot_id, expected_slot):
            raise ValueError("observation_slot_id does not match catalog-bound receive identity")
        expected = compute_raw_observation_id(
            source_catalog_version=self.source_catalog_version,
            source_catalog_hash=self.source_catalog_hash,
            catalog_entry_hash_value=self.catalog_entry_hash,
            source_id=self.source_id,
            endpoint_id=self.endpoint_id,
            operation_type=self.operation_type,
            coin=self.coin,
            candle_interval=self.candle_interval,
            capture_mode=self.capture_mode.value,
            connection_id=self.connection_id,
            subscription_id=self.subscription_id,
            receive_sequence=self.receive_sequence,
            payload_sha256=self.payload_sha256,
        )
        if not hmac.compare_digest(self.source_event_id, expected):
            raise ValueError("source_event_id does not match catalog-bound raw identity")
        return self

    @classmethod
    def bind_observation(cls, **payload: Any) -> RawEventV0:
        forbidden = {
            "schema_version",
            "source_event_id",
            "observation_slot_id",
            "source_id",
            "source_catalog_version",
            "source_catalog_hash",
            "catalog_entry_hash",
        }
        supplied = forbidden.intersection(payload)
        if supplied:
            raise ValueError(
                "authority fields must not be supplied to bind_observation(): "
                + ", ".join(sorted(supplied))
            )
        endpoint_id = str(payload["endpoint_id"])
        operation_type = str(payload["operation_type"])
        coin = payload.get("coin")
        candle_interval = payload.get("candle_interval")
        entry = validate_public_selection(
            endpoint_id,
            operation_type,
            coin=coin,
            interval=candle_interval,
        )
        expected_mode = (
            RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD
            if entry.endpoint_kind == "WEBSOCKET"
            else RawCaptureModeV0.HTTP_RESPONSE_BODY
        )
        provided_mode = RawCaptureModeV0(payload["capture_mode"])
        if provided_mode is not expected_mode:
            raise ValueError("capture_mode does not match source endpoint kind")
        entry_hash = catalog_entry_hash(entry)
        fixed = {
            "schema_version": A0_SCHEMA_VERSION,
            "source_id": SOURCE_ID,
            "source_catalog_version": SOURCE_CATALOG_VERSION,
            "source_catalog_hash": SOURCE_CATALOG_HASH,
            "catalog_entry_hash": entry_hash,
        }
        slot = compute_observation_slot_id(
            source_catalog_version=SOURCE_CATALOG_VERSION,
            source_catalog_hash=SOURCE_CATALOG_HASH,
            catalog_entry_hash_value=entry_hash,
            source_id=SOURCE_ID,
            endpoint_id=endpoint_id,
            operation_type=operation_type,
            coin=coin,
            candle_interval=candle_interval,
            capture_mode=provided_mode.value,
            connection_id=str(payload["connection_id"]),
            subscription_id=str(payload["subscription_id"]),
            receive_sequence=int(payload["receive_sequence"]),
        )
        identity = compute_raw_observation_id(
            source_catalog_version=SOURCE_CATALOG_VERSION,
            source_catalog_hash=SOURCE_CATALOG_HASH,
            catalog_entry_hash_value=entry_hash,
            source_id=SOURCE_ID,
            endpoint_id=endpoint_id,
            operation_type=operation_type,
            coin=coin,
            candle_interval=candle_interval,
            capture_mode=provided_mode.value,
            connection_id=str(payload["connection_id"]),
            subscription_id=str(payload["subscription_id"]),
            receive_sequence=int(payload["receive_sequence"]),
            payload_sha256=str(payload["payload_sha256"]),
        )
        return cls.model_validate(
            {
                **payload,
                **fixed,
                "observation_slot_id": slot,
                "source_event_id": identity,
            }
        )


def _revalidate_exact[T: BaseModel](value: Any, expected_type: type[T]) -> T:
    if isinstance(value, BaseModel):
        if type(value) is not expected_type:
            raise ValueError(f"expected exact {expected_type.__name__} authority object")
        value = BaseModel.model_dump(value, mode="python", round_trip=True)
    validated = expected_type.model_validate(value)
    if type(validated) is not expected_type:
        raise ValueError(f"expected exact {expected_type.__name__} authority object")
    return validated


class RawManifestEntryV0(_A0AuthorityModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    manifest_format_version: Literal["0.1.0"] = "0.1.0"
    hash_chain_version: Literal["trader-assist-v0/raw-manifest-entry/v1"] = (
        "trader-assist-v0/raw-manifest-entry/v1"
    )
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
        if self.entry_index == 0 and self.previous_entry_hash != MANIFEST_GENESIS_HASH:
            raise ValueError("first manifest entry must use the genesis previous hash")
        if self.entry_index > 0 and self.previous_entry_hash == MANIFEST_GENESIS_HASH:
            raise ValueError("non-first manifest entry cannot use the genesis previous hash")
        expected = compute_manifest_entry_hash(
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
        segment_id: str,
        entry_index: int,
        previous_entry_hash: str,
        raw_event: RawEventV0,
        **forbidden_versions: Any,
    ) -> RawManifestEntryV0:
        if forbidden_versions:
            raise ValueError("manifest authority versions are implementation-controlled")
        exact_event = _revalidate_exact(raw_event, RawEventV0)
        digest = compute_manifest_entry_hash(
            segment_id=segment_id,
            entry_index=entry_index,
            previous_entry_hash=previous_entry_hash,
            raw_event=exact_event,
        )
        return cls.model_validate(
            {
                "schema_version": A0_SCHEMA_VERSION,
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
    segment_id: str,
    entry_index: int,
    previous_entry_hash: str,
    raw_event: RawEventV0,
) -> str:
    exact_event = _revalidate_exact(raw_event, RawEventV0)
    material = canonical_json_bytes(
        {
            "schema_version": A0_SCHEMA_VERSION,
            "manifest_format_version": MANIFEST_FORMAT_VERSION,
            "hash_chain_version": MANIFEST_HASH_CHAIN_VERSION,
            "segment_id": segment_id,
            "entry_index": entry_index,
            "previous_entry_hash": previous_entry_hash,
            "raw_event": BaseModel.model_dump(exact_event, mode="python", round_trip=True),
        }
    )
    return sha256_hex(MANIFEST_HASH_CHAIN_VERSION.encode() + b"\0" + material)


class RawManifestCheckpointV0(_A0AuthorityModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    checkpoint_version: Literal["0.1.0"] = "0.1.0"
    manifest_date: date
    segment_id: OpaqueId
    source_catalog_version: Literal["hyperliquid-public-mainnet.0.1.0"] = (
        "hyperliquid-public-mainnet.0.1.0"
    )
    expected_entry_count: int = Field(ge=0)
    terminal_entry_hash: Sha256Hex
    completed: Literal[True] = True
    checkpoint_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_checkpoint(self) -> Self:
        if type(self) is not RawManifestCheckpointV0:
            raise ValueError("expected exact RawManifestCheckpointV0 authority object")
        if self.expected_entry_count == 0:
            if self.terminal_entry_hash != MANIFEST_GENESIS_HASH:
                raise ValueError("zero-entry checkpoint must use the genesis terminal hash")
        elif self.terminal_entry_hash == MANIFEST_GENESIS_HASH:
            raise ValueError("non-empty checkpoint cannot use the genesis terminal hash")
        expected = compute_manifest_checkpoint_hash_from_payload(
            {
                "schema_version": self.schema_version,
                "checkpoint_version": self.checkpoint_version,
                "manifest_date": self.manifest_date,
                "segment_id": self.segment_id,
                "source_catalog_version": self.source_catalog_version,
                "expected_entry_count": self.expected_entry_count,
                "terminal_entry_hash": self.terminal_entry_hash,
                "completed": self.completed,
            }
        )
        if not hmac.compare_digest(self.checkpoint_hash, expected):
            raise ValueError("checkpoint_hash does not match canonical checkpoint")
        return self

    @classmethod
    def bind(
        cls,
        *,
        manifest_date: date,
        segment_id: str,
        expected_entry_count: int,
        terminal_entry_hash: str,
        **forbidden_authority: Any,
    ) -> RawManifestCheckpointV0:
        if forbidden_authority:
            raise ValueError("checkpoint authority fields are implementation-controlled")
        payload = {
            "schema_version": A0_SCHEMA_VERSION,
            "checkpoint_version": MANIFEST_CHECKPOINT_VERSION,
            "manifest_date": manifest_date,
            "segment_id": segment_id,
            "source_catalog_version": SOURCE_CATALOG_VERSION,
            "expected_entry_count": expected_entry_count,
            "terminal_entry_hash": terminal_entry_hash,
            "completed": True,
        }
        return cls.model_validate(
            {**payload, "checkpoint_hash": compute_manifest_checkpoint_hash_from_payload(payload)}
        )


def compute_manifest_checkpoint_hash_from_payload(payload: Mapping[str, Any]) -> str:
    normalized = dict(payload)
    manifest_date = normalized.get("manifest_date")
    if isinstance(manifest_date, date):
        normalized["manifest_date"] = manifest_date.isoformat()
    return sha256_hex(
        MANIFEST_CHECKPOINT_HASH_VERSION.encode()
        + b"\0"
        + canonical_json_bytes(normalized)
    )


def compute_manifest_checkpoint_hash(checkpoint: RawManifestCheckpointV0) -> str:
    payload = BaseModel.model_dump(checkpoint, mode="python", round_trip=True)
    payload.pop("checkpoint_hash", None)
    return compute_manifest_checkpoint_hash_from_payload(payload)


class BronzeReplayReportV0(_A0AuthorityModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    replay_report_version: Literal["0.1.0"] = "0.1.0"
    manifest_segment_id: OpaqueId
    source_catalog_version: Literal["hyperliquid-public-mainnet.0.1.0"] = (
        "hyperliquid-public-mainnet.0.1.0"
    )
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
        forbidden = {
            "schema_version",
            "replay_report_version",
            "source_catalog_version",
            "report_hash",
        }
        supplied = forbidden.intersection(payload)
        if supplied:
            raise ValueError(
                "report authority fields must not be supplied to bind(): "
                + ", ".join(sorted(supplied))
            )
        normalized = {
            **payload,
            "schema_version": A0_SCHEMA_VERSION,
            "replay_report_version": REPLAY_REPORT_VERSION,
            "source_catalog_version": SOURCE_CATALOG_VERSION,
        }
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
