from __future__ import annotations

import hmac
import json
from collections.abc import Mapping, Set
from typing import Annotated, Any, ClassVar, Final, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    StrictInt,
    StrictStr,
    ValidationInfo,
    model_validator,
)
from pydantic.config import ExtraValues

from .common import Sha256Hex, canonical_json_bytes, sha256_hex

CAPTURE_SCHEMA_VERSION: Final[Literal["0.1.0"]] = "0.1.0"
CAPTURE_CONTRACT_VERSION: Final[Literal["trader-assist-v0/capture-now-authority/v1"]] = (
    "trader-assist-v0/capture-now-authority/v1"
)
CAPTURE_PLANE_ID: Final[Literal["CAPTURE_AUTHORITY"]] = "CAPTURE_AUTHORITY"
CAPTURE_ENVIRONMENT: Final[Literal["READ_ONLY"]] = "READ_ONLY"

CAPTURE_SOURCE_CATALOG_VERSION: Final[Literal["hyperliquid-public-mainnet.0.1.0"]] = (
    "hyperliquid-public-mainnet.0.1.0"
)
CAPTURE_SOURCE_CATALOG_HASH: Final[
    Literal["0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"]
] = (
    "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
)


RefId = Annotated[StrictStr, Field(min_length=1, max_length=160)]
BoundedText = Annotated[StrictStr, Field(min_length=1, max_length=800)]


def _freeze_json_arrays(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze_json_arrays(item) for item in value)
    if isinstance(value, dict):
        return {key: _freeze_json_arrays(item) for key, item in value.items()}
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_non_finite(token: str) -> None:
    raise ValueError(f"non-finite JSON number is prohibited: {token}")


def _canonical_json_input(json_data: str | bytes | bytearray) -> Any:
    if isinstance(json_data, bytearray):
        json_data = bytes(json_data)
    if isinstance(json_data, bytes):
        raw_bytes = json_data
        text = json_data.decode("utf-8", errors="strict")
    elif type(json_data) is str:
        text = json_data
        raw_bytes = text.encode("utf-8")
    else:
        raise TypeError("Capture JSON input must be exact text or bytes")
    decoded = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_non_finite,
    )
    if raw_bytes != canonical_json_bytes(decoded):
        raise ValueError("Capture JSON bytes must be canonical")
    return _freeze_json_arrays(decoded)


