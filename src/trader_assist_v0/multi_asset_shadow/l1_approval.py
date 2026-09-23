"""L1 package identity and zero-write Human approval evidence.

This module is deliberately independent of market-data and execution adapters.
It persists only project-owned evidence in the existing SQLite evidence surface;
an accepted activation always produces ``NOT_SUBMITTED`` workflow evidence.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex


class L1ContractError(ValueError):
    """The package, displayed identity, or approval transition is invalid."""


class AuthorityMode(StrEnum):
    ZERO_WRITE = "ZERO_WRITE"
    LIVE_WRITE = "LIVE_WRITE"  # Contract boundary only; never activated here.


class ApprovalMode(StrEnum):
    POST_ACTIVATION = "POST_ACTIVATION"
    PREAUTHORIZED_ARMED = "PREAUTHORIZED_ARMED"


class ApprovalState(StrEnum):
    DRAFT = "DRAFT"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    PREAUTHORIZED_ARMED = "PREAUTHORIZED_ARMED"
    ACTIVATED = "ACTIVATED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    AMBIGUOUS_RESTART = "AMBIGUOUS_RESTART"


class EvidenceStream(StrEnum):
    STRATEGY_BASELINE_SHADOW = "STRATEGY_BASELINE_SHADOW"
    HUMAN_WORKFLOW_SHADOW = "HUMAN_WORKFLOW_SHADOW"
    FUTURE_LIVE_EXECUTION = "FUTURE_LIVE_EXECUTION"


NOT_SUBMITTED = "NOT_SUBMITTED"
_PACKAGE_VERSION = "L1-1"


def _canonical_decimal(value: Decimal) -> str:
    if not value.is_finite() or value <= 0:
        raise L1ContractError("sizing values must be positive finite decimals")
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class PackageLeg:
    market_id: str
    side: str
    quantity: Decimal
    fixed_margin_usd: Decimal
    fixed_leverage: Decimal

    def canonical(self) -> dict[str, str]:
        if not self.market_id or self.side not in {"LONG", "SHORT"}:
            raise L1ContractError("package leg identity is invalid")
        return {
            "market_id": self.market_id,
            "side": self.side,
            "quantity": _canonical_decimal(self.quantity),
            "fixed_margin_usd": _canonical_decimal(self.fixed_margin_usd),
            "fixed_leverage": _canonical_decimal(self.fixed_leverage),
        }


@dataclass(frozen=True)
class StrategyOrderPackage:
    """Immutable, displayed identity for one versioned multi-asset package."""

    parent_strategy_order_id: str
    strategy_version: str
    parameter_version: str
    created_server_ms: int
    expires_server_ms: int
    authority_mode: AuthorityMode
    activation_opportunity_id: str
    legs: tuple[PackageLeg, ...]
    package_id: str
    package_hash: str

    @classmethod
    def create(
        cls,
        *,
        parent_strategy_order_id: str,
        strategy_version: str,
        parameter_version: str,
        created_server_ms: int,
        expires_server_ms: int,
        activation_opportunity_id: str,
        authority_mode: AuthorityMode = AuthorityMode.ZERO_WRITE,
        legs: tuple[PackageLeg, ...],
    ) -> StrategyOrderPackage:
        if (
            not parent_strategy_order_id
            or not strategy_version
            or not parameter_version
            or not activation_opportunity_id
        ):
            raise L1ContractError("package parent and version identity are required")
        if created_server_ms < 0 or expires_server_ms <= created_server_ms:
            raise L1ContractError("package expiry must follow its server creation time")
        if not legs or len({leg.market_id for leg in legs}) != len(legs):
            raise L1ContractError("package must contain unique market legs")
        payload = {
            "package_version": _PACKAGE_VERSION,
            "parent_strategy_order_id": parent_strategy_order_id,
            "strategy_version": strategy_version,
            "parameter_version": parameter_version,
            "created_server_ms": created_server_ms,
            "expires_server_ms": expires_server_ms,
            "authority_mode": authority_mode.value,
            "activation_opportunity_id": activation_opportunity_id,
            "legs": [leg.canonical() for leg in legs],
        }
        package_hash = sha256_hex(
            b"trader-assist-v0/l1-package/v1\0" + canonical_json_bytes(payload)
        )
        package_id = sha256_hex(
            b"trader-assist-v0/l1-package-id/v1\0"
            + canonical_json_bytes({"parent": parent_strategy_order_id, "hash": package_hash})
        )
        return cls(
            parent_strategy_order_id=parent_strategy_order_id,
            strategy_version=strategy_version,
            parameter_version=parameter_version,
            created_server_ms=created_server_ms,
            expires_server_ms=expires_server_ms,
            authority_mode=authority_mode,
            activation_opportunity_id=activation_opportunity_id,
            legs=legs,
            package_id=package_id,
            package_hash=package_hash,
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "package_version": _PACKAGE_VERSION,
            "parent_strategy_order_id": self.parent_strategy_order_id,
            "strategy_version": self.strategy_version,
            "parameter_version": self.parameter_version,
            "created_server_ms": self.created_server_ms,
            "expires_server_ms": self.expires_server_ms,
            "authority_mode": self.authority_mode.value,
            "activation_opportunity_id": self.activation_opportunity_id,
            "legs": [leg.canonical() for leg in self.legs],
        }


@dataclass(frozen=True)
class WorkflowEvidence:
    parent_strategy_order_id: str
    package_id: str
    package_hash: str
    stream: EvidenceStream
    recorded_server_ms: int
    submission_status: str = NOT_SUBMITTED


class HumanApprovalLedger:
    """Append-only approval FSM over an existing SQLite connection.

    The caller supplies server-owned causal time.  Idempotency is keyed by a
    human/action request identity; a reused key with different content fails
    closed.  Incomplete activation journals are intentionally unrecoverable.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS l1_packages (
                    package_id TEXT PRIMARY KEY NOT NULL,
                    package_hash TEXT NOT NULL UNIQUE,
                    parent_strategy_order_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                ) STRICT;
                CREATE TABLE IF NOT EXISTS l1_approval_events (
                    action_key TEXT PRIMARY KEY NOT NULL,
                    package_id TEXT NOT NULL REFERENCES l1_packages(package_id),
                    package_hash TEXT NOT NULL,
                    event_kind TEXT NOT NULL,
                    approval_mode TEXT,
                    server_ms INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                ) STRICT;
                CREATE TABLE IF NOT EXISTS l1_workflow_evidence (
                    event_key TEXT PRIMARY KEY NOT NULL,
                    package_id TEXT NOT NULL REFERENCES l1_packages(package_id),
                    package_hash TEXT NOT NULL,
                    stream TEXT NOT NULL,
                    recorded_server_ms INTEGER NOT NULL,
                    submission_status TEXT NOT NULL CHECK (submission_status = 'NOT_SUBMITTED')
                ) STRICT;
                """
            )

    def display(self, package: StrategyOrderPackage) -> StrategyOrderPackage:
        payload = self._validated_payload(package)
        with self._connection:
            row = self._connection.execute(
                "SELECT package_hash, parent_strategy_order_id, payload_json "
                "FROM l1_packages WHERE package_id = ?",
                (package.package_id,),
            ).fetchone()
            if row is not None:
                if (
                    row["package_hash"] != package.package_hash
                    or row["parent_strategy_order_id"] != package.parent_strategy_order_id
                    or row["payload_json"] != payload
                ):
                    raise L1ContractError(
                        "package identity conflicts with retained displayed package"
                    )
                return package
            self._connection.execute(
                "INSERT INTO l1_packages VALUES (?, ?, ?, ?)",
                (
                    package.package_id,
                    package.package_hash,
                    package.parent_strategy_order_id,
                    payload,
                ),
            )
            self._event(
                "display:" + package.package_id,
                package,
                "DISPLAYED",
                None,
                package.created_server_ms,
            )
        return package

    def record_baseline(self, package: StrategyOrderPackage, *, server_ms: int) -> WorkflowEvidence:
        self._require_displayed(package)
        return self._evidence(
            "baseline:" + package.package_id,
            package,
            EvidenceStream.STRATEGY_BASELINE_SHADOW,
            server_ms,
        )

    def record_future_live_boundary(
        self, package: StrategyOrderPackage, *, server_ms: int
    ) -> WorkflowEvidence:
        """Reserve the distinct future child identity without submission authority."""
        self._require_displayed(package)
        return self._evidence(
            "future-live:" + package.package_id,
            package,
            EvidenceStream.FUTURE_LIVE_EXECUTION,
            server_ms,
        )

    def arm(
        self, package: StrategyOrderPackage, *, action_key: str, server_ms: int
    ) -> ApprovalState:
        self._require_displayed(package)
        self._require_fresh(package, server_ms)
        return self._event(
            action_key,
            package,
            "ARMED",
            ApprovalMode.PREAUTHORIZED_ARMED,
            server_ms,
            {"activation_opportunity_id": package.activation_opportunity_id},
        )

    def activate(
        self,
        package: StrategyOrderPackage,
        *,
        action_key: str,
        server_ms: int,
        activation_opportunity_id: str | None,
    ) -> ApprovalState:
        self._require_displayed(package)
        self._require_fresh(package, server_ms)
        retained = self._retained_event_state(
            action_key,
            package,
            "ACTIVATED",
            ApprovalMode.PREAUTHORIZED_ARMED,
            server_ms,
            {"activation_opportunity_id": activation_opportunity_id}
            if activation_opportunity_id is not None
            else None,
        )
        if retained is not None:
            return retained
        prior = self.state(package, server_ms=server_ms)
        if prior is ApprovalState.PREAUTHORIZED_ARMED:
            if activation_opportunity_id != package.activation_opportunity_id:
                raise L1ContractError("preauthorization requires its exact activation opportunity")
            with self._connection:
                self._event(
                    action_key,
                    package,
                    "ACTIVATED",
                    ApprovalMode.PREAUTHORIZED_ARMED,
                    server_ms,
                    {"activation_opportunity_id": activation_opportunity_id},
                )
                self._evidence(
                    "workflow:" + action_key,
                    package,
                    EvidenceStream.HUMAN_WORKFLOW_SHADOW,
                    server_ms,
                )
            return ApprovalState.ACTIVATED
        if prior in {ApprovalState.DRAFT, ApprovalState.AWAITING_HUMAN_APPROVAL}:
            self._event(
                action_key,
                package,
                "ACTIVATION_OPEN",
                ApprovalMode.POST_ACTIVATION,
                server_ms,
                {"activation_opportunity_id": activation_opportunity_id}
                if activation_opportunity_id is not None
                else None,
            )
            return ApprovalState.AWAITING_HUMAN_APPROVAL
        raise L1ContractError("activation authority is already consumed")

    def approve_post_activation(
        self, package: StrategyOrderPackage, *, action_key: str, server_ms: int
    ) -> ApprovalState:
        self._require_displayed(package)
        self._require_fresh(package, server_ms)
        retained = self._retained_event_state(
            action_key,
            package,
            "ACTIVATED",
            ApprovalMode.POST_ACTIVATION,
            server_ms,
            None,
        )
        if retained is not None:
            return retained
        if self.state(package, server_ms=server_ms) is not ApprovalState.AWAITING_HUMAN_APPROVAL:
            raise L1ContractError("post-activation approval requires an open activation")
        with self._connection:
            self._event(action_key, package, "ACTIVATED", ApprovalMode.POST_ACTIVATION, server_ms)
            self._evidence(
                "workflow:" + action_key, package, EvidenceStream.HUMAN_WORKFLOW_SHADOW, server_ms
            )
        return ApprovalState.ACTIVATED

    def supersede(
        self, old: StrategyOrderPackage, new: StrategyOrderPackage, *, server_ms: int
    ) -> None:
        self._require_displayed(old)
        self.display(new)
        self._event(
            "supersede:" + old.package_id + ":" + new.package_id,
            old,
            "SUPERSEDED",
            None,
            server_ms,
            {"replacement": new.package_id},
        )

    def state(self, package: StrategyOrderPackage, *, server_ms: int) -> ApprovalState:
        self._require_displayed(package)
        rows = self._connection.execute(
            "SELECT event_kind FROM l1_approval_events WHERE package_id = ? "
            "ORDER BY server_ms, action_key",
            (package.package_id,),
        ).fetchall()
        kinds = [str(row["event_kind"]) for row in rows]
        if "ACTIVATION_STARTED" in kinds:
            return ApprovalState.AMBIGUOUS_RESTART
        if "SUPERSEDED" in kinds:
            return ApprovalState.SUPERSEDED
        if server_ms >= package.expires_server_ms and "ACTIVATED" not in kinds:
            return ApprovalState.EXPIRED
        if "ACTIVATED" in kinds:
            return ApprovalState.ACTIVATED
        if "ARMED" in kinds:
            return ApprovalState.PREAUTHORIZED_ARMED
        if "ACTIVATION_OPEN" in kinds:
            return ApprovalState.AWAITING_HUMAN_APPROVAL
        return ApprovalState.DRAFT

    def _require_displayed(self, package: StrategyOrderPackage) -> None:
        payload = self._validated_payload(package)
        row = self._connection.execute(
            "SELECT package_hash, parent_strategy_order_id, payload_json "
            "FROM l1_packages WHERE package_id = ?",
            (package.package_id,),
        ).fetchone()
        if (
            row is None
            or row["package_hash"] != package.package_hash
            or row["parent_strategy_order_id"] != package.parent_strategy_order_id
            or row["payload_json"] != payload
        ):
            raise L1ContractError("exact displayed package/hash binding is required")

    @staticmethod
    def _validated_payload(package: StrategyOrderPackage) -> str:
        """Recompute both identities; never trust caller-supplied id/hash fields."""
        try:
            payload = package.canonical_payload()
            canonical_payload = canonical_json_bytes(payload)
            expected_hash = sha256_hex(b"trader-assist-v0/l1-package/v1\0" + canonical_payload)
            expected_id = sha256_hex(
                b"trader-assist-v0/l1-package-id/v1\0"
                + canonical_json_bytes(
                    {"parent": package.parent_strategy_order_id, "hash": expected_hash}
                )
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise L1ContractError("package canonical payload is invalid") from exc
        if package.package_hash != expected_hash or package.package_id != expected_id:
            raise L1ContractError("package id/hash does not bind canonical payload")
        return canonical_payload.decode("utf-8")

    @staticmethod
    def _require_fresh(package: StrategyOrderPackage, server_ms: int) -> None:
        if server_ms < package.created_server_ms or server_ms >= package.expires_server_ms:
            raise L1ContractError("expired or causally invalid package cannot activate")

    def _event(
        self,
        action_key: str,
        package: StrategyOrderPackage,
        kind: str,
        mode: ApprovalMode | None,
        server_ms: int,
        extra: dict[str, str | None] | None = None,
    ) -> ApprovalState:
        payload = json.dumps(extra or {}, sort_keys=True, separators=(",", ":"))
        row = self._connection.execute(
            "SELECT package_id, package_hash, event_kind, approval_mode, server_ms, "
            "payload_json FROM l1_approval_events WHERE action_key = ?",
            (action_key,),
        ).fetchone()
        expected = (
            package.package_id,
            package.package_hash,
            kind,
            None if mode is None else mode.value,
            server_ms,
            payload,
        )
        if row is not None:
            if tuple(row) != expected:
                raise L1ContractError(
                    "duplicate human action conflicts with retained idempotency key"
                )
            return self.state(package, server_ms=server_ms)
        self._connection.execute(
            "INSERT INTO l1_approval_events VALUES (?, ?, ?, ?, ?, ?, ?)", (action_key, *expected)
        )
        return self.state(package, server_ms=server_ms)

    def _retained_event_state(
        self,
        action_key: str,
        package: StrategyOrderPackage,
        kind: str,
        mode: ApprovalMode,
        server_ms: int,
        extra: dict[str, str | None] | None,
    ) -> ApprovalState | None:
        payload = json.dumps(extra or {}, sort_keys=True, separators=(",", ":"))
        row = self._connection.execute(
            "SELECT package_id, package_hash, event_kind, approval_mode, server_ms, "
            "payload_json FROM l1_approval_events WHERE action_key = ?",
            (action_key,),
        ).fetchone()
        if row is None:
            return None
        expected = (package.package_id, package.package_hash, kind, mode.value, server_ms, payload)
        if tuple(row) != expected:
            raise L1ContractError("duplicate human action conflicts with retained idempotency key")
        return self.state(package, server_ms=server_ms)

    def _evidence(
        self, event_key: str, package: StrategyOrderPackage, stream: EvidenceStream, server_ms: int
    ) -> WorkflowEvidence:
        row = self._connection.execute(
            "SELECT package_id, package_hash, stream, recorded_server_ms "
            "FROM l1_workflow_evidence WHERE event_key = ?",
            (event_key,),
        ).fetchone()
        expected = (package.package_id, package.package_hash, stream.value, server_ms)
        if row is not None:
            if tuple(row) != expected:
                raise L1ContractError("workflow evidence idempotency key conflicts")
        else:
            self._connection.execute(
                "INSERT INTO l1_workflow_evidence VALUES (?, ?, ?, ?, ?, ?)",
                (event_key, *expected, NOT_SUBMITTED),
            )
        return WorkflowEvidence(
            package.parent_strategy_order_id,
            package.package_id,
            package.package_hash,
            stream,
            server_ms,
        )
