"""Narrow operator configuration and read-model contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.multi_asset_shadow.l1_approval import StrategyOrderPackage

RUNTIME_EVIDENCE_PATH = Path("/var/lib/trader-assist-v0/three-setup-shadow/evidence.sqlite")
OPERATOR_LEDGER_PATH = Path("/var/lib/trader-assist-v0/three-setup-operator/operator.sqlite")


@dataclass(frozen=True)
class DashboardEvent:
    event_key: str
    package_id: str
    state: str
    server_ms: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DashboardModel:
    overall: Literal["READY", "BLOCKED", "DEGRADED", "UNKNOWN"]
    reasons: tuple[str, ...]
    package_gate: Literal["PASS", "BLOCKED"]
    package: StrategyOrderPackage | None
    details: dict[str, object]
    state: str
    observed_ms: int
    events: tuple[DashboardEvent, ...]
    events_available: bool
    module_id: str
    module_renderer: str


class OperatorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_evidence_path: Path = RUNTIME_EVIDENCE_PATH
    operator_ledger_path: Path = OPERATOR_LEDGER_PATH
    credential_path: Path
    allowed_hosts: tuple[str, ...]
    allowed_origin: str
    bind_host: str = "127.0.0.1"
    bind_port: int = Field(default=8768, ge=1, le=65535)
    tls_cert_path: Path | None = None
    tls_key_path: Path | None = None
    reference_scenario: Literal["1pct", "2pct"] | None = None
    approval_mode: Literal["POST_ACTIVATION", "PREAUTHORIZED_ARMED"] = "POST_ACTIVATION"
    approval_ttl_ms: int = Field(default=300_000, ge=1, le=3_600_000)
    reconcile_interval_ms: int = Field(default=500, ge=100, le=5000)

    @model_validator(mode="after")
    def validate_isolation(self) -> OperatorConfig:
        if self.runtime_evidence_path.resolve() == self.operator_ledger_path.resolve():
            raise ValueError("runtime and operator databases must be distinct")
        if self.bind_host not in {"127.0.0.1", "::1"}:
            raise ValueError("operator must bind loopback")
        if not self.allowed_hosts or any(not host or "*" in host for host in self.allowed_hosts):
            raise ValueError("exact allowed hosts are required")
        if not self.allowed_origin.startswith("https://") or self.allowed_origin.endswith("/"):
            raise ValueError("exact HTTPS origin is required")
        if (self.tls_cert_path is None) != (self.tls_key_path is None):
            raise ValueError("direct TLS certificate and key must be configured together")
        return self

    @classmethod
    def load(cls, path: Path) -> OperatorConfig:
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))


class OperatorCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token: str = Field(min_length=43)
    session_signing_secret: str = Field(min_length=43)

    @model_validator(mode="after")
    def separate_secrets(self) -> OperatorCredential:
        if self.access_token == self.session_signing_secret:
            raise ValueError("operator secrets must be separate")
        if "REPLACE_WITH" in self.access_token or "REPLACE_WITH" in self.session_signing_secret:
            raise ValueError("example credential cannot be used")
        return self

    @classmethod
    def load(cls, path: Path) -> OperatorCredential:
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))
