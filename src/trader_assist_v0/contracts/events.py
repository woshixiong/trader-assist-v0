from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from .common import EnvironmentV0, OpaqueId, Sha256Hex, StrictModel, UTCDateTime, VersionId


class EventTypeV0(StrEnum):
    TRADE = "TradeEventV0"
    BBO = "BboEventV0"
    BOOK_SNAPSHOT = "BookSnapshotEventV0"
    BOOK_DELTA = "BookDeltaEventV0"
    CANDLE = "CandleEventV0"
    ASSET_CONTEXT = "AssetContextEventV0"
    ACCOUNT_STATE = "AccountStateEventV0"
    POSITION = "PositionEventV0"
    OPEN_ORDER = "OpenOrderEventV0"
    ORDER_UPDATE = "OrderUpdateEventV0"
    FILL = "FillEventV0"
    FUNDING = "FundingEventV0"
    LEDGER = "LedgerEventV0"
    MACRO = "MacroEventV0"
    NEWS = "NewsEventV0"
    SOCIAL = "SocialEventV0"
    LIQUIDATION_CONTEXT = "LiquidationContextEventV0"
    LARGE_FLOW = "LargeFlowEventV0"
    DATA_HEALTH = "DataHealthEventV0"


class RawEventV0(StrictModel):
    schema_version: VersionId
    source_event_id: OpaqueId
    source_id: OpaqueId
    connection_id: OpaqueId
    endpoint: str = Field(min_length=1, max_length=300)
    subscription: str = Field(min_length=1, max_length=300)
    environment: EnvironmentV0
    collector_version: VersionId
    collector_receive_time: UTCDateTime
    source_event_time: UTCDateTime | None = None
    receive_sequence: int = Field(ge=0)
    payload_sha256: Sha256Hex
    payload_size_bytes: int = Field(ge=0)
    payload_encoding: str = Field(min_length=1, max_length=40)
    payload_ref: str = Field(min_length=1, max_length=500)


class NormalizedEventV0(StrictModel):
    schema_version: VersionId
    normalized_event_id: OpaqueId
    source_event_id: OpaqueId
    event_type: EventTypeV0
    normalized_time: UTCDateTime
    normalized_payload_sha256: Sha256Hex
    units: dict[str, str] = Field(default_factory=dict)
    precision: dict[str, int] = Field(default_factory=dict)
    payload: dict[str, Any]
