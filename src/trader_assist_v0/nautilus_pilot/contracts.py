"""Nautilus-independent project contracts for the bounded E3 pilot seam."""

from __future__ import annotations

import hmac
from dataclasses import asdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    SCANNER_VERSION,
    KernelResult,
    ScannerLinkage,
)

E3_CONTRACT_SCHEMA_VERSION = "1"
E3_INPUT_KIND = "TRADE_OS_STRATEGY_INPUT"
E3_AUTHORITY_MARKER = "NONAUTHORITATIVE_E3_PILOT"
_INPUT_HASH_DOMAIN = b"trader-assist-v0/nautilus-pilot/input/v1\0"
_KERNEL_RESULT_HASH_DOMAIN = b"trader-assist-v0/nautilus-pilot/kernel-result/v1\0"
_EVALUATION_HASH_DOMAIN = b"trader-assist-v0/nautilus-pilot/evaluation/v1\0"


def close_boundary_ns(close_time_ms: int) -> int:
    """Map a canonical millisecond close boundary to nanoseconds exactly."""
    if type(close_time_ms) is not int or close_time_ms < 1:
        raise ValueError("close_time_ms must be a positive exact integer")
    return close_time_ms * 1_000_000


def _revalidate_closed_bar(value: object) -> ClosedBar:
    if type(value) is ClosedBar:
        payload = value.model_dump(mode="python", round_trip=True)
    elif isinstance(value, dict):
        payload = value
    else:
        raise ValueError("strategy input must contain an exact ClosedBar")
    return ClosedBar.model_validate(payload)


def _scanner_payload(value: ScannerLinkage | None) -> dict[str, object] | None:
    return None if value is None else asdict(value)