def _ordered_unique(values: tuple[str, ...], field_name: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicate references")
    if tuple(sorted(values)) != values:
        raise ValueError(f"{field_name} must be ordered")


def _hash_material(domain: str, payload: Mapping[str, Any]) -> str:
    return sha256_hex(domain.encode("utf-8") + b"\0" + canonical_json_bytes(dict(payload)))


def _payload_with_model_defaults(
    model_type: type[BaseModel],
    payload: Mapping[str, Any],
    excluded_fields: set[str],
) -> dict[str, Any]:
    material: dict[str, Any] = {}
    for field_name, field_info in model_type.model_fields.items():
        if field_name in excluded_fields:
            continue
        if field_name in payload:
            material[field_name] = payload[field_name]
        elif not field_info.is_required():
            material[field_name] = field_info.get_default(call_default_factory=True)
    return material


class _CaptureAuthorityModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
        allow_inf_nan=False,
        str_strip_whitespace=False,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_capture_input(cls, value: Any, info: ValidationInfo) -> Any:
        if info.mode != "python":
            raise ValueError("Capture core JSON validation is unsupported; use model_validate_json")
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise ValueError(f"expected exact {cls.__name__} Capture authority object")
            value = BaseModel.model_dump(value, mode="python", round_trip=True)
        if not isinstance(value, Mapping):
            raise TypeError("Capture authority input must be an exact mapping")
        extras = set(value).difference(cls.model_fields)
        if extras:
            raise ValueError("Capture authority input contains extra fields")
        return value

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
        if strict is not None and strict is not True:
            raise TypeError("Capture validation is permanently strict")
        if extra not in (None, "forbid"):
            raise TypeError("Capture validation permanently forbids extras")
        if from_attributes is not None and from_attributes is not False:
            raise TypeError("Capture validation forbids from_attributes")
        return super().model_validate(
            obj,
            strict=True,
            extra="forbid",
            from_attributes=False,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if strict is not None and strict is not True:
            raise TypeError("Capture JSON validation is permanently strict")
        if extra not in (None, "forbid"):
            raise TypeError("Capture JSON validation permanently forbids extras")
        return cls.model_validate(
            _canonical_json_input(json_data),
            strict=True,
            extra="forbid",
            from_attributes=False,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_strings(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        raise TypeError("Capture string validation is unsupported")

    @classmethod
    def model_construct(cls, _fields_set: set[str] | None = None, **values: Any) -> Self:
        raise TypeError("Capture authority models cannot bypass validation")

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        raise TypeError("Capture authority models cannot be copied")

    def copy(
        self,
        *,
        include: Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None = None,
        exclude: Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None = None,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        raise TypeError("Capture authority models cannot be copied")


class _HashBoundCaptureModel(_CaptureAuthorityModel):
    hash_field: ClassVar[str]
    hash_domain: ClassVar[str]

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        model_type = type(self)
        actual = object.__getattribute__(self, model_type.hash_field)
        payload = BaseModel.model_dump(self, mode="python", round_trip=True)
        payload.pop(model_type.hash_field, None)
        expected = _hash_material(model_type.hash_domain, payload)
        if not hmac.compare_digest(actual, expected):
            raise ValueError(f"{model_type.hash_field} does not match Capture authority")
        return self

    @classmethod
    def bind(cls, **payload: Any) -> Self:
        if cls.hash_field in payload:
            raise ValueError(f"{cls.hash_field} is binder-controlled")
        material = _payload_with_model_defaults(cls, payload, {cls.hash_field})
        digest = _hash_material(cls.hash_domain, material)
        return cls.model_validate({**material, cls.hash_field: digest})


class _CaptureRecordModel(_CaptureAuthorityModel):
    record_id: Sha256Hex
    record_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_record_identity(self) -> Self:
        payload = BaseModel.model_dump(self, mode="python", round_trip=True)
        actual_id = payload.pop("record_id")
        actual_hash = payload.pop("record_hash")
        record_type = payload.get("record_type")
        if type(record_type) is not str:
            raise ValueError("record_type must be bound before record identity")
        expected_id = _hash_material(
            f"{CAPTURE_CONTRACT_VERSION}/record-id/{record_type}",
            payload,
        )
        if not hmac.compare_digest(actual_id, expected_id):
            raise ValueError("record_id does not match Capture authority")
        expected_hash = _hash_material(
            f"{CAPTURE_CONTRACT_VERSION}/record-hash/{record_type}",
            {**payload, "record_id": actual_id},
        )
        if not hmac.compare_digest(actual_hash, expected_hash):
            raise ValueError("record_hash does not match Capture authority")
        return self

    @classmethod
    def bind(cls, **payload: Any) -> Self:
        if "record_id" in payload or "record_hash" in payload:
            raise ValueError("record identity and hash are binder-controlled")
        material = _payload_with_model_defaults(cls, payload, {"record_id", "record_hash"})
        record_type = material.get("record_type")
        if type(record_type) is not str:
            record_type = cls.model_fields["record_type"].default
        if type(record_type) is not str:
            raise ValueError("record_type is required before binding")
        record_id = _hash_material(f"{CAPTURE_CONTRACT_VERSION}/record-id/{record_type}", material)
        record_hash = _hash_material(
            f"{CAPTURE_CONTRACT_VERSION}/record-hash/{record_type}",
            {**material, "record_id": record_id},
        )
        return cls.model_validate({**material, "record_id": record_id, "record_hash": record_hash})


class ProducerIdentityV0(_HashBoundCaptureModel):
    hash_field: ClassVar[str] = "identity_hash"
    hash_domain: ClassVar[str] = f"{CAPTURE_CONTRACT_VERSION}/producer-identity"

    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    identity_domain: Literal[
        "SIGNAL_PLAN_SHADOW_PRODUCER",
        "MARKET_PATH_SOURCE",
        "HUMAN_OPERATOR",
        "RUNTIME_CONTROL_ACTOR",
    ]
    producer_id: RefId
    display_name: BoundedText
    identity_hash: Sha256Hex


class SignalCaptureV0(_CaptureRecordModel):
    record_type: Literal["SIGNAL_CAPTURE"] = "SIGNAL_CAPTURE"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    producer_identity: ProducerIdentityV0
    signal_kind: Literal["LONG", "SHORT", "WAIT"]
    observed_at_utc: RefId
    evidence_refs: tuple[RefId, ...] = ()
    plan_record_refs: tuple[RefId, ...] = ()
    shadow_intent_refs: tuple[RefId, ...] = ()
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_signal(self) -> Self:
        if self.producer_identity.identity_domain != "SIGNAL_PLAN_SHADOW_PRODUCER":
            raise ValueError("signals require producer_identity")
        for field_name in ("evidence_refs", "plan_record_refs", "shadow_intent_refs"):
            _ordered_unique(object.__getattribute__(self, field_name), field_name)
        if self.signal_kind == "WAIT":
            if len(self.plan_record_refs) > 1:
                raise ValueError("WAIT allows at most one non-actionable CapturePlan")
            if self.shadow_intent_refs:
                raise ValueError("WAIT must not reference ShadowOrderIntent")
        return self


class CapturePlanV0(_CaptureRecordModel):
    record_type: Literal["CAPTURE_PLAN"] = "CAPTURE_PLAN"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    producer_identity: ProducerIdentityV0
    signal_record_ref: RefId
    signal_kind: Literal["LONG", "SHORT", "WAIT"]
    actionable: Literal[False] = False
    executable: Literal[False] = False
    exchange_submission_authorized: Literal[False] = False
    minimal_evidence_summary: BoundedText
    non_actionable_plan_label: Literal["CAPTURE_ONLY_NOT_TRADE_PLAN"] = (
        "CAPTURE_ONLY_NOT_TRADE_PLAN"
    )
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if self.producer_identity.identity_domain != "SIGNAL_PLAN_SHADOW_PRODUCER":
            raise ValueError("plans require producer_identity")
        return self


class ShadowOrderIntentV0(_CaptureRecordModel):
    record_type: Literal["SHADOW_ORDER_INTENT"] = "SHADOW_ORDER_INTENT"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    producer_identity: ProducerIdentityV0
    plan_record_ref: RefId
    shadow_only: Literal[True] = True
    executable: Literal[False] = False
    exchange_submission_authorized: Literal[False] = False
    intent_summary: BoundedText
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_shadow(self) -> Self:
        if self.producer_identity.identity_domain != "SIGNAL_PLAN_SHADOW_PRODUCER":
            raise ValueError("shadow intents require producer_identity")
        return self


class HumanObservationV0(_CaptureRecordModel):
    record_type: Literal["HUMAN_OBSERVATION"] = "HUMAN_OBSERVATION"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    operator_identity: ProducerIdentityV0
    observed_record_refs: tuple[RefId, ...] = Field(min_length=1)
    observation_kind: Literal["TAKEN", "SKIPPED", "REJECTED", "NOTE"]
    observation_text: BoundedText
    append_only: Literal[True] = True
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_human_observation(self) -> Self:
        if self.operator_identity.identity_domain != "HUMAN_OPERATOR":
            raise ValueError("human observations require operator_identity")
        _ordered_unique(self.observed_record_refs, "observed_record_refs")
        return self


class MarketPathEvidenceV0(_CaptureRecordModel):
    record_type: Literal["MARKET_PATH_EVIDENCE"] = "MARKET_PATH_EVIDENCE"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    source_identity: ProducerIdentityV0
    source_record_refs: tuple[RefId, ...] = Field(min_length=1)
    window_start_ms: StrictInt = Field(ge=0)
    window_end_ms: StrictInt = Field(ge=0)
    finalized_append_only_window: Literal[True] = True
    chunk_sequence: StrictInt = Field(ge=0)
    missing_ranges_ms: tuple[tuple[StrictInt, StrictInt], ...] = ()
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_market_path(self) -> Self:
        if self.source_identity.identity_domain != "MARKET_PATH_SOURCE":
            raise ValueError("market path evidence requires source_identity")
        if self.window_start_ms >= self.window_end_ms:
            raise ValueError("window_start_ms must be before window_end_ms")
        _ordered_unique(self.source_record_refs, "source_record_refs")
        previous_end: int | None = None
        for start, end in self.missing_ranges_ms:
            if type(start) is not int or type(end) is not int:
                raise TypeError("missing ranges must use exact integer endpoints")
            if start >= end:
                raise ValueError("missing range start must be before end")
            if start < self.window_start_ms or end > self.window_end_ms:
                raise ValueError("missing ranges must stay inside the finalized window")
            if previous_end is not None and start < previous_end:
                raise ValueError("missing ranges must be ordered and non-overlapping")
            previous_end = end
        return self


class CaptureLifecycleEventV0(_CaptureRecordModel):
    record_type: Literal["CAPTURE_LIFECYCLE_EVENT"] = "CAPTURE_LIFECYCLE_EVENT"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    producer_identity: ProducerIdentityV0
    event_kind: Literal[
        "CAPTURE_RECORD_CREATED",
        "CAPTURE_RECORD_CORRECTED",
        "CAPTURE_RECORD_SUPERSEDED",
        "CAPTURE_WINDOW_FINALIZED",
    ]
    subject_record_ref: RefId
    reference_record_refs: tuple[RefId, ...] = ()
    transition_authorized: Literal["APPEND_ONLY_CAPTURE_METADATA"] = (
        "APPEND_ONLY_CAPTURE_METADATA"
    )
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.producer_identity.identity_domain != "SIGNAL_PLAN_SHADOW_PRODUCER":
            raise ValueError("lifecycle events require capture producer identity")
        _ordered_unique(self.reference_record_refs, "reference_record_refs")
        return self


class RuntimeControlEventV0(_CaptureRecordModel):
    record_type: Literal["RUNTIME_CONTROL_EVENT"] = "RUNTIME_CONTROL_EVENT"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    supervisor_or_runtime_actor_identity: ProducerIdentityV0
    event_kind: Literal[
        "START_PERMIT_ISSUED",
        "KILL_ENGAGED",
        "RESUME_PERMIT_ISSUED",
        "INTEGRITY_CHECK_COMPLETED",
    ]
    subject_runtime_ref: RefId
    single_use_permit_ref: RefId | None = None
    integrity_check_ref: RefId | None = None
    kill_state_ref: RefId | None = None
    fail_closed: Literal[True] = True
    runtime_authorized: Literal[False] = False
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_runtime_control(self) -> Self:
        if self.supervisor_or_runtime_actor_identity.identity_domain != "RUNTIME_CONTROL_ACTOR":
            raise ValueError("runtime control requires supervisor_or_runtime_actor_identity")
        if self.event_kind == "RESUME_PERMIT_ISSUED" and (
            self.single_use_permit_ref is None or self.integrity_check_ref is None
        ):
            raise ValueError("resume requires permit and integrity references")
        return self


class CaptureKillStateV0(_CaptureRecordModel):
    record_type: Literal["CAPTURE_KILL_STATE"] = "CAPTURE_KILL_STATE"
    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    environment: Literal["READ_ONLY"] = CAPTURE_ENVIRONMENT
    supervisor_or_runtime_actor_identity: ProducerIdentityV0
    kill_state: Literal[
        "KILLED_FAIL_CLOSED",
        "RESUME_BLOCKED_PENDING_PERMIT",
        "RESUME_PERMITTED_AFTER_INTEGRITY_CHECK",
    ]
    fail_closed: Literal[True] = True
    runtime_authorized: Literal[False] = False
    resume_requires_single_use_permit: Literal[True] = True
    resume_requires_integrity_check: Literal[True] = True
    resume_requires_runtime_control_event: Literal[True] = True
    single_use_permit_ref: RefId | None = None
    integrity_check_ref: RefId | None = None
    runtime_control_event_ref: RefId | None = None
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_kill_state(self) -> Self:
        if self.supervisor_or_runtime_actor_identity.identity_domain != "RUNTIME_CONTROL_ACTOR":
            raise ValueError("kill state requires supervisor_or_runtime_actor_identity")
        if self.kill_state == "RESUME_PERMITTED_AFTER_INTEGRITY_CHECK" and (
            self.single_use_permit_ref is None
            or self.integrity_check_ref is None
            or self.runtime_control_event_ref is None
        ):
            raise ValueError("resume requires permit, integrity, and runtime-control references")
        return self


class CaptureManifestEntryV0(_HashBoundCaptureModel):
    hash_field: ClassVar[str] = "manifest_entry_hash"
    hash_domain: ClassVar[str] = f"{CAPTURE_CONTRACT_VERSION}/manifest-entry"

    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    entry_index: StrictInt = Field(ge=0)
    record_ref: RefId
    record_hash: Sha256Hex
    previous_manifest_entry_hash: Sha256Hex | None
    io_authorized: Literal[False] = False
    manifest_entry_hash: Sha256Hex


class CaptureCheckpointV0(_HashBoundCaptureModel):
    hash_field: ClassVar[str] = "checkpoint_hash"
    hash_domain: ClassVar[str] = f"{CAPTURE_CONTRACT_VERSION}/checkpoint"

    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    checkpoint_kind: Literal["CAPTURE_INTEGRITY_ONLY"] = "CAPTURE_INTEGRITY_ONLY"
    terminal_manifest_entry_hash: Sha256Hex
    record_count: StrictInt = Field(ge=0)
    finalized: Literal[True] = True
    io_authorized: Literal[False] = False
    checkpoint_hash: Sha256Hex


class CaptureReplayReportV0(_HashBoundCaptureModel):
    hash_field: ClassVar[str] = "replay_report_hash"
    hash_domain: ClassVar[str] = f"{CAPTURE_CONTRACT_VERSION}/replay-report"

    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    checkpoint_hash: Sha256Hex
    replay_status: Literal["PASS", "FAIL"]
    verified_record_count: StrictInt = Field(ge=0)
    performance_adjudication_authorized: Literal[False] = False
    promotion_judgment_authorized: Literal[False] = False
    replay_report_hash: Sha256Hex


class CaptureLocalSafetyPolicyV0(_HashBoundCaptureModel):
    hash_field: ClassVar[str] = "policy_hash"
    hash_domain: ClassVar[str] = f"{CAPTURE_CONTRACT_VERSION}/local-safety-policy"

    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    policy_kind: Literal["LOCAL_SAFETY_POLICY_NOT_OFFICIAL_FACT"] = (
        "LOCAL_SAFETY_POLICY_NOT_OFFICIAL_FACT"
    )
    max_active_ws_connections: Literal[1] = 1
    connection_attempts_per_start_permit: Literal[1] = 1
    start_permit_manual: Literal[True] = True
    start_permit_single_use: Literal[True] = True
    start_permit_durable: Literal[True] = True
    start_permit_non_replayable: Literal[True] = True
    automatic_reconnect: Literal[False] = False
    automatic_backfill: Literal[False] = False
    active_network_probes: Literal[False] = False
    info_http_requests: Literal[False] = False
    runtime_authorized: Literal[False] = False
    official_hyperliquid_fact: Literal[False] = False
    policy_hash: Sha256Hex


class CaptureEndpointAllowlistV0(_HashBoundCaptureModel):
    hash_field: ClassVar[str] = "allowlist_hash"
    hash_domain: ClassVar[str] = f"{CAPTURE_CONTRACT_VERSION}/endpoint-allowlist"

    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    source_catalog_version: Literal["hyperliquid-public-mainnet.0.1.0"] = (
        CAPTURE_SOURCE_CATALOG_VERSION
    )
    source_catalog_hash: Literal[
        "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
    ] = CAPTURE_SOURCE_CATALOG_HASH
    source: Literal["hyperliquid-public-mainnet"] = "hyperliquid-public-mainnet"
    endpoint: Literal["hl-ws-mainnet-public"] = "hl-ws-mainnet-public"
    endpoint_kind: Literal["WEBSOCKET"] = "WEBSOCKET"
    operation_class: Literal["public read-only observation only"] = (
        "public read-only observation only"
    )
    operation: Literal["candle"] = "candle"
    coin: Literal["ETH"] = "ETH"
    intervals: tuple[Literal["5m"], Literal["15m"]] = ("5m", "15m")
    capture_mode: Literal["WS_TEXT_UTF8_APPLICATION_PAYLOAD"] = (
        "WS_TEXT_UTF8_APPLICATION_PAYLOAD"
    )
    allowlist_status: Literal["RATIFIED_CONTRACT_ONLY"] = "RATIFIED_CONTRACT_ONLY"
    runtime_authorized: Literal[False] = False
    allowlist_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_allowlist(self) -> Self:
        if self.intervals != ("5m", "15m"):
            raise ValueError("Capture endpoint allowlist is exactly ETH 5m and 15m")
        return self


CaptureRecordUnion = Annotated[
    SignalCaptureV0
    | CapturePlanV0
    | ShadowOrderIntentV0
    | HumanObservationV0
    | MarketPathEvidenceV0
    | CaptureLifecycleEventV0
    | RuntimeControlEventV0
    | CaptureKillStateV0,
    Field(discriminator="record_type"),
]


class CaptureRecordV0(RootModel[CaptureRecordUnion]):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        allow_inf_nan=False,
    )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if strict is not None and strict is not True:
            raise TypeError("CaptureRecord JSON validation is permanently strict")
        if extra not in (None, "forbid"):
            raise TypeError("CaptureRecord JSON validation permanently forbids extras")
        return cls.model_validate(
            _canonical_json_input(json_data),
            strict=True,
            extra="forbid",
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_construct(  # type: ignore[override]
        cls,
        root: CaptureRecordUnion,
        _fields_set: set[str] | None = None,
    ) -> Self:
        raise TypeError("CaptureRecordV0 cannot bypass validation")

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        raise TypeError("CaptureRecordV0 cannot be copied")
