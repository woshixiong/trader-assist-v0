from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_UP, Decimal, localcontext
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, TypeAdapter, ValidationError

from scripts.export_schemas import render
from trader_assist_v0.contracts import (
    EnvironmentV0,
    HashBoundModel,
    InstrumentPrecisionContractV0,
    OrderPackageV0,
    PlaybookIdV0,
    PromotionRecordV0,
    PromotionStateV0,
    ProposalV0,
    RequiredFeedContractV0,
    StrategyCandidateV0,
    validate_execution_permit_bindings,
    validate_promotion_chain,
)
from trader_assist_v0.contracts.common import (
    MAX_DECIMAL_INTEGER_DIGITS,
    MAX_DECIMAL_SCALE,
    MAX_DECIMAL_SIGNIFICANT_DIGITS,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
)

_BASE = runpy.run_path("tests/test_round2_review_blockers.py")
NOW = _BASE["NOW"]
H = _BASE["H"]
candidate = _BASE["candidate"]
order = _BASE["order"]
proposal = _BASE["proposal"]
decision = _BASE["decision"]
execution_permit = _BASE["permit"]
_promotion_record = _BASE["promotion_record"]


def _rebind(model: HashBoundModel, **updates: Any) -> Any:
    payload = BaseModel.model_dump(model, mode="python", round_trip=True)
    payload.pop(type(model).hash_field)
    payload.update(updates)
    return type(model).bind(**payload)


def precision(**updates: Any) -> InstrumentPrecisionContractV0:
    return _rebind(_BASE["precision"](), **updates)


def feed_contract(
    *,
    playbook_id: str = "LQS-FR",
    feeds: frozenset[str] = frozenset({"hl-bbo", "hl-trades"}),
) -> RequiredFeedContractV0:
    return _rebind(
        _BASE["feed_contract"](),
        playbook_id=playbook_id,
        mandatory_feed_ids=feeds,
    )


PROMOTION_STEPS = (
    (PromotionStateV0.DRAFT, EnvironmentV0.READ_ONLY),
    (PromotionStateV0.SHADOW, EnvironmentV0.SHADOW),
    (PromotionStateV0.HUMAN_REVIEW, EnvironmentV0.HUMAN_REVIEW),
    (PromotionStateV0.TESTNET_ELIGIBLE, EnvironmentV0.TESTNET),
    (PromotionStateV0.MAINNET_PILOT_ELIGIBLE, EnvironmentV0.MAINNET_PILOT),
    (PromotionStateV0.MAINNET_PILOT_ACTIVE, EnvironmentV0.MAINNET_PILOT),
)


