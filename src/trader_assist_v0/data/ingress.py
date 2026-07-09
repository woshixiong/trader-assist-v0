from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from trader_assist_v0.contracts.common import EnvironmentV0
from trader_assist_v0.contracts.events import RawCaptureModeV0, RawEventV0
from trader_assist_v0.contracts.source_catalog import (
    PUBLIC_READ_ONLY_ENVIRONMENT,
    PUBLIC_READ_ONLY_OPERATION_CLASS,
    RATE_LIMIT_STATUS,
    SOURCE_ID,
    assert_rate_limit_allows_live_transport,
    rate_limit_entry_gate,
    validate_read_only_transport_entry,
)
from trader_assist_v0.data.bronze import (
    BronzeStore,
    ManifestAppendResult,
    ManifestWriter,
    PayloadWriteResult,
    payload_relative_path,
    payload_sha256,
)

A2_CONTRACT_ID = "V0-01A2-NO-NETWORK-PUBLIC-OBSERVATION-INGRESS-CONTRACT"
A2_COLLECTOR_VERSION = "trader-assist-v0.v0-01a2"


@dataclass(frozen=True)
class PublicObservationIngressResult:
    raw_event: RawEventV0
    payload_write: PayloadWriteResult | None = None
    manifest_append: ManifestAppendResult | None = None


def assert_live_transport_blocked_by_rate_limit_gate() -> None:
    gate = rate_limit_entry_gate()
    if RATE_LIMIT_STATUS != "UNRESOLVED_OFFICIAL_LIMIT":
        raise ValueError("V0-01A2 must not resolve official numeric rate limits")
    if gate.get("live_transport_authorized") is not False:
        raise ValueError("live transport must remain blocked while rate limits are unresolved")
    try:
        assert_rate_limit_allows_live_transport()
    except ValueError:
        return
    raise ValueError("live transport entry gate unexpectedly allowed runtime transport")


def bind_public_observation_bytes(
    *,
    payload: bytes,
    endpoint_id: str,
    operation_type: str,
    capture_mode: RawCaptureModeV0 | str,
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
    first_observed_time: datetime,
    collector_receive_time: datetime,
    collector_monotonic_ns: int,
    coin: Literal["BTC", "ETH"] | None = None,
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"] | None = None,
    content_type: str = "application/json",
    payload_encoding: str = "utf-8",
    collector_version: str = A2_COLLECTOR_VERSION,
) -> RawEventV0:
    if type(payload) is not bytes:
        raise TypeError("payload must be exact bytes supplied by the caller")

    capture = RawCaptureModeV0(capture_mode)
    validate_read_only_transport_entry(
        source_id=SOURCE_ID,
        environment=PUBLIC_READ_ONLY_ENVIRONMENT,
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        coin=coin,
        interval=candle_interval,
        capture_mode=capture.value,
        operation_class=PUBLIC_READ_ONLY_OPERATION_CLASS,
    )
    assert_live_transport_blocked_by_rate_limit_gate()

    digest = payload_sha256(payload)
    return RawEventV0.bind_observation(
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        coin=coin,
        candle_interval=candle_interval,
        capture_mode=capture,
        connection_id=connection_id,
        subscription_id=subscription_id,
        receive_sequence=receive_sequence,
        source_native_id=None,
        source_native_cursor=None,
        collector_version=collector_version,
        environment=EnvironmentV0.READ_ONLY,
        content_type=content_type,
        payload_sha256=digest,
        payload_size_bytes=len(payload),
        payload_encoding=payload_encoding,
        payload_ref=payload_relative_path(digest),
        source_event_time=None,
        source_publish_time=None,
        first_observed_time=first_observed_time,
        collector_receive_time=collector_receive_time,
        collector_monotonic_ns=collector_monotonic_ns,
        revision_time=None,
    )


def ingest_public_observation_bytes(
    *,
    payload: bytes,
    endpoint_id: str,
    operation_type: str,
    capture_mode: RawCaptureModeV0 | str,
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
    first_observed_time: datetime,
    collector_receive_time: datetime,
    collector_monotonic_ns: int,
    coin: Literal["BTC", "ETH"] | None = None,
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"] | None = None,
    content_type: str = "application/json",
    payload_encoding: str = "utf-8",
    collector_version: str = A2_COLLECTOR_VERSION,
    store: BronzeStore | None = None,
    writer: ManifestWriter | None = None,
) -> PublicObservationIngressResult:
    raw_event = bind_public_observation_bytes(
        payload=payload,
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        coin=coin,
        candle_interval=candle_interval,
        capture_mode=capture_mode,
        connection_id=connection_id,
        subscription_id=subscription_id,
        receive_sequence=receive_sequence,
        first_observed_time=first_observed_time,
        collector_receive_time=collector_receive_time,
        collector_monotonic_ns=collector_monotonic_ns,
        content_type=content_type,
        payload_encoding=payload_encoding,
        collector_version=collector_version,
    )

    if writer is not None and store is not None and writer.store is not store:
        raise ValueError("store must be the same BronzeStore used by the manifest writer")
    target_store: BronzeStore | None = store
    if target_store is None and writer is not None:
        target_store = writer.store
    payload_write = target_store.write_payload(payload) if target_store is not None else None
    manifest_append = writer.append(raw_event) if writer is not None else None
    return PublicObservationIngressResult(
        raw_event=raw_event,
        payload_write=payload_write,
        manifest_append=manifest_append,
    )
