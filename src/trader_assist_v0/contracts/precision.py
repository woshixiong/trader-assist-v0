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
    _validate_decimal_bounds,
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
    exact = _validate_decimal_bounds(value)
    sign, digits, exponent = Decimal.as_tuple(exact)
    coefficient = int("".join(str(digit) for digit in digits) or "0")
    if coefficient == 0:
        return 0
    if not isinstance(exponent, int):
        raise ValueError("precision value must be finite")
    shift = exponent + scale
    if shift < 0:
        raise ValueError("precision scale calculation is inconsistent")
    scaled = coefficient * (10**shift)
    return int(-scaled if sign else scaled)


def require_step_aligned(value: Decimal, step: Decimal, field_name: str) -> None:
    exact_value = _validate_decimal_bounds(value)
    exact_step = _validate_decimal_bounds(step)
    if exact_step <= 0:
        raise ValueError(f"{field_name} precision step must be positive")
    value_exponent = Decimal.as_tuple(exact_value).exponent
    step_exponent = Decimal.as_tuple(exact_step).exponent
    if not isinstance(value_exponent, int) or not isinstance(step_exponent, int):
        raise ValueError(f"{field_name} cannot be evaluated against precision step")
    scale = max(0, -value_exponent, -step_exponent)
    value_integer = _scaled_integer(exact_value, scale)
    step_integer = _scaled_integer(exact_step, scale)
    if step_integer <= 0 or value_integer % step_integer != 0:
        raise ValueError(f"{field_name} must align to precision step {exact_step}")
