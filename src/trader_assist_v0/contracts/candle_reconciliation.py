from __future__ import annotations

import hmac
import json
import re
import traceback
from collections.abc import Mapping, Set
from copy import deepcopy
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    WrapValidator,
    model_validator,
)
from pydantic.config import ExtraValues
from pydantic_core import PydanticCustomError, SchemaValidator

from .candles import (
    CandleEnvelopeShapeV0,
    CandlePayloadExtractionV0,
    ExtractedCandleV0,
    compute_candle_extraction_hash,
    compute_candle_logical_key,
)
from .common import (
    FiniteDecimalString,
    Sha256Hex,
    StrictModel,
    canonical_json_bytes,
    decimal_to_canonical_string,
    sha256_hex,
)

A6_CONTRACT_ID = "V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT"
A6_SCHEMA_VERSION = "0.1.0"
A6_HASH_VERSION = "trader-assist-v0/candle-cross-source-reconciliation/v1"
A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_PATTERN = r"^(0|[1-9][0-9]*)$"

_A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_RE = re.compile(
    A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_PATTERN
)
_A6_CANONICAL_JSON_INTEGER_RE = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z")
_A6_INTEGER_WIRE_FIELDS = frozenset(
    {
        "open_time_ms",
        "close_time_ms",
        "trade_count",
        "match_count",
        "conflict_count",
        "ws_only_count",
        "info_only_count",
    }
)
_A6_STRING_WIRE_FIELDS = frozenset(
    {
        "schema_version",
        "contract_id",
        "extraction_version",
        "hash_version",
        "source_id",
        "coin",
        "candle_interval",
        "ws_source_event_id",
        "ws_extraction_hash",
        "info_source_event_id",
        "info_extraction_hash",
        "source_event_id",
        "payload_sha256",
        "extraction_hash",
        "reconciliation_hash",
        "candle_logical_key",
        "status",
        "side",
        "endpoint_id",
        "operation_type",
        "envelope_shape",
        "field_name",
        "ws_value",
        "info_value",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_base",
    }
)

_A5_CANDLE_FIELDS = frozenset(
    {
        "candle_logical_key",
        "open_time_ms",
        "close_time_ms",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_base",
        "trade_count",
    }
)
_A5_EXTRACTION_FIELDS = frozenset(
    {
        "schema_version",
        "contract_id",
        "extraction_version",
        "source_id",
        "source_event_id",
        "payload_sha256",
        "endpoint_id",
        "operation_type",
        "coin",
        "candle_interval",
        "envelope_shape",
        "candles",
        "extraction_hash",
    }
)
_A6_INPUT_AUTHORITY_FIELDS = frozenset(
    {
        "side",
        "source_event_id",
        "extraction_hash",
        "endpoint_id",
        "operation_type",
        "envelope_shape",
    }
)
_A6_FIELD_DIFFERENCE_FIELDS = frozenset(
    {"field_name", "ws_value", "info_value"}
)
_A6_COMPARISON_FIELDS = frozenset(
    {
        "candle_logical_key",
        "source_id",
        "coin",
        "candle_interval",
        "open_time_ms",
        "status",
        "ws_candle",
        "ws_authority",
        "info_candle",
        "info_authority",
        "field_differences",
    }
)
_A6_REPORT_FIELDS = frozenset(
    {
        "schema_version",
        "contract_id",
        "hash_version",
        "source_id",
        "coin",
        "candle_interval",
        "ws_extraction",
        "info_extraction",
        "ws_source_event_id",
        "ws_extraction_hash",
        "info_source_event_id",
        "info_extraction_hash",
        "comparisons",
        "match_count",
        "conflict_count",
        "ws_only_count",
        "info_only_count",
        "reconciliation_hash",
    }
)


def _persistent_json_extracted_candle(
    value: Any,
    handler: Any,
    _info: ValidationInfo,
) -> Any:
    return handler(value)


def _persistent_json_candle_extraction(
    value: Any,
    handler: Any,
    _info: ValidationInfo,
) -> Any:
    return handler(value)


_A6ExtractedCandleV0 = Annotated[
    ExtractedCandleV0,
    WrapValidator(_persistent_json_extracted_candle),
]
_A6CandlePayloadExtractionV0 = Annotated[
    CandlePayloadExtractionV0,
    WrapValidator(_persistent_json_candle_extraction),
]

CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS = (
    "close_time_ms",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume_base",
    "trade_count",
)

type CandleCrossSourceComparableFieldV0 = Literal[
    "close_time_ms",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume_base",
    "trade_count",
]
type CandleCrossSourceComparableValueV0 = FiniteDecimalString


class CandleCrossSourceComparisonStatusV0(StrEnum):
    MATCH = "MATCH"
    CONFLICT = "CONFLICT"
    WS_ONLY = "WS_ONLY"
    INFO_ONLY = "INFO_ONLY"


class CandleCrossSourceAuthoritySideV0(StrEnum):
    WS = "WS"
    INFO = "INFO"


