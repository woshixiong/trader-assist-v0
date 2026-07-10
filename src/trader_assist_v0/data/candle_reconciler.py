from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from trader_assist_v0.contracts.candle_reconciliation import (
    CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS,
    CandleCrossSourceAuthoritySideV0,
    CandleCrossSourceComparisonItemV0,
    CandleCrossSourceComparisonStatusV0,
    CandleCrossSourceFieldDifferenceV0,
    CandleCrossSourceInputAuthorityV0,
    CandleCrossSourceReconciliationV0,
)
from trader_assist_v0.contracts.candles import (
    CandleEnvelopeShapeV0,
    CandlePayloadExtractionV0,
    ExtractedCandleV0,
)
from trader_assist_v0.contracts.common import decimal_to_canonical_string


class CandleCrossSourceReconciliationError(ValueError):
    pass


def _revalidate_extraction(
    value: Any,
    *,
    role: CandleCrossSourceAuthoritySideV0,
) -> CandlePayloadExtractionV0:
    if type(value) is not CandlePayloadExtractionV0:
        raise TypeError(f"{role.value} input must be exact CandlePayloadExtractionV0 authority")
    try:
        payload = BaseModel.model_dump(value, mode="python", round_trip=True)
        extraction = CandlePayloadExtractionV0.model_validate(payload)
    except (AttributeError, TypeError, ValueError) as exc:
        raise CandleCrossSourceReconciliationError(
            f"{role.value} extraction authority revalidation failed"
        ) from exc

    if role is CandleCrossSourceAuthoritySideV0.WS:
        if extraction.endpoint_id != "hl-ws-mainnet-public":
            raise CandleCrossSourceReconciliationError(
                "WS extraction requires the frozen WebSocket endpoint"
            )
        if extraction.operation_type != "candle":
            raise CandleCrossSourceReconciliationError("WS extraction requires operation candle")
        if extraction.envelope_shape not in {
            CandleEnvelopeShapeV0.WS_DATA_CANDLE,
            CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY,
        }:
            raise CandleCrossSourceReconciliationError("WS extraction has invalid envelope shape")
    else:
        if extraction.endpoint_id != "hl-info-mainnet-public":
            raise CandleCrossSourceReconciliationError(
                "Info extraction requires the frozen Info endpoint"
            )
        if extraction.operation_type != "candleSnapshot":
            raise CandleCrossSourceReconciliationError(
                "Info extraction requires operation candleSnapshot"
            )
        if extraction.envelope_shape is not CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY:
            raise CandleCrossSourceReconciliationError("Info extraction has invalid envelope shape")
    return extraction


def _authority(
    extraction: CandlePayloadExtractionV0,
    *,
    role: CandleCrossSourceAuthoritySideV0,
) -> CandleCrossSourceInputAuthorityV0:
    return CandleCrossSourceInputAuthorityV0.model_validate(
        {
            "side": role,
            "source_event_id": extraction.source_event_id,
            "extraction_hash": extraction.extraction_hash,
            "endpoint_id": extraction.endpoint_id,
            "operation_type": extraction.operation_type,
            "envelope_shape": extraction.envelope_shape,
        }
    )


def _differences(
    ws_candle: ExtractedCandleV0,
    info_candle: ExtractedCandleV0,
) -> tuple[CandleCrossSourceFieldDifferenceV0, ...]:
    differences: list[CandleCrossSourceFieldDifferenceV0] = []
    for field_name in CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS:
        ws_value = getattr(ws_candle, field_name)
        info_value = getattr(info_candle, field_name)
        if ws_value != info_value:
            differences.append(
                CandleCrossSourceFieldDifferenceV0.model_validate(
                    {
                        "field_name": field_name,
                        "ws_value": _comparison_wire_value(ws_value),
                        "info_value": _comparison_wire_value(info_value),
                    }
                )
            )
    return tuple(differences)


def _comparison_wire_value(value: Any) -> str:
    if type(value) is int:
        return str(value)
    return decimal_to_canonical_string(value)


def reconcile_candle_extractions(
    *,
    ws_extraction: CandlePayloadExtractionV0,
    info_extraction: CandlePayloadExtractionV0,
) -> CandleCrossSourceReconciliationV0:
    ws = _revalidate_extraction(
        ws_extraction,
        role=CandleCrossSourceAuthoritySideV0.WS,
    )
    info = _revalidate_extraction(
        info_extraction,
        role=CandleCrossSourceAuthoritySideV0.INFO,
    )
    if ws.source_id != info.source_id:
        raise CandleCrossSourceReconciliationError("source identity mismatch")
    if ws.coin != info.coin:
        raise CandleCrossSourceReconciliationError("coin identity mismatch")
    if ws.candle_interval != info.candle_interval:
        raise CandleCrossSourceReconciliationError("candle interval identity mismatch")

    ws_by_key = {candle.candle_logical_key: candle for candle in ws.candles}
    info_by_key = {candle.candle_logical_key: candle for candle in info.candles}
    union_keys = ws_by_key.keys() | info_by_key.keys()
    ordered_keys = sorted(
        union_keys,
        key=lambda key: (
            (ws_by_key.get(key) or info_by_key[key]).open_time_ms,
            key,
        ),
    )

    ws_authority = _authority(
        ws,
        role=CandleCrossSourceAuthoritySideV0.WS,
    )
    info_authority = _authority(
        info,
        role=CandleCrossSourceAuthoritySideV0.INFO,
    )
    comparisons: list[CandleCrossSourceComparisonItemV0] = []
    for logical_key in ordered_keys:
        ws_candle = ws_by_key.get(logical_key)
        info_candle = info_by_key.get(logical_key)
        if ws_candle is None:
            status = CandleCrossSourceComparisonStatusV0.INFO_ONLY
            differences: tuple[CandleCrossSourceFieldDifferenceV0, ...] = ()
        elif info_candle is None:
            status = CandleCrossSourceComparisonStatusV0.WS_ONLY
            differences = ()
        else:
            differences = _differences(ws_candle, info_candle)
            status = (
                CandleCrossSourceComparisonStatusV0.CONFLICT
                if differences
                else CandleCrossSourceComparisonStatusV0.MATCH
            )
        identity_candle = ws_candle or info_candle
        if identity_candle is None:
            raise CandleCrossSourceReconciliationError(
                "logical key union produced no candle authority"
            )
        comparisons.append(
            CandleCrossSourceComparisonItemV0.model_validate(
                {
                    "candle_logical_key": logical_key,
                    "source_id": ws.source_id,
                    "coin": ws.coin,
                    "candle_interval": ws.candle_interval,
                    "open_time_ms": identity_candle.open_time_ms,
                    "status": status,
                    "ws_candle": ws_candle,
                    "ws_authority": ws_authority if ws_candle is not None else None,
                    "info_candle": info_candle,
                    "info_authority": (info_authority if info_candle is not None else None),
                    "field_differences": differences,
                }
            )
        )

    return CandleCrossSourceReconciliationV0.bind(
        source_id=ws.source_id,
        coin=ws.coin,
        candle_interval=ws.candle_interval,
        ws_source_event_id=ws.source_event_id,
        ws_extraction_hash=ws.extraction_hash,
        info_source_event_id=info.source_event_id,
        info_extraction_hash=info.extraction_hash,
        comparisons=tuple(comparisons),
    )
