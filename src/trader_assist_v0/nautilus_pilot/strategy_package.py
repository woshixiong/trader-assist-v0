"""Versioned Trade OS Strategy package; this module has no Nautilus imports."""

from __future__ import annotations

import hmac
from dataclasses import asdict
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from trader_assist_v0.contracts.common import (
    GitCommitOid,
    Sha256Hex,
    canonical_json_bytes,
    sha256_hex,
)
from trader_assist_v0.multi_asset_shadow.strategy_continuation import IncrementalStrategyState
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    PARAMETER_VERSION,
    SCANNER_VERSION,
    SCHEMA_VERSION,
    STRATEGY_VERSION,
    Bar,
    evaluate_strategy,
)

from .contracts import PilotEvaluationEnvelope, StrategyInputEvent, revalidate_strategy_input_event

STRATEGY_PACKAGE_VERSION = "THREE_SETUP_CHAMPION_E3_V1"
_MANIFEST_HASH_DOMAIN = b"trader-assist-v0/nautilus-pilot/strategy-package/v1\0"


class StrategyPackageManifest(BaseModel):
    """Immutable identity of the frozen current Three Setup Champion package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    package_version: Literal["THREE_SETUP_CHAMPION_E3_V1"] = "THREE_SETUP_CHAMPION_E3_V1"
    strategy_version: str = STRATEGY_VERSION
    parameter_version: str = PARAMETER_VERSION
    scanner_version: str = SCANNER_VERSION
    kernel_schema_version: str = SCHEMA_VERSION
    trade_os_release_sha: GitCommitOid
    manifest_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"manifest_hash"})

    @model_validator(mode="after")
    def validate_manifest(self) -> StrategyPackageManifest:
        if (
            self.package_version != STRATEGY_PACKAGE_VERSION
            or self.strategy_version != STRATEGY_VERSION
            or self.parameter_version != PARAMETER_VERSION
            or self.scanner_version != SCANNER_VERSION
            or self.kernel_schema_version != SCHEMA_VERSION
        ):
            raise ValueError("Strategy package versions do not match the current project kernel")
        expected = sha256_hex(
            _MANIFEST_HASH_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.manifest_hash, expected):
            raise ValueError("manifest_hash does not bind the Strategy package")
        return self

    @classmethod
    def create(cls, *, trade_os_release_sha: str) -> StrategyPackageManifest:
        payload: dict[str, object] = {
            "package_version": STRATEGY_PACKAGE_VERSION,
            "strategy_version": STRATEGY_VERSION,
            "parameter_version": PARAMETER_VERSION,
            "scanner_version": SCANNER_VERSION,
            "kernel_schema_version": SCHEMA_VERSION,
            "trade_os_release_sha": trade_os_release_sha,
        }
        manifest_hash = sha256_hex(_MANIFEST_HASH_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "manifest_hash": manifest_hash})


def select_strategy_package(
    *,
    package_version: str,
    strategy_version: str,
    parameter_version: str,
    scanner_version: str,
    kernel_schema_version: str,
    trade_os_release_sha: str,
    manifest_hash: str,
) -> StrategyPackageManifest:
    """Select only the exact current package identity; every mismatch fails closed."""
    expected = StrategyPackageManifest.create(trade_os_release_sha=trade_os_release_sha)
    supplied = (
        package_version,
        strategy_version,
        parameter_version,
        scanner_version,
        kernel_schema_version,
        manifest_hash,
    )
    current = (
        expected.package_version,
        expected.strategy_version,
        expected.parameter_version,
        expected.scanner_version,
        expected.kernel_schema_version,
        expected.manifest_hash,
    )
    if supplied != current:
        raise ValueError("requested Strategy package identity is not the exact current package")
    return expected


class PilotStrategyEvaluator:
    """One-market ephemeral evaluator over the accepted continuation and kernel."""

    def __init__(
        self,
        *,
        manifest: StrategyPackageManifest,
        market_id: str,
        minimum_tick: Decimal,
    ) -> None:
        selected = select_strategy_package(
            package_version=manifest.package_version,
            strategy_version=manifest.strategy_version,
            parameter_version=manifest.parameter_version,
            scanner_version=manifest.scanner_version,
            kernel_schema_version=manifest.kernel_schema_version,
            trade_os_release_sha=manifest.trade_os_release_sha,
            manifest_hash=manifest.manifest_hash,
        )
        if not market_id or len(market_id) != 64:
            raise ValueError("pilot evaluator market_id is invalid")
        if not minimum_tick.is_finite() or minimum_tick <= 0:
            raise ValueError("pilot evaluator minimum_tick must be positive and finite")
        self._manifest = selected
        self._market_id = market_id
        self._minimum_tick = minimum_tick
        self._state = IncrementalStrategyState(market_id=market_id)

    @property
    def manifest(self) -> StrategyPackageManifest:
        return self._manifest

    @property
    def source_history_commitment(self) -> str:
        return self._state.source_history_commitment

    def evaluate(self, event: StrategyInputEvent) -> PilotEvaluationEnvelope | None:
        validated = revalidate_strategy_input_event(event)
        if validated.strategy_package_hash != self._manifest.manifest_hash:
            raise ValueError("strategy input package identity contradicts selected package")
        if validated.market_id != self._market_id or validated.interval != "5m":
            raise ValueError("strategy input market or interval contradicts evaluator config")
        closed = validated.closed_bar
        project_bar = Bar(
            market_id=closed.market_id,
            interval=closed.interval,
            open_time_ms=closed.open_time_ms,
            close_time_ms=closed.close_time_ms,
            open=closed.open,
            high=closed.high,
            low=closed.low,
            close=closed.close,
            volume=closed.volume,
            source_identity=closed.canonical_hash,
        )
        working = self._state.clone()
        working.ingest(project_bar)
        try:
            inputs = working.evaluation_input(
                minimum_tick=self._minimum_tick,
                scanner_linkage=validated.scanner_linkage,
            )
        except ValueError as exc:
            if str(exc) != "Strategy continuation context is insufficient":
                raise
            self._state = working
            return None
        result = evaluate_strategy(inputs, working.ledger)
        working.retain_result(result.ledger, asdict(result))
        self._state = working
        return PilotEvaluationEnvelope.create(
            strategy_package_hash=self._manifest.manifest_hash,
            input_event=validated,
            kernel_result=result,
        )
