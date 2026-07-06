from __future__ import annotations

from decimal import Decimal
from typing import Literal

from .common import (
    HashBoundModel,
    HashDomainV0,
    OpaqueId,
    PositiveFiniteDecimal,
    Sha256Hex,
    UTCDateTime,
    VersionId,
)


class InstrumentPrecisionContractV0(HashBoundModel):
    hash_domain = HashDomainV0.INSTRUMENT_PRECISION_CONTRACT
    hash_field = "contract_hash"

    schema_version: VersionId
    contract_id: OpaqueId
    contract_hash: Sha256Hex
    contract_version: VersionId
    venue: OpaqueId
    symbol: Literal["ETH"] = "ETH"
    price_tick: PositiveFiniteDecimal
    quantity_step: PositiveFiniteDecimal
    source_metadata_version: VersionId
    source_snapshot_hash: Sha256Hex
    created_at: UTCDateTime


def require_step_aligned(value: Decimal, step: Decimal, field_name: str) -> None:
    if value % step != 0:
        raise ValueError(f"{field_name} must align to precision step {step}")
