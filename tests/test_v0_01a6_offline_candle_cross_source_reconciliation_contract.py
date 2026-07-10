from __future__ import annotations

import ast
import copy
import inspect
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, TypeAdapter, ValidationError

from scripts.export_schemas import A6_SCHEMA_BOUNDARY_DESCRIPTION, render
from trader_assist_v0.contracts.candle_reconciliation import (
    A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_PATTERN,
    A6_CONTRACT_ID,
    A6_HASH_VERSION,
    A6_SCHEMA_VERSION,
    CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS,
    CandleCrossSourceAuthoritySideV0,
    CandleCrossSourceComparisonItemV0,
    CandleCrossSourceComparisonStatusV0,
    CandleCrossSourceFieldDifferenceV0,
    CandleCrossSourceInputAuthorityV0,
    CandleCrossSourceReconciliationV0,
    compute_candle_cross_source_reconciliation_hash,
    compute_candle_cross_source_reconciliation_hash_from_payload,
)
from trader_assist_v0.contracts.candles import (
    CandleEnvelopeShapeV0,
    CandlePayloadExtractionV0,
    ExtractedCandleV0,
    compute_candle_logical_key,
)
from trader_assist_v0.contracts.source_catalog import (
    RATE_LIMIT_STATUS,
    SOURCE_CATALOG_HASH,
)
from trader_assist_v0.data import candle_reconciler
from trader_assist_v0.data.candle_reconciler import (
    CandleCrossSourceReconciliationError,
    reconcile_candle_extractions,
)

_SOURCE_ID = "hyperliquid-public-mainnet"


def _candle(
    *,
    open_time_ms: int,
    close_time_ms: int | None = None,
    coin: str = "ETH",
    interval: str = "1m",
    open_price: str = "3000",
    high_price: str = "3002",
    low_price: str = "2999",
    close_price: str = "3001",
    volume_base: str = "12.5",
    trade_count: int = 7,
) -> ExtractedCandleV0:
    return ExtractedCandleV0.model_validate(
        {
            "candle_logical_key": compute_candle_logical_key(
                source_id=_SOURCE_ID,
                coin=coin,
                candle_interval=interval,
                open_time_ms=open_time_ms,
            ),
            "open_time_ms": open_time_ms,
            "close_time_ms": (close_time_ms if close_time_ms is not None else open_time_ms + 999),
            "open_price": Decimal(open_price),
            "high_price": Decimal(high_price),
            "low_price": Decimal(low_price),
            "close_price": Decimal(close_price),
            "volume_base": Decimal(volume_base),
            "trade_count": trade_count,
        }
    )


def _extraction(
    *,
    side: str,
    candles: tuple[ExtractedCandleV0, ...],
    coin: str = "ETH",
    interval: str = "1m",
    event_digit: str | None = None,
) -> CandlePayloadExtractionV0:
    if side == "ws":
        endpoint_id = "hl-ws-mainnet-public"
        operation_type = "candle"
        envelope_shape = CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY
        digit = event_digit or "1"
    else:
        endpoint_id = "hl-info-mainnet-public"
        operation_type = "candleSnapshot"
        envelope_shape = CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY
        digit = event_digit or "2"
    return CandlePayloadExtractionV0.bind(
        source_event_id=digit * 64,
        payload_sha256=("a" if side == "ws" else "b") * 64,
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        coin=coin,
        candle_interval=interval,
        envelope_shape=envelope_shape,
        candles=candles,
    )


def _reconcile(
    ws_candles: tuple[ExtractedCandleV0, ...],
    info_candles: tuple[ExtractedCandleV0, ...],
    *,
    coin: str = "ETH",
    interval: str = "1m",
) -> CandleCrossSourceReconciliationV0:
    return reconcile_candle_extractions(
        ws_extraction=_extraction(
            side="ws",
            candles=ws_candles,
            coin=coin,
            interval=interval,
        ),
        info_extraction=_extraction(
            side="info",
            candles=info_candles,
            coin=coin,
            interval=interval,
        ),
    )


def _material(report: CandleCrossSourceReconciliationV0) -> dict[str, Any]:
    value = cast(dict[str, Any], json.loads(report.model_dump_json()))
    value.pop("reconciliation_hash")
    return value


def _rehash(value: dict[str, Any]) -> dict[str, Any]:
    material = copy.deepcopy(value)
    material.pop("reconciliation_hash", None)
    return {
        **material,
        "reconciliation_hash": (
            compute_candle_cross_source_reconciliation_hash_from_payload(material)
        ),
    }


def _wire(report: CandleCrossSourceReconciliationV0) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(report.model_dump_json()))


def _validate_runtime_json(value: dict[str, Any]) -> CandleCrossSourceReconciliationV0:
    return CandleCrossSourceReconciliationV0.model_validate_json(
        json.dumps(value, separators=(",", ":"))
    )


def _validation_path_calls(
    value: dict[str, Any],
) -> tuple[tuple[str, Any], ...]:
    encoded = json.dumps(value, separators=(",", ":"))
    return (
        (
            "model_validate_json",
            lambda: CandleCrossSourceReconciliationV0.model_validate_json(encoded),
        ),
        (
            "model_validate decoded mapping",
            lambda: CandleCrossSourceReconciliationV0.model_validate(copy.deepcopy(value)),
        ),
        (
            "BaseModel.model_validate.__func__",
            lambda: BaseModel.model_validate.__func__(
                CandleCrossSourceReconciliationV0,
                copy.deepcopy(value),
            ),
        ),
        (
            "TypeAdapter.validate_python",
            lambda: TypeAdapter(CandleCrossSourceReconciliationV0).validate_python(
                copy.deepcopy(value)
            ),
        ),
    )


def _base_class_bypasses(model: BaseModel, update: dict[str, Any]) -> tuple[BaseModel, ...]:
    payload = BaseModel.model_dump(model, mode="python", round_trip=True)
    payload.update(update)
    authority_base = type(model).__mro__[1]
    return (
        BaseModel.model_copy(model, update=update),
        BaseModel.copy(model, update=update),
        super(authority_base, model).model_copy(update=update),
        BaseModel.model_construct.__func__(type(model), **payload),
    )


