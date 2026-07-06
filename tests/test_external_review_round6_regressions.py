from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from decimal import Decimal, DecimalTuple

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_core import PydanticSerializationError

from trader_assist_v0.contracts import OrderPackageV0, ProposalV0
from trader_assist_v0.contracts.common import (
    FiniteDecimal,
    HashBoundModel,
    HashDomainV0,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    _coerce_exact_decimal,
    canonical_json_bytes,
    contract_hash,
    decimal_to_canonical_string,
    revalidate_hash_bound_instance,
    revalidate_nested_hash_bound,
)
from trader_assist_v0.contracts.precision import require_step_aligned

_BASE = runpy.run_path("tests/test_round2_review_blockers.py")
_R5 = runpy.run_path("tests/test_external_review_round5_regressions.py")
candidate = _BASE["candidate"]
order = _BASE["order"]
proposal = _BASE["proposal"]
precision = _R5["precision"]


class SpoofedDecimal(Decimal):
    def is_finite(self) -> bool:
        return True

    def as_tuple(self) -> DecimalTuple:
        return Decimal("1.25").as_tuple()

    def __str__(self) -> str:
        return "1.25"


class WrongViewDecimal(Decimal):
    def is_finite(self) -> bool:
        return False

    def as_tuple(self) -> DecimalTuple:
        return Decimal("9.99").as_tuple()

    def __str__(self) -> str:
        return "9.99"


class _DecimalHashPayload(BaseModel):
    value: Decimal


def _hash_payload(value: Decimal) -> _DecimalHashPayload:
    return BaseModel.model_construct.__func__(_DecimalHashPayload, value=value)


def _tampered_packages(value: Decimal) -> tuple[OrderPackageV0, tuple[OrderPackageV0, ...]]:
    valid = order()
    copied = BaseModel.model_copy(valid, update={"quantity": value})
    payload = BaseModel.model_dump(valid, mode="python", round_trip=True)
    payload["quantity"] = value
    constructed = BaseModel.model_construct.__func__(OrderPackageV0, **payload)
    return valid, (copied, constructed)


EXTREME_VALUES = (
    "1E+1000000000",
    "1E-1000000000",
    "-1E+1000000000",
    "-1E-1000000000",
)


@pytest.mark.parametrize("raw", EXTREME_VALUES)
def test_spoofed_extreme_decimal_uses_real_value_at_all_entry_points(raw: str) -> None:
    evil = SpoofedDecimal(raw)
    with pytest.raises(ValueError, match="decimal bounds exceeded"):
        decimal_to_canonical_string(evil)
    with pytest.raises(ValueError, match="decimal bounds exceeded"):
        canonical_json_bytes({"value": evil})
    with pytest.raises(ValueError, match="decimal bounds exceeded"):
        contract_hash(HashDomainV0.ORDER_PACKAGE, _hash_payload(evil))

    for decimal_type in (FiniteDecimal, PositiveFiniteDecimal, NonNegativeFiniteDecimal):
        with pytest.raises(ValidationError):
            TypeAdapter(decimal_type).validate_python(evil)


@pytest.mark.parametrize("raw", ("NaN", "Infinity", "-Infinity"))
def test_spoofed_nonfinite_decimal_is_rejected_everywhere(raw: str) -> None:
    evil = SpoofedDecimal(raw)
    with pytest.raises(ValueError, match="finite"):
        decimal_to_canonical_string(evil)
    with pytest.raises(ValueError, match="non-finite|finite"):
        canonical_json_bytes({"value": evil})
    with pytest.raises(ValueError, match="non-finite|finite"):
        contract_hash(HashDomainV0.ORDER_PACKAGE, _hash_payload(evil))

    for decimal_type in (FiniteDecimal, PositiveFiniteDecimal, NonNegativeFiniteDecimal):
        with pytest.raises(ValidationError):
            TypeAdapter(decimal_type).validate_python(evil)

    with pytest.raises(ValidationError):
        precision(price_tick=evil)
    with pytest.raises(ValidationError):
        order(quantity=evil)
    with pytest.raises(ValidationError):
        candidate(entry_zone_low=evil)


