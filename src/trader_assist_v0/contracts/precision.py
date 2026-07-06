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


def _scaled_integer(value: Decimal, scale: int) -> int:
    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError("precision value must be finite")
    coefficient = int("".join(str(digit) for digit in digits) or "0")
    shift = exponent + scale
    if shift < 0:
        raise ValueError("precision scale calculation is inconsistent")
    scaled = coefficient * (10**shift)
    return int(-scaled if sign else scaled)


def require_step_aligned(value: Decimal, step: Decimal, field_name: str) -> None:
    value_exponent = value.as_tuple().exponent
    step_exponent = step.as_tuple().exponent
    if not isinstance(value_exponent, int) or not isinstance(step_exponent, int):
        raise ValueError(f"{field_name} cannot be evaluated against precision step")
    scale = max(0, -value_exponent, -step_exponent)
    value_integer = _scaled_integer(value, scale)
    step_integer = _scaled_integer(step, scale)
    if step_integer <= 0 or value_integer % step_integer != 0:
        raise ValueError(f"{field_name} must align to precision step {step}")