class StrategyInputEvent(BaseModel):
    """Versioned projection around the existing canonical ``ClosedBar``."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    schema_version: Literal["1"] = "1"
    event_kind: Literal["TRADE_OS_STRATEGY_INPUT"] = "TRADE_OS_STRATEGY_INPUT"
    strategy_package_hash: Sha256Hex
    market_id: Sha256Hex
    interval: str
    open_time_ms: int = Field(ge=0)
    close_time_ms: int = Field(ge=1)
    ts_event: int = Field(ge=1)
    ts_init: int = Field(ge=1)
    source_id: str
    provenance_hash: Sha256Hex
    source_canonical_hash: Sha256Hex
    scanner_linkage: ScannerLinkage | None
    closed_bar: ClosedBar
    canonical_hash: Sha256Hex

    @model_validator(mode="before")
    @classmethod
    def revalidate_nested_bar(cls, value: Any) -> Any:
        if isinstance(value, dict) and "closed_bar" in value:
            copied = dict(value)
            copied["closed_bar"] = _revalidate_closed_bar(copied["closed_bar"])
            return copied
        return value

    @staticmethod
    def hash_payload(payload: dict[str, object]) -> str:
        return sha256_hex(_INPUT_HASH_DOMAIN + canonical_json_bytes(payload))

    def identity_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_kind": self.event_kind,
            "strategy_package_hash": self.strategy_package_hash,
            "market_id": self.market_id,
            "interval": self.interval,
            "open_time_ms": self.open_time_ms,
            "close_time_ms": self.close_time_ms,
            "ts_event": self.ts_event,
            "ts_init": self.ts_init,
            "source_id": self.source_id,
            "provenance_hash": self.provenance_hash,
            "source_canonical_hash": self.source_canonical_hash,
            "scanner_linkage": _scanner_payload(self.scanner_linkage),
            "closed_bar": self.closed_bar.model_dump(mode="json"),
        }

    @model_validator(mode="after")
    def validate_projection(self) -> StrategyInputEvent:
        bar = _revalidate_closed_bar(self.closed_bar)
        expected_boundary = close_boundary_ns(bar.close_time_ms)
        if (
            self.market_id != bar.market_id
            or self.interval != bar.interval
            or self.open_time_ms != bar.open_time_ms
            or self.close_time_ms != bar.close_time_ms
            or self.source_id != bar.source_id
            or self.provenance_hash != bar.provenance_hash
            or self.source_canonical_hash != bar.canonical_hash
        ):
            raise ValueError("strategy input identity contradicts canonical ClosedBar")
        if self.ts_event != expected_boundary or self.ts_init != expected_boundary:
            raise ValueError("strategy input timestamps must equal the exact close boundary")
        if self.scanner_linkage is not None:
            if not self.scanner_linkage.candidate_id:
                raise ValueError("scanner linkage candidate identity is empty")
            if self.scanner_linkage.scanner_version != SCANNER_VERSION:
                raise ValueError("scanner linkage version contradicts the current project version")
        expected_hash = self.hash_payload(self.identity_payload())
        if not hmac.compare_digest(self.canonical_hash, expected_hash):
            raise ValueError("strategy input canonical_hash does not bind the projection")
        return self

    @classmethod
    def create(
        cls,
        *,
        strategy_package_hash: str,
        closed_bar: ClosedBar,
        scanner_linkage: ScannerLinkage | None = None,
    ) -> StrategyInputEvent:
        bar = _revalidate_closed_bar(closed_bar)
        boundary = close_boundary_ns(bar.close_time_ms)
        payload: dict[str, object] = {
            "schema_version": E3_CONTRACT_SCHEMA_VERSION,
            "event_kind": E3_INPUT_KIND,
            "strategy_package_hash": strategy_package_hash,
            "market_id": bar.market_id,
            "interval": bar.interval,
            "open_time_ms": bar.open_time_ms,
            "close_time_ms": bar.close_time_ms,
            "ts_event": boundary,
            "ts_init": boundary,
            "source_id": bar.source_id,
            "provenance_hash": bar.provenance_hash,
            "source_canonical_hash": bar.canonical_hash,
            "scanner_linkage": scanner_linkage,
            "closed_bar": bar,
        }
        identity_payload = {
            **payload,
            "scanner_linkage": _scanner_payload(scanner_linkage),
            "closed_bar": bar.model_dump(mode="json"),
        }
        return cls.model_validate(
            {**payload, "canonical_hash": cls.hash_payload(identity_payload)}
        )


def revalidate_strategy_input_event(value: object) -> StrategyInputEvent:
    """Rebuild an exact input event so mutated nested instances fail closed."""
    if type(value) is not StrategyInputEvent:
        raise ValueError("expected exact StrategyInputEvent project contract")
    return StrategyInputEvent.model_validate(value.model_dump(mode="python", round_trip=True))


def kernel_result_identity(result: KernelResult) -> str:
    if type(result) is not KernelResult:
        raise ValueError("expected exact project KernelResult")
    return sha256_hex(_KERNEL_RESULT_HASH_DOMAIN + canonical_json_bytes(asdict(result)))


class PilotEvaluationEnvelope(BaseModel):
    """Mechanically non-authoritative, rebuildable result of the unchanged kernel."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    schema_version: Literal["1"] = "1"
    authority_marker: Literal["NONAUTHORITATIVE_E3_PILOT"] = "NONAUTHORITATIVE_E3_PILOT"
    rebuildable: Literal[True] = True
    strategy_package_hash: Sha256Hex
    input_event_hash: Sha256Hex
    source_canonical_hash: Sha256Hex
    kernel_result_hash: Sha256Hex
    kernel_result: KernelResult
    evaluation_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "authority_marker": self.authority_marker,
            "rebuildable": self.rebuildable,
            "strategy_package_hash": self.strategy_package_hash,
            "input_event_hash": self.input_event_hash,
            "source_canonical_hash": self.source_canonical_hash,
            "kernel_result_hash": self.kernel_result_hash,
        }

    @model_validator(mode="after")
    def validate_envelope(self) -> PilotEvaluationEnvelope:
        expected_result = kernel_result_identity(self.kernel_result)
        if not hmac.compare_digest(self.kernel_result_hash, expected_result):
            raise ValueError("kernel_result_hash does not bind the project KernelResult")
        expected_evaluation = sha256_hex(
            _EVALUATION_HASH_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.evaluation_hash, expected_evaluation):
            raise ValueError("evaluation_hash does not bind the pilot envelope")
        return self

    @classmethod
    def create(
        cls,
        *,
        strategy_package_hash: str,
        input_event: StrategyInputEvent,
        kernel_result: KernelResult,
    ) -> PilotEvaluationEnvelope:
        event = revalidate_strategy_input_event(input_event)
        result_hash = kernel_result_identity(kernel_result)
        payload: dict[str, object] = {
            "schema_version": E3_CONTRACT_SCHEMA_VERSION,
            "authority_marker": E3_AUTHORITY_MARKER,
            "rebuildable": True,
            "strategy_package_hash": strategy_package_hash,
            "input_event_hash": event.canonical_hash,
            "source_canonical_hash": event.source_canonical_hash,
            "kernel_result_hash": result_hash,
            "kernel_result": kernel_result,
        }
        identity_payload = {key: value for key, value in payload.items() if key != "kernel_result"}
        evaluation_hash = sha256_hex(
            _EVALUATION_HASH_DOMAIN + canonical_json_bytes(identity_payload)
        )
        return cls.model_validate({**payload, "evaluation_hash": evaluation_hash})