def test_actual_misalignment_cannot_be_hidden_by_virtual_tuple() -> None:
    evil = SpoofedDecimal("1.251")
    with pytest.raises(ValueError, match="quantity must align"):
        require_step_aligned(evil, Decimal("0.01"), "quantity")
    with pytest.raises(ValidationError, match="quantity must align"):
        order(quantity=evil)
    with pytest.raises(ValidationError, match="limit_price must align"):
        order(limit_price=evil)
    with pytest.raises(ValidationError, match="entry_zone_low must align"):
        candidate(entry_zone_low=evil)
    with pytest.raises(ValidationError, match=r"target_prices\[0\] must align"):
        candidate(target_prices=(evil,))


def test_actual_step_cannot_be_hidden_by_virtual_tuple() -> None:
    evil_step = SpoofedDecimal("0.011")
    with pytest.raises(ValueError, match=r"precision step 0\.011"):
        require_step_aligned(Decimal("1.25"), evil_step, "quantity")

    precision_contract = precision(quantity_step=evil_step)
    assert type(precision_contract.quantity_step) is Decimal
    assert precision_contract.quantity_step == Decimal("0.011")
    with pytest.raises(ValidationError, match="quantity must align"):
        order(instrument_precision=precision_contract, quantity=Decimal("1.25"))


def test_model_copy_and_construct_revalidate_real_misaligned_value() -> None:
    valid, tampered_packages = _tampered_packages(SpoofedDecimal("1.251"))
    for tampered in tampered_packages:
        with pytest.raises(ValidationError):
            OrderPackageV0.model_validate(tampered)
        assert contract_hash(HashDomainV0.ORDER_PACKAGE, tampered) != valid.order_package_hash
        dumped = json.loads(tampered.model_dump_json())
        assert dumped["quantity"] == "1.251"
        assert dumped["quantity"] != "1.25"


def test_model_copy_and_construct_extreme_value_fail_closed() -> None:
    _, tampered_packages = _tampered_packages(SpoofedDecimal("1E+1000000000"))
    for tampered in tampered_packages:
        with pytest.raises(ValidationError):
            OrderPackageV0.model_validate(tampered)
        with pytest.raises(ValueError, match="decimal bounds exceeded"):
            contract_hash(HashDomainV0.ORDER_PACKAGE, tampered)
        with pytest.raises(PydanticSerializationError, match="decimal bounds exceeded"):
            tampered.model_dump_json()


def test_nested_proposal_rejects_tampered_decimal_subclasses() -> None:
    _, tampered_packages = _tampered_packages(SpoofedDecimal("1.251"))
    valid_proposal = proposal()
    for tampered in tampered_packages:
        with pytest.raises((ValidationError, ValueError)):
            proposal(tampered)
        with pytest.raises((ValidationError, ValueError)):
            revalidate_hash_bound_instance(tampered, OrderPackageV0)
        with pytest.raises((ValidationError, ValueError)):
            revalidate_nested_hash_bound(tampered, OrderPackageV0)

        payload = BaseModel.model_dump(valid_proposal, mode="python", round_trip=True)
        payload["order_package"] = tampered
        with pytest.raises(ValidationError):
            ProposalV0.model_validate(payload)