def _malformed_exact_a5_authorities(
    extraction: CandlePayloadExtractionV0,
) -> tuple[tuple[str, CandlePayloadExtractionV0], ...]:
    candle = extraction.candles[0]
    malformed: list[tuple[str, CandlePayloadExtractionV0]] = []
    nested_attacks = (
        ("open_time_ms int to string", {"open_time_ms": str(candle.open_time_ms)}),
        ("trade_count int to float", {"trade_count": float(candle.trade_count)}),
        ("integer to bool", {"open_time_ms": True}),
        ("nested decimal to string", {"open_price": str(candle.open_price)}),
    )
    bypass_names = (
        "BaseModel.model_copy",
        "BaseModel.copy",
        "superclass model_copy",
        "BaseModel.model_construct.__func__",
    )
    for attack_name, update in nested_attacks:
        for bypass_name, malformed_candle in zip(
            bypass_names,
            _base_class_bypasses(candle, update),
            strict=True,
        ):
            malformed.append(
                (
                    f"{bypass_name}: {attack_name}",
                    cast(
                        CandlePayloadExtractionV0,
                        BaseModel.model_copy(
                            extraction,
                            update={"candles": (malformed_candle,)},
                        ),
                    ),
                )
            )

    for bypass_name, malformed_extraction in zip(
        bypass_names,
        _base_class_bypasses(
            extraction,
            {"extraction_hash": extraction.extraction_hash + " "},
        ),
        strict=True,
    ):
        malformed.append(
            (
                f"{bypass_name}: padded extraction hash",
                cast(CandlePayloadExtractionV0, malformed_extraction),
            )
        )

    missing_payload = BaseModel.model_dump(extraction, mode="python", round_trip=True)
    del missing_payload["payload_sha256"]
    malformed.append(
        (
            "BaseModel.model_construct.__func__: missing stored payload_sha256",
            BaseModel.model_construct.__func__(CandlePayloadExtractionV0, **missing_payload),
        )
    )
    return tuple(malformed)


def _replace_nested(
    value: dict[str, Any],
    path: tuple[str | int, ...],
    replacement: Any,
) -> None:
    target: Any = value
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement


def _delete_nested(value: dict[str, Any], path: tuple[str | int, ...]) -> None:
    target: Any = value
    for component in path[:-1]:
        target = target[component]
    del target[path[-1]]


def _coherently_rehash_comparison_attack(value: dict[str, Any]) -> dict[str, Any]:
    attacked = copy.deepcopy(value)
    attacked["comparisons"] = sorted(
        attacked["comparisons"],
        key=lambda item: (item["open_time_ms"], item["candle_logical_key"]),
    )
    status_to_count = {
        "MATCH": "match_count",
        "CONFLICT": "conflict_count",
        "WS_ONLY": "ws_only_count",
        "INFO_ONLY": "info_only_count",
    }
    for count_field in status_to_count.values():
        attacked[count_field] = 0
    for item in attacked["comparisons"]:
        attacked[status_to_count[item["status"]]] += 1
    return _rehash(attacked)


def test_a6_frozen_authorities_and_prior_gates_remain_fail_closed() -> None:
    assert A6_CONTRACT_ID == ("V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT")
    assert A6_SCHEMA_VERSION == "0.1.0"
    assert A6_HASH_VERSION == ("trader-assist-v0/candle-cross-source-reconciliation/v1")
    assert CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS == (
        "close_time_ms",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_base",
        "trade_count",
    )
    assert SOURCE_CATALOG_HASH == (
        "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
    )
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    assert A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_PATTERN == r"^(0|[1-9][0-9]*)$"


def test_canonical_wire_rejection_is_identical_across_every_public_validation_path() -> None:
    base = _wire(
        _reconcile(
            (_candle(open_time_ms=1000),),
            (_candle(open_time_ms=1000, trade_count=8),),
        )
    )
    for path_name, validate in _validation_path_calls(base):
        assert validate() == CandleCrossSourceReconciliationV0.model_validate(base), path_name

    attacks: list[tuple[str, dict[str, Any]]] = []
    for name, path, replacement in (
        ("integer as string", ("match_count",), "0"),
        ("integer as float", ("match_count",), 0.0),
        ("boolean as integer", ("match_count",), False),
        ("padded string", ("comparisons", 0, "status"), "CONFLICT "),
        ("padded hash", ("ws_extraction_hash",), " " + base["ws_extraction_hash"]),
        ("non-string string field", ("source_id",), 7),
    ):
        attacked = copy.deepcopy(base)
        _replace_nested(attacked, path, replacement)
        attacks.append((name, attacked))

    missing_root = copy.deepcopy(base)
    del missing_root["source_id"]
    attacks.append(("missing mandatory root field", missing_root))

    missing_item_source = copy.deepcopy(base)
    del missing_item_source["comparisons"][0]["source_id"]
    attacks.append(("missing comparison source_id", missing_item_source))

    extra = copy.deepcopy(base)
    extra["winner"] = "WS"
    attacks.append(("extra field", extra))

    for _attack_name, attacked in attacks:
        for _path_name, validate in _validation_path_calls(attacked):
            with pytest.raises(ValidationError):
                validate()


