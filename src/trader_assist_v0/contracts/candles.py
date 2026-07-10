from __future__ import annotations

import hmac
from collections.abc import Mapping, Set
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.config import ExtraValues

from .common import (
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    Sha256Hex,
    StrictModel,
    canonical_json_bytes,
    sha256_hex,
)

A5_CONTRACT_ID = "V0-01A5-OFFLINE-CANDLE-PAYLOAD-EXTRACTION-CONTRACT"
CANDLE_EXTRACTION_SCHEMA_VERSION = "0.1.0"
CANDLE_EXTRACTION_HASH_VERSION = "trader-assist-v0/candle-payload-extraction/v1"
CANDLE_LOGICAL_KEY_VERSION = "trader-assist-v0/candle-logical-key/v1"
SOURCE_ID = "hyperliquid-public-mainnet"


class CandleEnvelopeShapeV0(StrEnum):
    WS_DATA_CANDLE = "WS_DATA_CANDLE"
    WS_DATA_CANDLE_ARRAY = "WS_DATA_CANDLE_ARRAY"
    INFO_CANDLE_ARRAY = "INFO_CANDLE_ARRAY"


class _A5AuthorityModel(StrictModel):
    model_config = ConfigDict(revalidate_instances="always")

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if isinstance(obj, BaseModel):
            if type(obj) is not cls:
                raise ValueError(f"expected exact {cls.__name__} authority object")
            obj = BaseModel.model_dump(obj, mode="python", round_trip=True)
        return super().model_validate(
            obj,
            strict=strict,
            extra=extra,
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if update is not None:
            raise TypeError("A5 authority models cannot be copied with updates")
        return super().model_copy(deep=deep)

    def copy(
        self,
        *,
        include: (
            Set[int]
            | Set[str]
            | Mapping[int, Any]
            | Mapping[str, Any]
            | None
        ) = None,
        exclude: (
            Set[int]
            | Set[str]
            | Mapping[int, Any]
            | Mapping[str, Any]
            | None
        ) = None,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if include is not None or exclude is not None or update is not None:
            raise TypeError("A5 authority models cannot be copied with field changes")
        return self.model_copy(deep=deep)

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        raise TypeError("A5 authority models cannot bypass validation with model_construct")


def compute_candle_logical_key(
    *,
    source_id: str,
    coin: str,
    candle_interval: str,
    open_time_ms: int,
) -> str:
    material = canonical_json_bytes(
        {
            "logical_key_version": CANDLE_LOGICAL_KEY_VERSION,
            "source_id": source_id,
            "coin": coin,
            "candle_interval": candle_interval,
            "open_time_ms": open_time_ms,
        }
    )
    return sha256_hex(CANDLE_LOGICAL_KEY_VERSION.encode() + b"\0" + material)


class ExtractedCandleV0(_A5AuthorityModel):
    candle_logical_key: Sha256Hex
    open_time_ms: int = Field(ge=0)
    close_time_ms: int = Field(ge=0)
    open_price: PositiveFiniteDecimal
    high_price: PositiveFiniteDecimal
    low_price: PositiveFiniteDecimal
    close_price: PositiveFiniteDecimal
    volume_base: NonNegativeFiniteDecimal
    trade_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_candle(self) -> Self:
        if type(self) is not ExtractedCandleV0:
            raise ValueError("expected exact ExtractedCandleV0 authority object")
        if self.close_time_ms <= self.open_time_ms:
            raise ValueError("close_time_ms must be greater than open_time_ms")
        if self.high_price < max(
            self.open_price,
            self.close_price,
            self.low_price,
        ):
            raise ValueError("high_price is below candle price range")
        if self.low_price > min(
            self.open_price,
            self.close_price,
            self.high_price,
        ):
            raise ValueError("low_price is above candle price range")
        return self


class CandlePayloadExtractionV0(_A5AuthorityModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    contract_id: Literal[
        "V0-01A5-OFFLINE-CANDLE-PAYLOAD-EXTRACTION-CONTRACT"
    ] = "V0-01A5-OFFLINE-CANDLE-PAYLOAD-EXTRACTION-CONTRACT"
    extraction_version: Literal[
        "trader-assist-v0/candle-payload-extraction/v1"
    ] = "trader-assist-v0/candle-payload-extraction/v1"
    source_id: Literal["hyperliquid-public-mainnet"] = "hyperliquid-public-mainnet"
    source_event_id: Sha256Hex
    payload_sha256: Sha256Hex
    endpoint_id: Literal["hl-ws-mainnet-public", "hl-info-mainnet-public"]
    operation_type: Literal["candle", "candleSnapshot"]
    coin: Literal["BTC", "ETH"]
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"]
    envelope_shape: CandleEnvelopeShapeV0
    candles: tuple[ExtractedCandleV0, ...]
    extraction_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_extraction(self) -> Self:
        if type(self) is not CandlePayloadExtractionV0:
            raise ValueError("expected exact CandlePayloadExtractionV0 authority object")
        if self.endpoint_id == "hl-ws-mainnet-public":
            if self.operation_type != "candle":
                raise ValueError("WebSocket candle extraction requires operation candle")
            if self.envelope_shape not in {
                CandleEnvelopeShapeV0.WS_DATA_CANDLE,
                CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY,
            }:
                raise ValueError(
                    "WebSocket candle extraction has invalid envelope shape"
                )
        else:
            if self.operation_type != "candleSnapshot":
                raise ValueError(
                    "Info candle extraction requires operation candleSnapshot"
                )
            if self.envelope_shape is not CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY:
                raise ValueError("Info candle extraction has invalid envelope shape")

        logical_keys: set[str] = set()
        for candle in self.candles:
            expected_key = compute_candle_logical_key(
                source_id=self.source_id,
                coin=self.coin,
                candle_interval=self.candle_interval,
                open_time_ms=candle.open_time_ms,
            )
            if not hmac.compare_digest(candle.candle_logical_key, expected_key):
                raise ValueError(
                    "candle_logical_key does not match extraction authority"
                )
            if candle.candle_logical_key in logical_keys:
                raise ValueError("duplicate candle logical key in extraction")
            logical_keys.add(candle.candle_logical_key)

        expected_hash = compute_candle_extraction_hash(self)
        if not hmac.compare_digest(self.extraction_hash, expected_hash):
            raise ValueError("extraction_hash does not match canonical extraction")
        return self

    @classmethod
    def bind(
        cls,
        *,
        source_event_id: str,
        payload_sha256: str,
        endpoint_id: str,
        operation_type: str,
        coin: str,
        candle_interval: str,
        envelope_shape: CandleEnvelopeShapeV0 | str,
        candles: tuple[ExtractedCandleV0, ...],
        **forbidden_authority: Any,
    ) -> CandlePayloadExtractionV0:
        if forbidden_authority:
            raise ValueError(
                "A5 extraction authority fields are implementation-controlled"
            )
        payload = {
            "schema_version": CANDLE_EXTRACTION_SCHEMA_VERSION,
            "contract_id": A5_CONTRACT_ID,
            "extraction_version": CANDLE_EXTRACTION_HASH_VERSION,
            "source_id": SOURCE_ID,
            "source_event_id": source_event_id,
            "payload_sha256": payload_sha256,
            "endpoint_id": endpoint_id,
            "operation_type": operation_type,
            "coin": coin,
            "candle_interval": candle_interval,
            "envelope_shape": CandleEnvelopeShapeV0(envelope_shape),
            "candles": candles,
        }
        digest = compute_candle_extraction_hash_from_payload(payload)
        return cls.model_validate({**payload, "extraction_hash": digest})


def compute_candle_extraction_hash_from_payload(
    payload: Mapping[str, Any],
) -> str:
    return sha256_hex(
        CANDLE_EXTRACTION_HASH_VERSION.encode()
        + b"\0"
        + canonical_json_bytes(dict(payload))
    )


def compute_candle_extraction_hash(
    extraction: CandlePayloadExtractionV0,
) -> str:
    payload = BaseModel.model_dump(extraction, mode="python", round_trip=True)
    payload.pop("extraction_hash", None)
    return compute_candle_extraction_hash_from_payload(payload)