def test_legal_subclass_is_exactified_and_matches_all_roundtrips() -> None:
    evil = WrongViewDecimal("1.25")
    exact = _coerce_exact_decimal(evil)
    assert type(exact) is Decimal
    assert exact == Decimal("1.25")
    assert decimal_to_canonical_string(evil) == "1.25"
    assert canonical_json_bytes({"value": evil}) == b'{"value":"1.25"}'

    for decimal_type in (FiniteDecimal, PositiveFiniteDecimal, NonNegativeFiniteDecimal):
        validated = TypeAdapter(decimal_type).validate_python(evil)
        assert type(validated) is Decimal
        assert validated == Decimal("1.25")

    package = order(quantity=evil)
    ordinary = order(quantity=Decimal("1.25"))
    assert type(package.quantity) is Decimal
    assert package.quantity == Decimal("1.25")
    assert package.order_package_hash == ordinary.order_package_hash

    python_payload = BaseModel.model_dump(package, mode="python", round_trip=True)
    assert type(python_payload["quantity"]) is Decimal
    assert python_payload["quantity"] == Decimal("1.25")
    assert json.loads(package.model_dump_json())["quantity"] == "1.25"
    assert OrderPackageV0.model_validate(python_payload) == package
    assert OrderPackageV0.model_validate_json(package.model_dump_json()) == package
    assert contract_hash(
        HashDomainV0.ORDER_PACKAGE, _hash_payload(evil)
    ) == contract_hash(HashDomainV0.ORDER_PACKAGE, _hash_payload(Decimal("1.25")))


def test_hash_bound_config_preserves_strictness_and_revalidates_instances() -> None:
    assert HashBoundModel.model_config["revalidate_instances"] == "always"
    assert HashBoundModel.model_config["extra"] == "forbid"
    assert HashBoundModel.model_config["frozen"] is True
    assert HashBoundModel.model_config["str_strip_whitespace"] is True
    assert HashBoundModel.model_config["allow_inf_nan"] is False

    valid = order()
    revalidated = OrderPackageV0.model_validate(valid)
    assert revalidated == valid
    assert revalidated is not valid


def test_spoofed_extreme_decimal_remains_controlled_under_address_space_limit() -> None:
    if not sys.platform.startswith("linux"):
        pytest.skip("RLIMIT_AS resource-safety regression is Linux-specific")

    script = r'''
import os
import resource
from decimal import Decimal

from pydantic import BaseModel, TypeAdapter, ValidationError

from trader_assist_v0.contracts.common import (
    FiniteDecimal,
    HashDomainV0,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    canonical_json_bytes,
    contract_hash,
    decimal_to_canonical_string,
)
from trader_assist_v0.contracts.precision import require_step_aligned


class SpoofedDecimal(Decimal):
    def is_finite(self):
        return True

    def as_tuple(self):
        return Decimal("1.25").as_tuple()

    def __str__(self):
        return "1.25"


class Payload(BaseModel):
    value: Decimal


adapters = tuple(
    TypeAdapter(decimal_type)
    for decimal_type in (FiniteDecimal, PositiveFiniteDecimal, NonNegativeFiniteDecimal)
)
for adapter in adapters:
    adapter.validate_python(Decimal("1"))

evil = SpoofedDecimal("1E+1000000000")
payload = BaseModel.model_construct.__func__(Payload, value=evil)


def expect_controlled_failure(operation):
    try:
        operation()
    except (ValidationError, ValueError):
        return
    raise AssertionError(operation)


try:
    with open("/proc/self/statm", encoding="ascii") as statm:
        current_pages = int(statm.read().split()[0])
    current_vms = current_pages * os.sysconf("SC_PAGE_SIZE")
    limit = current_vms + 90 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    expect_controlled_failure(lambda: decimal_to_canonical_string(evil))
    expect_controlled_failure(lambda: canonical_json_bytes({"value": evil}))
    expect_controlled_failure(lambda: contract_hash(HashDomainV0.ORDER_PACKAGE, payload))
    expect_controlled_failure(lambda: require_step_aligned(evil, Decimal("0.01"), "quantity"))
    for adapter in adapters:
        expect_controlled_failure(lambda adapter=adapter: adapter.validate_python(evil))
except MemoryError:
    os.write(1, b"MEMORY_ERROR\n")
    raise SystemExit(2)
except Exception as exc:
    os.write(1, f"UNEXPECTED_{type(exc).__name__}\n".encode("ascii"))
    raise SystemExit(4) from exc

os.write(1, b"CONTROLLED_VALIDATION_ERROR\n")
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
