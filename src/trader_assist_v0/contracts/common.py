from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, str_strip_whitespace=True, allow_inf_nan=False
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
    str, StringConstraints(min_length=3, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
]
VersionId = Annotated[str, StringConstraints(min_length=1, max_length=80)]
FiniteDecimal = Annotated[Decimal, AfterValidator(_finite_decimal)]
PositiveFiniteDecimal = Annotated[Decimal, Field(gt=Decimal("0")), AfterValidator(_finite_decimal)]
NonNegativeFiniteDecimal = Annotated[
    Decimal, Field(ge=Decimal("0")), AfterValidator(_finite_decimal)
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
    RAW_EVENT = "trader-assist-v0/raw-event/v1"
    NORMALIZED_EVENT = "trader-assist-v0/normalized-event/v1"
    STRATEGY_CANDIDATE = "trader-assist-v0/strategy-candidate/v1"
    AI_RECOMMENDATION = "trader-assist-v0/ai-recommendation/v1"
    ORDER_PACKAGE = "trader-assist-v0/order-package/v1"
    PROPOSAL = "trader-assist-v0/proposal/v1"
    HUMAN_DECISION = "trader-assist-v0/human-decision/v1"
    PROMOTION_RECORD = "trader-assist-v0/promotion-record/v1"
    EXECUTION_PERMIT = "trader-assist-v0/execution-permit/v1"
    EVIDENCE_BUNDLE = "trader-assist-v0/evidence-bundle/v1"


HASH_FIELDS_BY_DOMAIN: dict[HashDomainV0, frozenset[str]] = {
    HashDomainV0.RAW_EVENT: frozenset({"payload_sha256"}),
    HashDomainV0.NORMALIZED_EVENT: frozenset({"normalized_payload_sha256"}),
    HashDomainV0.STRATEGY_CANDIDATE: frozenset({"candidate_hash"}),
    HashDomainV0.AI_RECOMMENDATION: frozenset({"recommendation_hash"}),
    HashDomainV0.ORDER_PACKAGE: frozenset({"order_package_hash"}),
    HashDomainV0.PROPOSAL: frozenset({"proposal_hash"}),
    HashDomainV0.HUMAN_DECISION: frozenset({"human_decision_hash"}),
    HashDomainV0.PROMOTION_RECORD: frozenset({"promotion_record_hash"}),
    HashDomainV0.EXECUTION_PERMIT: frozenset({"permit_hash"}),
    HashDomainV0.EVIDENCE_BUNDLE: frozenset(),
}


def _normalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple, frozenset, set)):
        return [_normalize(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("cannot hash non-finite decimal")
        return format(value, "f")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def contract_hash(domain: HashDomainV0, model: BaseModel) -> str:
    payload = model.model_dump(mode="python")
    for field in HASH_FIELDS_BY_DOMAIN[domain]:
        payload.pop(field, None)
    return sha256_hex(domain.value.encode("utf-8") + b"\0" + canonical_json_bytes(payload))
