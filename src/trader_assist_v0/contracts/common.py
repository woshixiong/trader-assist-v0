from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, StringConstraints


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UTCDateTime = Annotated[AwareDatetime, AfterValidator(_as_utc)]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
OpaqueId = Annotated[
    str, StringConstraints(min_length=3, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
]
VersionId = Annotated[str, StringConstraints(min_length=1, max_length=80)]


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


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