def test_a6_schema_and_runtime_require_every_serialized_authority_field() -> None:
    payload = _wire(
        _reconcile(
            (_candle(open_time_ms=1000),),
            (_candle(open_time_ms=1000, trade_count=8),),
        )
    )
    generated_schema = json.loads(render(CandleCrossSourceReconciliationV0))
    checked_schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "schemas/v0/CandleCrossSourceReconciliationV0.schema.json"
        ).read_text(encoding="utf-8")
    )
    validators = (
        Draft202012Validator(generated_schema),
        Draft202012Validator(checked_schema),
    )

    extraction_required = {
        "schema_version",
        "contract_id",
        "extraction_version",
        "source_id",
        "source_event_id",
        "payload_sha256",
        "endpoint_id",
        "operation_type",
        "coin",
        "candle_interval",
        "envelope_shape",
        "candles",
        "extraction_hash",
    }
    candle_required = {
        "candle_logical_key",
        "open_time_ms",
        "close_time_ms",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_base",
        "trade_count",
    }
    for schema in (generated_schema, checked_schema):
        assert extraction_required <= set(
            schema["$defs"]["CandlePayloadExtractionV0"]["required"]
        )
        assert candle_required <= set(schema["$defs"]["ExtractedCandleV0"]["required"])
        assert {
            "schema_version",
            "contract_id",
            "hash_version",
            "source_id",
            "ws_extraction",
            "info_extraction",
        } <= set(schema["required"])
        assert "source_id" in schema["$defs"]["CandleCrossSourceComparisonItemV0"][
            "required"
        ]

    missing_paths: tuple[tuple[str | int, ...], ...] = (
        ("schema_version",),
        ("contract_id",),
        ("hash_version",),
        ("source_id",),
        ("comparisons", 0, "source_id"),
        ("ws_extraction", "schema_version"),
        ("ws_extraction", "contract_id"),
        ("ws_extraction", "extraction_version"),
        ("ws_extraction", "source_id"),
        ("ws_extraction", "payload_sha256"),
        ("ws_extraction", "extraction_hash"),
        ("ws_extraction", "endpoint_id"),
        ("ws_extraction", "operation_type"),
        ("ws_extraction", "envelope_shape"),
        ("ws_extraction", "candles", 0, "candle_logical_key"),
        ("ws_extraction", "candles", 0, "trade_count"),
    )
    for path in missing_paths:
        attacked = copy.deepcopy(payload)
        _delete_nested(attacked, path)
        attacked = _rehash(attacked)
        for validator in validators:
            assert not validator.is_valid(attacked), path
        for _path_name, validate in _validation_path_calls(attacked):
            with pytest.raises(ValidationError):
                validate()


def test_match_binds_both_authorities_and_exact_identity() -> None:
    candle = _candle(open_time_ms=1000)
    report = _reconcile((candle,), (_candle(open_time_ms=1000),))

    assert report.match_count == 1
    assert report.conflict_count == 0
    assert report.ws_only_count == 0
    assert report.info_only_count == 0
    item = report.comparisons[0]
    assert item.status is CandleCrossSourceComparisonStatusV0.MATCH
    assert item.field_differences == ()
    assert item.ws_candle == item.info_candle
    assert item.ws_authority is not None
    assert item.info_authority is not None
    assert item.ws_authority.source_event_id == report.ws_source_event_id
    assert item.info_authority.source_event_id == report.info_source_event_id
    assert item.candle_logical_key == candle.candle_logical_key


def test_one_field_and_multi_field_conflicts_use_fixed_difference_order() -> None:
    ws = _candle(open_time_ms=1000)
    one_field = _candle(open_time_ms=1000, trade_count=8)
    one = _reconcile((ws,), (one_field,))
    assert one.conflict_count == 1
    assert [difference.field_name for difference in one.comparisons[0].field_differences] == [
        "trade_count"
    ]
    assert one.comparisons[0].field_differences[0].ws_value == "7"
    assert one.comparisons[0].field_differences[0].info_value == "8"

    multi_field = _candle(
        open_time_ms=1000,
        close_time_ms=2001,
        high_price="3003",
        close_price="3002",
        volume_base="13.5",
        trade_count=8,
    )
    multiple = _reconcile((ws,), (multi_field,))
    assert [difference.field_name for difference in multiple.comparisons[0].field_differences] == [
        "close_time_ms",
        "high_price",
        "close_price",
        "volume_base",
        "trade_count",
    ]


def test_ws_only_info_only_and_mixed_union_have_deterministic_order() -> None:
    ws_only = _candle(open_time_ms=3000)
    match_ws = _candle(open_time_ms=2000)
    info_only = _candle(open_time_ms=1000)
    match_info = _candle(open_time_ms=2000)

    first = _reconcile((ws_only, match_ws), (match_info, info_only))
    second = _reconcile((match_ws, ws_only), (info_only, match_info))

    assert [item.open_time_ms for item in first.comparisons] == [1000, 2000, 3000]
    assert [item.status for item in first.comparisons] == [
        CandleCrossSourceComparisonStatusV0.INFO_ONLY,
        CandleCrossSourceComparisonStatusV0.MATCH,
        CandleCrossSourceComparisonStatusV0.WS_ONLY,
    ]
    assert (first.match_count, first.ws_only_count, first.info_only_count) == (1, 1, 1)
    assert [
        (item.open_time_ms, item.candle_logical_key, item.status) for item in first.comparisons
    ] == [(item.open_time_ms, item.candle_logical_key, item.status) for item in second.comparisons]
    assert first.ws_extraction_hash != second.ws_extraction_hash
    assert first.info_extraction_hash != second.info_extraction_hash
    assert first.reconciliation_hash != second.reconciliation_hash


def test_empty_pair_returns_empty_report_with_zero_counts() -> None:
    report = _reconcile((), ())
    assert report.comparisons == ()
    assert (
        report.match_count,
        report.conflict_count,
        report.ws_only_count,
        report.info_only_count,
    ) == (0, 0, 0, 0)
    assert report.reconciliation_hash == (compute_candle_cross_source_reconciliation_hash(report))


def test_bind_accepts_only_two_exact_extractions_and_derives_every_other_field() -> None:
    ws = _extraction(side="ws", candles=(_candle(open_time_ms=1000),))
    info = _extraction(side="info", candles=(_candle(open_time_ms=1000),))
    bound = CandleCrossSourceReconciliationV0.bind(
        ws_extraction=ws,
        info_extraction=info,
    )
    assert bound == reconcile_candle_extractions(ws_extraction=ws, info_extraction=info)

    parameters = inspect.signature(CandleCrossSourceReconciliationV0.bind).parameters
    assert set(parameters) == {"ws_extraction", "info_extraction", "forbidden_authority"}
    for forbidden_field, forbidden_value in (
        ("comparisons", ()),
        ("match_count", 0),
        ("conflict_count", 0),
        ("ws_only_count", 0),
        ("info_only_count", 0),
        ("ws_source_event_id", ws.source_event_id),
        ("info_source_event_id", info.source_event_id),
        ("ws_extraction_hash", ws.extraction_hash),
        ("info_extraction_hash", info.extraction_hash),
        ("reconciliation_hash", "0" * 64),
        ("source_id", _SOURCE_ID),
        ("coin", "ETH"),
        ("candle_interval", "1m"),
    ):
        with pytest.raises(ValueError, match="implementation-controlled"):
            CandleCrossSourceReconciliationV0.bind(
                ws_extraction=ws,
                info_extraction=info,
                **{forbidden_field: forbidden_value},
            )


