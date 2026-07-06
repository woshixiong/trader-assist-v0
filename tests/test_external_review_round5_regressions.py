from __future__ import annotations

import os
import runpy
import subprocess
import sys
from decimal import Decimal
from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from trader_assist_v0.contracts import (
    InstrumentPrecisionContractV0,
    OrderPackageV0,
    ProposalV0,
)
from trader_assist_v0.contracts.common import (
    MAX_DECIMAL_INTEGER_DIGITS,
    MAX_DECIMAL_SCALE,
    MAX_DECIMAL_SIGNIFICANT_DIGITS,
    MAX_DECIMAL_WIRE_LENGTH,
    FiniteDecimal,
    HashDomainV0,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    _analyze_decimal_shape,
    _raise_for_decimal_bounds,
    contract_hash,
    decimal_to_canonical_string,
)

_BASE = runpy.run_path("tests/test_round2_review_blockers.py")
candidate = _BASE["candidate"]
order = _BASE["order"]
proposal = _BASE["proposal"]
precision = _BASE["precision"]

EXTREME_DECIMALS = (
    Decimal("1E+100000000"),
    Decimal("1E-100000000"),
    Decimal("-1E+100000000"),
    Decimal("-1E-100000000"),
)


class _DecimalHashPayload(BaseModel):
    value: Decimal


@pytest.mark.parametrize("value", EXTREME_DECIMALS)
def test_extreme_exponents_fail_closed_at_all_decimal_entry_points(value: Decimal) -> None:
    for decimal_type in (FiniteDecimal, NonNegativeFiniteDecimal, PositiveFiniteDecimal):
        with pytest.raises(ValidationError):
            TypeAdapter(decimal_type).validate_python(value)

    with pytest.raises(ValueError, match="decimal bounds exceeded"):
        decimal_to_canonical_string(value)

    with pytest.raises(ValueError, match="decimal bounds exceeded"):
        contract_hash(HashDomainV0.ORDER_PACKAGE, _DecimalHashPayload(value=value))


