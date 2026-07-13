from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
T2_COLLECTOR_VERSION = "trader-assist-v0.v0-t2-eth-public-capture"
_T2_PROOF_AUTHORITY = object()
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


@dataclass(frozen=True)
class PublicObservationIngressResult:
    raw_event: RawEventV0
    payload_write: PayloadWriteResult | None = None
    manifest_append: ManifestAppendResult | None = None


@dataclass(frozen=True, init=False)
class _T2ConsumedPermitProof:
    consumed_path: Path
    receipt_path: Path
    receipt_sha256: str
    permit_id: str
    _authority: object


def _issue_t2_consumed_permit_proof(
    *,
    consumed_path: Path,
    receipt_path: Path,
    receipt_sha256: str,
    permit_id: str,
) -> _T2ConsumedPermitProof:
    if _NOFOLLOW == 0:
        raise ValueError("T2 ingress proof issuance requires O_NOFOLLOW support")
    consumed_metadata = _verified_private_regular_file(consumed_path)
    receipt_metadata = _verified_private_regular_file(receipt_path)
    if _SHA256_RE.fullmatch(receipt_sha256) is None:
        raise ValueError("T2 receipt hash must be lowercase SHA-256")
    consumed_fd = os.open(consumed_path, os.O_RDONLY | _NOFOLLOW)
    try:
        opened = os.fstat(consumed_fd)
        if (opened.st_dev, opened.st_ino) != (
            consumed_metadata.st_dev,
            consumed_metadata.st_ino,
        ):
            raise ValueError("T2 consumed permit identity changed during proof issuance")
    finally:
        os.close(consumed_fd)
    receipt_fd = os.open(receipt_path, os.O_RDONLY | _NOFOLLOW)
    try:
        opened = os.fstat(receipt_fd)
        if (opened.st_dev, opened.st_ino) != (
            receipt_metadata.st_dev,
            receipt_metadata.st_ino,
        ):
            raise ValueError("T2 receipt identity changed during proof issuance")
        receipt_bytes = _read_bounded_receipt(receipt_fd)
    finally:
        os.close(receipt_fd)
    if hashlib.sha256(receipt_bytes).hexdigest() != receipt_sha256:
        raise ValueError("T2 receipt hash does not match its exact canonical bytes")
    if consumed_metadata.st_nlink < 1:
        raise ValueError("T2 consumed permit is no longer durable")

    proof = object.__new__(_T2ConsumedPermitProof)
    object.__setattr__(proof, "consumed_path", consumed_path)
    object.__setattr__(proof, "receipt_path", receipt_path)
    object.__setattr__(proof, "receipt_sha256", receipt_sha256)
    object.__setattr__(proof, "permit_id", permit_id)
    object.__setattr__(proof, "_authority", _T2_PROOF_AUTHORITY)
    return proof


def _verified_private_regular_file(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError("T2 ingress proof authority file is missing") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("T2 ingress proof authority must be an exact regular file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("T2 ingress proof authority file mode must be exactly 0600")
    if metadata.st_uid != os.geteuid():
        raise ValueError("T2 ingress proof authority file must be owned by the effective user")
    return metadata


def _read_bounded_receipt(fd: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > 16 * 1024:
            raise ValueError("T2 receipt exceeds the bounded proof size")
        chunks.append(chunk)


def _validate_t2_consumed_permit_proof(proof: _T2ConsumedPermitProof) -> None:
    if type(proof) is not _T2ConsumedPermitProof or proof._authority is not _T2_PROOF_AUTHORITY:
        raise ValueError("T2 ingress requires an authentic consumed start-permit proof")
    if (
        not proof.permit_id
        or not proof.consumed_path.name
        or not proof.receipt_path.name
        or _SHA256_RE.fullmatch(proof.receipt_sha256) is None
    ):
        raise ValueError("T2 consumed start-permit proof is incomplete")


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
    return _bind_public_observation_bytes(
        payload=payload,
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        capture_mode=capture_mode,
        connection_id=connection_id,
        subscription_id=subscription_id,
        receive_sequence=receive_sequence,
        first_observed_time=first_observed_time,
        collector_receive_time=collector_receive_time,
        collector_monotonic_ns=collector_monotonic_ns,
        coin=coin,
        candle_interval=candle_interval,
        content_type=content_type,
        payload_encoding=payload_encoding,
        collector_version=collector_version,
        t2_consumed_permit=None,
    )


def _bind_public_observation_bytes(
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
    coin: Literal["BTC", "ETH"] | None,
    candle_interval: Literal["1m", "3m", "5m", "15m", "1h"] | None,
    content_type: str,
    payload_encoding: str,
    collector_version: str,
    t2_consumed_permit: _T2ConsumedPermitProof | None,
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
    if t2_consumed_permit is None:
        assert_live_transport_blocked_by_rate_limit_gate()
    else:
        _validate_t2_consumed_permit_proof(t2_consumed_permit)

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


def _persist_public_observation(
    *,
    payload: bytes,
    raw_event: RawEventV0,
    store: BronzeStore | None,
    writer: ManifestWriter | None,
) -> PublicObservationIngressResult:
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

    return _persist_public_observation(
        payload=payload,
        raw_event=raw_event,
        store=store,
        writer=writer,
    )


def ingest_t2_eth_public_candle_bytes(
    *,
    payload: bytes,
    consumed_permit: _T2ConsumedPermitProof,
    candle_interval: Literal["5m", "15m"],
    connection_id: str,
    subscription_id: str,
    receive_sequence: int,
    first_observed_time: datetime,
    collector_receive_time: datetime,
    collector_monotonic_ns: int,
    store: BronzeStore,
    writer: ManifestWriter,
) -> PublicObservationIngressResult:
    _validate_t2_consumed_permit_proof(consumed_permit)
    if candle_interval not in {"5m", "15m"}:
        raise ValueError("T2 ingress accepts only ETH 5m or 15m candles")
    raw_event = _bind_public_observation_bytes(
        payload=payload,
        endpoint_id="hl-ws-mainnet-public",
        operation_type="candle",
        coin="ETH",
        candle_interval=candle_interval,
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        connection_id=connection_id,
        subscription_id=subscription_id,
        receive_sequence=receive_sequence,
        first_observed_time=first_observed_time,
        collector_receive_time=collector_receive_time,
        collector_monotonic_ns=collector_monotonic_ns,
        content_type="application/json",
        payload_encoding="utf-8",
        collector_version=T2_COLLECTOR_VERSION,
        t2_consumed_permit=consumed_permit,
    )
    return _persist_public_observation(
        payload=payload,
        raw_event=raw_event,
        store=store,
        writer=writer,
    )