def test_rejects_source_coin_and_interval_identity_mismatch() -> None:
    ws = _extraction(side="ws", candles=(_candle(open_time_ms=1000),))
    info = _extraction(
        side="info",
        candles=(_candle(open_time_ms=1000, coin="BTC"),),
        coin="BTC",
    )
    with pytest.raises(CandleCrossSourceReconciliationError, match="coin"):
        reconcile_candle_extractions(ws_extraction=ws, info_extraction=info)

    info_interval = _extraction(
        side="info",
        candles=(_candle(open_time_ms=1000, interval="5m"),),
        interval="5m",
    )
    with pytest.raises(CandleCrossSourceReconciliationError, match="interval"):
        reconcile_candle_extractions(
            ws_extraction=ws,
            info_extraction=info_interval,
        )

    forged_source = _extraction(side="info", candles=())
    object.__setattr__(forged_source, "source_id", "other-source")
    with pytest.raises(
        CandleCrossSourceReconciliationError,
        match="revalidation",
    ):
        reconcile_candle_extractions(
            ws_extraction=_extraction(side="ws", candles=()),
            info_extraction=forged_source,
        )


def test_rejects_role_reversal_and_endpoint_operation_envelope_attacks() -> None:
    ws = _extraction(side="ws", candles=())
    info = _extraction(side="info", candles=())
    with pytest.raises(CandleCrossSourceReconciliationError, match="WS extraction"):
        reconcile_candle_extractions(
            ws_extraction=info,
            info_extraction=ws,
        )

    for field, value in (
        ("endpoint_id", "hl-info-mainnet-public"),
        ("operation_type", "candleSnapshot"),
        ("envelope_shape", CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY),
    ):
        forged = _extraction(side="ws", candles=())
        object.__setattr__(forged, field, value)
        with pytest.raises(CandleCrossSourceReconciliationError, match="revalidation"):
            reconcile_candle_extractions(
                ws_extraction=forged,
                info_extraction=info,
            )


def test_requires_exact_revalidated_a5_authorities() -> None:
    valid_ws = _extraction(side="ws", candles=(_candle(open_time_ms=1000),))
    valid_info = _extraction(side="info", candles=(_candle(open_time_ms=1000),))

    with pytest.raises(TypeError, match="exact"):
        reconcile_candle_extractions(
            ws_extraction=cast(Any, valid_ws.model_dump()),
            info_extraction=valid_info,
        )

    class CandlePayloadExtractionSubclass(CandlePayloadExtractionV0):
        pass

    fabricated = object.__new__(CandlePayloadExtractionSubclass)
    with pytest.raises(TypeError, match="exact"):
        reconcile_candle_extractions(
            ws_extraction=cast(Any, fabricated),
            info_extraction=valid_info,
        )

    object.__setattr__(valid_ws, "extraction_hash", "0" * 64)
    with pytest.raises(CandleCrossSourceReconciliationError, match="revalidation"):
        reconcile_candle_extractions(
            ws_extraction=valid_ws,
            info_extraction=valid_info,
        )


def test_nested_candle_and_extraction_hashes_are_revalidated() -> None:
    ws = _extraction(side="ws", candles=(_candle(open_time_ms=1000),))
    info = _extraction(side="info", candles=(_candle(open_time_ms=1000),))
    object.__setattr__(ws.candles[0], "trade_count", 999)
    with pytest.raises(CandleCrossSourceReconciliationError, match="revalidation"):
        reconcile_candle_extractions(ws_extraction=ws, info_extraction=info)


def test_report_hash_is_deterministic_and_binds_every_authority_category() -> None:
    report = _reconcile(
        (_candle(open_time_ms=1000), _candle(open_time_ms=3000)),
        (
            _candle(open_time_ms=1000, trade_count=8),
            _candle(open_time_ms=2000),
        ),
    )
    material = _material(report)
    base_hash = compute_candle_cross_source_reconciliation_hash_from_payload(material)
    assert base_hash == report.reconciliation_hash

    scalar_mutations: dict[str, Any] = {
        "schema_version": "9.9.9",
        "contract_id": "other-contract",
        "hash_version": "other-hash-version",
        "source_id": "other-source",
        "coin": "BTC",
        "candle_interval": "5m",
        "ws_source_event_id": "3" * 64,
        "ws_extraction_hash": "4" * 64,
        "info_source_event_id": "5" * 64,
        "info_extraction_hash": "6" * 64,
        "match_count": material["match_count"] + 1,
        "conflict_count": material["conflict_count"] + 1,
        "ws_only_count": material["ws_only_count"] + 1,
        "info_only_count": material["info_only_count"] + 1,
    }
    for field, changed_value in scalar_mutations.items():
        changed = copy.deepcopy(material)
        changed[field] = changed_value
        assert compute_candle_cross_source_reconciliation_hash_from_payload(changed) != base_hash

    for path, replacement in (
        (("ws_extraction", "payload_sha256"), "c" * 64),
        (("ws_extraction", "candles", 0, "trade_count"), 99),
        (("info_extraction", "source_event_id"), "d" * 64),
        (("info_extraction", "candles", 0, "volume_base"), "99"),
    ):
        changed = copy.deepcopy(material)
        _replace_nested(changed, path, replacement)
        assert compute_candle_cross_source_reconciliation_hash_from_payload(changed) != base_hash

    changed_comparison = copy.deepcopy(material)
    changed_comparison["comparisons"][0]["open_time_ms"] += 1
    assert (
        compute_candle_cross_source_reconciliation_hash_from_payload(changed_comparison)
        != base_hash
    )
    reversed_comparisons = copy.deepcopy(material)
    reversed_comparisons["comparisons"] = tuple(reversed(reversed_comparisons["comparisons"]))
    assert (
        compute_candle_cross_source_reconciliation_hash_from_payload(reversed_comparisons)
        != base_hash
    )

    nested_mutations: tuple[tuple[tuple[str | int, ...], Any], ...] = (
        (("comparisons", 0, "candle_logical_key"), "7" * 64),
        (("comparisons", 0, "source_id"), "other-source"),
        (("comparisons", 0, "coin"), "BTC"),
        (("comparisons", 0, "candle_interval"), "5m"),
        (("comparisons", 0, "status"), "MATCH"),
        (("comparisons", 0, "ws_candle", "trade_count"), 99),
        (("comparisons", 0, "ws_authority", "source_event_id"), "8" * 64),
        (("comparisons", 0, "ws_authority", "extraction_hash"), "9" * 64),
        (("comparisons", 0, "ws_authority", "endpoint_id"), "other-endpoint"),
        (("comparisons", 0, "ws_authority", "operation_type"), "other-operation"),
        (("comparisons", 0, "ws_authority", "envelope_shape"), "INFO_CANDLE_ARRAY"),
        (("comparisons", 0, "info_candle", "volume_base"), Decimal("99")),
        (("comparisons", 0, "info_authority", "source_event_id"), "a" * 64),
        (("comparisons", 0, "info_authority", "extraction_hash"), "b" * 64),
        (("comparisons", 0, "info_authority", "endpoint_id"), "other-endpoint"),
        (("comparisons", 0, "info_authority", "operation_type"), "other-operation"),
        (("comparisons", 0, "info_authority", "envelope_shape"), "WS_DATA_CANDLE"),
        (("comparisons", 0, "field_differences", 0, "field_name"), "volume_base"),
        (("comparisons", 0, "field_differences", 0, "ws_value"), "99"),
        (("comparisons", 0, "field_differences", 0, "info_value"), "100"),
    )
    for path, replacement in nested_mutations:
        changed = copy.deepcopy(material)
        _replace_nested(changed, path, replacement)
        assert compute_candle_cross_source_reconciliation_hash_from_payload(changed) != base_hash, (
            path
        )


