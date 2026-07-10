from __future__ import annotations

import hmac
from collections.abc import Mapping, Set
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator
from pydantic.config import ExtraValues

from .candles import (
    CandleEnvelopeShapeV0,
    ExtractedCandleV0,
    compute_candle_logical_key,
)
from .common import (
    FiniteDecimalString,
    Sha256Hex,
    StrictModel,
    canonical_json_bytes,
    decimal_to_canonical_string,
    sha256_hex,
)

A6_CONTRACT_ID = "V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT"
A6_SCHEMA_VERSION = "0.1.0"
A6_HASH_VERSION = "trader-assist-v0/candle-cross-source-reconciliation/v1"

_A6_INTEGER_WIRE_FIELDS = frozenset(
    {
        "open_time_ms",
        "close_time_ms",
        "trade_count",
        "match_count",
        "conflict_count",
        "ws_only_count",
        "info_only_count",
    }
)
_A6_STRING_WIRE_FIELDS = frozenset(
    {
        "schema_version",
        "contract_id",
        "hash_version",
        "source_id",
        "coin",
        "candle_interval",
        "ws_source_event_id",
        "ws_extraction_hash",
        "info_source_event_id",
        "info_extraction_hash",
        "reconciliation_hash",
        "candle_logical_key",
        "status",
        "side",
        "source_event_id",
        "extraction_hash",
        "endpoint_id",
        "operation_type",
        "envelope_shape",
        "field_name",
        "ws_value",
        "info_value",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_base",
    }
)

CANDLE_CROSS_SOURCE_COMPARABLE_FIELDS = (
    "close_time_ms",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume_base",
    "trade_count",
)

type CandleCrossSourceComparableFieldV0 = Literal[
    "close_time_ms",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume_base",
    "trade_count",
]
type CandleCrossSourceComparableValueV0 = FiniteDecimalString


class CandleCrossSourceComparisonStatusV0(StrEnum):
    MATCH = "MATCH"
    CONFLICT = "CONFLICT"
    WS_ONLY = "WS_ONLY"
    INFO_ONLY = "INFO_ONLY"


class CandleCrossSourceAuthoritySideV0(StrEnum):
    WS = "WS"
    INFO = "INFO"


def _validate_a6_json_wire(value: Any) -> None:
    if isinstance(value, dict):
        for field_name, item in value.items():
            if field_name in _A6_INTEGER_WIRE_FIELDS and type(item) is not int:
                raise ValueError(f"{field_name} JSON value must be an integer")
            if field_name in _A6_STRING_WIRE_FIELDS and type(item) is not str:
                raise ValueError(f"{field_name} JSON value must be a string")
            _validate_a6_json_wire(item)
        return
    if isinstance(value, list):
        for item in value:
            _validate_a6_json_wire(item)
        return
    if isinstance(value, str) and value != value.strip():
        raise ValueError("A6 JSON strings must not be whitespace padded")


