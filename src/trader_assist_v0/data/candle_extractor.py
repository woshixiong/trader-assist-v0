from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

from trader_assist_v0.contracts.candles import (
    CandleEnvelopeShapeV0,
    CandlePayloadExtractionV0,
    ExtractedCandleV0,
    compute_candle_logical_key,
)
from trader_assist_v0.contracts.common import decimal_to_canonical_string
from trader_assist_v0.contracts.events import RawCaptureModeV0, RawEventV0

_WS_ENDPOINT = "hl-ws-mainnet-public"
_WS_OPERATION = "candle"
_INFO_ENDPOINT = "hl-info-mainnet-public"
_INFO_OPERATION = "candleSnapshot"
_CANDLE_FIELDS = frozenset(
    {"t", "T", "s", "i", "o", "c", "h", "l", "v", "n"}
)


class CandlePayloadExtractionError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise CandlePayloadExtractionError(
        f"non-finite JSON number is forbidden: {value}"
    )


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CandlePayloadExtractionError(
                f"duplicate JSON object key: {key}"
            )
        result[key] = value
    return result


def _decode_json(payload: bytes) -> Any:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise CandlePayloadExtractionError("UTF-8 BOM is forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CandlePayloadExtractionError(
            "payload is not valid UTF-8"
        ) from exc
    try:
        return json.loads(
            text,
            parse_float=Decimal,
            parse_int=int,
            parse_constant=_reject_constant,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except CandlePayloadExtractionError:
        raise
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise CandlePayloadExtractionError(
            "payload is not valid strict JSON"
        ) from exc


def _exact_nonnegative_integer(value: Any, field_name: str) -> int:
    if type(value) is not int:
        raise CandlePayloadExtractionError(
            f"{field_name} must be an exact JSON integer"
        )
    if value < 0:
        raise CandlePayloadExtractionError(
            f"{field_name} must be nonnegative"
        )
    return value


def _exact_decimal(
    value: Any,
    field_name: str,
    *,
    positive: bool,
) -> Decimal:
    if type(value) is int:
        decimal_value = Decimal(value)
    elif type(value) is Decimal:
        decimal_value = value
    else:
        raise CandlePayloadExtractionError(
            f"{field_name} must be an exact JSON number"
        )
    if not decimal_value.is_finite():
        raise CandlePayloadExtractionError(f"{field_name} must be finite")
    if positive and decimal_value <= 0:
        raise CandlePayloadExtractionError(f"{field_name} must be positive")
    if not positive and decimal_value < 0:
        raise CandlePayloadExtractionError(
            f"{field_name} must be nonnegative"
        )
    decimal_to_canonical_string(decimal_value)
    return decimal_value


def _extract_candle(
    value: Any,
    *,
    expected_coin: str,
    expected_interval: str,
) -> ExtractedCandleV0:
    if type(value) is not dict:
        raise CandlePayloadExtractionError(
            "each candle must be a JSON object"
        )
    keys = frozenset(value)
    if keys != _CANDLE_FIELDS:
        missing = sorted(_CANDLE_FIELDS - keys)
        extra = sorted(keys - _CANDLE_FIELDS)
        raise CandlePayloadExtractionError(
            "candle fields must match frozen authority; "
            f"missing={missing}; extra={extra}"
        )

    coin = value["s"]
    interval = value["i"]
    if type(coin) is not str or coin != expected_coin:
        raise CandlePayloadExtractionError(
            "candle coin does not match RawEvent authority"
        )
    if type(interval) is not str or interval != expected_interval:
        raise CandlePayloadExtractionError(
            "candle interval does not match RawEvent authority"
        )

    open_time_ms = _exact_nonnegative_integer(value["t"], "t")
    close_time_ms = _exact_nonnegative_integer(value["T"], "T")
    trade_count = _exact_nonnegative_integer(value["n"], "n")
    open_price = _exact_decimal(value["o"], "o", positive=True)
    close_price = _exact_decimal(value["c"], "c", positive=True)
    high_price = _exact_decimal(value["h"], "h", positive=True)
    low_price = _exact_decimal(value["l"], "l", positive=True)
    volume_base = _exact_decimal(value["v"], "v", positive=False)

    logical_key = compute_candle_logical_key(
        source_id="hyperliquid-public-mainnet",
        coin=expected_coin,
        candle_interval=expected_interval,
        open_time_ms=open_time_ms,
    )
    return ExtractedCandleV0.model_validate(
        {
            "candle_logical_key": logical_key,
            "open_time_ms": open_time_ms,
            "close_time_ms": close_time_ms,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "close_price": close_price,
            "volume_base": volume_base,
            "trade_count": trade_count,
        }
    )


def extract_candle_payload(
    *,
    raw_event: RawEventV0,
    payload: bytes,
) -> CandlePayloadExtractionV0:
    if type(raw_event) is not RawEventV0:
        raise TypeError(
            "raw_event must be an exact RawEventV0 authority object"
        )
    if type(payload) is not bytes:
        raise TypeError("payload must be exact bytes supplied by the caller")
    exact_event = RawEventV0.model_validate(raw_event)

    if exact_event.content_type != "application/json":
        raise CandlePayloadExtractionError(
            "content_type must be application/json"
        )
    if exact_event.payload_encoding != "utf-8":
        raise CandlePayloadExtractionError("payload_encoding must be utf-8")
    if len(payload) != exact_event.payload_size_bytes:
        raise CandlePayloadExtractionError(
            "payload size does not match RawEvent authority"
        )
    digest = hashlib.sha256(payload).hexdigest()
    if digest != exact_event.payload_sha256:
        raise CandlePayloadExtractionError(
            "payload hash does not match RawEvent authority"
        )
    if exact_event.coin is None or exact_event.candle_interval is None:
        raise CandlePayloadExtractionError(
            "candle extraction requires coin and interval authority"
        )

    parsed = _decode_json(payload)
    envelope_shape: CandleEnvelopeShapeV0
    candle_values: list[Any]

    if (
        exact_event.endpoint_id == _WS_ENDPOINT
        and exact_event.operation_type == _WS_OPERATION
    ):
        if (
            exact_event.capture_mode
            is not RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD
        ):
            raise CandlePayloadExtractionError(
                "WebSocket candle capture mode mismatch"
            )
        if (
            type(parsed) is not dict
            or frozenset(parsed) != frozenset({"channel", "data"})
        ):
            raise CandlePayloadExtractionError(
                "WebSocket candle payload has invalid envelope"
            )
        if parsed["channel"] != "candle":
            raise CandlePayloadExtractionError(
                "WebSocket candle channel mismatch"
            )
        data = parsed["data"]
        if type(data) is dict:
            envelope_shape = CandleEnvelopeShapeV0.WS_DATA_CANDLE
            candle_values = [data]
        elif type(data) is list:
            envelope_shape = CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY
            candle_values = data
        else:
            raise CandlePayloadExtractionError(
                "WebSocket candle data must be an object or array"
            )
    elif (
        exact_event.endpoint_id == _INFO_ENDPOINT
        and exact_event.operation_type == _INFO_OPERATION
    ):
        if exact_event.capture_mode is not RawCaptureModeV0.HTTP_RESPONSE_BODY:
            raise CandlePayloadExtractionError(
                "Info candle capture mode mismatch"
            )
        if type(parsed) is not list:
            raise CandlePayloadExtractionError(
                "Info candleSnapshot payload must be an array"
            )
        envelope_shape = CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY
        candle_values = parsed
    else:
        raise CandlePayloadExtractionError(
            "RawEvent selection is not a supported candle source"
        )

    candles = tuple(
        _extract_candle(
            value,
            expected_coin=exact_event.coin,
            expected_interval=exact_event.candle_interval,
        )
        for value in candle_values
    )
    logical_keys = [candle.candle_logical_key for candle in candles]
    if len(logical_keys) != len(set(logical_keys)):
        raise CandlePayloadExtractionError(
            "duplicate candle logical key in one payload"
        )

    return CandlePayloadExtractionV0.bind(
        source_event_id=exact_event.source_event_id,
        payload_sha256=exact_event.payload_sha256,
        endpoint_id=exact_event.endpoint_id,
        operation_type=exact_event.operation_type,
        coin=exact_event.coin,
        candle_interval=exact_event.candle_interval,
        envelope_shape=envelope_shape,
        candles=candles,
    )