def test_forged_report_hash_constants_and_extra_fields_are_rejected() -> None:
    report = _reconcile((_candle(open_time_ms=1000),), (_candle(open_time_ms=1000),))
    forged_hash = _wire(report)
    forged_hash["reconciliation_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="reconciliation_hash"):
        CandleCrossSourceReconciliationV0.model_validate(forged_hash)

    for field in ("schema_version", "contract_id", "hash_version"):
        wrong_constant = _material(report)
        wrong_constant[field] = "other-authority"
        with pytest.raises(ValidationError):
            CandleCrossSourceReconciliationV0.model_validate(_rehash(wrong_constant))

    noncanonical_hash = _wire(report)
    noncanonical_hash["reconciliation_hash"] = report.reconciliation_hash.upper()
    with pytest.raises(ValidationError):
        CandleCrossSourceReconciliationV0.model_validate(noncanonical_hash)

    extra = _wire(report)
    extra["winner"] = "WS"
    with pytest.raises(ValidationError, match="extra"):
        CandleCrossSourceReconciliationV0.model_validate(extra)


def test_count_status_candle_and_difference_consistency_fail_closed() -> None:
    report = _reconcile(
        (_candle(open_time_ms=1000),),
        (_candle(open_time_ms=1000, trade_count=8),),
    )
    material = _material(report)

    wrong_count = copy.deepcopy(material)
    wrong_count["conflict_count"] = 0
    with pytest.raises(ValidationError, match="exact complete logical-key union"):
        CandleCrossSourceReconciliationV0.model_validate(_rehash(wrong_count))

    wrong_status = copy.deepcopy(material)
    wrong_status["comparisons"][0]["status"] = "MATCH"
    with pytest.raises(ValidationError, match="MATCH"):
        CandleCrossSourceReconciliationV0.model_validate(_rehash(wrong_status))

    missing_candle = copy.deepcopy(material)
    missing_candle["comparisons"][0]["info_candle"] = None
    missing_candle["comparisons"][0]["info_authority"] = None
    with pytest.raises(ValidationError):
        CandleCrossSourceReconciliationV0.model_validate(_rehash(missing_candle))

    forged_difference = copy.deepcopy(material)
    forged_difference["comparisons"][0]["field_differences"][0]["field_name"] = "volume_base"
    with pytest.raises(ValidationError, match="differences"):
        CandleCrossSourceReconciliationV0.model_validate(_rehash(forged_difference))

    forged_value = copy.deepcopy(material)
    forged_value["comparisons"][0]["field_differences"][0]["ws_value"] = "999"
    with pytest.raises(ValidationError, match="differences"):
        CandleCrossSourceReconciliationV0.model_validate(_rehash(forged_value))


def test_report_rejects_noncanonical_comparison_order_with_valid_hash() -> None:
    report = _reconcile(
        (_candle(open_time_ms=1000), _candle(open_time_ms=3000)),
        (_candle(open_time_ms=2000),),
    )
    material = _material(report)
    material["comparisons"] = list(reversed(material["comparisons"]))
    with pytest.raises(ValidationError, match="exact complete logical-key union"):
        CandleCrossSourceReconciliationV0.model_validate(_rehash(material))


def test_comparison_and_report_models_block_construct_copy_and_subclasses() -> None:
    report = _reconcile((), ())
    with pytest.raises(TypeError):
        CandleCrossSourceFieldDifferenceV0.model_construct()
    with pytest.raises(TypeError):
        CandleCrossSourceComparisonItemV0.model_construct()
    with pytest.raises(TypeError):
        CandleCrossSourceReconciliationV0.model_construct()
    with pytest.raises(TypeError):
        report.model_copy(update={"match_count": 1})

    class ReconciliationSubclass(CandleCrossSourceReconciliationV0):
        pass

    with pytest.raises(ValidationError, match="exact"):
        ReconciliationSubclass.model_validate(_wire(report))


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("match_count",), "1"),
        (("match_count",), 1.0),
        (("comparisons", 0, "open_time_ms"), "1000"),
        (("comparisons", 0, "open_time_ms"), 1000.0),
        (("comparisons", 0, "ws_candle", "open_time_ms"), "1000"),
        (("comparisons", 0, "ws_candle", "open_time_ms"), 1000.0),
        (("comparisons", 0, "ws_candle", "trade_count"), "7"),
        (("comparisons", 0, "ws_candle", "trade_count"), 7.0),
        (("comparisons", 0, "ws_candle", "trade_count"), True),
        (("ws_source_event_id",), " " + ("1" * 64)),
        (("comparisons", 0, "ws_authority", "extraction_hash"), ("a" * 64) + " "),
        (("contract_id",), " " + A6_CONTRACT_ID),
        (("comparisons", 0, "status"), "CONFLICT "),
        (("comparisons", 0, "ws_authority", "side"), " WS"),
        (("comparisons", 0, "ws_authority", "side"), 1),
        (("comparisons", 0, "field_differences", 0, "ws_value"), 7),
    ],
)
def test_a6_public_json_rejects_noncanonical_scalar_encodings(
    path: tuple[str | int, ...],
    replacement: Any,
) -> None:
    payload = _wire(
        _reconcile(
            (_candle(open_time_ms=1000),),
            (_candle(open_time_ms=1000, trade_count=8),),
        )
    )
    _replace_nested(payload, path, replacement)
    with pytest.raises(ValidationError, match="JSON value|whitespace padded"):
        _validate_runtime_json(payload)