class _A6AuthorityModel(StrictModel):
    model_config = ConfigDict(
        revalidate_instances="always",
        str_strip_whitespace=False,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_json_wire(cls, value: Any, info: ValidationInfo) -> Any:
        if info.mode == "json":
            _validate_a6_json_wire(value)
        return value

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
            raise TypeError("A6 authority models cannot be copied with updates")
        return super().model_copy(deep=deep)

    def copy(
        self,
        *,
        include: (Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None) = None,
        exclude: (Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None) = None,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        if include is not None or exclude is not None or update is not None:
            raise TypeError("A6 authority models cannot be copied with field changes")
        return self.model_copy(deep=deep)

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        raise TypeError("A6 authority models cannot bypass validation with model_construct")


class CandleCrossSourceInputAuthorityV0(_A6AuthorityModel):
    side: CandleCrossSourceAuthoritySideV0
    source_event_id: Sha256Hex
    extraction_hash: Sha256Hex
    endpoint_id: Literal["hl-ws-mainnet-public", "hl-info-mainnet-public"]
    operation_type: Literal["candle", "candleSnapshot"]
    envelope_shape: CandleEnvelopeShapeV0

    @model_validator(mode="after")
    def validate_role(self) -> Self:
        if type(self) is not CandleCrossSourceInputAuthorityV0:
            raise ValueError("expected exact CandleCrossSourceInputAuthorityV0 authority object")
        if self.side is CandleCrossSourceAuthoritySideV0.WS:
            if self.endpoint_id != "hl-ws-mainnet-public":
                raise ValueError("WS authority requires the frozen WebSocket endpoint")
            if self.operation_type != "candle":
                raise ValueError("WS authority requires operation candle")
            if self.envelope_shape not in {
                CandleEnvelopeShapeV0.WS_DATA_CANDLE,
                CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY,
            }:
                raise ValueError("WS authority has invalid envelope shape")
        else:
            if self.endpoint_id != "hl-info-mainnet-public":
                raise ValueError("Info authority requires the frozen Info endpoint")
            if self.operation_type != "candleSnapshot":
                raise ValueError("Info authority requires operation candleSnapshot")
            if self.envelope_shape is not CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY:
                raise ValueError("Info authority has invalid envelope shape")
        return self


class CandleCrossSourceFieldDifferenceV0(_A6AuthorityModel):
    field_name: CandleCrossSourceComparableFieldV0
    ws_value: CandleCrossSourceComparableValueV0
    info_value: CandleCrossSourceComparableValueV0

    @model_validator(mode="after")
    def validate_value_kinds(self) -> Self:
        if type(self) is not CandleCrossSourceFieldDifferenceV0:
            raise ValueError("expected exact CandleCrossSourceFieldDifferenceV0 authority object")
        integer_field = self.field_name in {"close_time_ms", "trade_count"}
        if integer_field and (not self.ws_value.isdigit() or not self.info_value.isdigit()):
            raise ValueError(f"{self.field_name} difference values must be integers")
        if self.ws_value == self.info_value:
            raise ValueError("field difference values must differ")
        return self


def _revalidate_extracted_candle(value: ExtractedCandleV0) -> ExtractedCandleV0:
    if type(value) is not ExtractedCandleV0:
        raise ValueError("expected exact ExtractedCandleV0 authority object")
    payload = BaseModel.model_dump(value, mode="python", round_trip=True)
    return ExtractedCandleV0.model_validate(payload)


def _expected_differences(
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


def _comparison_wire_value(value: int | Decimal) -> str:
    if isinstance(value, int):
        return str(value)
    return decimal_to_canonical_string(value)


class CandleCrossSourceComparisonItemV0(_A6AuthorityModel):
    candle_logical_key: Sha256Hex
    source_id: Literal["hyperliquid-public-mainnet"] = "hyperliquid-public-mainnet"
    coin: Literal["BTC", "ETH"]
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"]
    open_time_ms: int = Field(ge=0)
    status: CandleCrossSourceComparisonStatusV0
    ws_candle: ExtractedCandleV0 | None
    ws_authority: CandleCrossSourceInputAuthorityV0 | None
    info_candle: ExtractedCandleV0 | None
    info_authority: CandleCrossSourceInputAuthorityV0 | None
    field_differences: tuple[CandleCrossSourceFieldDifferenceV0, ...]

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        if type(self) is not CandleCrossSourceComparisonItemV0:
            raise ValueError("expected exact CandleCrossSourceComparisonItemV0 authority object")
        expected_key = compute_candle_logical_key(
            source_id=self.source_id,
            coin=self.coin,
            candle_interval=self.candle_interval,
            open_time_ms=self.open_time_ms,
        )
        if not hmac.compare_digest(self.candle_logical_key, expected_key):
            raise ValueError("comparison logical key does not match identity fields")

        ws_candle = (
            _revalidate_extracted_candle(self.ws_candle) if self.ws_candle is not None else None
        )
        info_candle = (
            _revalidate_extracted_candle(self.info_candle) if self.info_candle is not None else None
        )
        if (ws_candle is None) != (self.ws_authority is None):
            raise ValueError("WS candle and authority must be present or absent together")
        if (info_candle is None) != (self.info_authority is None):
            raise ValueError("Info candle and authority must be present or absent together")

        for candle in (ws_candle, info_candle):
            if candle is None:
                continue
            if candle.open_time_ms != self.open_time_ms:
                raise ValueError("comparison candle open time conflicts with identity")
            if not hmac.compare_digest(
                candle.candle_logical_key,
                self.candle_logical_key,
            ):
                raise ValueError("comparison candle logical key conflicts with identity")

        if self.ws_authority is not None:
            if type(self.ws_authority) is not CandleCrossSourceInputAuthorityV0:
                raise ValueError("WS item authority must have exact A6 authority type")
            if self.ws_authority.side is not CandleCrossSourceAuthoritySideV0.WS:
                raise ValueError("WS item authority has reversed role")
        if self.info_authority is not None:
            if type(self.info_authority) is not CandleCrossSourceInputAuthorityV0:
                raise ValueError("Info item authority must have exact A6 authority type")
            if self.info_authority.side is not CandleCrossSourceAuthoritySideV0.INFO:
                raise ValueError("Info item authority has reversed role")

        if self.status is CandleCrossSourceComparisonStatusV0.WS_ONLY:
            if ws_candle is None or info_candle is not None:
                raise ValueError("WS_ONLY requires only a WS candle")
            expected_differences: tuple[CandleCrossSourceFieldDifferenceV0, ...] = ()
        elif self.status is CandleCrossSourceComparisonStatusV0.INFO_ONLY:
            if ws_candle is not None or info_candle is None:
                raise ValueError("INFO_ONLY requires only an Info candle")
            expected_differences = ()
        else:
            if ws_candle is None or info_candle is None:
                raise ValueError("MATCH and CONFLICT require both source candles")
            expected_differences = _expected_differences(ws_candle, info_candle)
            if self.status is CandleCrossSourceComparisonStatusV0.MATCH:
                if expected_differences:
                    raise ValueError("MATCH cannot contain differing comparable fields")
            elif not expected_differences:
                raise ValueError("CONFLICT requires at least one field difference")

        if self.field_differences != expected_differences:
            raise ValueError("field differences do not match exact comparable field authority")
        return self


class CandleCrossSourceReconciliationV0(_A6AuthorityModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    contract_id: Literal["V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT"] = (
        "V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT"
    )
    hash_version: Literal["trader-assist-v0/candle-cross-source-reconciliation/v1"] = (
        "trader-assist-v0/candle-cross-source-reconciliation/v1"
    )
    source_id: Literal["hyperliquid-public-mainnet"] = "hyperliquid-public-mainnet"
    coin: Literal["BTC", "ETH"]
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"]
    ws_source_event_id: Sha256Hex
    ws_extraction_hash: Sha256Hex
    info_source_event_id: Sha256Hex
    info_extraction_hash: Sha256Hex
    comparisons: tuple[CandleCrossSourceComparisonItemV0, ...]
    match_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    ws_only_count: int = Field(ge=0)
    info_only_count: int = Field(ge=0)
    reconciliation_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        if type(self) is not CandleCrossSourceReconciliationV0:
            raise ValueError("expected exact CandleCrossSourceReconciliationV0 authority object")
        ordering: list[tuple[int, str]] = []
        counts = {
            CandleCrossSourceComparisonStatusV0.MATCH: 0,
            CandleCrossSourceComparisonStatusV0.CONFLICT: 0,
            CandleCrossSourceComparisonStatusV0.WS_ONLY: 0,
            CandleCrossSourceComparisonStatusV0.INFO_ONLY: 0,
        }
        for item in self.comparisons:
            if type(item) is not CandleCrossSourceComparisonItemV0:
                raise ValueError("report requires exact A6 comparison items")
            if (
                item.source_id != self.source_id
                or item.coin != self.coin
                or item.candle_interval != self.candle_interval
            ):
                raise ValueError("comparison identity conflicts with report identity")
            if item.ws_authority is not None and (
                item.ws_authority.source_event_id != self.ws_source_event_id
                or item.ws_authority.extraction_hash != self.ws_extraction_hash
            ):
                raise ValueError("WS item authority conflicts with report authority")
            if item.info_authority is not None and (
                item.info_authority.source_event_id != self.info_source_event_id
                or item.info_authority.extraction_hash != self.info_extraction_hash
            ):
                raise ValueError("Info item authority conflicts with report authority")
            ordering.append((item.open_time_ms, item.candle_logical_key))
            counts[item.status] += 1

        if ordering != sorted(ordering) or len(ordering) != len(set(ordering)):
            raise ValueError("comparisons must be uniquely ordered by open time and logical key")
        expected_counts = (
            counts[CandleCrossSourceComparisonStatusV0.MATCH],
            counts[CandleCrossSourceComparisonStatusV0.CONFLICT],
            counts[CandleCrossSourceComparisonStatusV0.WS_ONLY],
            counts[CandleCrossSourceComparisonStatusV0.INFO_ONLY],
        )
        actual_counts = (
            self.match_count,
            self.conflict_count,
            self.ws_only_count,
            self.info_only_count,
        )
        if actual_counts != expected_counts:
            raise ValueError("report counts do not match comparison statuses")

        expected_hash = compute_candle_cross_source_reconciliation_hash(self)
        if not hmac.compare_digest(self.reconciliation_hash, expected_hash):
            raise ValueError("reconciliation_hash does not match canonical reconciliation")
        return self

    @classmethod
    def bind(
        cls,
        *,
        source_id: str,
        coin: str,
        candle_interval: str,
        ws_source_event_id: str,
        ws_extraction_hash: str,
        info_source_event_id: str,
        info_extraction_hash: str,
        comparisons: tuple[CandleCrossSourceComparisonItemV0, ...],
        **forbidden_authority: Any,
    ) -> CandleCrossSourceReconciliationV0:
        if forbidden_authority:
            raise ValueError("A6 reconciliation authority fields are implementation-controlled")
        counts = {
            status: sum(item.status is status for item in comparisons)
            for status in CandleCrossSourceComparisonStatusV0
        }
        payload = {
            "schema_version": A6_SCHEMA_VERSION,
            "contract_id": A6_CONTRACT_ID,
            "hash_version": A6_HASH_VERSION,
            "source_id": source_id,
            "coin": coin,
            "candle_interval": candle_interval,
            "ws_source_event_id": ws_source_event_id,
            "ws_extraction_hash": ws_extraction_hash,
            "info_source_event_id": info_source_event_id,
            "info_extraction_hash": info_extraction_hash,
            "comparisons": comparisons,
            "match_count": counts[CandleCrossSourceComparisonStatusV0.MATCH],
            "conflict_count": counts[CandleCrossSourceComparisonStatusV0.CONFLICT],
            "ws_only_count": counts[CandleCrossSourceComparisonStatusV0.WS_ONLY],
            "info_only_count": counts[CandleCrossSourceComparisonStatusV0.INFO_ONLY],
        }
        digest = compute_candle_cross_source_reconciliation_hash_from_payload(payload)
        return cls.model_validate({**payload, "reconciliation_hash": digest})


def compute_candle_cross_source_reconciliation_hash_from_payload(
    payload: Mapping[str, Any],
) -> str:
    return sha256_hex(A6_HASH_VERSION.encode() + b"\0" + canonical_json_bytes(dict(payload)))


def compute_candle_cross_source_reconciliation_hash(
    reconciliation: CandleCrossSourceReconciliationV0,
) -> str:
    payload = BaseModel.model_dump(
        reconciliation,
        mode="python",
        round_trip=True,
    )
    payload.pop("reconciliation_hash", None)
    return compute_candle_cross_source_reconciliation_hash_from_payload(payload)
