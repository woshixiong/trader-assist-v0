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
from pydantic import ValidationError

from scripts.export_schemas import render
from trader_assist_v0.contracts.candle_reconciliation import (
    A6_CONTRACT_ID,
    A6_HASH_VERSION,
    A6_SCHEMA_VERSION,
    CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS,
    CandleCrossSourceComparisonItemV0,
    CandleCrossSourceComparisonStatusV0,
    CandleCrossSourceFieldDifferenceV0,
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
    value = report.model_dump(mode="python", round_trip=True)
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


def _replace_nested(
    value: dict[str, Any],
    path: tuple[str | int, ...],
    replacement: Any,
) -> None:
    target: Any = value
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement


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
    forged_hash = report.model_dump(mode="python", round_trip=True)
    forged_hash["reconciliation_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="reconciliation_hash"):
        CandleCrossSourceReconciliationV0.model_validate(forged_hash)

    for field in ("schema_version", "contract_id", "hash_version"):
        wrong_constant = _material(report)
        wrong_constant[field] = "other-authority"
        with pytest.raises(ValidationError):
            CandleCrossSourceReconciliationV0.model_validate(_rehash(wrong_constant))

    noncanonical_hash = report.model_dump(mode="python", round_trip=True)
    noncanonical_hash["reconciliation_hash"] = report.reconciliation_hash.upper()
    with pytest.raises(ValidationError):
        CandleCrossSourceReconciliationV0.model_validate(noncanonical_hash)

    extra = report.model_dump(mode="python", round_trip=True)
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
    with pytest.raises(ValidationError, match="counts"):
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
    with pytest.raises(ValidationError, match="ordered"):
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
        ReconciliationSubclass.model_validate(report.model_dump(mode="python", round_trip=True))


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
    validator = Draft202012Validator(json.loads(rendered))
    payload = json.loads(report.model_dump_json())
    assert validator.is_valid(payload)
    assert CandleCrossSourceReconciliationV0.model_validate_json(report.model_dump_json()) == report


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
