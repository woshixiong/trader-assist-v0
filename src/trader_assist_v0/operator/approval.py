"""Server-only zero-write Human actions and pending-approval reconciliation."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.l1_approval import (
    ApprovalMode,
    HumanApprovalLedger,
    L1ContractError,
    StrategyOrderPackage,
)
from trader_assist_v0.multi_asset_shadow.shadow_records.records import RecordError
from trader_assist_v0.multi_asset_shadow.shadow_records.store import ReadOnlyEvidenceSnapshot
from trader_assist_v0.nautilus_e4.contracts import GuardDecision, GuardInputs
from trader_assist_v0.nautilus_e4.guard import evaluate_entry_guard

from .contracts import OperatorConfig
from .projection import (
    ProjectionBlocked,
    SourceProjection,
    project_post_activation,
    project_preauthorized_armed,
    prove_later_activation,
)


class OperatorBlocked(ValueError):
    """The operator cannot make an authoritative zero-write transition."""


@dataclass(frozen=True)
class CurrentGuardEvidence:
    inputs: GuardInputs
    executable_price: Decimal
    source_ref: str


GuardReader = Callable[[ReadOnlyEvidenceSnapshot, SourceProjection], CurrentGuardEvidence | None]


@dataclass(frozen=True)
class GuardDisposition:
    state: str
    reasons: tuple[str, ...]
    source_refs: dict[str, str]
    snapshot_digest: str


@dataclass(frozen=True)
class HumanActionRecord:
    state: str
    observed_server_ms: int


class OperatorEngine:
    """Owns only the operator ledger and read-only source snapshots."""

    def __init__(self, config: OperatorConfig, *, guard_reader: GuardReader | None = None) -> None:
        self.config = config
        self._guard_reader = guard_reader
        if config.runtime_evidence_path.resolve() == config.operator_ledger_path.resolve():
            raise OperatorBlocked("runtime and operator databases must be distinct")

    def _ledger(self) -> tuple[sqlite3.Connection, HumanApprovalLedger]:
        connection = sqlite3.connect(self.config.operator_ledger_path, timeout=0.1)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection, HumanApprovalLedger(connection)

    def latest(self, *, now_ms: int | None = None) -> tuple[SourceProjection, str]:
        now_ms = _now_ms() if now_ms is None else now_ms
        try:
            with ReadOnlyEvidenceSnapshot(self.config.runtime_evidence_path) as source:
                if self.config.approval_mode == "PREAUTHORIZED_ARMED":
                    projection = project_preauthorized_armed(
                        source, self.config, _observed_ms=now_ms
                    )
                else:
                    projection = project_post_activation(source, self.config, observed_ms=now_ms)
            connection, ledger = self._ledger()
            try:
                state = ledger.ts8_state(projection.package.package_id)
            finally:
                connection.close()
            effective = state or "AWAITING_HUMAN_APPROVAL"
            if effective == "AWAITING_HUMAN_APPROVAL" and now_ms >= (
                projection.package.expires_server_ms
            ):
                effective = "EXPIRED"
            return projection, effective
        except (sqlite3.Error, L1ContractError, ProjectionBlocked) as exc:
            raise OperatorBlocked(str(exc)) from exc

    def revision(self) -> int:
        connection, ledger = self._ledger()
        try:
            return ledger.ts8_revision()
        finally:
            connection.close()

    def recent_terminal(self) -> tuple[str, str] | None:
        connection, ledger = self._ledger()
        try:
            return ledger.ts8_recent_terminal()
        finally:
            connection.close()

    def _guard(
        self, source: ReadOnlyEvidenceSnapshot, projection: SourceProjection
    ) -> GuardDisposition:
        current = None if self._guard_reader is None else self._guard_reader(source, projection)
        if current is None:
            return GuardDisposition(
                "NO_SUBMIT",
                ("DATA_HEALTH_FAIL", "ENTRY_POLICY_UNRESOLVED"),
                projection.source_refs,
                projection.snapshot_digest,
            )
        details = projection.package.ts8_details
        if details is None:
            raise OperatorBlocked("package details are absent")
        approved_entry = details.get("max_approved_entry")
        policy_version = details.get("policy_version")
        try:
            max_approved_entry = Decimal(str(approved_entry))
        except (InvalidOperation, ValueError):
            max_approved_entry = Decimal("NaN")
        if (
            approved_entry is None
            or policy_version is None
            or not max_approved_entry.is_finite()
            or max_approved_entry <= 0
            or current.inputs.guard_config_version != policy_version
        ):
            return GuardDisposition(
                "NO_SUBMIT", ("ENTRY_POLICY_UNRESOLVED",), projection.source_refs,
                projection.snapshot_digest,
            )
        side = str(details.get("side"))
        adverse = (
            current.executable_price > max_approved_entry
            if side == "LONG"
            else current.executable_price < max_approved_entry
        )
        result = evaluate_entry_guard(current.inputs)
        reasons = tuple(result.reason_codes)
        if adverse:
            reasons += ("PRICE_MOVED_TOO_FAR",)
        refs = {**projection.source_refs, "current_guard": current.source_ref}
        digest = sha256_hex(
            canonical_json_bytes(
                {
                    "projection": projection.snapshot_digest,
                    "guard": current.inputs.model_dump(mode="json"),
                    "executable_price": str(current.executable_price),
                    "max_approved_entry": str(max_approved_entry),
                    "source_ref": current.source_ref,
                }
            )
        )
        return GuardDisposition(
            "WOULD_SUBMIT"
            if result.decision is GuardDecision.PASS and not adverse
            else "NO_SUBMIT",
            reasons,
            refs,
            digest,
        )

    def human_action(
        self,
        *,
        shadow_id: str,
        package_id: str,
        package_hash: str,
        action_key: str,
        action: str,
        session_id: str,
        now_ms: int | None = None,
    ) -> str:
        return self.human_action_record(
            shadow_id=shadow_id, package_id=package_id, package_hash=package_hash,
            action_key=action_key, action=action, session_id=session_id, now_ms=now_ms,
        ).state

    def human_action_record(
        self,
        *,
        shadow_id: str,
        package_id: str,
        package_hash: str,
        action_key: str,
        action: str,
        session_id: str,
        now_ms: int | None = None,
    ) -> HumanActionRecord:
        realtime = now_ms is None
        now_ms = _now_ms() if now_ms is None else now_ms
        if (
            action not in {"APPROVE", "REJECT"}
            or len(shadow_id) != 64 or len(package_id) != 64
            or len(package_hash) != 64 or not 1 <= len(action_key) <= 160
            or not session_id
        ):
            raise OperatorBlocked("invalid Human action identity")
        if self.config.approval_mode != "POST_ACTIVATION":
            raise OperatorBlocked("PREAUTHORIZED_ARMED exact package is not reviewable")
        request_digest = sha256_hex(
            canonical_json_bytes(
                {
                    "package_id": package_id,
                    "package_hash": package_hash,
                    "action": action,
                    "session_id": session_id,
                }
            )
        )
        try:
            connection, ledger = self._ledger()
            try:
                replay = ledger.ts8_action_replay(
                    action_key=action_key, package_id=package_id,
                    request_digest=request_digest, action=action, shadow_id=shadow_id,
                )
            finally:
                connection.close()
            if replay is not None:
                return HumanActionRecord(replay[0], replay[1])
            with ReadOnlyEvidenceSnapshot(self.config.runtime_evidence_path) as source:
                projection = project_post_activation(
                    source,
                    self.config,
                    shadow_id=shadow_id,
                    observed_ms=now_ms,
                )
                if projection.package.package_id != package_id or (
                    projection.package.package_hash != package_hash
                ):
                    raise OperatorBlocked("browser package is stale or altered")
                expired = now_ms >= projection.package.expires_server_ms
                disposition = (
                    self._guard(source, projection) if action == "APPROVE" and not expired else None
                )
            decision_ms = _now_ms() if realtime else now_ms
            expired = decision_ms >= projection.package.expires_server_ms
            if expired:
                connection, ledger = self._ledger()
                try:
                    ledger.ts8_terminalize_post(
                        projection.package, terminal="EXPIRED", server_ms=decision_ms,
                        snapshot_digest=projection.snapshot_digest,
                        source_refs=projection.source_refs, reason_code="PACKAGE_EXPIRED",
                    )
                finally:
                    connection.close()
                raise OperatorBlocked("package expired")
            connection, ledger = self._ledger()
            try:
                result = ledger.ts8_action(
                    projection.package,
                    action_key=action_key,
                    request_digest=request_digest,
                    action=action,
                    approval_mode=ApprovalMode.POST_ACTIVATION,
                    server_ms=decision_ms,
                    snapshot_digest=(
                        projection.snapshot_digest
                        if disposition is None
                        else disposition.snapshot_digest
                    ),
                    source_refs=(
                        projection.source_refs if disposition is None else disposition.source_refs
                    ),
                    post_disposition=None if disposition is None else disposition.state,
                    reason_codes=() if disposition is None else disposition.reasons,
                )
                if result == "EXPIRED":
                    raise OperatorBlocked("package expired")
                committed = ledger.ts8_action_replay(
                    action_key=action_key, package_id=package_id,
                    request_digest=request_digest, action=action, shadow_id=shadow_id,
                )
                if committed is None:
                    raise OperatorBlocked("committed Human action is missing")
                return HumanActionRecord(committed[0], committed[1])
            finally:
                connection.close()
        except (sqlite3.Error, L1ContractError, ProjectionBlocked) as exc:
            raise OperatorBlocked(str(exc)) from exc

    def reconcile_once(self, *, now_ms: int | None = None) -> int:
        """One bounded pass; never called by HTTP GET or SSE handlers."""
        now_ms = _now_ms() if now_ms is None else now_ms
        connection, ledger = self._ledger()
        try:
            pending = tuple(
                (package, ledger.ts8_approval_time(package.package_id))
                for package in ledger.ts8_pending(limit=32)
            )
        finally:
            connection.close()
        count = 0
        for package, approved_ms in pending:
            if now_ms >= package.expires_server_ms:
                self._fail_pending(package, now_ms, "PACKAGE_EXPIRED")
                count += 1
                continue
            try:
                with ReadOnlyEvidenceSnapshot(self.config.runtime_evidence_path) as source:
                    projection = prove_later_activation(
                        source, self.config, package, observed_ms=now_ms, approved_ms=approved_ms
                    )
                    if projection is None:
                        continue
                    disposition = self._guard(source, projection)
                connection, ledger = self._ledger()
                try:
                    ledger.ts8_reconcile(
                        package,
                        activation_id=projection.activation_id,
                        server_ms=now_ms,
                        snapshot_digest=disposition.snapshot_digest,
                        source_refs=disposition.source_refs,
                        disposition=disposition.state,
                        reason_codes=disposition.reasons,
                    )
                finally:
                    connection.close()
                count += 1
            except (sqlite3.Error, ProjectionBlocked, L1ContractError):
                # A missing/ambiguous source never becomes a guard pass. Keep
                # waiting only within the exact approval window.
                continue
        if self.config.approval_mode == "POST_ACTIVATION":
            count += self._reconcile_post(now_ms)
        return count

    def _reconcile_post(self, now_ms: int) -> int:
        connection, ledger = self._ledger()
        try:
            open_packages = ledger.ts8_open_post(limit=32)
        finally:
            connection.close()
        transitions: list[tuple[StrategyOrderPackage, str, str, str, dict[str, str]]] = []
        for package in open_packages:
            if now_ms >= package.expires_server_ms:
                transitions.append((
                    package, "EXPIRED", "PACKAGE_EXPIRED",
                    _terminal_digest(package, now_ms, "PACKAGE_EXPIRED"),
                    _package_source_refs(package),
                ))
        still_open = tuple(p for p in open_packages if now_ms < p.expires_server_ms)
        current: SourceProjection | None = None
        try:
            with ReadOnlyEvidenceSnapshot(self.config.runtime_evidence_path) as source:
                try:
                    current = project_post_activation(source, self.config, observed_ms=now_ms)
                except ProjectionBlocked:
                    pass
                for package in still_open:
                    classified = _classify_post_source(source, package, current, now_ms)
                    if classified is not None:
                        terminal, reason, digest, refs = classified
                        transitions.append((package, terminal, reason, digest, refs))
        except (sqlite3.Error, RecordError, ProjectionBlocked):
            # Source failure cannot prove a thesis terminal. Pure time expiry
            # remains authoritative and can still be committed below.
            current = None
        connection, ledger = self._ledger()
        try:
            count = 0
            for package, terminal, reason, digest, refs in transitions:
                if ledger.ts8_terminalize_post(
                    package, terminal=terminal, server_ms=now_ms,
                    snapshot_digest=digest, source_refs=refs, reason_code=reason,
                ) == terminal:
                    count += 1
            if current is not None:
                package = current.package
                if now_ms >= package.expires_server_ms:
                    if ledger.ts8_terminalize_post(
                        package, terminal="EXPIRED", server_ms=now_ms,
                        snapshot_digest=current.snapshot_digest,
                        source_refs=current.source_refs, reason_code="PACKAGE_EXPIRED",
                    ) == "EXPIRED":
                        count += 1
                else:
                    ledger.ts8_display(package, mode=ApprovalMode.POST_ACTIVATION)
            return count
        finally:
            connection.close()

    def _fail_pending(self, package: StrategyOrderPackage, now_ms: int, reason: str) -> None:
        connection, ledger = self._ledger()
        try:
            ledger.ts8_fail_pending(
                package,
                server_ms=now_ms,
                snapshot_digest="SOURCE_UNAVAILABLE",
                source_refs={},
                reason_code=reason,
            )
        finally:
            connection.close()


def _package_source_refs(package: StrategyOrderPackage) -> dict[str, str]:
    details = package.ts8_details or {}
    ids = details.get("source_ids")
    hashes = details.get("source_hashes")
    if not isinstance(ids, dict) or not isinstance(hashes, dict):
        return {}
    return {
        key: value
        for name, record_id in ids.items()
        if isinstance(name, str) and isinstance(record_id, str)
        for key, value in (
            (name + ".id", record_id),
            (name + ".hash", str(hashes.get(name, ""))),
        )
    }


def _terminal_digest(package: StrategyOrderPackage, now_ms: int, reason: str) -> str:
    return sha256_hex(canonical_json_bytes({
        "package_id": package.package_id,
        "source_refs": _package_source_refs(package),
        "observed_ms": now_ms,
        "reason": reason,
    }))


def _classify_post_source(
    source: ReadOnlyEvidenceSnapshot,
    package: StrategyOrderPackage,
    current: SourceProjection | None,
    now_ms: int,
) -> tuple[str, str, str, dict[str, str]] | None:
    """Classify only proven replacement or retained immutable contradictions."""
    if (
        current is not None
        and current.package.package_id != package.package_id
        and current.package.created_server_ms > package.created_server_ms
    ):
        refs = {**_package_source_refs(package), **{
            "replacement_package_id": current.package.package_id,
            "replacement_package_hash": current.package.package_hash,
        }}
        digest = sha256_hex(canonical_json_bytes({
            "old_package_id": package.package_id,
            "replacement_snapshot_digest": current.snapshot_digest,
            "refs": refs,
        }))
        return "SUPERSEDED", "PACKAGE_SUPERSEDED", digest, refs
    details = package.ts8_details or {}
    ids = details.get("source_ids")
    hashes = details.get("source_hashes")
    if not isinstance(ids, dict) or not isinstance(hashes, dict):
        return None
    records = {}
    try:
        for name, record_id in ids.items():
            if not isinstance(name, str) or not isinstance(record_id, str):
                return None
            record = source.get(record_id)
            if record is None:
                return None  # Missing source may be transient; never claim thesis invalidity.
            records[name] = record
        contradiction = any(
            record.canonical_hash != hashes.get(name) for name, record in records.items()
        )
        shadow = records.get("shadow")
        signal = records.get("signal")
        plan = records.get("plan")
        if shadow is not None and signal is not None and plan is not None:
            contradiction |= (
                shadow.payload.get("signal_id") != signal.record_id
                or shadow.payload.get("plan_id") != plan.record_id
                or plan.payload.get("signal_id") != signal.record_id
            )
            evaluation_id = signal.payload.get("strategy_evaluation_id")
            if evaluation_id is not None:
                contradiction |= len(source.matching(
                    "strategy_evaluation", "evaluation_id", str(evaluation_id)
                )) > 1
        if not contradiction:
            return None
    except RecordError:
        return None  # Decode/read corruption is not definitive thesis evidence.
    refs = _package_source_refs(package)
    return (
        "THESIS_INVALID", "RETAINED_THESIS_CONTRADICTION",
        _terminal_digest(package, now_ms, "RETAINED_THESIS_CONTRADICTION"), refs,
    )


def _now_ms() -> int:
    return time.time_ns() // 1_000_000