def test_schema_expressible_role_and_status_corpus_fails_schema_and_runtime() -> None:
    schema = json.loads(render(CandleCrossSourceReconciliationV0))
    validator = Draft202012Validator(schema)
    match = _wire(_reconcile((_candle(open_time_ms=1000),), (_candle(open_time_ms=1000),)))
    conflict = _wire(
        _reconcile(
            (_candle(open_time_ms=1000),),
            (_candle(open_time_ms=1000, trade_count=8),),
        )
    )
    ws_only = _wire(_reconcile((_candle(open_time_ms=1000),), ()))
    info_only = _wire(_reconcile((), (_candle(open_time_ms=1000),)))

    malformed: list[tuple[str, dict[str, Any]]] = []
    for field, invalid in (
        ("endpoint_id", "hl-info-mainnet-public"),
        ("operation_type", "candleSnapshot"),
        ("envelope_shape", "INFO_CANDLE_ARRAY"),
    ):
        value = copy.deepcopy(conflict)
        value["comparisons"][0]["ws_authority"][field] = invalid
        malformed.append((f"WS role {field}", _rehash(value)))
    for field, invalid in (
        ("endpoint_id", "hl-ws-mainnet-public"),
        ("operation_type", "candle"),
        ("envelope_shape", "WS_DATA_CANDLE"),
    ):
        value = copy.deepcopy(conflict)
        value["comparisons"][0]["info_authority"][field] = invalid
        malformed.append((f"Info role {field}", _rehash(value)))

    match_missing = copy.deepcopy(match)
    match_missing["comparisons"][0]["info_candle"] = None
    match_missing["comparisons"][0]["info_authority"] = None
    malformed.append(("MATCH missing source", _rehash(match_missing)))

    match_differences = copy.deepcopy(match)
    match_differences["comparisons"][0]["field_differences"] = copy.deepcopy(
        conflict["comparisons"][0]["field_differences"]
    )
    malformed.append(("MATCH with differences", _rehash(match_differences)))

    conflict_missing = copy.deepcopy(conflict)
    conflict_missing["comparisons"][0]["info_candle"] = None
    conflict_missing["comparisons"][0]["info_authority"] = None
    malformed.append(("CONFLICT missing source", _rehash(conflict_missing)))

    conflict_empty = copy.deepcopy(conflict)
    conflict_empty["comparisons"][0]["field_differences"] = []
    malformed.append(("CONFLICT without differences", _rehash(conflict_empty)))

    ws_with_info = copy.deepcopy(ws_only)
    ws_with_info["info_source_event_id"] = match["info_source_event_id"]
    ws_with_info["info_extraction_hash"] = match["info_extraction_hash"]
    ws_with_info["comparisons"][0]["info_candle"] = copy.deepcopy(
        match["comparisons"][0]["info_candle"]
    )
    ws_with_info["comparisons"][0]["info_authority"] = copy.deepcopy(
        match["comparisons"][0]["info_authority"]
    )
    malformed.append(("WS_ONLY with Info source", _rehash(ws_with_info)))

    info_with_ws = copy.deepcopy(info_only)
    info_with_ws["ws_source_event_id"] = match["ws_source_event_id"]
    info_with_ws["ws_extraction_hash"] = match["ws_extraction_hash"]
    info_with_ws["comparisons"][0]["ws_candle"] = copy.deepcopy(
        match["comparisons"][0]["ws_candle"]
    )
    info_with_ws["comparisons"][0]["ws_authority"] = copy.deepcopy(
        match["comparisons"][0]["ws_authority"]
    )
    malformed.append(("INFO_ONLY with WS source", _rehash(info_with_ws)))

    for name, payload in malformed:
        assert not validator.is_valid(payload), name
        with pytest.raises(ValidationError):
            _validate_runtime_json(payload)


@pytest.mark.parametrize("field_name", ["close_time_ms", "trade_count"])
@pytest.mark.parametrize(
    "invalid_value",
    ["1.5", "-1", "01", "1e3", "\uff11\uff12", " 1", "1 ", ""],
)
def test_integer_difference_value_kind_has_checked_generated_and_runtime_parity(
    field_name: str,
    invalid_value: str,
) -> None:
    report = _reconcile(
        (_candle(open_time_ms=1000),),
        (_candle(open_time_ms=1000, close_time_ms=2001, trade_count=8),),
    )
    payload = _wire(report)
    differences = payload["comparisons"][0]["field_differences"]
    difference = next(item for item in differences if item["field_name"] == field_name)
    difference["ws_value"] = invalid_value
    payload = _rehash(payload)

    generated = Draft202012Validator(
        json.loads(render(CandleCrossSourceReconciliationV0))
    )
    checked = Draft202012Validator(
        json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "schemas/v0/CandleCrossSourceReconciliationV0.schema.json"
            ).read_text(encoding="utf-8")
        )
    )
    assert not generated.is_valid(payload)
    assert not checked.is_valid(payload)
    with pytest.raises(ValidationError):
        CandleCrossSourceReconciliationV0.model_validate(payload)