def test_extreme_exponents_remain_controlled_under_address_space_limit() -> None:
    if not sys.platform.startswith("linux"):
        pytest.skip("RLIMIT_AS resource-safety regression is Linux-specific")

    script = r'''
import os
import resource
import sys
from decimal import Decimal
from pydantic import TypeAdapter, ValidationError
from trader_assist_v0.contracts.common import (
    FiniteDecimal,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    decimal_to_canonical_string,
)

adapters = tuple(
    TypeAdapter(decimal_type)
    for decimal_type in (FiniteDecimal, NonNegativeFiniteDecimal, PositiveFiniteDecimal)
)
for adapter in adapters:
    adapter.validate_python(Decimal("1"))
values = (
    Decimal("1E+100000000"),
    Decimal("1E-100000000"),
    Decimal("-1E+100000000"),
    Decimal("-1E-100000000"),
)

pid = os.fork()
if pid == 0:
    try:
        with open("/proc/self/statm", encoding="ascii") as statm:
            current_pages = int(statm.read().split()[0])
        current_vms = current_pages * os.sysconf("SC_PAGE_SIZE")
        limit = current_vms + 90 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        for value in values:
            for adapter in adapters:
                try:
                    adapter.validate_python(value)
                except (ValidationError, ValueError):
                    pass
                else:
                    raise AssertionError((adapter, value))
            try:
                decimal_to_canonical_string(value)
            except ValueError:
                pass
            else:
                raise AssertionError(value)
    except MemoryError:
        os.write(1, b"MEMORY_ERROR\n")
        os._exit(2)
    except BaseException:
        os.write(1, b"UNEXPECTED_ERROR\n")
        os._exit(4)
    os.write(1, b"CONTROLLED_VALIDATION_ERROR\n")
    os._exit(0)

_, status = os.waitpid(pid, 0)
if os.WIFSIGNALED(status):
    print(f"SIGNAL_{os.WTERMSIG(status)}")
    raise SystemExit(3)
raise SystemExit(os.waitstatus_to_exitcode(status))
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
    assert "CONTROLLED_VALIDATION_ERROR" in completed.stdout


@pytest.mark.parametrize(
    ("factory", "updates"),
    [
        (precision, {"price_tick": Decimal("1E-100000000")}),
        (order, {"quantity": Decimal("1E+100000000")}),
        (order, {"max_slippage_bps": Decimal("1E-100000000")}),
        (candidate, {"entry_zone_low": Decimal("1E+100000000")}),
        (candidate, {"stop_price": Decimal("1E-100000000")}),
        (candidate, {"target_prices": (Decimal("1E+100000000"),)}),
    ],
)
def test_contract_bind_entry_points_reject_extreme_exponents(
    factory: Any, updates: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        factory(**updates)


@pytest.mark.parametrize("construction", ["model_copy", "model_construct"])
def test_tampered_nested_order_and_hash_recomputation_fail_closed(
    construction: str,
) -> None:
    exact = order()
    extreme = Decimal("1E+100000000")
    if construction == "model_copy":
        tampered = BaseModel.model_copy(exact, update={"quantity": extreme})
    else:
        payload = BaseModel.model_dump(exact, mode="python", round_trip=True)
        payload["quantity"] = extreme
        tampered = BaseModel.model_construct.__func__(OrderPackageV0, **payload)

    with pytest.raises(ValidationError):
        proposal(tampered)
    with pytest.raises(ValueError, match="decimal bounds exceeded"):
        contract_hash(HashDomainV0.ORDER_PACKAGE, tampered)


def test_proposal_direct_nested_payload_rejects_extreme_decimal() -> None:
    exact = proposal()
    payload = BaseModel.model_dump(exact, mode="python", round_trip=True)
    payload["order_package"]["max_slippage_bps"] = Decimal("1E-100000000")
    with pytest.raises(ValidationError):
        ProposalV0.model_validate(payload)


def test_significant_digit_boundary_has_no_off_by_one() -> None:
    accepted = Decimal("1" * MAX_DECIMAL_SIGNIFICANT_DIGITS)
    rejected = Decimal("1" * (MAX_DECIMAL_SIGNIFICANT_DIGITS + 1))
    assert TypeAdapter(PositiveFiniteDecimal).validate_python(accepted) == accepted
    with pytest.raises(ValidationError, match=r"significant digits exceed 80 \(actual 81\)"):
        TypeAdapter(PositiveFiniteDecimal).validate_python(rejected)


def test_integer_digit_positive_exponent_and_wire_boundaries() -> None:
    accepted = Decimal(f"1E+{MAX_DECIMAL_INTEGER_DIGITS - 1}")
    rejected = Decimal(f"1E+{MAX_DECIMAL_INTEGER_DIGITS}")
    rendered = decimal_to_canonical_string(accepted)
    assert len(rendered) == MAX_DECIMAL_WIRE_LENGTH
    assert rendered == "1" + "0" * (MAX_DECIMAL_INTEGER_DIGITS - 1)
    with pytest.raises(
        ValueError,
        match=(
            r"integer digits exceed 80 \(actual 81\).*"
            r"canonical wire length exceeds 80 \(projected 81\)"
        ),
    ):
        decimal_to_canonical_string(rejected)


def test_negative_exponent_effective_wire_boundary_has_no_off_by_one() -> None:
    accepted = Decimal(f"1E-{MAX_DECIMAL_WIRE_LENGTH - 2}")
    rejected = Decimal(f"1E-{MAX_DECIMAL_WIRE_LENGTH - 1}")
    assert len(decimal_to_canonical_string(accepted)) == MAX_DECIMAL_WIRE_LENGTH
    with pytest.raises(ValueError, match=r"canonical wire length exceeds 80 \(projected 81\)"):
        decimal_to_canonical_string(rejected)


def test_scale_guard_accepts_exact_limit_and_rejects_first_excess() -> None:
    at_limit = _analyze_decimal_shape(Decimal(f"1E-{MAX_DECIMAL_SCALE}"))
    first_excess = _analyze_decimal_shape(Decimal(f"1E-{MAX_DECIMAL_SCALE + 1}"))
    assert at_limit.scale == MAX_DECIMAL_SCALE
    assert first_excess.scale == MAX_DECIMAL_SCALE + 1

    with pytest.raises(ValueError) as at_limit_error:
        _raise_for_decimal_bounds(at_limit)
    assert "scale exceeds 80 (actual 80)" not in str(at_limit_error.value)
    assert "canonical wire length" in str(at_limit_error.value)

    with pytest.raises(ValueError, match=r"scale exceeds 80 \(actual 81\)"):
        _raise_for_decimal_bounds(first_excess)


def test_zero_and_safe_rendering_controls_are_unchanged() -> None:
    assert decimal_to_canonical_string(Decimal("-0E+100000000")) == "0"
    assert decimal_to_canonical_string(Decimal("1.2300")) == "1.23"
    assert decimal_to_canonical_string(Decimal("1E+2")) == "100"
    assert decimal_to_canonical_string(Decimal("1E-2")) == "0.01"


def test_exact_model_controls_still_bind_and_roundtrip() -> None:
    precision_contract = precision()
    package = order(instrument_precision=precision_contract)
    proposed = proposal(package)
    assert InstrumentPrecisionContractV0.model_validate(
        BaseModel.model_dump(precision_contract, mode="python", round_trip=True)
    ) == precision_contract
    assert OrderPackageV0.model_validate_json(package.model_dump_json()) == package
    assert ProposalV0.model_validate_json(proposed.model_dump_json()) == proposed