def _require_exact_wire_mapping(
    value: Any,
    *,
    fields: frozenset[str],
    authority_name: str,
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{authority_name} must be a decoded JSON object")
    actual_fields = set(value)
    missing = fields - actual_fields
    extra = actual_fields - fields
    if missing:
        raise ValueError(
            f"{authority_name} is missing mandatory fields: {', '.join(sorted(missing))}"
        )
    if extra:
        raise ValueError(
            f"{authority_name} has extra fields: {', '.join(sorted(str(item) for item in extra))}"
        )
    return value


def _validate_a6_json_scalar_kinds(value: Any) -> None:
    if isinstance(value, dict):
        for field_name, item in value.items():
            if field_name in _A6_INTEGER_WIRE_FIELDS and type(item) is not int:
                raise ValueError(f"{field_name} JSON value must be an integer")
            if field_name in _A6_STRING_WIRE_FIELDS and type(item) is not str:
                raise ValueError(f"{field_name} JSON value must be a string")
            _validate_a6_json_scalar_kinds(item)
        return
    if isinstance(value, list):
        for item in value:
            _validate_a6_json_scalar_kinds(item)
        return
    if isinstance(value, str) and value != value.strip():
        raise ValueError("A6 JSON strings must not be whitespace padded")


def _validate_a5_candle_wire(value: Any) -> None:
    _require_exact_wire_mapping(
        value,
        fields=_A5_CANDLE_FIELDS,
        authority_name="embedded A5 candle",
    )
    _validate_a6_json_scalar_kinds(value)


def _validate_a5_extraction_wire(value: Any) -> None:
    mapping = _require_exact_wire_mapping(
        value,
        fields=_A5_EXTRACTION_FIELDS,
        authority_name="embedded A5 extraction",
    )
    _validate_a6_json_scalar_kinds(mapping)
    candles = mapping["candles"]
    if type(candles) is not list:
        raise ValueError("embedded A5 candles must be a decoded JSON array")
    for candle in candles:
        _validate_a5_candle_wire(candle)


def _validate_input_authority_wire(value: Any) -> None:
    mapping = _require_exact_wire_mapping(
        value,
        fields=_A6_INPUT_AUTHORITY_FIELDS,
        authority_name="A6 input authority",
    )
    _validate_a6_json_scalar_kinds(mapping)


def _validate_field_difference_wire(value: Any) -> None:
    mapping = _require_exact_wire_mapping(
        value,
        fields=_A6_FIELD_DIFFERENCE_FIELDS,
        authority_name="A6 field difference",
    )
    _validate_a6_json_scalar_kinds(mapping)


def _validate_comparison_wire(value: Any) -> None:
    mapping = _require_exact_wire_mapping(
        value,
        fields=_A6_COMPARISON_FIELDS,
        authority_name="A6 comparison",
    )
    _validate_a6_json_scalar_kinds(mapping)
    for candle_field in ("ws_candle", "info_candle"):
        candle = mapping[candle_field]
        if candle is not None:
            _validate_a5_candle_wire(candle)
    for authority_field in ("ws_authority", "info_authority"):
        authority = mapping[authority_field]
        if authority is not None:
            _validate_input_authority_wire(authority)
    differences = mapping["field_differences"]
    if type(differences) is not list:
        raise ValueError("A6 field_differences must be a decoded JSON array")
    for difference in differences:
        _validate_field_difference_wire(difference)


def _validate_report_wire(value: Any) -> None:
    mapping = _require_exact_wire_mapping(
        value,
        fields=_A6_REPORT_FIELDS,
        authority_name="A6 report",
    )
    _validate_a6_json_scalar_kinds(mapping)
    _validate_a5_extraction_wire(mapping["ws_extraction"])
    _validate_a5_extraction_wire(mapping["info_extraction"])
    comparisons = mapping["comparisons"]
    if type(comparisons) is not list:
        raise ValueError("A6 comparisons must be a decoded JSON array")
    for comparison in comparisons:
        _validate_comparison_wire(comparison)


def _a6_object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate A6 JSON object key: {key}")
        value[key] = item
    return value


def _a6_parse_json_integer(token: str) -> int:
    if token == "-0":
        raise ValueError("A6 JSON integers must not use -0")
    if _A6_CANONICAL_JSON_INTEGER_RE.fullmatch(token) is None:
        raise ValueError("A6 JSON integer token is not canonical")
    return int(token)


def _a6_reject_json_float(token: str) -> None:
    raise ValueError(f"A6 JSON numbers must use integer tokens, not {token}")


def _a6_reject_json_constant(token: str) -> None:
    raise ValueError(f"A6 JSON non-finite constant is prohibited: {token}")


def _approved_canonical_a6_json_bytes(
    json_data: str | bytes | bytearray,
) -> bytes:
    if isinstance(json_data, str):
        text = json_data
        try:
            raw_bytes = text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ValueError("A6 JSON text must be valid UTF-8") from exc
    elif isinstance(json_data, bytes | bytearray):
        raw_bytes = bytes(json_data)
        try:
            text = raw_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("A6 JSON bytes must be strict UTF-8") from exc
    else:
        raise TypeError("A6 raw JSON input must be str, bytes, or bytearray")

    if raw_bytes.startswith(b"\xef\xbb\xbf") or text.startswith("\ufeff"):
        raise ValueError("A6 JSON must not contain a UTF-8 BOM")

    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_a6_object_from_pairs,
            parse_int=_a6_parse_json_integer,
            parse_float=_a6_reject_json_float,
            parse_constant=_a6_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("A6 JSON must contain exactly one complete JSON value") from exc

    try:
        canonical_bytes = canonical_json_bytes(decoded)
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise ValueError("A6 JSON value cannot be canonically encoded") from exc
    if raw_bytes != canonical_bytes:
        raise ValueError("A6 JSON bytes must equal canonical_json_bytes(decoded_value)")
    return raw_bytes


def _restore_call_local_json_values(
    model_type: type[BaseModel],
    value: Any,
) -> dict[str, Any]:
    mapping = cast(dict[str, Any], value)
    restored = dict(mapping)
    if model_type is CandleCrossSourceComparisonItemV0:
        for candle_field in ("ws_candle", "info_candle"):
            candle = mapping[candle_field]
            if candle is not None:
                restored[candle_field] = ExtractedCandleV0.model_validate_json(
                    canonical_json_bytes(candle)
                )
        restored["field_differences"] = tuple(mapping["field_differences"])
    elif model_type is CandleCrossSourceReconciliationV0:
        restored["ws_extraction"] = CandlePayloadExtractionV0.model_validate_json(
            canonical_json_bytes(mapping["ws_extraction"])
        )
        restored["info_extraction"] = CandlePayloadExtractionV0.model_validate_json(
            canonical_json_bytes(mapping["info_extraction"])
        )
        restored["comparisons"] = tuple(mapping["comparisons"])
    return restored


class _A6AuthorityModel(StrictModel):
    model_config = ConfigDict(
        revalidate_instances="always",
        str_strip_whitespace=False,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_canonical_authority_input(
        cls,
        value: Any,
        info: ValidationInfo,
    ) -> Any:
        if info.mode != "python":
            raise ValueError(
                "A6 inherited/core JSON and string validation paths are unsupported"
            )
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise ValueError(f"expected exact {cls.__name__} authority object")
            _validate_current_a6_authority(value)
            value = BaseModel.model_dump(
                value,
                mode="json",
                round_trip=True,
            )
        _validate_wire_for_model(cls, value)
        return value

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
        canonical_bytes = _approved_canonical_a6_json_bytes(json_data)

        def isolated_runner() -> tuple[Any, ...]:
            def sensitive_inner() -> BaseModel:
                expected_a6_nodes: dict[
                    type[BaseModel], tuple[type[BaseModel], ...]
                ] = {
                    CandleCrossSourceInputAuthorityV0: (
                        CandleCrossSourceInputAuthorityV0,
                    ),
                    CandleCrossSourceFieldDifferenceV0: (
                        CandleCrossSourceFieldDifferenceV0,
                    ),
                    CandleCrossSourceComparisonItemV0: (
                        CandleCrossSourceComparisonItemV0,
                        CandleCrossSourceFieldDifferenceV0,
                        CandleCrossSourceInputAuthorityV0,
                    ),
                    CandleCrossSourceReconciliationV0: (
                        CandleCrossSourceReconciliationV0,
                        CandleCrossSourceComparisonItemV0,
                        CandleCrossSourceFieldDifferenceV0,
                        CandleCrossSourceInputAuthorityV0,
                    ),
                }
                expected_nested_nodes: dict[
                    type[BaseModel], tuple[type[BaseModel], ...]
                ] = {
                    CandleCrossSourceInputAuthorityV0: (),
                    CandleCrossSourceFieldDifferenceV0: (),
                    CandleCrossSourceComparisonItemV0: (
                        ExtractedCandleV0,
                        ExtractedCandleV0,
                    ),
                    CandleCrossSourceReconciliationV0: (
                        CandlePayloadExtractionV0,
                        CandlePayloadExtractionV0,
                        ExtractedCandleV0,
                        ExtractedCandleV0,
                    ),
                }
                if cls not in expected_a6_nodes:
                    raise ValueError("unsupported A6 authority model class")

                call_schema = deepcopy(cls.__pydantic_core_schema__)
                replaced_a6_nodes: list[type[BaseModel]] = []
                replaced_nested_nodes: list[type[BaseModel]] = []
                persistent_before_function = (
                    _A6AuthorityModel.validate_canonical_authority_input.__func__
                )

                def call_local_a6_before(
                    model_type: type[BaseModel],
                ) -> Any:
                    def validate(value: Any, info: ValidationInfo) -> Any:
                        if info.mode != "json":
                            raise ValueError("call-local A6 validator requires JSON mode")
                        _validate_wire_for_model(model_type, value)
                        return _restore_call_local_json_values(model_type, value)

                    return validate

                def call_local_nested_wrap(
                    model_type: type[BaseModel],
                ) -> Any:
                    def validate(value: Any, _handler: Any, info: ValidationInfo) -> Any:
                        if info.mode != "json" or type(value) is not model_type:
                            raise ValueError(
                                "call-local nested authority requires exact "
                                "JSON-restored authority"
                            )
                        return value

                    return validate

                def replace_call_local_nodes(value: Any) -> None:
                    if isinstance(value, dict):
                        function = value.get("function")
                        if isinstance(function, dict):
                            callable_value = function.get("function")
                            callable_function = getattr(
                                callable_value, "__func__", callable_value
                            )
                            if callable_function is persistent_before_function:
                                if value.get("type") != "function-before" or function.get(
                                    "type"
                                ) != "with-info":
                                    raise ValueError(
                                        "unexpected A6 before-validator schema shape"
                                    )
                                model_type = getattr(callable_value, "__self__", None)
                                if model_type not in expected_a6_nodes[cls]:
                                    raise ValueError(
                                        "unexpected A6 authority schema node"
                                    )
                                function["function"] = call_local_a6_before(model_type)
                                replaced_a6_nodes.append(model_type)
                            elif callable_value is _persistent_json_extracted_candle:
                                if value.get("type") != "function-wrap" or function.get(
                                    "type"
                                ) != "with-info":
                                    raise ValueError(
                                        "unexpected A5 candle wrapper schema shape"
                                    )
                                function["function"] = call_local_nested_wrap(
                                    ExtractedCandleV0
                                )
                                replaced_nested_nodes.append(ExtractedCandleV0)
                            elif callable_value is _persistent_json_candle_extraction:
                                if value.get("type") != "function-wrap" or function.get(
                                    "type"
                                ) != "with-info":
                                    raise ValueError(
                                        "unexpected A5 extraction wrapper schema shape"
                                    )
                                function["function"] = call_local_nested_wrap(
                                    CandlePayloadExtractionV0
                                )
                                replaced_nested_nodes.append(
                                    CandlePayloadExtractionV0
                                )
                        for item in value.values():
                            replace_call_local_nodes(item)
                    elif isinstance(value, list | tuple):
                        for item in value:
                            replace_call_local_nodes(item)

                replace_call_local_nodes(call_schema)
                if sorted(item.__name__ for item in replaced_a6_nodes) != sorted(
                    item.__name__ for item in expected_a6_nodes[cls]
                ):
                    raise ValueError(
                        "unexpected A6 before-validator identity or count"
                    )
                if sorted(item.__name__ for item in replaced_nested_nodes) != sorted(
                    item.__name__ for item in expected_nested_nodes[cls]
                ):
                    raise ValueError(
                        "unexpected nested authority wrapper identity or count"
                    )

                call_validator = SchemaValidator(call_schema)
                return cast(
                    Self,
                    call_validator.validate_json(
                        canonical_bytes,
                        strict=strict,
                        extra=extra,
                        context=context,
                        by_alias=by_alias,
                        by_name=by_name,
                    ),
                )

            sensitive_function = sensitive_inner
            del sensitive_inner
            try:
                validated_model: BaseModel = sensitive_function()
            except Exception as original_error:
                neutral_errors: tuple[
                    tuple[tuple[str | int, ...], str, str], ...
                ] = ()
                if isinstance(original_error, ValidationError):
                    neutral_errors = tuple(
                        (
                            tuple(
                                item
                                if isinstance(item, str | int)
                                else str(item)
                                for item in error.get("loc", ())[:64]
                            ),
                            str(error.get("msg", "validation failed"))[:2000],
                            str(error.get("type", "validation_error"))[:200],
                        )
                        for error in original_error.errors(
                            include_url=False,
                            include_context=False,
                            include_input=False,
                        )[:256]
                    )
                    neutral_outcome: tuple[Any, ...] = (
                        "validation_error",
                        str(original_error.title)[:200],
                        neutral_errors,
                    )
                else:
                    neutral_outcome = (
                        "internal_error",
                        "isolated A6 JSON validation failed internally "
                        f"({type(original_error).__name__})",
                    )

                exception_stack: list[BaseException] = [original_error]
                seen_exceptions: set[int] = set()
                while exception_stack:
                    current_error = exception_stack.pop()
                    if id(current_error) in seen_exceptions:
                        continue
                    seen_exceptions.add(id(current_error))
                    if current_error.__context__ is not None:
                        exception_stack.append(current_error.__context__)
                    if current_error.__cause__ is not None:
                        exception_stack.append(current_error.__cause__)
                    if isinstance(current_error, BaseExceptionGroup):
                        exception_stack.extend(current_error.exceptions)
                    original_traceback = current_error.__traceback__
                    if original_traceback is not None:
                        traceback.clear_frames(original_traceback)
                    current_error.__traceback__ = None
                    current_error.__context__ = None
                    current_error.__cause__ = None

                del (
                    current_error,
                    exception_stack,
                    neutral_errors,
                    original_error,
                    original_traceback,
                    seen_exceptions,
                    sensitive_function,
                )
                return neutral_outcome
            return ("success", validated_model)

        outcome = isolated_runner()
        if outcome[0] == "success":
            validated_model = cast(Self, outcome[1])
            del isolated_runner, outcome
            return validated_model

        safe_outcome_kind = cast(str, outcome[0])
        safe_error_title_or_message = cast(str, outcome[1])
        safe_line_errors = cast(
            tuple[tuple[tuple[str | int, ...], str, str], ...],
            outcome[2] if safe_outcome_kind == "validation_error" else (),
        )
        del isolated_runner, outcome
        if safe_outcome_kind == "validation_error":
            raise ValidationError.from_exception_data(
                safe_error_title_or_message,
                [
                    {
                        "type": PydanticCustomError(
                            "a6_sanitized_validation",
                            f"{safe_message} (category: {safe_category})",
                        ),
                        "loc": safe_location,
                        "input": None,
                    }
                    for safe_location, safe_message, safe_category in safe_line_errors
                ],
            ) from None
        raise RuntimeError(safe_error_title_or_message) from None

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            raise TypeError("A6 authority models cannot be copied with updates")
        return super().model_copy(deep=deep)

    def copy(
        self,
        *,
        include: (Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None) = None,
        exclude: (Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None) = None,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if include is not None or exclude is not None or update is not None:
            raise TypeError("A6 authority models cannot be copied with field changes")
        return self.model_copy(deep=deep)

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        raise TypeError("A6 authority models cannot bypass validation with model_construct")


class CandleCrossSourceInputAuthorityV0(_A6AuthorityModel):
    side: CandleCrossSourceAuthoritySideV0
    source_event_id: Sha256Hex
    extraction_hash: Sha256Hex
    endpoint_id: Literal["hl-ws-mainnet-public", "hl-info-mainnet-public"]
    operation_type: Literal["candle", "candleSnapshot"]
    envelope_shape: CandleEnvelopeShapeV0

    @model_validator(mode="after")
    def validate_role(self) -> Self:
        if type(self) is not CandleCrossSourceInputAuthorityV0:
            raise ValueError("expected exact CandleCrossSourceInputAuthorityV0 authority object")
        if self.side is CandleCrossSourceAuthoritySideV0.WS:
            if self.endpoint_id != "hl-ws-mainnet-public":
                raise ValueError("WS authority requires the frozen WebSocket endpoint")
            if self.operation_type != "candle":
                raise ValueError("WS authority requires operation candle")
            if self.envelope_shape not in {
                CandleEnvelopeShapeV0.WS_DATA_CANDLE,
                CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY,
            }:
                raise ValueError("WS authority has invalid envelope shape")
        else:
            if self.endpoint_id != "hl-info-mainnet-public":
                raise ValueError("Info authority requires the frozen Info endpoint")
            if self.operation_type != "candleSnapshot":
                raise ValueError("Info authority requires operation candleSnapshot")
            if self.envelope_shape is not CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY:
                raise ValueError("Info authority has invalid envelope shape")
        return self


class CandleCrossSourceFieldDifferenceV0(_A6AuthorityModel):
    field_name: CandleCrossSourceComparableFieldV0
    ws_value: CandleCrossSourceComparableValueV0
    info_value: CandleCrossSourceComparableValueV0

    @model_validator(mode="after")
    def validate_value_kinds(self) -> Self:
        if type(self) is not CandleCrossSourceFieldDifferenceV0:
            raise ValueError("expected exact CandleCrossSourceFieldDifferenceV0 authority object")
        if self.field_name in {"close_time_ms", "trade_count"} and (
            _A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_RE.fullmatch(self.ws_value) is None
            or _A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_RE.fullmatch(self.info_value) is None
        ):
            raise ValueError(
                f"{self.field_name} difference values must be canonical nonnegative integers"
            )
        if self.ws_value == self.info_value:
            raise ValueError("field difference values must differ")
        return self


def _assert_exact_string(value: Any, field_name: str) -> None:
    if type(value) is not str:
        raise ValueError(f"{field_name} stored value must be an exact string")
    if value != value.strip():
        raise ValueError(f"{field_name} stored value must not be whitespace padded")


def _assert_exact_integer(value: Any, field_name: str) -> None:
    if type(value) is not int:
        raise ValueError(f"{field_name} stored value must be an exact integer")


def _assert_exact_model_storage(
    value: BaseModel,
    *,
    model_type: type[BaseModel],
    fields: frozenset[str],
    authority_name: str,
) -> None:
    if type(value) is not model_type:
        raise ValueError(f"expected exact {model_type.__name__} {authority_name}")
    stored_fields = set(value.__dict__)
    if stored_fields != fields:
        raise ValueError(f"{authority_name} current stored fields are incomplete or extra")
    if value.__pydantic_extra__:
        raise ValueError(f"{authority_name} current stored authority has extra fields")


def _validate_current_a5_candle(value: Any) -> ExtractedCandleV0:
    if not isinstance(value, BaseModel):
        raise ValueError("embedded candle must be an exact A5 authority object")
    _assert_exact_model_storage(
        value,
        model_type=ExtractedCandleV0,
        fields=_A5_CANDLE_FIELDS,
        authority_name="A5 candle authority",
    )
    candle = cast(ExtractedCandleV0, value)
    _assert_exact_string(candle.candle_logical_key, "candle_logical_key")
    _assert_exact_integer(candle.open_time_ms, "open_time_ms")
    _assert_exact_integer(candle.close_time_ms, "close_time_ms")
    _assert_exact_integer(candle.trade_count, "trade_count")
    for field_name in (
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_base",
    ):
        field_value = getattr(candle, field_name)
        if type(field_value) is not Decimal or not field_value.is_finite():
            raise ValueError(f"{field_name} stored value must be an exact finite Decimal")
    return candle


def _validate_current_a5_extraction(value: Any) -> CandlePayloadExtractionV0:
    if not isinstance(value, BaseModel):
        raise ValueError("extraction must be an exact A5 authority object")
    _assert_exact_model_storage(
        value,
        model_type=CandlePayloadExtractionV0,
        fields=_A5_EXTRACTION_FIELDS,
        authority_name="A5 extraction authority",
    )
    extraction = cast(CandlePayloadExtractionV0, value)
    for field_name in (
        "schema_version",
        "contract_id",
        "extraction_version",
        "source_id",
        "source_event_id",
        "payload_sha256",
        "endpoint_id",
        "operation_type",
        "coin",
        "candle_interval",
        "extraction_hash",
    ):
        _assert_exact_string(getattr(extraction, field_name), field_name)
    if type(extraction.envelope_shape) is not CandleEnvelopeShapeV0:
        raise ValueError("envelope_shape stored value must be exact CandleEnvelopeShapeV0")
    if type(extraction.candles) is not tuple:
        raise ValueError("candles stored value must be an exact tuple")
    for candle in extraction.candles:
        _validate_current_a5_candle(candle)
    return extraction


def _strict_revalidate_a5_extraction(
    value: Any,
    *,
    role: CandleCrossSourceAuthoritySideV0,
) -> CandlePayloadExtractionV0:
    if type(value) is not CandlePayloadExtractionV0:
        raise TypeError(f"{role.value} input must be exact CandlePayloadExtractionV0 authority")
    current = _validate_current_a5_extraction(value)
    payload = BaseModel.model_dump(current, mode="python", round_trip=True)
    extraction = CandlePayloadExtractionV0.model_validate(payload, strict=True)

    logical_keys: set[str] = set()
    for candle in extraction.candles:
        _validate_current_a5_candle(candle)
        expected_key = compute_candle_logical_key(
            source_id=extraction.source_id,
            coin=extraction.coin,
            candle_interval=extraction.candle_interval,
            open_time_ms=candle.open_time_ms,
        )
        if not hmac.compare_digest(candle.candle_logical_key, expected_key):
            raise ValueError("A5 candle logical key failed independent revalidation")
        if candle.candle_logical_key in logical_keys:
            raise ValueError("A5 extraction contains duplicate logical keys")
        logical_keys.add(candle.candle_logical_key)

    expected_hash = compute_candle_extraction_hash(extraction)
    if not hmac.compare_digest(extraction.extraction_hash, expected_hash):
        raise ValueError("A5 extraction hash failed independent revalidation")

    if role is CandleCrossSourceAuthoritySideV0.WS:
        if extraction.endpoint_id != "hl-ws-mainnet-public":
            raise ValueError("WS extraction requires the frozen WebSocket endpoint")
        if extraction.operation_type != "candle":
            raise ValueError("WS extraction requires operation candle")
        if extraction.envelope_shape not in {
            CandleEnvelopeShapeV0.WS_DATA_CANDLE,
            CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY,
        }:
            raise ValueError("WS extraction has invalid envelope shape")
    else:
        if extraction.endpoint_id != "hl-info-mainnet-public":
            raise ValueError("Info extraction requires the frozen Info endpoint")
        if extraction.operation_type != "candleSnapshot":
            raise ValueError("Info extraction requires operation candleSnapshot")
        if extraction.envelope_shape is not CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY:
            raise ValueError("Info extraction has invalid envelope shape")
    return extraction


def _revalidate_extracted_candle(value: Any) -> ExtractedCandleV0:
    current = _validate_current_a5_candle(value)
    payload = BaseModel.model_dump(current, mode="python", round_trip=True)
    return ExtractedCandleV0.model_validate(payload, strict=True)


def _comparison_wire_value(value: int | Decimal) -> str:
    if type(value) is int:
        return str(value)
    if type(value) is Decimal:
        return decimal_to_canonical_string(value)
    raise ValueError("comparison values must be exact integers or Decimals")


def _expected_differences(
    ws_candle: ExtractedCandleV0,
    info_candle: ExtractedCandleV0,
) -> tuple[CandleCrossSourceFieldDifferenceV0, ...]:
    differences: list[CandleCrossSourceFieldDifferenceV0] = []
    for field_name in CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS:
        ws_value = getattr(ws_candle, field_name)
        info_value = getattr(info_candle, field_name)
        if ws_value != info_value:
            differences.append(
                CandleCrossSourceFieldDifferenceV0.model_validate(
                    {
                        "field_name": field_name,
                        "ws_value": _comparison_wire_value(ws_value),
                        "info_value": _comparison_wire_value(info_value),
                    }
                )
            )
    return tuple(differences)


class CandleCrossSourceComparisonItemV0(_A6AuthorityModel):
    candle_logical_key: Sha256Hex
    source_id: Literal["hyperliquid-public-mainnet"]
    coin: Literal["BTC", "ETH"]
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"]
    open_time_ms: int = Field(ge=0)
    status: CandleCrossSourceComparisonStatusV0
    ws_candle: _A6ExtractedCandleV0 | None
    ws_authority: CandleCrossSourceInputAuthorityV0 | None
    info_candle: _A6ExtractedCandleV0 | None
    info_authority: CandleCrossSourceInputAuthorityV0 | None
    field_differences: tuple[CandleCrossSourceFieldDifferenceV0, ...]

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        if type(self) is not CandleCrossSourceComparisonItemV0:
            raise ValueError("expected exact CandleCrossSourceComparisonItemV0 authority object")
        expected_key = compute_candle_logical_key(
            source_id=self.source_id,
            coin=self.coin,
            candle_interval=self.candle_interval,
            open_time_ms=self.open_time_ms,
        )
        if not hmac.compare_digest(self.candle_logical_key, expected_key):
            raise ValueError("comparison logical key does not match identity fields")

        ws_candle = (
            _revalidate_extracted_candle(self.ws_candle) if self.ws_candle is not None else None
        )
        info_candle = (
            _revalidate_extracted_candle(self.info_candle)
            if self.info_candle is not None
            else None
        )
        if (ws_candle is None) != (self.ws_authority is None):
            raise ValueError("WS candle and authority must be present or absent together")
        if (info_candle is None) != (self.info_authority is None):
            raise ValueError("Info candle and authority must be present or absent together")

        for candle in (ws_candle, info_candle):
            if candle is None:
                continue
            if candle.open_time_ms != self.open_time_ms:
                raise ValueError("comparison candle open time conflicts with identity")
            if not hmac.compare_digest(candle.candle_logical_key, self.candle_logical_key):
                raise ValueError("comparison candle logical key conflicts with identity")

        if self.ws_authority is not None:
            if type(self.ws_authority) is not CandleCrossSourceInputAuthorityV0:
                raise ValueError("WS item authority must have exact A6 authority type")
            if self.ws_authority.side is not CandleCrossSourceAuthoritySideV0.WS:
                raise ValueError("WS item authority has reversed role")
        if self.info_authority is not None:
            if type(self.info_authority) is not CandleCrossSourceInputAuthorityV0:
                raise ValueError("Info item authority must have exact A6 authority type")
            if self.info_authority.side is not CandleCrossSourceAuthoritySideV0.INFO:
                raise ValueError("Info item authority has reversed role")

        if self.status is CandleCrossSourceComparisonStatusV0.WS_ONLY:
            if ws_candle is None or info_candle is not None:
                raise ValueError("WS_ONLY requires only a WS candle")
            expected_differences: tuple[CandleCrossSourceFieldDifferenceV0, ...] = ()
        elif self.status is CandleCrossSourceComparisonStatusV0.INFO_ONLY:
            if ws_candle is not None or info_candle is None:
                raise ValueError("INFO_ONLY requires only an Info candle")
            expected_differences = ()
        else:
            if ws_candle is None or info_candle is None:
                raise ValueError("MATCH and CONFLICT require both source candles")
            expected_differences = _expected_differences(ws_candle, info_candle)
            if self.status is CandleCrossSourceComparisonStatusV0.MATCH:
                if expected_differences:
                    raise ValueError("MATCH cannot contain differing comparable fields")
            elif not expected_differences:
                raise ValueError("CONFLICT requires at least one field difference")

        if self.field_differences != expected_differences:
            raise ValueError("field differences do not match exact comparable field authority")
        return self


def _model_json_mapping(value: BaseModel) -> dict[str, Any]:
    payload = BaseModel.model_dump(value, mode="json", round_trip=True)
    if type(payload) is not dict:
        raise ValueError("authority serialization must produce a JSON object")
    return payload


def _input_authority_payload(
    extraction: CandlePayloadExtractionV0,
    *,
    role: CandleCrossSourceAuthoritySideV0,
) -> dict[str, Any]:
    authority = CandleCrossSourceInputAuthorityV0.model_validate(
        {
            "side": role.value,
            "source_event_id": extraction.source_event_id,
            "extraction_hash": extraction.extraction_hash,
            "endpoint_id": extraction.endpoint_id,
            "operation_type": extraction.operation_type,
            "envelope_shape": extraction.envelope_shape.value,
        }
    )
    return _model_json_mapping(authority)


def _logical_key_map(
    extraction: CandlePayloadExtractionV0,
    *,
    role: CandleCrossSourceAuthoritySideV0,
) -> dict[str, ExtractedCandleV0]:
    by_key: dict[str, ExtractedCandleV0] = {}
    for candle in extraction.candles:
        if candle.candle_logical_key in by_key:
            raise ValueError(f"{role.value} extraction contains duplicate logical keys")
        by_key[candle.candle_logical_key] = candle
    return by_key


def _derive_reconciliation_payload(
    *,
    ws_extraction: Any,
    info_extraction: Any,
) -> dict[str, Any]:
    ws = _strict_revalidate_a5_extraction(
        ws_extraction,
        role=CandleCrossSourceAuthoritySideV0.WS,
    )
    info = _strict_revalidate_a5_extraction(
        info_extraction,
        role=CandleCrossSourceAuthoritySideV0.INFO,
    )
    if ws.source_id != info.source_id:
        raise ValueError("source identity mismatch")
    if ws.coin != info.coin:
        raise ValueError("coin identity mismatch")
    if ws.candle_interval != info.candle_interval:
        raise ValueError("candle interval identity mismatch")

    ws_by_key = _logical_key_map(ws, role=CandleCrossSourceAuthoritySideV0.WS)
    info_by_key = _logical_key_map(info, role=CandleCrossSourceAuthoritySideV0.INFO)
    ordered_keys = sorted(
        ws_by_key.keys() | info_by_key.keys(),
        key=lambda key: (
            (ws_by_key.get(key) or info_by_key[key]).open_time_ms,
            key,
        ),
    )
    ws_authority = _input_authority_payload(
        ws,
        role=CandleCrossSourceAuthoritySideV0.WS,
    )
    info_authority = _input_authority_payload(
        info,
        role=CandleCrossSourceAuthoritySideV0.INFO,
    )

    comparisons: list[dict[str, Any]] = []
    counts = {status: 0 for status in CandleCrossSourceComparisonStatusV0}
    for logical_key in ordered_keys:
        ws_candle = ws_by_key.get(logical_key)
        info_candle = info_by_key.get(logical_key)
        if ws_candle is None:
            status = CandleCrossSourceComparisonStatusV0.INFO_ONLY
            differences: tuple[CandleCrossSourceFieldDifferenceV0, ...] = ()
        elif info_candle is None:
            status = CandleCrossSourceComparisonStatusV0.WS_ONLY
            differences = ()
        else:
            differences = _expected_differences(ws_candle, info_candle)
            status = (
                CandleCrossSourceComparisonStatusV0.CONFLICT
                if differences
                else CandleCrossSourceComparisonStatusV0.MATCH
            )
        identity_candle = ws_candle or info_candle
        if identity_candle is None:
            raise ValueError("logical-key union produced no candle authority")

        comparison = CandleCrossSourceComparisonItemV0.model_validate(
            {
                "candle_logical_key": logical_key,
                "source_id": ws.source_id,
                "coin": ws.coin,
                "candle_interval": ws.candle_interval,
                "open_time_ms": identity_candle.open_time_ms,
                "status": status.value,
                "ws_candle": (
                    _model_json_mapping(ws_candle) if ws_candle is not None else None
                ),
                "ws_authority": ws_authority if ws_candle is not None else None,
                "info_candle": (
                    _model_json_mapping(info_candle) if info_candle is not None else None
                ),
                "info_authority": info_authority if info_candle is not None else None,
                "field_differences": [
                    _model_json_mapping(difference) for difference in differences
                ],
            }
        )
        comparisons.append(_model_json_mapping(comparison))
        counts[status] += 1

    return {
        "schema_version": A6_SCHEMA_VERSION,
        "contract_id": A6_CONTRACT_ID,
        "hash_version": A6_HASH_VERSION,
        "source_id": ws.source_id,
        "coin": ws.coin,
        "candle_interval": ws.candle_interval,
        "ws_extraction": _model_json_mapping(ws),
        "info_extraction": _model_json_mapping(info),
        "ws_source_event_id": ws.source_event_id,
        "ws_extraction_hash": ws.extraction_hash,
        "info_source_event_id": info.source_event_id,
        "info_extraction_hash": info.extraction_hash,
        "comparisons": comparisons,
        "match_count": counts[CandleCrossSourceComparisonStatusV0.MATCH],
        "conflict_count": counts[CandleCrossSourceComparisonStatusV0.CONFLICT],
        "ws_only_count": counts[CandleCrossSourceComparisonStatusV0.WS_ONLY],
        "info_only_count": counts[CandleCrossSourceComparisonStatusV0.INFO_ONLY],
    }


class CandleCrossSourceReconciliationV0(_A6AuthorityModel):
    schema_version: Literal["0.1.0"]
    contract_id: Literal["V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT"]
    hash_version: Literal["trader-assist-v0/candle-cross-source-reconciliation/v1"]
    source_id: Literal["hyperliquid-public-mainnet"]
    coin: Literal["BTC", "ETH"]
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"]
    ws_extraction: _A6CandlePayloadExtractionV0
    info_extraction: _A6CandlePayloadExtractionV0
    ws_source_event_id: Sha256Hex
    ws_extraction_hash: Sha256Hex
    info_source_event_id: Sha256Hex
    info_extraction_hash: Sha256Hex
    comparisons: tuple[CandleCrossSourceComparisonItemV0, ...]
    match_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    ws_only_count: int = Field(ge=0)
    info_only_count: int = Field(ge=0)
    reconciliation_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        if type(self) is not CandleCrossSourceReconciliationV0:
            raise ValueError("expected exact CandleCrossSourceReconciliationV0 authority object")

        expected_payload = _derive_reconciliation_payload(
            ws_extraction=self.ws_extraction,
            info_extraction=self.info_extraction,
        )
        actual_payload = _model_json_mapping(self)
        supplied_hash = actual_payload.pop("reconciliation_hash")

        if self.ws_source_event_id != self.ws_extraction.source_event_id:
            raise ValueError("WS scalar source event authority conflicts with embedded extraction")
        if self.ws_extraction_hash != self.ws_extraction.extraction_hash:
            raise ValueError("WS scalar extraction hash conflicts with embedded extraction")
        if self.info_source_event_id != self.info_extraction.source_event_id:
            raise ValueError(
                "Info scalar source event authority conflicts with embedded extraction"
            )
        if self.info_extraction_hash != self.info_extraction.extraction_hash:
            raise ValueError("Info scalar extraction hash conflicts with embedded extraction")

        if actual_payload != expected_payload:
            raise ValueError(
                "report does not match the exact complete logical-key union derivation"
            )

        expected_hash = compute_candle_cross_source_reconciliation_hash_from_payload(
            expected_payload
        )
        if not hmac.compare_digest(str(supplied_hash), expected_hash):
            raise ValueError("reconciliation_hash does not match canonical reconciliation")
        return self

    @classmethod
    def bind(
        cls,
        *,
        ws_extraction: CandlePayloadExtractionV0,
        info_extraction: CandlePayloadExtractionV0,
        **forbidden_authority: Any,
    ) -> CandleCrossSourceReconciliationV0:
        if forbidden_authority:
            raise ValueError("A6 reconciliation authority fields are implementation-controlled")
        payload = _derive_reconciliation_payload(
            ws_extraction=ws_extraction,
            info_extraction=info_extraction,
        )
        digest = compute_candle_cross_source_reconciliation_hash_from_payload(payload)
        return cls.model_validate({**payload, "reconciliation_hash": digest})


def _validate_wire_for_model(model_type: type[BaseModel], value: Any) -> None:
    if model_type is CandleCrossSourceInputAuthorityV0:
        _validate_input_authority_wire(value)
    elif model_type is CandleCrossSourceFieldDifferenceV0:
        _validate_field_difference_wire(value)
    elif model_type is CandleCrossSourceComparisonItemV0:
        _validate_comparison_wire(value)
    elif model_type is CandleCrossSourceReconciliationV0:
        _validate_report_wire(value)
    elif issubclass(model_type, _A6AuthorityModel):
        raise ValueError("expected exact A6 authority model class")
    else:
        raise ValueError("unsupported A6 authority model")


def _validate_current_a6_authority(value: BaseModel) -> None:
    if type(value) is CandleCrossSourceInputAuthorityV0:
        _assert_exact_model_storage(
            value,
            model_type=CandleCrossSourceInputAuthorityV0,
            fields=_A6_INPUT_AUTHORITY_FIELDS,
            authority_name="A6 input authority",
        )
        if type(value.side) is not CandleCrossSourceAuthoritySideV0:
            raise ValueError("side stored value must be exact A6 authority side")
        if type(value.envelope_shape) is not CandleEnvelopeShapeV0:
            raise ValueError("envelope_shape stored value must be exact A5 envelope shape")
        for field_name in (
            "source_event_id",
            "extraction_hash",
            "endpoint_id",
            "operation_type",
        ):
            _assert_exact_string(getattr(value, field_name), field_name)
        return

    if type(value) is CandleCrossSourceFieldDifferenceV0:
        _assert_exact_model_storage(
            value,
            model_type=CandleCrossSourceFieldDifferenceV0,
            fields=_A6_FIELD_DIFFERENCE_FIELDS,
            authority_name="A6 field difference",
        )
        for field_name in _A6_FIELD_DIFFERENCE_FIELDS:
            _assert_exact_string(getattr(value, field_name), field_name)
        return

    if type(value) is CandleCrossSourceComparisonItemV0:
        _assert_exact_model_storage(
            value,
            model_type=CandleCrossSourceComparisonItemV0,
            fields=_A6_COMPARISON_FIELDS,
            authority_name="A6 comparison",
        )
        for field_name in (
            "candle_logical_key",
            "source_id",
            "coin",
            "candle_interval",
        ):
            _assert_exact_string(getattr(value, field_name), field_name)
        _assert_exact_integer(value.open_time_ms, "open_time_ms")
        if type(value.status) is not CandleCrossSourceComparisonStatusV0:
            raise ValueError("status stored value must be exact A6 comparison status")
        for candle in (value.ws_candle, value.info_candle):
            if candle is not None:
                _validate_current_a5_candle(candle)
        for authority in (value.ws_authority, value.info_authority):
            if authority is not None:
                _validate_current_a6_authority(authority)
        if type(value.field_differences) is not tuple:
            raise ValueError("field_differences stored value must be an exact tuple")
        for difference in value.field_differences:
            _validate_current_a6_authority(difference)
        return

    if type(value) is CandleCrossSourceReconciliationV0:
        _assert_exact_model_storage(
            value,
            model_type=CandleCrossSourceReconciliationV0,
            fields=_A6_REPORT_FIELDS,
            authority_name="A6 report",
        )
        for field_name in (
            "schema_version",
            "contract_id",
            "hash_version",
            "source_id",
            "coin",
            "candle_interval",
            "ws_source_event_id",
            "ws_extraction_hash",
            "info_source_event_id",
            "info_extraction_hash",
            "reconciliation_hash",
        ):
            _assert_exact_string(getattr(value, field_name), field_name)
        _validate_current_a5_extraction(value.ws_extraction)
        _validate_current_a5_extraction(value.info_extraction)
        if type(value.comparisons) is not tuple:
            raise ValueError("comparisons stored value must be an exact tuple")
        for comparison in value.comparisons:
            _validate_current_a6_authority(comparison)
        for field_name in (
            "match_count",
            "conflict_count",
            "ws_only_count",
            "info_only_count",
        ):
            _assert_exact_integer(getattr(value, field_name), field_name)
        return

    raise ValueError("expected exact A6 authority object")


def compute_candle_cross_source_reconciliation_hash_from_payload(
    payload: Mapping[str, Any],
) -> str:
    return sha256_hex(A6_HASH_VERSION.encode() + b"\0" + canonical_json_bytes(dict(payload)))


def compute_candle_cross_source_reconciliation_hash(
    reconciliation: CandleCrossSourceReconciliationV0,
) -> str:
    payload = _model_json_mapping(reconciliation)
    payload.pop("reconciliation_hash", None)
    return compute_candle_cross_source_reconciliation_hash_from_payload(payload)
