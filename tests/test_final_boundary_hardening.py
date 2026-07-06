from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from jsonschema import Draft202012Validator
from pydantic import TypeAdapter, ValidationError

from scripts.export_schemas import render
from trader_assist_v0.contracts import (
    EnvironmentV0,
    OrderPackageV0,
    PlaybookIdV0,
    PromotionRecordV0,
    PromotionStateV0,
    validate_promotion_chain,
)
from trader_assist_v0.contracts.common import (
    MAX_DECIMAL_WIRE_LENGTH,
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
)

NOW = datetime(2026, 7, 6, tzinfo=UTC)
H = "a" * 64


@pytest.mark.parametrize("value", ["1e3", "1E3", "+", "-", ".", "-1", "0"])
def test_positive_decimal_json_rejects_noncanonical_or_nonpositive_strings(value: str) -> None:
    adapter = TypeAdapter(PositiveFiniteDecimal)
    with pytest.raises(ValidationError):
        adapter.validate_json(json.dumps(value))


def test_decimal_json_rejects_number_tokens_and_oversized_strings() -> None:
    positive = TypeAdapter(PositiveFiniteDecimal)
    nonnegative = TypeAdapter(NonNegativeFiniteDecimal)
    with pytest.raises(ValidationError, match="must be a string"):
        positive.validate_json("1.25")
    with pytest.raises(ValidationError, match="must be a string"):
        nonnegative.validate_json("0")
    with pytest.raises(ValidationError, match="exceeds"):
        positive.validate_json(json.dumps("1" * (MAX_DECIMAL_WIRE_LENGTH + 1)))


def test_decimal_json_accepts_canonical_string_tokens() -> None:
    assert TypeAdapter(PositiveFiniteDecimal).validate_json('"1.25"').is_finite()
    assert TypeAdapter(NonNegativeFiniteDecimal).validate_json('"0"').is_zero()


def test_generated_schema_caps_decimal_wire_length() -> None:
    schema = json.loads(render(OrderPackageV0))
    quantity = schema["properties"]["quantity"]
    assert quantity["type"] == "string"
    assert quantity["maxLength"] == MAX_DECIMAL_WIRE_LENGTH
    validator = Draft202012Validator(quantity)
    assert validator.is_valid("1.25")
    assert not validator.is_valid("1" * (MAX_DECIMAL_WIRE_LENGTH + 1))


def test_promotion_chain_ignores_instance_model_dump_shadow() -> None:
    draft = PromotionRecordV0.bind(
        schema_version="0.1.0",
        promotion_record_id="promotion-shadow-test",
        playbook_id=PlaybookIdV0.LQS_FR,
        strategy_version="lqs-fr.0.1",
        parameter_version="params.0.1",
        feature_version="features.0.1",
        label_version="labels.0.1",
        required_feed_contract_id="feeds-lqs-fr-001",
        required_feed_contract_version="feeds.0.1",
        required_feed_contract_hash=H,
        state=PromotionStateV0.DRAFT,
        environment=EnvironmentV0.READ_ONLY,
        evidence_dataset_ids=(),
        reviewed_by="reviewer-001",
        reviewed_at=NOW,
        rationale="initial draft",
    )

    def poisoned_model_dump(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("instance model_dump shadow must not be called")

    object.__setattr__(draft, "model_dump", poisoned_model_dump)
    assert validate_promotion_chain((draft,))[0].promotion_record_hash == draft.promotion_record_hash