def test_coherently_rehashed_dynamic_invalid_corpus_requires_runtime_validation() -> None:
    report = _reconcile(
        (
            _candle(open_time_ms=1000),
            _candle(open_time_ms=2000),
            _candle(open_time_ms=3000),
        ),
        (
            _candle(
                open_time_ms=1000,
                close_time_ms=2001,
                high_price="3003",
                close_price="3002",
                volume_base="13.5",
                trade_count=8,
            ),
            _candle(open_time_ms=2000),
            _candle(open_time_ms=4000),
        ),
    )
    base = _wire(report)
    validator = Draft202012Validator(
        json.loads(render(CandleCrossSourceReconciliationV0))
    )

    duplicate_identity = copy.deepcopy(base)
    duplicate_identity["comparisons"].insert(
        2,
        copy.deepcopy(duplicate_identity["comparisons"][1]),
    )
    duplicate_identity["match_count"] += 1

    duplicate_membership = copy.deepcopy(base)
    duplicate_membership["comparisons"][2]["ws_candle"] = copy.deepcopy(
        duplicate_membership["comparisons"][1]["ws_candle"]
    )

    comparison_order = copy.deepcopy(base)
    comparison_order["comparisons"][0:2] = reversed(comparison_order["comparisons"][0:2])

    difference_order = copy.deepcopy(base)
    difference_order["comparisons"][0]["field_differences"] = list(
        reversed(difference_order["comparisons"][0]["field_differences"])
    )

    wrong_identity = copy.deepcopy(base)
    wrong_identity["comparisons"][1]["coin"] = "BTC"

    wrong_counts = copy.deepcopy(base)
    wrong_counts["match_count"] += 1

    status_source = copy.deepcopy(base)
    status_source["comparisons"][1]["status"] = "WS_ONLY"
    status_source["match_count"] -= 1
    status_source["ws_only_count"] += 1

    forged_values = copy.deepcopy(base)
    forged_values["comparisons"][0]["field_differences"][0]["ws_value"] = "999"

    malformed = (
        ("duplicate comparison logical identity", duplicate_identity, True),
        ("duplicate source membership", duplicate_membership, True),
        ("noncanonical comparison order", comparison_order, True),
        ("noncanonical field-difference order", difference_order, True),
        ("wrong item identity", wrong_identity, True),
        ("wrong counts", wrong_counts, True),
        ("status/source inconsistency", status_source, False),
        ("forged difference values", forged_values, True),
    )
    for name, value, schema_may_pass in malformed:
        payload = _rehash(value)
        material = copy.deepcopy(payload)
        supplied_hash = material.pop("reconciliation_hash")
        assert supplied_hash == compute_candle_cross_source_reconciliation_hash_from_payload(
            material
        ), name
        assert validator.is_valid(payload) is schema_may_pass, name
        with pytest.raises(ValidationError):
            _validate_runtime_json(payload)


def test_complete_union_proof_rejects_coherently_rehashed_omission_and_injection_attacks() -> None:
    ws_candles = (
        _candle(open_time_ms=1000),
        _candle(open_time_ms=2000),
        _candle(open_time_ms=3000),
    )
    info_candles = (
        _candle(open_time_ms=1000, trade_count=8),
        _candle(open_time_ms=2000),
        _candle(open_time_ms=4000),
    )
    base = _wire(_reconcile(ws_candles, info_candles))

    def item_at(payload: dict[str, Any], open_time_ms: int) -> dict[str, Any]:
        return copy.deepcopy(
            next(
                item
                for item in payload["comparisons"]
                if item["open_time_ms"] == open_time_ms
            )
        )

    extended_ws = _wire(
        _reconcile((*ws_candles, _candle(open_time_ms=5000)), info_candles)
    )
    extended_info = _wire(
        _reconcile(ws_candles, (*info_candles, _candle(open_time_ms=6000)))
    )
    substituted_source = _wire(
        _reconcile(
            (
                _candle(open_time_ms=1000, trade_count=9),
                _candle(open_time_ms=2000),
                _candle(open_time_ms=3000),
            ),
            info_candles,
        )
    )

    omitted = copy.deepcopy(base)
    omitted["comparisons"] = [
        item for item in omitted["comparisons"] if item["open_time_ms"] != 2000
    ]

    injected_ws = copy.deepcopy(base)
    injected_ws["comparisons"].append(item_at(extended_ws, 5000))

    injected_info = copy.deepcopy(base)
    injected_info["comparisons"].append(item_at(extended_info, 6000))

    substituted = copy.deepcopy(base)
    substituted["comparisons"] = [
        item_at(substituted_source, 1000)
        if item["open_time_ms"] == 1000
        else item
        for item in substituted["comparisons"]
    ]

    moved_side = copy.deepcopy(base)
    moved_item = next(
        item for item in moved_side["comparisons"] if item["open_time_ms"] == 3000
    )
    moved_item["status"] = "INFO_ONLY"
    moved_item["info_candle"] = moved_item["ws_candle"]
    moved_item["info_authority"] = item_at(base, 1000)["info_authority"]
    moved_item["ws_candle"] = None
    moved_item["ws_authority"] = None
    moved_item["field_differences"] = []

    modified_membership = copy.deepcopy(base)
    membership_item = next(
        item
        for item in modified_membership["comparisons"]
        if item["open_time_ms"] == 2000
    )
    membership_item["status"] = "WS_ONLY"
    membership_item["info_candle"] = None
    membership_item["info_authority"] = None
    membership_item["field_differences"] = []

    incomplete_union = copy.deepcopy(base)
    incomplete_union["comparisons"] = [
        item
        for item in incomplete_union["comparisons"]
        if item["open_time_ms"] not in {1000, 4000}
    ]

    superset_union = copy.deepcopy(base)
    superset_union["comparisons"].extend(
        (item_at(extended_ws, 5000), item_at(extended_info, 6000))
    )

    attacks = (
        ("deleted comparison", omitted),
        ("injected non-member WS_ONLY", injected_ws),
        ("injected non-member INFO_ONLY", injected_info),
        ("substituted extraction-external candle", substituted),
        ("real candle moved to wrong membership side", moved_side),
        ("modified source membership", modified_membership),
        ("incomplete union", incomplete_union),
        ("superset union", superset_union),
    )
    schema_validator = Draft202012Validator(
        json.loads(render(CandleCrossSourceReconciliationV0))
    )
    for attack_name, attack in attacks:
        payload = _coherently_rehash_comparison_attack(attack)
        material = copy.deepcopy(payload)
        supplied_hash = material.pop("reconciliation_hash")
        assert supplied_hash == compute_candle_cross_source_reconciliation_hash_from_payload(
            material
        ), attack_name
        assert schema_validator.is_valid(payload), attack_name
        with pytest.raises(
            ValidationError,
            match="exact complete logical-key union",
        ):
            CandleCrossSourceReconciliationV0.model_validate(payload)


