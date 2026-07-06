from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Set
from contextvars import ContextVar
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, ClassVar, NamedTuple, Self, TypeVar

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    ValidationInfo,
    model_validator,
)

MAX_DECIMAL_WIRE_LENGTH = 80
MAX_DECIMAL_SIGNIFICANT_DIGITS = 80
MAX_DECIMAL_SCALE = 80
MAX_DECIMAL_INTEGER_DIGITS = 80

FINITE_DECIMAL_STRING_PATTERN = (
    r"^(?:0|[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]+|"
    r"-(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*))$"
)
NONNEGATIVE_DECIMAL_STRING_PATTERN = r"^(?:0|[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]+)$"
POSITIVE_DECIMAL_STRING_PATTERN = (
    r"^(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)$"
)

FiniteDecimalString = Annotated[
    str,
    StringConstraints(pattern=FINITE_DECIMAL_STRING_PATTERN, max_length=MAX_DECIMAL_WIRE_LENGTH),
]
NonNegativeFiniteDecimalString = Annotated[
    str,
    StringConstraints(
        pattern=NONNEGATIVE_DECIMAL_STRING_PATTERN,
        max_length=MAX_DECIMAL_WIRE_LENGTH,
    ),
]
PositiveFiniteDecimalString = Annotated[
    str,
    StringConstraints(pattern=POSITIVE_DECIMAL_STRING_PATTERN, max_length=MAX_DECIMAL_WIRE_LENGTH),
]

_FINITE_DECIMAL_WIRE_RE = re.compile(FINITE_DECIMAL_STRING_PATTERN)
_POSITIVE_DECIMAL_WIRE_RE = re.compile(POSITIVE_DECIMAL_STRING_PATTERN)
_NONNEGATIVE_DECIMAL_WIRE_RE = re.compile(NONNEGATIVE_DECIMAL_STRING_PATTERN)


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _coerce_exact_decimal(value: Decimal) -> Decimal:
    """Return a base Decimal preserving the input's real internal value."""
    exact = Decimal(value)
    if type(exact) is not Decimal:
        raise TypeError("decimal conversion must produce an exact base Decimal")
    if not Decimal.is_finite(exact):
        raise ValueError("decimal value must be finite")
    return exact


def _finite_decimal(value: Decimal) -> Decimal:
    return _coerce_exact_decimal(value)


class _DecimalShape(NamedTuple):
    sign: int
    coefficient: str
    exponent: int
    significant_digits: int
    integer_digits: int
    scale: int
    projected_length: int


def _trim_decimal_coefficient(value: Decimal) -> tuple[int, str, int]:
    exact = _coerce_exact_decimal(value)
    sign, digits, exponent = Decimal.as_tuple(exact)
    if not isinstance(exponent, int):
        raise ValueError("decimal exponent must be finite")
    coefficient = "".join(str(digit) for digit in digits) or "0"
    if not coefficient.strip("0"):
        return 0, "0", 0
    if exponent < 0:
        trimmed = coefficient.rstrip("0")
        exponent += len(coefficient) - len(trimmed)
        coefficient = trimmed
    return sign, coefficient, exponent


def _analyze_decimal_shape(value: Decimal) -> _DecimalShape:
    sign, coefficient, exponent = _trim_decimal_coefficient(value)
    if coefficient == "0":
        return _DecimalShape(0, "0", 0, 0, 1, 0, 1)

    coefficient_length = len(coefficient)
    significant_digits = len(coefficient.lstrip("0"))
    if exponent >= 0:
        integer_digits = coefficient_length + exponent
        scale = 0
        unsigned_output_length = coefficient_length + exponent
    else:
        split = coefficient_length + exponent
        scale = -exponent
        if split > 0:
            integer_digits = split
            unsigned_output_length = coefficient_length + 1
        else:
            integer_digits = 1
            unsigned_output_length = 2 - exponent
    projected_length = unsigned_output_length + (1 if sign else 0)
    return _DecimalShape(
        sign,
        coefficient,
        exponent,
        significant_digits,
        integer_digits,
        scale,
        projected_length,
    )


def _raise_for_decimal_bounds(shape: _DecimalShape) -> None:
    failures: list[str] = []
    if shape.significant_digits > MAX_DECIMAL_SIGNIFICANT_DIGITS:
        failures.append(
            f"significant digits exceed {MAX_DECIMAL_SIGNIFICANT_DIGITS} "
            f"(actual {shape.significant_digits})"
        )
    if shape.scale > MAX_DECIMAL_SCALE:
        failures.append(f"scale exceeds {MAX_DECIMAL_SCALE} (actual {shape.scale})")
    if shape.integer_digits > MAX_DECIMAL_INTEGER_DIGITS:
        failures.append(
            f"integer digits exceed {MAX_DECIMAL_INTEGER_DIGITS} "
            f"(actual {shape.integer_digits})"
        )
    if shape.projected_length > MAX_DECIMAL_WIRE_LENGTH:
        failures.append(
            f"canonical wire length exceeds {MAX_DECIMAL_WIRE_LENGTH} "
            f"(projected {shape.projected_length})"
        )
    if failures:
        raise ValueError("decimal bounds exceeded: " + "; ".join(failures))


