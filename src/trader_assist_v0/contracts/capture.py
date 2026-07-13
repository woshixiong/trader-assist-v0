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
    record_id_excluded_fields: ClassVar[frozenset[str]] = frozenset()

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
        record_id_payload = {
            key: value
            for key, value in payload.items()
            if key not in type(self).record_id_excluded_fields
        }
        expected_id = _hash_material(
            f"{CAPTURE_CONTRACT_VERSION}/record-id/{record_type}",
            record_id_payload,
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
        record_id_material = {
            key: value
            for key, value in material.items()
            if key not in cls.record_id_excluded_fields
        }
        record_id = _hash_material(
            f"{CAPTURE_CONTRACT_VERSION}/record-id/{record_type}",
            record_id_material,
        )
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
    record_id_excluded_fields: ClassVar[frozenset[str]] = frozenset(
        {"plan_record_refs", "shadow_intent_refs"}
    )

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
    evidence_refs: tuple[RefId, ...] = Field(min_length=1)
    non_actionable_plan_label: Literal["CAPTURE_ONLY_NOT_TRADE_PLAN"] = (
        "CAPTURE_ONLY_NOT_TRADE_PLAN"
    )
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if self.producer_identity.identity_domain != "SIGNAL_PLAN_SHADOW_PRODUCER":
            raise ValueError("plans require producer_identity")
        _ordered_unique(self.evidence_refs, "evidence_refs")
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
    hypothesis_kind: Literal["NON_EXECUTABLE_MARKET_PATH_HYPOTHESIS"] = (
        "NON_EXECUTABLE_MARKET_PATH_HYPOTHESIS"
    )
    evidence_refs: tuple[RefId, ...] = Field(min_length=1)
    shadow_only: Literal[True] = True
    executable: Literal[False] = False
    exchange_submission_authorized: Literal[False] = False
    correction_of_record_id: RefId | None = None
    supersedes_record_id: RefId | None = None

    @model_validator(mode="after")
    def validate_shadow(self) -> Self:
        if self.producer_identity.identity_domain != "SIGNAL_PLAN_SHADOW_PRODUCER":
            raise ValueError("shadow intents require producer_identity")
        _ordered_unique(self.evidence_refs, "evidence_refs")
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
    market_path_series_ref: RefId
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
    subject_record_type: Literal[
        "SIGNAL_CAPTURE",
        "CAPTURE_PLAN",
        "SHADOW_ORDER_INTENT",
        "HUMAN_OBSERVATION",
        "MARKET_PATH_EVIDENCE",
    ]
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
        if self.event_kind == "CAPTURE_RECORD_CREATED":
            if self.correction_of_record_id is not None or self.supersedes_record_id is not None:
                raise ValueError("created lifecycle events cannot correct or supersede")
            if self.reference_record_refs:
                raise ValueError("created lifecycle events cannot carry references")
        elif self.event_kind == "CAPTURE_RECORD_CORRECTED":
            if self.correction_of_record_id is None or self.supersedes_record_id is not None:
                raise ValueError("corrected lifecycle events require only correction target")
            if self.reference_record_refs != (self.correction_of_record_id,):
                raise ValueError("corrected lifecycle references must equal correction target")
        elif self.event_kind == "CAPTURE_RECORD_SUPERSEDED":
            if self.supersedes_record_id is None or self.correction_of_record_id is not None:
                raise ValueError("superseded lifecycle events require only supersession target")
            if self.reference_record_refs != (self.supersedes_record_id,):
                raise ValueError("superseded lifecycle references must equal supersession target")
        else:
            if self.subject_record_type != "MARKET_PATH_EVIDENCE":
                raise ValueError("window finalization requires market-path subject")
            if self.correction_of_record_id is not None or self.supersedes_record_id is not None:
                raise ValueError("window finalization cannot correct or supersede")
            if self.reference_record_refs:
                raise ValueError("window finalization cannot carry references")
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
    runtime_scope_ref: RefId
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
        if self.correction_of_record_id is not None or self.supersedes_record_id is not None:
            raise ValueError("runtime-control events cannot correct or supersede")
        refs = (
            self.single_use_permit_ref,
            self.integrity_check_ref,
            self.kill_state_ref,
        )
        if self.event_kind == "START_PERMIT_ISSUED":
            if refs[0] is None or refs[1:] != (None, None):
                raise ValueError("start permit requires only single_use_permit_ref")
        elif self.event_kind == "KILL_ENGAGED":
            if refs[2] is None or refs[:2] != (None, None):
                raise ValueError("kill requires only kill_state_ref")
        elif self.event_kind == "INTEGRITY_CHECK_COMPLETED":
            if refs[1] is None or refs[0] is not None or refs[2] is not None:
                raise ValueError("integrity event requires only integrity_check_ref")
        elif any(reference is None for reference in refs):
            raise ValueError("resume requires permit, integrity, and kill references")
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
        if self.correction_of_record_id is not None or self.supersedes_record_id is not None:
            raise ValueError("kill states cannot correct or supersede")
        refs = (
            self.single_use_permit_ref,
            self.integrity_check_ref,
            self.runtime_control_event_ref,
        )
        if self.kill_state == "KILLED_FAIL_CLOSED" and refs != (None, None, None):
            raise ValueError("killed state cannot carry resume references")
        if self.kill_state == "RESUME_BLOCKED_PENDING_PERMIT" and (
            self.single_use_permit_ref is not None
            or self.runtime_control_event_ref is not None
        ):
            raise ValueError("blocked resume may carry only integrity_check_ref")
        if self.kill_state == "RESUME_PERMITTED_AFTER_INTEGRITY_CHECK" and any(
            reference is None for reference in refs
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
    observation_slot_ref: RefId
    writer_epoch: StrictInt = Field(ge=0)
    writer_authority_ref: RefId
    record_ref: RefId
    record_hash: Sha256Hex
    duplicate_classification: Literal[
        "UNIQUE",
        "EXACT_DUPLICATE",
        "CONFLICTING_DUPLICATE",
    ]
    previous_manifest_entry_hash: Sha256Hex | None
    io_authorized: Literal[False] = False
    manifest_entry_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_manifest_position(self) -> Self:
        if self.entry_index == 0 and self.previous_manifest_entry_hash is not None:
            raise ValueError("genesis manifest entry must not have previous hash")
        if self.entry_index > 0 and self.previous_manifest_entry_hash is None:
            raise ValueError("non-genesis manifest entry requires previous hash")
        return self


class CaptureCheckpointV0(_HashBoundCaptureModel):
    hash_field: ClassVar[str] = "checkpoint_hash"
    hash_domain: ClassVar[str] = f"{CAPTURE_CONTRACT_VERSION}/checkpoint"

    schema_version: Literal["0.1.0"] = CAPTURE_SCHEMA_VERSION
    contract_version: Literal["trader-assist-v0/capture-now-authority/v1"] = (
        CAPTURE_CONTRACT_VERSION
    )
    plane_id: Literal["CAPTURE_AUTHORITY"] = CAPTURE_PLANE_ID
    checkpoint_kind: Literal["CAPTURE_INTEGRITY_ONLY"] = "CAPTURE_INTEGRITY_ONLY"
    manifest_root_hash: Sha256Hex
    terminal_manifest_entry_hash: Sha256Hex
    terminal_entry_index: StrictInt = Field(ge=0)
    manifest_entry_count: StrictInt = Field(ge=1)
    record_count: StrictInt = Field(ge=1)
    writer_epoch: StrictInt = Field(ge=0)
    writer_authority_ref: RefId
    finalized: Literal[True] = True
    io_authorized: Literal[False] = False
    checkpoint_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_checkpoint_position(self) -> Self:
        if self.terminal_entry_index != self.manifest_entry_count - 1:
            raise ValueError("terminal_entry_index must equal manifest_entry_count - 1")
        return self


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
    verified_manifest_entry_count: StrictInt = Field(ge=0)
    exact_duplicate_count: StrictInt = Field(ge=0)
    conflicting_duplicate_count: StrictInt = Field(ge=0)
    missing_reference_count: StrictInt = Field(ge=0)
    chain_integrity: bool
    checkpoint_integrity: bool
    deterministic_replay: Literal[True] = True
    performance_adjudication_authorized: Literal[False] = False
    promotion_judgment_authorized: Literal[False] = False
    replay_report_hash: Sha256Hex

    @classmethod
    def bind(cls, **payload: Any) -> Self:
        raise TypeError("Capture replay reports must be built from ledger authority")

    @classmethod
    def _bind_derived(cls, **payload: Any) -> Self:
        return super().bind(**payload)


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


_CAPTURE_RECORD_TYPES: Final[tuple[type[_CaptureRecordModel], ...]] = (
    SignalCaptureV0,
    CapturePlanV0,
    ShadowOrderIntentV0,
    HumanObservationV0,
    MarketPathEvidenceV0,
    CaptureLifecycleEventV0,
    RuntimeControlEventV0,
    CaptureKillStateV0,
)


def _validated_capture_records(
    records: tuple[CaptureRecordUnion, ...],
) -> tuple[CaptureRecordUnion, ...]:
    if type(records) is not tuple:
        raise TypeError("records must be an exact tuple")
    validated: list[CaptureRecordUnion] = []
    record_ids: set[str] = set()
    for record in records:
        if type(record) not in _CAPTURE_RECORD_TYPES:
            raise TypeError("records must contain exact concrete Capture record types")
        checked = type(record).model_validate(record)
        if checked.record_id in record_ids:
            raise ValueError(f"duplicate record ID: {checked.record_id}")
        record_ids.add(checked.record_id)
        validated.append(checked)
    return tuple(validated)


def _validated_manifest_entries(
    manifest: tuple[CaptureManifestEntryV0, ...],
) -> tuple[CaptureManifestEntryV0, ...]:
    if type(manifest) is not tuple:
        raise TypeError("manifest must be an exact tuple")
    validated: list[CaptureManifestEntryV0] = []
    for entry in manifest:
        if type(entry) is not CaptureManifestEntryV0:
            raise TypeError("manifest must contain exact CaptureManifestEntryV0 objects")
        validated.append(CaptureManifestEntryV0.model_validate(entry))
    return tuple(validated)


def _validated_checkpoint(checkpoint: CaptureCheckpointV0) -> CaptureCheckpointV0:
    if type(checkpoint) is not CaptureCheckpointV0:
        raise TypeError("checkpoint must be an exact CaptureCheckpointV0")
    return CaptureCheckpointV0.model_validate(checkpoint)


def _record_lookup(
    records: tuple[CaptureRecordUnion, ...],
) -> dict[str, CaptureRecordUnion]:
    return {record.record_id: record for record in records}


def _manifest_record_order(
    manifest: tuple[CaptureManifestEntryV0, ...],
) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for entry in manifest:
        if entry.record_ref not in seen:
            seen.add(entry.record_ref)
            ordered.append(entry.record_ref)
    return tuple(ordered)


def validate_capture_manifest_chain(
    records: tuple[CaptureRecordUnion, ...],
    manifest: tuple[CaptureManifestEntryV0, ...],
) -> None:
    checked_records = _validated_capture_records(records)
    checked_manifest = _validated_manifest_entries(manifest)
    if not checked_manifest:
        raise ValueError("Capture manifest chain must not be empty")

    records_by_id = _record_lookup(checked_records)
    writer_epoch = checked_manifest[0].writer_epoch
    writer_authority_ref = checked_manifest[0].writer_authority_ref
    slots: dict[str, tuple[str, str]] = {}
    record_slots: dict[tuple[str, str], str] = {}
    manifest_record_refs: set[str] = set()

    for expected_index, entry in enumerate(checked_manifest):
        if entry.entry_index != expected_index:
            raise ValueError(f"manifest entry index gap at {expected_index}")
        expected_previous = (
            None
            if expected_index == 0
            else checked_manifest[expected_index - 1].manifest_entry_hash
        )
        if entry.previous_manifest_entry_hash != expected_previous:
            raise ValueError(f"manifest previous hash mismatch at {expected_index}")
        if entry.writer_epoch != writer_epoch or entry.writer_authority_ref != writer_authority_ref:
            raise ValueError(f"manifest writer authority mismatch at {expected_index}")

        record = records_by_id.get(entry.record_ref)
        if record is None:
            raise ValueError(f"manifest references missing record: {entry.record_ref}")
        if entry.record_hash != record.record_hash:
            raise ValueError(f"manifest record hash mismatch: {entry.record_ref}")
        manifest_record_refs.add(entry.record_ref)

        record_identity = (entry.record_ref, entry.record_hash)
        prior_slot = record_slots.get(record_identity)
        prior_identity = slots.get(entry.observation_slot_ref)
        if prior_identity is None:
            expected_classification = "UNIQUE"
            if prior_slot is not None and prior_slot != entry.observation_slot_ref:
                raise ValueError(
                    "record identity cannot evade duplicate detection by changing slot"
                )
            slots[entry.observation_slot_ref] = record_identity
        elif prior_identity == record_identity:
            expected_classification = "EXACT_DUPLICATE"
        else:
            expected_classification = "CONFLICTING_DUPLICATE"
        if entry.duplicate_classification != expected_classification:
            raise ValueError(
                f"duplicate classification mismatch at {expected_index}: "
                f"expected {expected_classification}"
            )
        record_slots.setdefault(record_identity, entry.observation_slot_ref)

    record_ids = set(records_by_id)
    if manifest_record_refs != record_ids:
        missing = sorted(record_ids - manifest_record_refs)
        unexpected = sorted(manifest_record_refs - record_ids)
        raise ValueError(
            f"manifest record set mismatch: missing={missing}, unexpected={unexpected}"
        )


def _require_earlier_record(
    *,
    reference: str,
    subject: CaptureRecordUnion,
    records_by_id: Mapping[str, CaptureRecordUnion],
    positions: Mapping[str, int],
    relation: str,
) -> CaptureRecordUnion:
    target = records_by_id.get(reference)
    if target is None:
        raise ValueError(f"{relation} target does not exist: {reference}")
    if reference == subject.record_id:
        raise ValueError(f"{relation} cannot self-reference")
    if positions[reference] >= positions[subject.record_id]:
        raise ValueError(f"{relation} target must be earlier in manifest order")
    return target


def _validate_generic_corrections(
    ordered_records: tuple[CaptureRecordUnion, ...],
    records_by_id: Mapping[str, CaptureRecordUnion],
    positions: Mapping[str, int],
) -> None:
    for record in ordered_records:
        if isinstance(record, CaptureLifecycleEventV0):
            continue
        correction = record.correction_of_record_id
        supersession = record.supersedes_record_id
        if correction is not None and supersession is not None:
            raise ValueError("correction and supersession cannot both be present")
        if isinstance(record, RuntimeControlEventV0 | CaptureKillStateV0):
            if correction is not None or supersession is not None:
                raise ValueError("runtime control and kill state cannot correct or supersede")
            continue
        reference = correction if correction is not None else supersession
        if reference is None:
            continue
        relation = "correction" if correction is not None else "supersession"
        target = _require_earlier_record(
            reference=reference,
            subject=record,
            records_by_id=records_by_id,
            positions=positions,
            relation=relation,
        )
        if target.record_type != record.record_type:
            raise ValueError(f"{relation} target must have the same record_type")


def _validate_signal_plan_shadow_graph(
    ordered_records: tuple[CaptureRecordUnion, ...],
    records_by_id: Mapping[str, CaptureRecordUnion],
) -> None:
    for record in ordered_records:
        if isinstance(record, SignalCaptureV0):
            for reference in record.evidence_refs:
                if reference not in records_by_id:
                    raise ValueError(f"signal evidence reference does not exist: {reference}")
            for reference in record.plan_record_refs:
                plan = records_by_id.get(reference)
                if type(plan) is not CapturePlanV0:
                    raise ValueError("signal plan references must point to CapturePlanV0")
                if (
                    plan.signal_record_ref != record.record_id
                    or plan.signal_kind != record.signal_kind
                ):
                    raise ValueError("signal and plan references must agree bidirectionally")
            for reference in record.shadow_intent_refs:
                shadow = records_by_id.get(reference)
                if type(shadow) is not ShadowOrderIntentV0:
                    raise ValueError("signal shadow references must point to ShadowOrderIntentV0")
                plan = records_by_id.get(shadow.plan_record_ref)
                if type(plan) is not CapturePlanV0 or plan.signal_record_ref != record.record_id:
                    raise ValueError("signal and shadow references must agree through a real plan")
        elif isinstance(record, CapturePlanV0):
            signal = records_by_id.get(record.signal_record_ref)
            if type(signal) is not SignalCaptureV0:
                raise ValueError("plan signal_record_ref must point to SignalCaptureV0")
            if signal.signal_kind != record.signal_kind:
                raise ValueError("plan signal_kind must equal its signal")
            if record.record_id not in signal.plan_record_refs:
                raise ValueError("signal must contain the plan reverse reference")
            for reference in record.evidence_refs:
                if reference not in records_by_id:
                    raise ValueError(f"plan evidence reference does not exist: {reference}")
        elif isinstance(record, ShadowOrderIntentV0):
            plan = records_by_id.get(record.plan_record_ref)
            if type(plan) is not CapturePlanV0:
                raise ValueError("shadow plan_record_ref must point to CapturePlanV0")
            signal = records_by_id.get(plan.signal_record_ref)
            if type(signal) is not SignalCaptureV0 or signal.signal_kind == "WAIT":
                raise ValueError("shadow requires a non-WAIT signal through a real plan")
            if record.record_id not in signal.shadow_intent_refs:
                raise ValueError("signal must contain the shadow reverse reference")
            for reference in record.evidence_refs:
                if reference not in records_by_id:
                    raise ValueError(f"shadow evidence reference does not exist: {reference}")
        elif isinstance(record, HumanObservationV0):
            for reference in record.observed_record_refs:
                if reference not in records_by_id:
                    raise ValueError(f"human observation reference does not exist: {reference}")


def _validate_lifecycle_graph(
    ordered_records: tuple[CaptureRecordUnion, ...],
    records_by_id: Mapping[str, CaptureRecordUnion],
    positions: Mapping[str, int],
) -> None:
    prohibited_subject_types = (
        CaptureLifecycleEventV0,
        RuntimeControlEventV0,
        CaptureKillStateV0,
    )
    for event in ordered_records:
        if not isinstance(event, CaptureLifecycleEventV0):
            continue
        subject = _require_earlier_record(
            reference=event.subject_record_ref,
            subject=event,
            records_by_id=records_by_id,
            positions=positions,
            relation="lifecycle subject",
        )
        if isinstance(subject, prohibited_subject_types):
            raise ValueError(
                "lifecycle subject cannot be lifecycle, runtime-control, or kill state"
            )
        if subject.record_type != event.subject_record_type:
            raise ValueError("lifecycle subject_record_type does not match subject")
        if event.event_kind == "CAPTURE_RECORD_CREATED":
            if (
                subject.correction_of_record_id is not None
                or subject.supersedes_record_id is not None
            ):
                raise ValueError("created lifecycle event cannot describe a correction")
            continue
        if event.event_kind == "CAPTURE_WINDOW_FINALIZED":
            if type(subject) is not MarketPathEvidenceV0:
                raise ValueError("window finalization requires MarketPathEvidenceV0")
            continue
        target_ref = (
            event.correction_of_record_id
            if event.event_kind == "CAPTURE_RECORD_CORRECTED"
            else event.supersedes_record_id
        )
        assert target_ref is not None
        target = _require_earlier_record(
            reference=target_ref,
            subject=event,
            records_by_id=records_by_id,
            positions=positions,
            relation="lifecycle transition",
        )
        if target.record_type != subject.record_type:
            raise ValueError("lifecycle transition target must match subject type")
        subject_target = (
            subject.correction_of_record_id
            if event.event_kind == "CAPTURE_RECORD_CORRECTED"
            else subject.supersedes_record_id
        )
        if subject_target != target_ref:
            raise ValueError("lifecycle transition must describe the subject's actual relation")


def _validate_market_path_series(
    ordered_records: tuple[CaptureRecordUnion, ...],
    records_by_id: Mapping[str, CaptureRecordUnion],
) -> None:
    normal_by_series: dict[str, MarketPathEvidenceV0] = {}
    source_by_series: dict[str, str] = {}
    for record in ordered_records:
        if not isinstance(record, MarketPathEvidenceV0):
            continue
        series = record.market_path_series_ref
        source_hash = record.source_identity.identity_hash
        expected_source = source_by_series.setdefault(series, source_hash)
        if source_hash != expected_source:
            raise ValueError("market-path series source identity changed")
        relation_ref = record.correction_of_record_id or record.supersedes_record_id
        if relation_ref is not None:
            target = records_by_id[relation_ref]
            if type(target) is not MarketPathEvidenceV0:
                raise ValueError("market-path correction target must be market-path evidence")
            if (
                target.market_path_series_ref != series
                or target.source_identity.identity_hash != source_hash
                or target.chunk_sequence != record.chunk_sequence
                or target.window_start_ms != record.window_start_ms
                or target.window_end_ms != record.window_end_ms
            ):
                raise ValueError(
                    "market-path correction cannot change series, source, sequence, or window"
                )
            continue
        previous = normal_by_series.get(series)
        if previous is None:
            if record.chunk_sequence != 0:
                raise ValueError("market-path series must start at chunk_sequence 0")
        else:
            if record.chunk_sequence != previous.chunk_sequence + 1:
                raise ValueError("market-path normal chunks must increment sequence by one")
            if record.window_start_ms < previous.window_end_ms:
                raise ValueError("market-path finalized windows cannot overlap or move backward")
        normal_by_series[series] = record


def _validate_runtime_control_graph(
    ordered_records: tuple[CaptureRecordUnion, ...],
    records_by_id: Mapping[str, CaptureRecordUnion],
    positions: Mapping[str, int],
) -> None:
    used_permits: set[str] = set()
    unresolved_kills: dict[str, tuple[str, int]] = {}
    integrity_by_scope: dict[str, dict[str, int]] = {}
    resume_events: dict[str, RuntimeControlEventV0] = {}

    for record in ordered_records:
        if not isinstance(record, RuntimeControlEventV0):
            continue
        if record.runtime_scope_ref in records_by_id:
            raise ValueError("runtime_scope_ref cannot masquerade as a Capture record")
        for opaque_ref in (record.single_use_permit_ref, record.integrity_check_ref):
            if opaque_ref is not None and opaque_ref in records_by_id:
                raise ValueError("runtime-control opaque references cannot use Capture record IDs")
        if record.event_kind in {"START_PERMIT_ISSUED", "RESUME_PERMIT_ISSUED"}:
            assert record.single_use_permit_ref is not None
            if record.single_use_permit_ref in used_permits:
                raise ValueError("runtime-control permit reference must be single-use")
            used_permits.add(record.single_use_permit_ref)
        if record.event_kind == "KILL_ENGAGED":
            assert record.kill_state_ref is not None
            kill = _require_earlier_record(
                reference=record.kill_state_ref,
                subject=record,
                records_by_id=records_by_id,
                positions=positions,
                relation="kill",
            )
            if type(kill) is not CaptureKillStateV0 or kill.kill_state == (
                "RESUME_PERMITTED_AFTER_INTEGRITY_CHECK"
            ):
                raise ValueError("KILL_ENGAGED must reference an unresolved CaptureKillStateV0")
            if record.runtime_scope_ref in unresolved_kills:
                raise ValueError("runtime scope already has an unresolved kill")
            unresolved_kills[record.runtime_scope_ref] = (
                kill.record_id,
                positions[record.record_id],
            )
            integrity_by_scope[record.runtime_scope_ref] = {}
        elif record.event_kind == "INTEGRITY_CHECK_COMPLETED":
            assert record.integrity_check_ref is not None
            integrity_by_scope.setdefault(record.runtime_scope_ref, {})[
                record.integrity_check_ref
            ] = positions[record.record_id]
        elif record.event_kind == "RESUME_PERMIT_ISSUED":
            assert record.kill_state_ref is not None
            assert record.integrity_check_ref is not None
            unresolved = unresolved_kills.get(record.runtime_scope_ref)
            if unresolved is None:
                raise ValueError("resume requires an unresolved kill in the same runtime scope")
            kill_ref, kill_event_position = unresolved
            if record.kill_state_ref != kill_ref:
                raise ValueError("resume must reference the current unresolved kill")
            integrity_position = integrity_by_scope.get(record.runtime_scope_ref, {}).get(
                record.integrity_check_ref
            )
            if integrity_position is None or not (
                kill_event_position < integrity_position < positions[record.record_id]
            ):
                raise ValueError("resume integrity check must occur after kill and before resume")
            resume_events[record.record_id] = record
            del unresolved_kills[record.runtime_scope_ref]

    integrity_events = {
        record.integrity_check_ref: record
        for record in ordered_records
        if isinstance(record, RuntimeControlEventV0)
        and record.event_kind == "INTEGRITY_CHECK_COMPLETED"
        and record.integrity_check_ref is not None
    }
    for kill_state in ordered_records:
        if not isinstance(kill_state, CaptureKillStateV0):
            continue
        if kill_state.kill_state == "RESUME_BLOCKED_PENDING_PERMIT":
            if kill_state.integrity_check_ref is not None:
                integrity_event = integrity_events.get(kill_state.integrity_check_ref)
                if (
                    integrity_event is None
                    or positions[integrity_event.record_id] >= positions[kill_state.record_id]
                ):
                    raise ValueError(
                        "blocked resume integrity reference must be completed earlier"
                    )
        elif kill_state.kill_state == "RESUME_PERMITTED_AFTER_INTEGRITY_CHECK":
            assert kill_state.runtime_control_event_ref is not None
            event = resume_events.get(kill_state.runtime_control_event_ref)
            if event is None or positions[event.record_id] >= positions[kill_state.record_id]:
                raise ValueError(
                    "permitted kill state must reference an earlier valid resume event"
                )
            if (
                kill_state.single_use_permit_ref != event.single_use_permit_ref
                or kill_state.integrity_check_ref != event.integrity_check_ref
            ):
                raise ValueError("permitted kill state references must match its resume event")


def validate_capture_record_graph(
    records: tuple[CaptureRecordUnion, ...],
    manifest: tuple[CaptureManifestEntryV0, ...],
) -> None:
    checked_records = _validated_capture_records(records)
    checked_manifest = _validated_manifest_entries(manifest)
    validate_capture_manifest_chain(checked_records, checked_manifest)
    records_by_id = _record_lookup(checked_records)
    ordered_ids = _manifest_record_order(checked_manifest)
    ordered_records = tuple(records_by_id[record_id] for record_id in ordered_ids)
    positions = {
        record_id: next(
            entry.entry_index for entry in checked_manifest if entry.record_ref == record_id
        )
        for record_id in ordered_ids
    }
    _validate_generic_corrections(ordered_records, records_by_id, positions)
    _validate_signal_plan_shadow_graph(ordered_records, records_by_id)
    _validate_lifecycle_graph(ordered_records, records_by_id, positions)
    _validate_market_path_series(ordered_records, records_by_id)
    _validate_runtime_control_graph(ordered_records, records_by_id, positions)


def validate_capture_checkpoint(
    records: tuple[CaptureRecordUnion, ...],
    manifest: tuple[CaptureManifestEntryV0, ...],
    checkpoint: CaptureCheckpointV0,
) -> None:
    checked_records = _validated_capture_records(records)
    checked_manifest = _validated_manifest_entries(manifest)
    checked_checkpoint = _validated_checkpoint(checkpoint)
    validate_capture_manifest_chain(checked_records, checked_manifest)
    expected = {
        "manifest_root_hash": checked_manifest[0].manifest_entry_hash,
        "terminal_manifest_entry_hash": checked_manifest[-1].manifest_entry_hash,
        "terminal_entry_index": checked_manifest[-1].entry_index,
        "manifest_entry_count": len(checked_manifest),
        "record_count": len({entry.record_ref for entry in checked_manifest}),
        "writer_epoch": checked_manifest[0].writer_epoch,
        "writer_authority_ref": checked_manifest[0].writer_authority_ref,
    }
    for field_name, expected_value in expected.items():
        if object.__getattribute__(checked_checkpoint, field_name) != expected_value:
            raise ValueError(f"checkpoint {field_name} does not match manifest chain")


def validate_capture_checkpoint_advance(
    old_checkpoint: CaptureCheckpointV0,
    new_checkpoint: CaptureCheckpointV0,
    old_manifest: tuple[CaptureManifestEntryV0, ...],
    new_manifest: tuple[CaptureManifestEntryV0, ...],
    old_records: tuple[CaptureRecordUnion, ...],
    new_records: tuple[CaptureRecordUnion, ...],
) -> None:
    checked_old_manifest = _validated_manifest_entries(old_manifest)
    checked_new_manifest = _validated_manifest_entries(new_manifest)
    checked_old_checkpoint = _validated_checkpoint(old_checkpoint)
    checked_new_checkpoint = _validated_checkpoint(new_checkpoint)
    validate_capture_checkpoint(old_records, checked_old_manifest, checked_old_checkpoint)
    validate_capture_checkpoint(new_records, checked_new_manifest, checked_new_checkpoint)
    if len(checked_new_manifest) < len(checked_old_manifest):
        raise ValueError("checkpoint advance cannot truncate manifest history")
    if checked_new_manifest[: len(checked_old_manifest)] != checked_old_manifest:
        raise ValueError("checkpoint advance cannot rewrite manifest history")
    if checked_new_checkpoint.manifest_root_hash != checked_old_checkpoint.manifest_root_hash:
        raise ValueError("checkpoint advance cannot change ledger root")
    if len(checked_new_manifest) == len(checked_old_manifest):
        if checked_new_checkpoint != checked_old_checkpoint:
            raise ValueError("unchanged manifest requires an exact duplicate checkpoint")
        return
    if (
        checked_new_checkpoint.terminal_entry_index
        <= checked_old_checkpoint.terminal_entry_index
        or checked_new_checkpoint.manifest_entry_count
        <= checked_old_checkpoint.manifest_entry_count
        or checked_new_checkpoint.record_count < checked_old_checkpoint.record_count
    ):
        raise ValueError("checkpoint extension cannot roll back index or counts")


def _missing_capture_reference_count(records: tuple[CaptureRecordUnion, ...]) -> int:
    record_ids = {record.record_id for record in records}
    references: list[str] = []
    for record in records:
        if isinstance(record, SignalCaptureV0):
            references.extend(record.evidence_refs)
            references.extend(record.plan_record_refs)
            references.extend(record.shadow_intent_refs)
        elif isinstance(record, CapturePlanV0):
            references.append(record.signal_record_ref)
            references.extend(record.evidence_refs)
        elif isinstance(record, ShadowOrderIntentV0):
            references.append(record.plan_record_ref)
            references.extend(record.evidence_refs)
        elif isinstance(record, HumanObservationV0):
            references.extend(record.observed_record_refs)
        elif isinstance(record, CaptureLifecycleEventV0):
            references.append(record.subject_record_ref)
            references.extend(record.reference_record_refs)
        elif isinstance(record, RuntimeControlEventV0) and record.kill_state_ref is not None:
            references.append(record.kill_state_ref)
        elif (
            isinstance(record, CaptureKillStateV0)
            and record.runtime_control_event_ref is not None
        ):
            references.append(record.runtime_control_event_ref)
        if not isinstance(record, CaptureLifecycleEventV0):
            if record.correction_of_record_id is not None:
                references.append(record.correction_of_record_id)
            if record.supersedes_record_id is not None:
                references.append(record.supersedes_record_id)
    return sum(reference not in record_ids for reference in references)


def build_capture_replay_report(
    records: tuple[CaptureRecordUnion, ...],
    manifest: tuple[CaptureManifestEntryV0, ...],
    checkpoint: CaptureCheckpointV0,
) -> CaptureReplayReportV0:
    checked_records = _validated_capture_records(records)
    checked_manifest = _validated_manifest_entries(manifest)
    checked_checkpoint = _validated_checkpoint(checkpoint)
    missing_reference_count = _missing_capture_reference_count(checked_records)
    chain_integrity = True
    try:
        validate_capture_manifest_chain(checked_records, checked_manifest)
        validate_capture_record_graph(checked_records, checked_manifest)
    except ValueError:
        chain_integrity = False
    checkpoint_integrity = True
    try:
        validate_capture_checkpoint(checked_records, checked_manifest, checked_checkpoint)
    except ValueError:
        checkpoint_integrity = False
    exact_duplicate_count = sum(
        entry.duplicate_classification == "EXACT_DUPLICATE" for entry in checked_manifest
    )
    conflicting_duplicate_count = sum(
        entry.duplicate_classification == "CONFLICTING_DUPLICATE"
        for entry in checked_manifest
    )
    replay_passes = (
        chain_integrity
        and checkpoint_integrity
        and missing_reference_count == 0
        and conflicting_duplicate_count == 0
    )
    return CaptureReplayReportV0._bind_derived(
        checkpoint_hash=checked_checkpoint.checkpoint_hash,
        replay_status="PASS" if replay_passes else "FAIL",
        verified_record_count=len(checked_records) if chain_integrity else 0,
        verified_manifest_entry_count=len(checked_manifest) if chain_integrity else 0,
        exact_duplicate_count=exact_duplicate_count,
        conflicting_duplicate_count=conflicting_duplicate_count,
        missing_reference_count=missing_reference_count,
        chain_integrity=chain_integrity,
        checkpoint_integrity=checkpoint_integrity,
    )


def validate_capture_replay_report(
    report: CaptureReplayReportV0,
    records: tuple[CaptureRecordUnion, ...],
    manifest: tuple[CaptureManifestEntryV0, ...],
    checkpoint: CaptureCheckpointV0,
) -> None:
    if type(report) is not CaptureReplayReportV0:
        raise TypeError("report must be an exact CaptureReplayReportV0")
    checked_report = CaptureReplayReportV0.model_validate(report)
    expected = build_capture_replay_report(records, manifest, checkpoint)
    if BaseModel.model_dump(checked_report, mode="python", round_trip=True) != BaseModel.model_dump(
        expected,
        mode="python",
        round_trip=True,
    ):
        raise ValueError("replay report does not match deterministic ledger replay")