@pytest.mark.filterwarnings("ignore:The `copy` method is deprecated")
@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings")
def test_base_class_bypass_attacks_fail_at_a5_and_a6_public_boundaries() -> None:
    ws = _extraction(side="ws", candles=(_candle(open_time_ms=1000),))
    info = _extraction(side="info", candles=(_candle(open_time_ms=1000),))
    for bypassed in _base_class_bypasses(
        ws,
        {"endpoint_id": "hl-info-mainnet-public"},
    ):
        with pytest.raises(CandleCrossSourceReconciliationError, match="revalidation"):
            reconcile_candle_extractions(
                ws_extraction=cast(Any, bypassed),
                info_extraction=info,
            )

    report = reconcile_candle_extractions(ws_extraction=ws, info_extraction=info)
    item = report.comparisons[0]
    ws_authority = item.ws_authority
    assert ws_authority is not None
    for bypassed in _base_class_bypasses(
        ws_authority,
        {"side": CandleCrossSourceAuthoritySideV0.INFO},
    ):
        with pytest.raises((ValueError, ValidationError)):
            CandleCrossSourceInputAuthorityV0.model_validate(bypassed)

    for bypassed in _base_class_bypasses(
        item,
        {"status": CandleCrossSourceComparisonStatusV0.WS_ONLY},
    ):
        with pytest.raises((ValueError, ValidationError)):
            CandleCrossSourceComparisonItemV0.model_validate(bypassed)

    for bypassed in _base_class_bypasses(report, {"match_count": 2}):
        with pytest.raises((ValueError, ValidationError)):
            CandleCrossSourceReconciliationV0.model_validate(bypassed)

    with pytest.raises(ValueError, match="expected exact"):
        CandleCrossSourceReconciliationV0.model_validate(ws)


@pytest.mark.filterwarnings("ignore:The `copy` method is deprecated")
@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings")
def test_malformed_exact_a5_objects_fail_direct_bind_and_report_core_paths() -> None:
    ws = _extraction(side="ws", candles=(_candle(open_time_ms=1000),))
    info = _extraction(side="info", candles=(_candle(open_time_ms=1000),))
    report = reconcile_candle_extractions(ws_extraction=ws, info_extraction=info)

    for _attack_name, malformed_ws in _malformed_exact_a5_authorities(ws):
        with pytest.raises(CandleCrossSourceReconciliationError, match="revalidation"):
            reconcile_candle_extractions(
                ws_extraction=malformed_ws,
                info_extraction=info,
            )
        with pytest.raises((TypeError, ValueError, ValidationError)):
            CandleCrossSourceReconciliationV0.bind(
                ws_extraction=malformed_ws,
                info_extraction=info,
            )

        malformed_report = BaseModel.model_copy(
            report,
            update={"ws_extraction": malformed_ws},
        )
        report_paths = (
            CandleCrossSourceReconciliationV0.model_validate,
            lambda value: BaseModel.model_validate.__func__(
                CandleCrossSourceReconciliationV0,
                value,
            ),
            TypeAdapter(CandleCrossSourceReconciliationV0).validate_python,
        )
        for validate in report_paths:
            with pytest.raises(ValidationError):
                validate(malformed_report)


def test_runtime_json_schema_and_checked_in_schema_agree() -> None:
    report = _reconcile(
        (_candle(open_time_ms=1000),),
        (_candle(open_time_ms=1000, trade_count=8),),
    )
    rendered = render(CandleCrossSourceReconciliationV0)
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas/v0/CandleCrossSourceReconciliationV0.schema.json"
    )
    assert schema_path.read_text(encoding="utf-8") == rendered
    schema = json.loads(rendered)
    validator = Draft202012Validator(schema)
    payload = json.loads(report.model_dump_json())
    assert validator.is_valid(payload)
    assert CandleCrossSourceReconciliationV0.model_validate_json(report.model_dump_json()) == report
    assert schema["description"] == A6_SCHEMA_BOUNDARY_DESCRIPTION
    assert "Schema validation alone does not authenticate" in schema["$comment"]

    data_plane = (
        Path(__file__).resolve().parents[1] / "docs/architecture/V0_01_DATA_PLANE.md"
    ).read_text(encoding="utf-8")
    assert "Schema validation alone does not authenticate an A6 report" in data_plane
    assert "runtime semantic validation remains mandatory" in data_plane


def test_repeated_execution_is_deterministic() -> None:
    ws = _extraction(
        side="ws",
        candles=(_candle(open_time_ms=2000), _candle(open_time_ms=1000)),
    )
    info = _extraction(
        side="info",
        candles=(
            _candle(open_time_ms=1000),
            _candle(open_time_ms=2000, trade_count=8),
        ),
    )
    results = [
        reconcile_candle_extractions(ws_extraction=ws, info_extraction=info) for _ in range(10)
    ]
    assert all(result == results[0] for result in results)
    assert len({result.reconciliation_hash for result in results}) == 1


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested_key for item in value.values() for nested_key in _all_keys(item)
        }
    if isinstance(value, list):
        return {nested_key for item in value for nested_key in _all_keys(item)}
    return set()


def test_output_and_runtime_have_no_winner_finality_normalized_or_silver_path() -> None:
    report = _reconcile((_candle(open_time_ms=1000),), ())
    keys = {key.lower() for key in _all_keys(json.loads(report.model_dump_json()))}
    for forbidden in (
        "winner",
        "canonical_winner",
        "finality",
        "revision",
        "normalized_event",
        "silver",
    ):
        assert forbidden not in keys

    tree = ast.parse(inspect.getsource(candle_reconciler))
    forbidden_import_roots = {
        "aiohttp",
        "asyncio",
        "http",
        "httpx",
        "pathlib",
        "requests",
        "socket",
        "ssl",
        "urllib",
        "urllib3",
        "websocket",
        "websockets",
    }
    for node in ast.walk(tree):
        assert not isinstance(
            node,
            ast.AsyncFunctionDef | ast.Await | ast.AsyncFor | ast.AsyncWith,
        )
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".")[0] for alias in node.names}
            assert roots.isdisjoint(forbidden_import_roots)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module.split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "exec", "eval"}