def decimal_to_canonical_string(value: Decimal) -> str:
    """Render an exact finite Decimal without consulting the ambient Decimal context."""
    shape = _analyze_decimal_shape(value)
    _raise_for_decimal_bounds(shape)
    if shape.coefficient == "0":
        return "0"
    if shape.exponent >= 0:
        rendered = shape.coefficient + ("0" * shape.exponent)
    else:
        split = len(shape.coefficient) + shape.exponent
        if split > 0:
            rendered = shape.coefficient[:split] + "." + shape.coefficient[split:]
        else:
            rendered = "0." + ("0" * (-split)) + shape.coefficient
    return ("-" if shape.sign else "") + rendered


def _validate_decimal_bounds(value: Decimal) -> Decimal:
    exact = _coerce_exact_decimal(value)
    shape = _analyze_decimal_shape(exact)
    _raise_for_decimal_bounds(shape)
    return exact


def _validate_decimal_wire(
    value: Any,
    info: ValidationInfo,
    pattern: re.Pattern[str],
    semantic_name: str,
) -> Any:
    if isinstance(value, str):
        if len(value) > MAX_DECIMAL_WIRE_LENGTH:
            raise ValueError(
                f"{semantic_name} decimal JSON string exceeds "
                f"{MAX_DECIMAL_WIRE_LENGTH} characters"
            )
        if pattern.fullmatch(value) is None:
            raise ValueError(f"{semantic_name} decimal JSON string has invalid syntax")
        return value
    if info.mode == "json":
        raise ValueError(f"{semantic_name} decimal JSON value must be a string")
    return value


def _finite_decimal_wire(value: Any, info: ValidationInfo) -> Any:
    return _validate_decimal_wire(value, info, _FINITE_DECIMAL_WIRE_RE, "finite")


def _positive_decimal_wire(value: Any, info: ValidationInfo) -> Any:
    return _validate_decimal_wire(value, info, _POSITIVE_DECIMAL_WIRE_RE, "positive")


def _nonnegative_decimal_wire(value: Any, info: ValidationInfo) -> Any:
    return _validate_decimal_wire(value, info, _NONNEGATIVE_DECIMAL_WIRE_RE, "nonnegative")


