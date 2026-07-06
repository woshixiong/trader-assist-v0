from __future__ import annotations

import hashlib
import hmac
import json
from contextvars import ContextVar
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _finite_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("decimal value must be finite")
    return value


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
FiniteDecimal = Annotated[Decimal, AfterValidator(_finite_decimal)]
PositiveFiniteDecimal = Annotated[
    Decimal,
    Field(gt=Decimal("0")),
    AfterValidator(_finite_decimal),
]
NonNegativeFiniteDecimal = Annotated[
    Decimal,
    Field(ge=Decimal("0")),
    AfterValidator(_finite_decimal),
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
    if not value.is_finite():
        raise ValueError("cannot hash non-finite decimal")
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _normalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="python"))
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
    payload = model.model_dump(mode="python")
    payload.pop(HASH_FIELD_BY_DOMAIN[domain], None)
    material = domain.value.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    return sha256_hex(material)


_HASH_BIND_TARGET: ContextVar[type[BaseModel] | None] = ContextVar(
    "trader_assist_v0_hash_bind_target",
    default=None,
)


class HashBoundModel(StrictModel):
    hash_domain: ClassVar[HashDomainV0]
    hash_field: ClassVar[str]

    @model_validator(mode="after")
    def verify_contract_hash(self) -> Self:
        if _HASH_BIND_TARGET.get() is type(self):
            return self
        actual = getattr(self, self.hash_field)
        expected = contract_hash(self.hash_domain, self)
        if not hmac.compare_digest(actual, expected):
            raise ValueError(
                f"{self.hash_field} does not match canonical {self.hash_domain.value} payload"
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