def promotion(
    previous: PromotionRecordV0 | None,
    index: int,
    *,
    reviewed_at: datetime | None = None,
    activated_at: datetime | None = None,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> PromotionRecordV0:
    state, environment = PROMOTION_STEPS[index]
    review_time = reviewed_at or NOW - timedelta(minutes=30 - index * 4)
    activation_time = activated_at
    if index > 0 and activation_time is None:
        activation_time = review_time + timedelta(minutes=1)
    return _promotion_record(
        previous,
        state,
        environment,
        index,
        review_time,
        activation_time,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def raw_promotion(
    previous: PromotionRecordV0 | None,
    index: int,
    *,
    reviewed_at: datetime,
    activated_at: datetime | None,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
    state: PromotionStateV0 | None = None,
    environment: EnvironmentV0 | None = None,
) -> PromotionRecordV0:
    default_state, default_environment = PROMOTION_STEPS[index]
    resolved_state = state or default_state
    resolved_environment = environment or default_environment
    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "promotion_record_id": f"raw-promotion-{index:03d}",
        "playbook_id": PlaybookIdV0.LQS_FR,
        "strategy_version": "lqs-fr.0.1",
        "parameter_version": "params.0.1",
        "feature_version": "features.0.1",
        "label_version": "labels.0.1",
        "required_feed_contract_id": "feeds-lqs-fr-001",
        "required_feed_contract_version": "feeds.0.1",
        "required_feed_contract_hash": feed_contract().contract_hash,
        "state": resolved_state,
        "environment": resolved_environment,
        "evidence_dataset_ids": ()
        if resolved_state is PromotionStateV0.DRAFT
        else (f"raw-dataset-{index:03d}",),
        "reviewed_by": "reviewer-001",
        "reviewed_at": reviewed_at,
        "activated_at": activated_at,
        "expires_at": expires_at,
        "revoked_at": revoked_at,
        "rationale": f"raw transition to {resolved_state.value}",
    }
    if previous is not None:
        payload.update(
            predecessor_record_id=previous.promotion_record_id,
            predecessor_record_hash=previous.promotion_record_hash,
            predecessor_state=previous.state,
        )
    return HashBoundModel.bind.__func__(PromotionRecordV0, **payload)


def test_nested_required_feed_subclass_getattribute_attack_is_rejected() -> None:
    exact = feed_contract(playbook_id="BRK-AR", feeds=frozenset({"fake-feed"}))

    class MaliciousFeed(RequiredFeedContractV0):
        def __getattribute__(self, name: str) -> Any:
            if name == "playbook_id":
                return "LQS-FR"
            if name == "mandatory_feed_ids":
                return frozenset({"hl-bbo", "hl-trades"})
            return super().__getattribute__(name)

    malicious = BaseModel.model_construct.__func__(
        MaliciousFeed, **BaseModel.model_dump(exact, mode="python", round_trip=True)
    )
    with pytest.raises(ValidationError, match="expected exact RequiredFeedContractV0"):
        candidate(required_feed_contract=malicious)


def test_nested_precision_subclass_virtual_quantity_step_is_rejected() -> None:
    exact = precision(quantity_step=Decimal("1"))

    class MaliciousPrecision(InstrumentPrecisionContractV0):
        def __getattribute__(self, name: str) -> Any:
            if name == "quantity_step":
                return Decimal("0.01")
            return super().__getattribute__(name)

    malicious = BaseModel.model_construct.__func__(
        MaliciousPrecision, **BaseModel.model_dump(exact, mode="python", round_trip=True)
    )
    with pytest.raises(ValidationError, match="expected exact InstrumentPrecisionContractV0"):
        order(instrument_precision=malicious, quantity=Decimal("1.25"))


def test_nested_order_package_subclass_property_shadow_is_rejected() -> None:
    exact = order()

    class MaliciousOrder(OrderPackageV0):
        @property
        def virtual_playbook(self) -> str:
            return "wrong-playbook"

        def __getattribute__(self, name: str) -> Any:
            if name == "valid_until":
                return NOW + timedelta(days=30)
            return super().__getattribute__(name)

    malicious = BaseModel.model_construct.__func__(
        MaliciousOrder, **BaseModel.model_dump(exact, mode="python", round_trip=True)
    )
    with pytest.raises(ValidationError, match="expected exact OrderPackageV0"):
        proposal(malicious)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda value: BaseModel.model_copy(value, update={"quantity_step": Decimal("0.0001")}),
        lambda value: BaseModel.copy(value, update={"quantity_step": Decimal("0.0001")}),
        lambda value: super(HashBoundModel, value).model_copy(
            update={"quantity_step": Decimal("0.0001")}
        ),
    ],
)
def test_nested_stale_hash_copy_paths_are_rejected(tamper: Any) -> None:
    with pytest.raises(ValidationError, match="contract_hash"):
        order(instrument_precision=tamper(precision()))


def test_nested_stale_hash_model_construct_is_rejected() -> None:
    exact = precision()
    payload = BaseModel.model_dump(exact, mode="python", round_trip=True)
    payload["quantity_step"] = Decimal("0.0001")
    stale = BaseModel.model_construct.__func__(InstrumentPrecisionContractV0, **payload)
    with pytest.raises(ValidationError, match="contract_hash"):
        order(instrument_precision=stale)


