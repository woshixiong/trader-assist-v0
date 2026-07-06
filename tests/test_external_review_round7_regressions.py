from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal, DecimalTuple

import pytest
from pydantic import TypeAdapter, ValidationError

from trader_assist_v0.contracts.common import (
    FiniteDecimal,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    _validate_decimal_bounds,
)
from trader_assist_v0.contracts.precision import _scaled_integer, require_step_aligned

ZERO_DECIMALS = (
    "0",
    "-0",
    "0.000",
    "-0.000",
    "0E+1000000000",
    "-0E+1000000000",
    "0E-1000000000",
    "-0E-1000000000",
)
EXTREME_ZERO_DECIMALS = ZERO_DECIMALS[4:]


class SpoofedZeroDecimal(Decimal):
    def is_finite(self) -> bool:
        return False

    def as_tuple(self) -> DecimalTuple:
        return Decimal("1.25").as_tuple()

    def __str__(self) -> str:
        return "1.25"


def assert_canonical_zero(value: Decimal) -> None:
    assert type(value) is Decimal
    assert value == Decimal("0")
    assert Decimal.as_tuple(value) == Decimal("0").as_tuple()


@pytest.mark.parametrize("raw", ZERO_DECIMALS)
def test_validate_decimal_bounds_returns_canonical_zero(raw: str) -> None:
    assert_canonical_zero(_validate_decimal_bounds(Decimal(raw)))


def test_validate_decimal_bounds_preserves_nonzero_exact_value() -> None:
    value = Decimal("1.2300")
    validated = _validate_decimal_bounds(value)
    assert type(validated) is Decimal
    assert Decimal.as_tuple(validated) == Decimal.as_tuple(value)


@pytest.mark.parametrize("raw", ZERO_DECIMALS)
def test_public_decimal_types_canonicalize_zero_without_weakening_positivity(raw: str) -> None:
    value = Decimal(raw)
    assert_canonical_zero(TypeAdapter(FiniteDecimal).validate_python(value))
    assert_canonical_zero(TypeAdapter(NonNegativeFiniteDecimal).validate_python(value))
    with pytest.raises(ValidationError):
        TypeAdapter(PositiveFiniteDecimal).validate_python(value)


@pytest.mark.parametrize("raw", EXTREME_ZERO_DECIMALS)
@pytest.mark.parametrize("scale", (0, 2, 80))
def test_scaled_integer_short_circuits_extreme_zero(raw: str, scale: int) -> None:
    assert _scaled_integer(Decimal(raw), scale) == 0


@pytest.mark.parametrize("raw", EXTREME_ZERO_DECIMALS)
def test_extreme_zero_value_aligns_to_positive_step(raw: str) -> None:
    require_step_aligned(Decimal(raw), Decimal("0.01"), "quantity")


@pytest.mark.parametrize(
    "raw",
    (
        "0",
        "-0",
        "0E+1000000000",
        "-0E+1000000000",
        "0E-1000000000",
        "-0E-1000000000",
        "-0.01",
    ),
)
def test_zero_or_negative_step_is_rejected_before_scaling(raw: str) -> None:
    with pytest.raises(ValueError, match="quantity precision step must be positive"):
        require_step_aligned(Decimal("1.25"), Decimal(raw), "quantity")


@pytest.mark.parametrize("raw", ("0E+1000000000", "0E-1000000000"))
def test_malicious_decimal_subclass_zero_uses_real_numeric_value(raw: str) -> None:
    value = SpoofedZeroDecimal(raw)
    assert_canonical_zero(_validate_decimal_bounds(value))
    assert _scaled_integer(value, 2) == 0
    require_step_aligned(value, Decimal("0.01"), "quantity")
    assert_canonical_zero(TypeAdapter(FiniteDecimal).validate_python(value))
    assert_canonical_zero(TypeAdapter(NonNegativeFiniteDecimal).validate_python(value))
    with pytest.raises(ValidationError):
        TypeAdapter(PositiveFiniteDecimal).validate_python(value)


def test_ordinary_alignment_semantics_do_not_regress() -> None:
    require_step_aligned(Decimal("1.25"), Decimal("0.01"), "quantity")
    require_step_aligned(Decimal("1"), Decimal("1"), "quantity")
    require_step_aligned(Decimal("-1.25"), Decimal("0.01"), "quantity")
    require_step_aligned(Decimal("0"), Decimal("0.01"), "quantity")
    with pytest.raises(ValueError, match="quantity must align"):
        require_step_aligned(Decimal("1.251"), Decimal("0.01"), "quantity")
    with pytest.raises(ValueError, match="quantity precision step must be positive"):
        require_step_aligned(Decimal("1.25"), Decimal("0"), "quantity")
    with pytest.raises(ValueError, match="quantity precision step must be positive"):
        require_step_aligned(Decimal("1.25"), Decimal("-0.01"), "quantity")


def test_extreme_zero_alignment_is_bounded_under_address_space_limit() -> None:
    if not sys.platform.startswith("linux"):
        pytest.skip("RLIMIT_AS resource-safety regression is Linux-specific")

    script = r'''
import os
import resource
from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from trader_assist_v0.contracts.common import (
    FiniteDecimal,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    _validate_decimal_bounds,
)
from trader_assist_v0.contracts.precision import _scaled_integer, require_step_aligned

zero_values = (
    "0E+1000000000",
    "-0E+1000000000",
    "0E-1000000000",
    "-0E-1000000000",
)
finite_adapter = TypeAdapter(FiniteDecimal)
nonnegative_adapter = TypeAdapter(NonNegativeFiniteDecimal)
positive_adapter = TypeAdapter(PositiveFiniteDecimal)
for adapter in (finite_adapter, nonnegative_adapter, positive_adapter):
    try:
        adapter.validate_python(Decimal("1"))
    except ValidationError:
        pass

with open("/proc/self/statm", encoding="ascii") as statm:
    current_pages = int(statm.read().split()[0])
current_vms = current_pages * os.sysconf("SC_PAGE_SIZE")
limit = current_vms + 90 * 1024 * 1024
resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

try:
    for raw in zero_values:
        value = Decimal(raw)
        bounded = _validate_decimal_bounds(value)
        assert Decimal.as_tuple(bounded) == Decimal("0").as_tuple()
        assert _scaled_integer(value, 2) == 0
        require_step_aligned(value, Decimal("0.01"), "quantity")
        for adapter in (finite_adapter, nonnegative_adapter):
            result = adapter.validate_python(value)
            assert Decimal.as_tuple(result) == Decimal("0").as_tuple()
        try:
            positive_adapter.validate_python(value)
        except ValidationError:
            pass
        else:
            raise AssertionError("PositiveFiniteDecimal accepted numeric zero")

    for raw in ("0E+1000000000", "0E-1000000000"):
        try:
            require_step_aligned(Decimal("1.25"), Decimal(raw), "quantity")
        except ValueError:
            pass
        else:
            raise AssertionError("zero precision step was accepted")
except MemoryError:
    os.write(1, b"MEMORY_ERROR\n")
    raise SystemExit(2)
except Exception as exc:
    os.write(1, f"UNEXPECTED_{type(exc).__name__}\n".encode("ascii"))
    raise SystemExit(4) from exc

os.write(1, b"CONTROLLED_ZERO_ALIGNMENT\n")
'''
    completed = subprocess.run(
        [sys.executable, "-c", script],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode >= 0, completed.stderr
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "MEMORY_ERROR" not in completed.stdout
    assert "CONTROLLED_ZERO_ALIGNMENT" in completed.stdout