UTCDateTime = Annotated[AwareDatetime, AfterValidator(_as_utc)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
GitCommitOid = Annotated[str, StringConstraints(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
OpaqueId = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
VersionId = Annotated[str, StringConstraints(min_length=1, max_length=80)]
FiniteDecimal = Annotated[
    Decimal,
    BeforeValidator(_finite_decimal_wire),
    AfterValidator(_finite_decimal),
    AfterValidator(_validate_decimal_bounds),
    PlainSerializer(decimal_to_canonical_string, return_type=str, when_used="json"),
]
PositiveFiniteDecimal = Annotated[
    Decimal,
    BeforeValidator(_positive_decimal_wire),
    Field(gt=Decimal("0")),
    AfterValidator(_finite_decimal),
    AfterValidator(_validate_decimal_bounds),
    PlainSerializer(decimal_to_canonical_string, return_type=str, when_used="json"),
]
NonNegativeFiniteDecimal = Annotated[
    Decimal,
    BeforeValidator(_nonnegative_decimal_wire),
    Field(ge=Decimal("0")),
    AfterValidator(_finite_decimal),
    AfterValidator(_validate_decimal_bounds),
    PlainSerializer(decimal_to_canonical_string, return_type=str, when_used="json"),
]


class EnvironmentV0(StrEnum):
    READ_ONLY = "READ_ONLY"
    SHADOW = "SHADOW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    TESTNET = "TESTNET"
    MAINNET_PILOT = "MAINNET_PILOT"


class DataLayerV0(StrEnum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class SourceAuthorityV0(StrEnum):
    AUTHORITATIVE = "AUTHORITATIVE"
    SEED = "SEED"
    REFERENCE = "REFERENCE"
    ARCHIVE = "ARCHIVE"
    REJECTED = "REJECTED"


class HashDomainV0(StrEnum):
    REQUIRED_FEED_CONTRACT = "trader-assist-v0/required-feed-contract/v1"
    INSTRUMENT_PRECISION_CONTRACT = "trader-assist-v0/instrument-precision-contract/v1"
    STRATEGY_CANDIDATE = "trader-assist-v0/strategy-candidate/v1"
    AI_RECOMMENDATION = "trader-assist-v0/ai-recommendation/v1"
    ORDER_PACKAGE = "trader-assist-v0/order-package/v1"
    PROPOSAL = "trader-assist-v0/proposal/v1"
    HUMAN_DECISION = "trader-assist-v0/human-decision/v1"
    PROMOTION_RECORD = "trader-assist-v0/promotion-record/v1"
    EXECUTION_PERMIT = "trader-assist-v0/execution-permit/v1"


HASH_FIELD_BY_DOMAIN: dict[HashDomainV0, str] = {
    HashDomainV0.REQUIRED_FEED_CONTRACT: "contract_hash",
    HashDomainV0.INSTRUMENT_PRECISION_CONTRACT: "contract_hash",
    HashDomainV0.STRATEGY_CANDIDATE: "candidate_hash",
    HashDomainV0.AI_RECOMMENDATION: "recommendation_hash",
    HashDomainV0.ORDER_PACKAGE: "order_package_hash",
    HashDomainV0.PROPOSAL: "proposal_hash",
    HashDomainV0.HUMAN_DECISION: "human_decision_hash",
    HashDomainV0.PROMOTION_RECORD: "promotion_record_hash",
    HashDomainV0.EXECUTION_PERMIT: "permit_hash",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


def _normalize_decimal(value: Decimal) -> str:
    try:
        exact = _coerce_exact_decimal(value)
    except ValueError as exc:
        raise ValueError("cannot hash non-finite decimal") from exc
    return decimal_to_canonical_string(exact)


def _normalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize(BaseModel.model_dump(value, mode="python", round_trip=True))
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, set | frozenset):
        normalized_items = [_normalize(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )
    if isinstance(value, list | tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return _normalize_decimal(value)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def contract_hash(domain: HashDomainV0, model: BaseModel) -> str:
    payload = BaseModel.model_dump(model, mode="python", round_trip=True)
    payload.pop(HASH_FIELD_BY_DOMAIN[domain], None)
    material = domain.value.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    return sha256_hex(material)


_HASH_BIND_TARGET: ContextVar[type[BaseModel] | None] = ContextVar(
    "trader_assist_v0_hash_bind_target",
    default=None,
)


class HashBoundModel(StrictModel):
    model_config = ConfigDict(revalidate_instances="always")

    hash_domain: ClassVar[HashDomainV0]
    hash_field: ClassVar[str]

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            raise TypeError(
                "hash-bound models cannot be copied with updates; construct a new bound model"
            )
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
            raise TypeError(
                "hash-bound models cannot be copied with field changes; construct a new bound model"
            )
        return self.model_copy(deep=deep)

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        raise TypeError(
            "hash-bound models cannot bypass validation with model_construct; "
            "use bind or model_validate"
        )

    @model_validator(mode="after")
    def verify_contract_hash(self) -> Self:
        model_type = type(self)
        if _HASH_BIND_TARGET.get() is model_type:
            return self
        actual = object.__getattribute__(self, model_type.hash_field)
        expected = contract_hash(model_type.hash_domain, self)
        if not hmac.compare_digest(actual, expected):
            raise ValueError(
                f"{model_type.hash_field} does not match canonical "
                f"{model_type.hash_domain.value} payload"
            )
        return self

    @classmethod
    def bind(cls, **payload: Any) -> Self:
        if cls.hash_field in payload:
            raise ValueError(f"{cls.hash_field} must not be supplied to bind()")
        token = _HASH_BIND_TARGET.set(cls)
        try:
            provisional = cls.model_validate({**payload, cls.hash_field: "0" * 64})
        finally:
            _HASH_BIND_TARGET.reset(token)
        digest = contract_hash(cls.hash_domain, provisional)
        return cls.model_validate({**payload, cls.hash_field: digest})


HashBoundT = TypeVar("HashBoundT", bound=HashBoundModel)


def revalidate_hash_bound_instance(
    value: HashBoundT,
    expected_type: type[HashBoundT],
) -> HashBoundT:
    """Return a newly validated exact-class authority object from non-virtual field storage."""
    if type(value) is not expected_type:
        raise ValueError(f"expected exact {expected_type.__name__} authority object")
    payload = BaseModel.model_dump(value, mode="python", round_trip=True)
    validated = expected_type.model_validate(payload)
    actual = object.__getattribute__(validated, expected_type.hash_field)
    expected = contract_hash(expected_type.hash_domain, validated)
    if not hmac.compare_digest(actual, expected):
        raise ValueError(
            f"{expected_type.hash_field} does not match canonical authority payload"
        )
    return validated


def revalidate_nested_hash_bound[T: HashBoundModel](
    value: Any,
    expected_type: type[T],
    *,
    json_mode: bool = False,
) -> Any:
    """Revalidate nested HashBound values before outer semantics and hash material are read."""
    if isinstance(value, HashBoundModel):
        return revalidate_hash_bound_instance(value, expected_type)
    if isinstance(value, dict):
        if json_mode:
            validated = expected_type.model_validate_json(
                json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            )
            revalidate_hash_bound_instance(validated, expected_type)
            return dict(value)
        validated = expected_type.model_validate(value)
        return revalidate_hash_bound_instance(validated, expected_type)
    return value