def test_nested_instance_method_shadow_is_ignored_by_base_dump() -> None:
    exact = precision()

    def poisoned_model_dump(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("instance model_dump shadow must not execute")

    object.__setattr__(exact, "model_dump", poisoned_model_dump)
    result = order(instrument_precision=exact)
    assert type(result.instrument_precision) is InstrumentPrecisionContractV0
    assert result.instrument_precision.contract_hash == exact.contract_hash


def test_nested_exact_objects_match_dict_and_json_roundtrips() -> None:
    exact_candidate = candidate()
    exact_order = order()
    exact_proposal = proposal(exact_order)
    for model_type, exact in (
        (StrategyCandidateV0, exact_candidate),
        (OrderPackageV0, exact_order),
        (ProposalV0, exact_proposal),
    ):
        from_dict = model_type.model_validate(
            BaseModel.model_dump(exact, mode="python", round_trip=True)
        )
        from_json = model_type.model_validate_json(exact.model_dump_json())
        assert from_dict == exact
        assert from_json == exact


@pytest.mark.parametrize(
    ("predecessor_index", "boundary_kind"),
    [(1, "expires"), (1, "revoked"), (2, "expires"), (3, "revoked"), (4, "expires")],
)
def test_invalid_intermediate_promotion_window_is_rejected(
    predecessor_index: int, boundary_kind: str
) -> None:
    records: list[PromotionRecordV0] = []
    previous: PromotionRecordV0 | None = None
    for index in range(predecessor_index + 1):
        successor_review = NOW - timedelta(minutes=30 - (index + 1) * 4)
        kwargs: dict[str, datetime] = {}
        if index == predecessor_index:
            kwargs[f"{boundary_kind}_at"] = successor_review
        previous = promotion(previous, index, **kwargs)
        records.append(previous)
    with pytest.raises(ValueError, match="predecessor (expired|revoked)"):
        promotion(previous, predecessor_index + 1)


@pytest.mark.parametrize("boundary_at", ["reviewed_at", "activated_at"])
@pytest.mark.parametrize("boundary_kind", ["expires_at", "revoked_at"])
def test_transition_equal_to_predecessor_boundary_fails_closed(
    boundary_at: str, boundary_kind: str
) -> None:
    draft = promotion(None, 0)
    shadow_review = NOW - timedelta(minutes=26)
    shadow_activation = shadow_review + timedelta(minutes=1)
    review_review = NOW - timedelta(minutes=22)
    review_activation = review_review + timedelta(minutes=1)
    boundary = review_review if boundary_at == "reviewed_at" else review_activation
    shadow = promotion(
        draft,
        1,
        reviewed_at=shadow_review,
        activated_at=shadow_activation,
        **{boundary_kind: boundary},
    )
    with pytest.raises(ValueError, match="predecessor (expired|revoked)"):
        promotion(shadow, 2, reviewed_at=review_review, activated_at=review_activation)


def test_revocation_after_completed_transition_is_not_retroactive() -> None:
    draft = promotion(None, 0)
    review_review = NOW - timedelta(minutes=22)
    review_activation = review_review + timedelta(minutes=1)
    shadow = promotion(draft, 1, revoked_at=review_activation + timedelta(minutes=1))
    human_review = promotion(shadow, 2, reviewed_at=review_review, activated_at=review_activation)
    validate_promotion_chain((draft, shadow, human_review))


def test_draft_expiry_and_revocation_use_reviewed_at_as_effective_start() -> None:
    with pytest.raises(ValidationError, match="expiry must be after"):
        promotion(None, 0, expires_at=NOW - timedelta(minutes=30))
    with pytest.raises(ValidationError, match="revocation must be after"):
        promotion(None, 0, revoked_at=NOW - timedelta(minutes=30))


def test_quarantined_recovery_is_fail_closed_and_retired_is_terminal() -> None:
    draft = promotion(None, 0)
    shadow = promotion(draft, 1)
    quarantine = raw_promotion(
        shadow,
        2,
        reviewed_at=NOW - timedelta(minutes=22),
        activated_at=NOW - timedelta(minutes=21),
        state=PromotionStateV0.QUARANTINED,
        environment=EnvironmentV0.SHADOW,
    )
    recovered = raw_promotion(
        quarantine,
        1,
        reviewed_at=NOW - timedelta(minutes=18),
        activated_at=NOW - timedelta(minutes=17),
    )
    with pytest.raises(ValueError, match="QUARANTINED recovery|does not permit"):
        validate_promotion_chain((draft, shadow, quarantine, recovered))
    retired = raw_promotion(
        shadow,
        2,
        reviewed_at=NOW - timedelta(minutes=22),
        activated_at=NOW - timedelta(minutes=21),
        state=PromotionStateV0.RETIRED,
        environment=EnvironmentV0.SHADOW,
    )
    after_retired = raw_promotion(
        retired,
        1,
        reviewed_at=NOW - timedelta(minutes=18),
        activated_at=NOW - timedelta(minutes=17),
    )
    with pytest.raises(ValueError, match="RETIRED is terminal|does not permit"):
        validate_promotion_chain((draft, shadow, retired, after_retired))


def _invalid_intermediate_testnet_history() -> tuple[PromotionRecordV0, ...]:
    draft = raw_promotion(None, 0, reviewed_at=NOW - timedelta(minutes=30), activated_at=None)
    shadow = raw_promotion(
        draft,
        1,
        reviewed_at=NOW - timedelta(minutes=26),
        activated_at=NOW - timedelta(minutes=25),
        expires_at=NOW - timedelta(minutes=23),
    )
    review = raw_promotion(
        shadow, 2, reviewed_at=NOW - timedelta(minutes=22), activated_at=NOW - timedelta(minutes=21)
    )
    testnet = raw_promotion(
        review, 3, reviewed_at=NOW - timedelta(minutes=18), activated_at=NOW - timedelta(minutes=17)
    )
    return (draft, shadow, review, testnet)


def test_permit_issuance_rejects_invalid_intermediate_record() -> None:
    proposed = proposal()
    approved = decision(proposed)
    history = _invalid_intermediate_testnet_history()
    permit = execution_permit(proposed, approved, history[-1])
    with pytest.raises(ValueError, match="invalid promotion authority.*predecessor expired"):
        validate_execution_permit_bindings(
            permit, proposed, approved, history[-1], promotion_history=history
        )


def test_complete_legal_promotion_chain_control() -> None:
    records: list[PromotionRecordV0] = []
    previous: PromotionRecordV0 | None = None
    for index in range(4):
        previous = promotion(previous, index)
        records.append(previous)
    assert validate_promotion_chain(tuple(records)) == tuple(records)


@pytest.mark.parametrize("value", ["0", "0.1", "1", "1.25", "3000.125"])
def test_canonical_decimal_wire_acceptance(value: str) -> None:
    nonnegative = TypeAdapter(NonNegativeFiniteDecimal)
    assert nonnegative.validate_json(json.dumps(value)) == Decimal(value)
    if Decimal(value) > 0:
        positive = TypeAdapter(PositiveFiniteDecimal)
        assert positive.validate_json(json.dumps(value)) == Decimal(value)


@pytest.mark.parametrize(
    "value", ["+1", ".5", "1.", "01", "00.1", "-0", "-0.0", "1e3", "NaN", "Infinity"]
)
def test_noncanonical_decimal_wire_rejected_by_runtime_and_schema(value: str) -> None:
    positive = TypeAdapter(PositiveFiniteDecimal)
    with pytest.raises(ValidationError):
        positive.validate_json(json.dumps(value))
    schema = json.loads(render(OrderPackageV0))["properties"]["quantity"]
    assert not Draft202012Validator(schema).is_valid(value)


def test_json_number_and_unquoted_plus_are_rejected() -> None:
    positive = TypeAdapter(PositiveFiniteDecimal)
    for raw_json in ("1", "1.25", "+1"):
        with pytest.raises(ValidationError):
            positive.validate_json(raw_json)


@pytest.mark.parametrize("value", ["0", "0.0"])
def test_positive_zero_wire_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(PositiveFiniteDecimal).validate_json(json.dumps(value))


@pytest.mark.parametrize("value", ["-1", "-0.1"])
def test_negative_nonnegative_wire_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(NonNegativeFiniteDecimal).validate_json(json.dumps(value))


def _mutated_json(model: BaseModel, path: tuple[str, ...], value: Any) -> str:
    payload = json.loads(model.model_dump_json())
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return json.dumps(payload, separators=(",", ":"))


@pytest.mark.parametrize("bad", ["+1", ".5", "1.", "01", "00.1", "-0", "1e3"])
def test_required_models_reject_noncanonical_decimal_json(bad: str) -> None:
    model_cases = (
        (InstrumentPrecisionContractV0, precision(), ("price_tick",)),
        (OrderPackageV0, order(), ("quantity",)),
        (StrategyCandidateV0, candidate(), ("entry_zone_low",)),
        (ProposalV0, proposal(), ("order_package", "quantity")),
    )
    for model_type, model, path in model_cases:
        with pytest.raises(ValidationError):
            model_type.model_validate_json(_mutated_json(model, path, bad))
        schema = json.loads(render(model_type))
        payload = json.loads(_mutated_json(model, path, bad))
        assert not Draft202012Validator(schema).is_valid(payload)


@pytest.mark.parametrize(
    ("model_type", "model", "path"),
    [
        (InstrumentPrecisionContractV0, precision(), ("price_tick",)),
        (OrderPackageV0, order(), ("quantity",)),
        (StrategyCandidateV0, candidate(), ("instrument_precision", "price_tick")),
        (ProposalV0, proposal(), ("order_package", "quantity")),
    ],
)
def test_required_models_reject_json_number_decimal_tokens(
    model_type: type[BaseModel], model: BaseModel, path: tuple[str, ...]
) -> None:
    mutated = _mutated_json(model, path, 1.25)
    with pytest.raises(ValidationError, match="must be a string"):
        model_type.model_validate_json(mutated)
    schema = json.loads(render(model_type))
    assert not Draft202012Validator(schema).is_valid(json.loads(mutated))


def _assert_decimal_json_strings(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                key
                in {
                    "price_tick",
                    "quantity_step",
                    "quantity",
                    "limit_price",
                    "max_slippage_bps",
                    "entry_zone_low",
                    "entry_zone_high",
                    "stop_price",
                }
                and item is not None
            ):
                assert isinstance(item, str)
            _assert_decimal_json_strings(item)
    elif isinstance(value, list):
        for item in value:
            _assert_decimal_json_strings(item)


def test_model_dump_json_and_schema_share_canonical_decimal_contract() -> None:
    models = (precision(), order(), candidate(), proposal())
    for model in models:
        payload = model.model_dump(mode="json")
        _assert_decimal_json_strings(payload)
        assert Draft202012Validator(json.loads(render(type(model)))).is_valid(payload)
    assert (
        order(max_slippage_bps=Decimal("-0.0")).model_dump(mode="json")["max_slippage_bps"] == "0"
    )


def _hash_bundle(precision_value: int, rounding: str) -> tuple[str, str, str]:
    with localcontext() as context:
        context.prec = precision_value
        context.rounding = rounding
        package = order(
            instrument_precision=precision(
                quantity_step=Decimal("0.0000000000000000000000000000001")
            ),
            quantity=Decimal("1.1234567890123456789012345678901"),
            max_slippage_bps=Decimal("2.1234567890123456789012345678901"),
        )
        proposed = proposal(package)
        return (
            package.instrument_precision.contract_hash,
            package.order_package_hash,
            proposed.proposal_hash,
        )


@pytest.mark.parametrize("precision_value", [6, 28, 50, 100])
@pytest.mark.parametrize("rounding", [ROUND_HALF_EVEN, ROUND_DOWN, ROUND_UP, ROUND_FLOOR])
def test_decimal_hashes_ignore_context_precision_and_rounding(
    precision_value: int, rounding: str
) -> None:
    assert _hash_bundle(precision_value, rounding) == _hash_bundle(100, ROUND_HALF_EVEN)


def test_values_differing_after_29th_digit_do_not_collide() -> None:
    step = Decimal("0.0000000000000000000000000000001")
    precision_contract = precision(quantity_step=step)
    first = order(
        instrument_precision=precision_contract,
        quantity=Decimal("1.1234567890123456789012345678901"),
    )
    second = order(
        instrument_precision=precision_contract,
        quantity=Decimal("1.1234567890123456789012345678902"),
    )
    assert first.order_package_hash != second.order_package_hash


def test_high_precision_slippage_and_precision_contracts_do_not_collide() -> None:
    first_order = order(max_slippage_bps=Decimal("2.1234567890123456789012345678901"))
    second_order = order(max_slippage_bps=Decimal("2.1234567890123456789012345678902"))
    assert first_order.order_package_hash != second_order.order_package_hash
    first_precision = precision(quantity_step=Decimal("0.1234567890123456789012345678901"))
    second_precision = precision(quantity_step=Decimal("0.1234567890123456789012345678902"))
    assert first_precision.contract_hash != second_precision.contract_hash


def test_negative_zero_and_trailing_zero_hash_equivalence() -> None:
    assert (
        order(max_slippage_bps=Decimal("-0.0")).order_package_hash
        == order(max_slippage_bps=Decimal("0")).order_package_hash
    )
    assert (
        order(quantity=Decimal("1.2500")).order_package_hash
        == order(quantity=Decimal("1.25")).order_package_hash
    )


def test_nested_proposal_hash_is_stable_across_dict_json_and_context() -> None:
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN
        original = proposal(order(max_slippage_bps=Decimal("2.1234567890123456789012345678901")))
    from_dict = ProposalV0.model_validate(
        BaseModel.model_dump(original, mode="python", round_trip=True)
    )
    from_json = ProposalV0.model_validate_json(original.model_dump_json())
    assert from_dict.proposal_hash == original.proposal_hash
    assert from_json.proposal_hash == original.proposal_hash


def test_decimal_hash_determinism_across_processes() -> None:
    script = (
        "import os, runpy\n"
        "from decimal import ROUND_DOWN\n"
        "ns = runpy.run_path('tests/test_external_review_round4_regressions.py')\n"
        "print(ns['_hash_bundle'](int(os.environ['DECIMAL_PREC']), ROUND_DOWN)[1])"
    )
    outputs = []
    for precision_value in (6, 28, 100):
        env = os.environ.copy()
        env["DECIMAL_PREC"] = str(precision_value)
        outputs.append(
            subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()
        )
    assert len(set(outputs)) == 1


@pytest.mark.parametrize(
    ("value", "expected_fragment"),
    [
        ("1" * (MAX_DECIMAL_SIGNIFICANT_DIGITS + 1), "significant digits"),
        ("1" + "0" * MAX_DECIMAL_INTEGER_DIGITS, "integer digits"),
        ("0." + "0" * MAX_DECIMAL_SCALE + "1", "scale"),
    ],
)
def test_decimal_named_bounds_fail_closed(value: str, expected_fragment: str) -> None:
    with pytest.raises(ValidationError, match=expected_fragment):
        TypeAdapter(PositiveFiniteDecimal).validate_python(Decimal(value))
