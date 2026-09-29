"""L1 package identity and zero-write Human approval evidence.

This module is deliberately independent of market-data and execution adapters.
It persists only project-owned evidence in the existing SQLite evidence surface;
an accepted activation always produces ``NOT_SUBMITTED`` workflow evidence.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

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


def _ts8_thesis_valid_no_submit(reasons: tuple[str, ...]) -> bool:
    return not any(
        reason in {"PACKAGE_EXPIRED", "THESIS_INVALID", "ACTIVATION_INVALID", "SUPERSEDED"}
        for reason in reasons
    )


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
    ts8_details: dict[str, object] | None = None

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
        ts8_details: dict[str, object] | None = None,
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
        if (not legs and ts8_details is None) or len({leg.market_id for leg in legs}) != len(legs):
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
        if ts8_details is not None:
            if authority_mode is not AuthorityMode.ZERO_WRITE:
                raise L1ContractError("TS8 package is zero-write only")
            payload["ts8_details"] = ts8_details
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
            ts8_details=ts8_details,
        )

    def canonical_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
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
        if self.ts8_details is not None:
            payload["ts8_details"] = self.ts8_details
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> StrategyOrderPackage:
        legs = tuple(
            PackageLeg(
                market_id=str(item["market_id"]),
                side=str(item["side"]),
                quantity=Decimal(str(item["quantity"])),
                fixed_margin_usd=Decimal(str(item["fixed_margin_usd"])),
                fixed_leverage=Decimal(str(item["fixed_leverage"])),
            )
            for item in payload["legs"]
        )
        return cls.create(
            parent_strategy_order_id=str(payload["parent_strategy_order_id"]),
            strategy_version=str(payload["strategy_version"]),
            parameter_version=str(payload["parameter_version"]),
            created_server_ms=int(payload["created_server_ms"]),
            expires_server_ms=int(payload["expires_server_ms"]),
            activation_opportunity_id=str(payload["activation_opportunity_id"]),
            authority_mode=AuthorityMode(str(payload["authority_mode"])),
            legs=legs,
            ts8_details=payload.get("ts8_details"),
        )


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
        if self._connection.in_transaction:
            raise L1ContractError("caller-owned SQLite transaction is not supported")
        # SQLite's connection-wide ``in_transaction`` cannot identify a nested
        # ledger mutation: it is also true for a transaction owned by our
        # caller.  Keep that ownership boundary locally instead.
        self._mutation_depth = 0
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
                CREATE TABLE IF NOT EXISTS ts8_state (
                    package_id TEXT PRIMARY KEY NOT NULL REFERENCES l1_packages(package_id),
                    state TEXT NOT NULL,
                    approval_mode TEXT NOT NULL,
                    activation_id TEXT,
                    updated_server_ms INTEGER NOT NULL,
                    submission_status TEXT NOT NULL CHECK (submission_status = 'NOT_SUBMITTED')
                ) STRICT;
                CREATE TABLE IF NOT EXISTS ts8_actions (
                    action_key TEXT PRIMARY KEY NOT NULL,
                    package_id TEXT NOT NULL REFERENCES l1_packages(package_id),
                    request_digest TEXT NOT NULL,
                    action TEXT NOT NULL,
                    observed_server_ms INTEGER NOT NULL,
                    snapshot_digest TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    result_state TEXT NOT NULL,
                    evidence_role TEXT NOT NULL CHECK (evidence_role = 'OBSERVED')
                ) STRICT;
                CREATE TABLE IF NOT EXISTS ts8_transitions (
                    event_key TEXT PRIMARY KEY NOT NULL,
                    package_id TEXT NOT NULL REFERENCES l1_packages(package_id),
                    state TEXT NOT NULL,
                    server_ms INTEGER NOT NULL,
                    activation_id TEXT,
                    snapshot_digest TEXT NOT NULL,
                    source_refs_json TEXT NOT NULL,
                    reason_codes_json TEXT NOT NULL,
                    submission_status TEXT NOT NULL CHECK (submission_status = 'NOT_SUBMITTED')
                ) STRICT;
                CREATE INDEX IF NOT EXISTS ts8_pending ON ts8_state(state, package_id);
                """
            )

    def ts8_package(self, package_id: str) -> StrategyOrderPackage | None:
        row = self._connection.execute(
            "SELECT package_hash, payload_json FROM l1_packages WHERE package_id = ?",
            (package_id,),
        ).fetchone()
        if row is None:
            return None
        package = StrategyOrderPackage.from_payload(json.loads(str(row["payload_json"])))
        if package.package_id != package_id or package.package_hash != row["package_hash"]:
            raise L1ContractError("stored package identity is invalid")
        return package

    def ts8_state(self, package_id: str) -> str | None:
        row = self._connection.execute(
            "SELECT state FROM ts8_state WHERE package_id = ?", (package_id,)
        ).fetchone()
        return None if row is None else str(row["state"])

    def ts8_action_replay(
        self, *, action_key: str, package_id: str, request_digest: str, action: str,
        shadow_id: str | None = None,
    ) -> tuple[str, int] | None:
        """Return exact committed result/time without consulting Strategy evidence."""
        row = self._connection.execute(
            "SELECT package_id, request_digest, action, result_state, observed_server_ms "
            "FROM ts8_actions WHERE action_key = ?",
            (action_key,),
        ).fetchone()
        if row is None:
            return None
        if (row["package_id"], row["request_digest"], row["action"]) != (
            package_id, request_digest, action
        ):
            raise L1ContractError("action key reused with altered payload")
        if shadow_id is not None:
            package = self.ts8_package(package_id)
            if package is None or package.parent_strategy_order_id != shadow_id:
                raise L1ContractError("action key reused with altered payload")
        return str(row["result_state"]), int(row["observed_server_ms"])

    def ts8_revision(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM ts8_transitions").fetchone()
        return int(row[0])

    def ts8_recent_terminal(self) -> tuple[str, str] | None:
        row = self._connection.execute(
            "SELECT state, package_id FROM ts8_state WHERE state IN "
            "('EXPIRED', 'SUPERSEDED', 'THESIS_INVALID', 'WAITING_FRESH_TRIGGER', "
            "'REJECTED', 'WOULD_SUBMIT') "
            "ORDER BY updated_server_ms DESC, package_id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return str(row["state"]), str(row["package_id"])

    def ts8_approval_time(self, package_id: str) -> int:
        rows = self._connection.execute(
            "SELECT observed_server_ms FROM ts8_actions WHERE package_id = ? "
            "AND action = 'APPROVE' ORDER BY observed_server_ms LIMIT 2",
            (package_id,),
        ).fetchall()
        if len(rows) != 1:
            raise L1ContractError("pending package lacks one observed approval")
        return int(rows[0][0])

    def ts8_pending(self, *, limit: int = 32) -> tuple[StrategyOrderPackage, ...]:
        if not 1 <= limit <= 128:
            raise L1ContractError("pending batch limit is invalid")
        rows = self._connection.execute(
            "SELECT package_id FROM ts8_state WHERE state = 'APPROVED_WAITING_ACTIVATION' "
            "ORDER BY package_id LIMIT ?",
            (limit,),
        ).fetchall()
        result = tuple(self.ts8_package(str(row["package_id"])) for row in rows)
        if any(package is None for package in result):
            raise L1ContractError("pending package is missing")
        return tuple(package for package in result if package is not None)

    def ts8_open_post(self, *, limit: int = 32) -> tuple[StrategyOrderPackage, ...]:
        if not 1 <= limit <= 128:
            raise L1ContractError("open POST batch limit is invalid")
        rows = self._connection.execute(
            "SELECT package_id FROM ts8_state WHERE approval_mode = 'POST_ACTIVATION' "
            "AND state = 'AWAITING_HUMAN_APPROVAL' ORDER BY package_id LIMIT ?",
            (limit,),
        ).fetchall()
        packages = tuple(self.ts8_package(str(row["package_id"])) for row in rows)
        if any(package is None for package in packages):
            raise L1ContractError("open POST package is missing")
        return tuple(package for package in packages if package is not None)

    def ts8_terminalize_post(
        self,
        package: StrategyOrderPackage,
        *,
        terminal: str,
        server_ms: int,
        snapshot_digest: str,
        source_refs: dict[str, str],
        reason_code: str,
    ) -> str:
        if terminal not in {"EXPIRED", "SUPERSEDED", "THESIS_INVALID"} or not reason_code:
            raise L1ContractError("invalid POST terminal disposition")
        with self._mutation():
            self.ts8_display(package, mode=ApprovalMode.POST_ACTIVATION)
            state = self.ts8_state(package.package_id)
            if state != "AWAITING_HUMAN_APPROVAL":
                if state is None:
                    raise L1ContractError("POST package state is missing")
                return state
            self._ts8_transition(
                "post-terminal:" + package.package_id,
                package,
                terminal,
                server_ms,
                None,
                snapshot_digest,
                canonical_json_bytes(source_refs).decode("utf-8"),
                (reason_code,),
            )
            self._connection.execute(
                "UPDATE ts8_state SET state = ?, updated_server_ms = ? WHERE package_id = ?",
                (terminal, server_ms, package.package_id),
            )
            return terminal

    def ts8_display(self, package: StrategyOrderPackage, *, mode: ApprovalMode) -> str:
        if package.ts8_details is None or package.ts8_details.get("approval_mode") != mode.value:
            raise L1ContractError("TS8 package approval mode mismatch")
        self.display(package)
        initial = (
            "ARMED_REVIEWABLE"
            if mode is ApprovalMode.PREAUTHORIZED_ARMED
            else "AWAITING_HUMAN_APPROVAL"
        )
        with self._mutation():
            row = self._connection.execute(
                "SELECT state, approval_mode FROM ts8_state WHERE package_id = ?",
                (package.package_id,),
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO ts8_state VALUES (?, ?, ?, NULL, ?, 'NOT_SUBMITTED')",
                    (package.package_id, initial, mode.value, package.created_server_ms),
                )
                return initial
            if row["approval_mode"] != mode.value:
                raise L1ContractError("retained TS8 approval mode conflicts")
            return str(row["state"])

    def ts8_action(
        self,
        package: StrategyOrderPackage,
        *,
        action_key: str,
        request_digest: str,
        action: str,
        approval_mode: ApprovalMode,
        server_ms: int,
        snapshot_digest: str,
        source_refs: dict[str, str],
        post_disposition: str | None = None,
        reason_codes: tuple[str, ...] = (),
    ) -> str:
        """Persist one observed Human action on the operator-owned connection."""
        if action not in {"APPROVE", "REJECT"} or not action_key or not request_digest:
            raise L1ContractError("invalid Human action")
        if package.ts8_details is None or package.authority_mode is not AuthorityMode.ZERO_WRITE:
            raise L1ContractError("TS8 action requires exact zero-write package")
        if post_disposition not in {None, "WOULD_SUBMIT", "NO_SUBMIT"}:
            raise L1ContractError("invalid zero-write disposition")
        refs_json = canonical_json_bytes(source_refs).decode("utf-8")
        with self._mutation():
            retained = self.ts8_action_replay(
                action_key=action_key, package_id=package.package_id,
                request_digest=request_digest, action=action,
                shadow_id=package.parent_strategy_order_id,
            )
            if retained is not None:
                return retained[0]
            # The initial display, Human action and final disposition share
            # one short operator-ledger transaction after the source closes.
            self.ts8_display(package, mode=approval_mode)
            self._require_displayed(package)
            state = self.ts8_state(package.package_id)
            if server_ms >= package.expires_server_ms and state == "AWAITING_HUMAN_APPROVAL":
                return self.ts8_terminalize_post(
                    package, terminal="EXPIRED", server_ms=server_ms,
                    snapshot_digest=snapshot_digest, source_refs=source_refs,
                    reason_code="PACKAGE_EXPIRED",
                )
            self._require_fresh(package, server_ms)
            if state not in {None, "ARMED_REVIEWABLE", "AWAITING_HUMAN_APPROVAL"}:
                raise L1ContractError("package is no longer reviewable")
            if approval_mode.value != package.ts8_details.get("approval_mode"):
                raise L1ContractError("approval mode does not match package")
            if action == "REJECT":
                result = "REJECTED"
            elif approval_mode is ApprovalMode.PREAUTHORIZED_ARMED:
                if state != "ARMED_REVIEWABLE":
                    raise L1ContractError("preauthorization requires proven ARMED state")
                result = "APPROVED_WAITING_ACTIVATION"
            else:
                if state != "AWAITING_HUMAN_APPROVAL" or post_disposition is None:
                    raise L1ContractError("post-activation approval requires final guard result")
                result = post_disposition
            self._connection.execute(
                "INSERT INTO ts8_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OBSERVED')",
                (
                    action_key,
                    package.package_id,
                    request_digest,
                    action,
                    server_ms,
                    snapshot_digest,
                    refs_json,
                    result,
                ),
            )
            self._connection.execute(
                "INSERT INTO ts8_state VALUES (?, ?, ?, NULL, ?, 'NOT_SUBMITTED') "
                "ON CONFLICT(package_id) DO UPDATE SET state=excluded.state, "
                "updated_server_ms=excluded.updated_server_ms",
                (package.package_id, result, approval_mode.value, server_ms),
            )
            if action == "APPROVE" and approval_mode is ApprovalMode.POST_ACTIVATION:
                self._ts8_transition(
                    "post-revalidate:" + action_key,
                    package,
                    "ACTIVATED_REVALIDATING",
                    server_ms,
                    package.activation_opportunity_id,
                    snapshot_digest,
                    refs_json,
                    (),
                )
            self._ts8_transition(
                "human:" + action_key,
                package,
                result,
                server_ms,
                None,
                snapshot_digest,
                refs_json,
                reason_codes,
            )
            self._evidence(
                "ts8-human:" + action_key,
                package,
                EvidenceStream.HUMAN_WORKFLOW_SHADOW,
                server_ms,
            )
            if result == "NO_SUBMIT" and _ts8_thesis_valid_no_submit(reason_codes):
                self._ts8_wait_fresh_trigger(
                    package, server_ms, snapshot_digest, refs_json, reason_codes
                )
            return result

    def ts8_reconcile(
        self,
        package: StrategyOrderPackage,
        *,
        activation_id: str,
        server_ms: int,
        snapshot_digest: str,
        source_refs: dict[str, str],
        disposition: str,
        reason_codes: tuple[str, ...] = (),
    ) -> str:
        if disposition not in {"WOULD_SUBMIT", "NO_SUBMIT"} or not activation_id:
            raise L1ContractError("invalid reconciler disposition")
        refs_json = canonical_json_bytes(source_refs).decode("utf-8")
        with self._mutation():
            self._require_displayed(package)
            state = self.ts8_state(package.package_id)
            if state in {
                "WOULD_SUBMIT", "NO_SUBMIT", "WAITING_FRESH_TRIGGER", "EXPIRED", "THESIS_INVALID"
            }:
                return state
            if state != "APPROVED_WAITING_ACTIVATION":
                raise L1ContractError("package is not waiting for activation")
            if server_ms >= package.expires_server_ms:
                disposition = "NO_SUBMIT"
                reason_codes = ("PACKAGE_EXPIRED",)
            self._ts8_transition(
                "activate:" + package.package_id + ":" + activation_id,
                package,
                "ACTIVATED_REVALIDATING",
                server_ms,
                activation_id,
                snapshot_digest,
                refs_json,
                (),
            )
            self._ts8_transition(
                "terminal:" + package.package_id + ":" + activation_id,
                package,
                disposition,
                server_ms,
                activation_id,
                snapshot_digest,
                refs_json,
                reason_codes,
            )
            self._connection.execute(
                "UPDATE ts8_state SET state = ?, activation_id = ?, updated_server_ms = ? "
                "WHERE package_id = ? AND state = 'APPROVED_WAITING_ACTIVATION'",
                (disposition, activation_id, server_ms, package.package_id),
            )
            self._evidence(
                "ts8-terminal:" + package.package_id,
                package,
                EvidenceStream.HUMAN_WORKFLOW_SHADOW,
                server_ms,
            )
            if disposition == "NO_SUBMIT" and _ts8_thesis_valid_no_submit(reason_codes):
                self._ts8_wait_fresh_trigger(
                    package, server_ms, snapshot_digest, refs_json, reason_codes
                )
            return disposition

    def ts8_fail_pending(
        self,
        package: StrategyOrderPackage,
        *,
        server_ms: int,
        snapshot_digest: str,
        source_refs: dict[str, str],
        reason_code: str,
    ) -> str:
        """Terminate an unprovable or expired pending approval without Activation."""
        if not reason_code:
            raise L1ContractError("terminal reason is required")
        with self._mutation():
            state = self.ts8_state(package.package_id)
            if state in {"NO_SUBMIT", "WAITING_FRESH_TRIGGER", "WOULD_SUBMIT", "EXPIRED"}:
                return state
            if state != "APPROVED_WAITING_ACTIVATION":
                raise L1ContractError("package is not pending")
            terminal = "EXPIRED" if reason_code == "PACKAGE_EXPIRED" else "NO_SUBMIT"
            refs_json = canonical_json_bytes(source_refs).decode("utf-8")
            self._ts8_transition(
                "pending-terminal:" + package.package_id,
                package,
                terminal,
                server_ms,
                None,
                snapshot_digest,
                refs_json,
                (reason_code,),
            )
            self._connection.execute(
                "UPDATE ts8_state SET state = ?, updated_server_ms = ? WHERE package_id = ?",
                (terminal, server_ms, package.package_id),
            )
            return terminal

    def _ts8_wait_fresh_trigger(
        self, package: StrategyOrderPackage, server_ms: int,
        snapshot_digest: str, refs_json: str, reasons: tuple[str, ...]
    ) -> None:
        self._ts8_transition(
            "fresh-trigger:" + package.package_id,
            package, "WAITING_FRESH_TRIGGER", server_ms, None,
            snapshot_digest, refs_json, reasons,
        )
        self._connection.execute(
            "UPDATE ts8_state SET state = 'WAITING_FRESH_TRIGGER', updated_server_ms = ? "
            "WHERE package_id = ? AND state = 'NO_SUBMIT'",
            (server_ms, package.package_id),
        )

    def _ts8_transition(
        self,
        key: str,
        package: StrategyOrderPackage,
        state: str,
        server_ms: int,
        activation_id: str | None,
        snapshot_digest: str,
        refs_json: str,
        reasons: tuple[str, ...],
    ) -> None:
        self._connection.execute(
            "INSERT INTO ts8_transitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'NOT_SUBMITTED')",
            (
                key,
                package.package_id,
                state,
                server_ms,
                activation_id,
                snapshot_digest,
                refs_json,
                canonical_json_bytes(reasons).decode("utf-8"),
            ),
        )

    def display(self, package: StrategyOrderPackage) -> StrategyOrderPackage:
        with self._mutation():
            payload = self._validated_payload(package)
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
        with self._mutation():
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
        with self._mutation():
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
        with self._mutation():
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
        with self._mutation():
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
                    raise L1ContractError(
                        "preauthorization requires its exact activation opportunity"
                    )
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
        with self._mutation():
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
            if (
                self.state(package, server_ms=server_ms)
                is not ApprovalState.AWAITING_HUMAN_APPROVAL
            ):
                raise L1ContractError("post-activation approval requires an open activation")
            self._event(action_key, package, "ACTIVATED", ApprovalMode.POST_ACTIVATION, server_ms)
            self._evidence(
                "workflow:" + action_key, package, EvidenceStream.HUMAN_WORKFLOW_SHADOW, server_ms
            )
            return ApprovalState.ACTIVATED

    def supersede(
        self, old: StrategyOrderPackage, new: StrategyOrderPackage, *, server_ms: int
    ) -> None:
        with self._mutation():
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

    @contextmanager
    def _mutation(self) -> Iterator[None]:
        """Commit one public authority transition, including nested public calls."""
        outermost = self._mutation_depth == 0
        if outermost:
            if self._connection.in_transaction:
                raise L1ContractError("caller-owned SQLite transaction is not supported")
            self._connection.execute("BEGIN IMMEDIATE")
        self._mutation_depth += 1
        try:
            yield
        except BaseException:
            if outermost:
                self._connection.rollback()
            raise
        else:
            if outermost:
                try:
                    self._connection.commit()
                except BaseException:
                    self._connection.rollback()
                    raise
        finally:
            self._mutation_depth -= 1

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
