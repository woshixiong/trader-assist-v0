"""Stateful project semantics around provider-owned market-data transport."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .causal import AdmissionOutcome, CausalAdmissionLedger
from .contracts import (
    POST_TERMINAL_CONTEXT_NS,
    POST_TERMINAL_MICRO_NS,
    PRE_DECISION_RETENTION_NS,
    AdmittedEvent,
    ApprovalProvenance,
    ApprovalTimingMode,
    CaptureTier,
    DataKind,
    DecisionState,
    EvidenceState,
    LifecycleKind,
    LifecycleRecord,
    LifecycleStatus,
    RunManifest,
    SourceEvent,
    StreamHealth,
    TailPhase,
    TailStatus,
)
from .storage import EvidenceStore, RawCatalogSink

_TERMINAL_LIFECYCLE_STATUSES = frozenset(
    {
        LifecycleStatus.TERMINAL,
        LifecycleStatus.EXPIRED,
        LifecycleStatus.SUPERSEDED,
    }
)


def _lifecycle_authority(record: LifecycleRecord) -> tuple[object, ...]:
    return (
        record.run_id,
        record.kind,
        record.parent_id,
        record.package_id,
        record.market_id,
        record.expression_id,
    )


def _validate_lifecycle_successor(
    previous: LifecycleRecord, record: LifecycleRecord
) -> None:
    if record.record_hash == previous.record_hash:
        raise ValueError("exact duplicate lifecycle fact")
    if _lifecycle_authority(record) != _lifecycle_authority(previous):
        raise ValueError("lifecycle object authority contradicts prior accepted fact")
    previous_order = (previous.state_ts, previous.last_admission_ordinal)
    record_order = (record.state_ts, record.last_admission_ordinal)
    if record_order <= previous_order:
        raise ValueError("lifecycle fact order must be strictly increasing")
    if previous.status in _TERMINAL_LIFECYCLE_STATUSES:
        raise ValueError("lifecycle fact cannot follow terminal-family state")
    if (
        previous.status is not LifecycleStatus.ACTIVE
        or record.status
        not in {LifecycleStatus.ACTIVE, *_TERMINAL_LIFECYCLE_STATUSES}
    ):
        raise ValueError("unsupported repeated-object lifecycle transition")


def _fold_lifecycle_records(
    records: Iterable[LifecycleRecord], *, run_id: str
) -> tuple[
    dict[str, LifecycleRecord],
    set[str],
    set[str],
    dict[str, set[str]],
]:
    """Validate immutable facts in durable append order and retain latest authority."""
    latest: dict[str, LifecycleRecord] = {}
    lifecycle_ids: set[str] = set()
    record_hashes: set[str] = set()
    hashes_by_object: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.run_id != run_id:
            raise ValueError("persisted lifecycle fact contradicts immutable run identity")
        if record.record_hash in record_hashes:
            raise ValueError("persisted lifecycle contains an exact duplicate fact")
        previous = latest.get(record.object_id)
        if previous is None:
            if record.parent_id is not None and record.parent_id not in lifecycle_ids:
                raise ValueError("persisted lifecycle parent identity is unknown")
        else:
            _validate_lifecycle_successor(previous, record)
        lifecycle_ids.add(record.object_id)
        record_hashes.add(record.record_hash)
        hashes_by_object[record.object_id].add(record.record_hash)
        latest[record.object_id] = record
    return latest, lifecycle_ids, record_hashes, hashes_by_object


@dataclass(frozen=True)
class SubscriptionPolicy:
    """Discovery gets bars; only Watch/Actionable get BBO and trades."""

    discovery: frozenset[str]
    watch: frozenset[str]
    actionable: frozenset[str]

    def __post_init__(self) -> None:
        if self.watch - self.discovery or self.actionable - self.discovery:
            raise ValueError("Watch/Actionable must be bounded subsets of Discovery")

    def tier(self, market_id: str) -> CaptureTier:
        if market_id in self.actionable:
            return CaptureTier.ACTIONABLE
        if market_id in self.watch:
            return CaptureTier.WATCH
        if market_id in self.discovery:
            return CaptureTier.DISCOVERY
        raise KeyError(f"market is outside the prospective PIT universe: {market_id}")

    def permits(self, market_id: str, data_kind: DataKind) -> bool:
        tier = self.tier(market_id)
        if data_kind in {DataKind.BAR, DataKind.CONTEXT}:
            return True
        return tier in {CaptureTier.WATCH, CaptureTier.ACTIONABLE}


@dataclass
class _PackageState:
    market_id: str
    expression_id: str
    opportunity_id: str
    thesis_id: str
    predecision_state: EvidenceState
    tail: TailStatus
    terminal_decision: DecisionState | None = None


class CaptureSession:
    """One append-only process epoch with deterministic restart/reconnect semantics."""

    def __init__(
        self,
        *,
        manifest: RunManifest,
        policy: SubscriptionPolicy,
        raw_sink: RawCatalogSink | None,
        evidence_store: EvidenceStore | None = None,
        batch_size: int = 128,
        seen_source_ids: set[str] | None = None,
        seen_lifecycle_ids: set[str] | None = None,
        latest_lifecycle_records: dict[str, LifecycleRecord] | None = None,
        durable_source_ids: set[str] | None = None,
        runtime_segment_index: int = 0,
        checkpoint_sequence: int = 0,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        raw_expressions = manifest.capture_configuration.get("expressions", [])
        if not isinstance(raw_expressions, list):
            raise ValueError("manifest expressions must be a list")
        manifest_markets = {
            item["market_id"]
            for item in raw_expressions
            if isinstance(item, dict) and isinstance(item.get("market_id"), str)
        }
        if manifest_markets and policy.discovery != manifest_markets:
            raise ValueError("subscription policy contradicts manifest expression universe")
        self.manifest = manifest
        self.policy = policy
        self.raw_sink = raw_sink
        self.evidence_store = evidence_store
        self.batch_size = batch_size
        self.ledger = CausalAdmissionLedger(
            process_epoch=manifest.process_epoch,
            continuity_epoch=manifest.continuity_epoch,
            admission_epoch=manifest.admission_epoch,
            seen_source_ids=seen_source_ids,
        )
        self._prebuffers: dict[str, deque[AdmittedEvent]] = defaultdict(deque)
        self._watch_started: dict[str, tuple[int, str]] = {}
        self._pending: list[AdmittedEvent] = []
        self._durable_source_ids = (
            set() if durable_source_ids is None else set(durable_source_ids)
        )
        self._packages: dict[str, _PackageState] = {}
        self._market_packages: dict[str, set[str]] = defaultdict(set)
        self._lifecycle_ids = set() if seen_lifecycle_ids is None else set(seen_lifecycle_ids)
        self._latest_lifecycle_records = (
            {} if latest_lifecycle_records is None else dict(latest_lifecycle_records)
        )
        if not set(self._latest_lifecycle_records) <= self._lifecycle_ids:
            raise ValueError("latest lifecycle authority is absent from lifecycle_ids")
        for object_id, record in self._latest_lifecycle_records.items():
            if record.object_id != object_id:
                raise ValueError("latest lifecycle checkpoint key contradicts object identity")
            if record.run_id != manifest.run_id:
                raise ValueError("latest lifecycle fact contradicts immutable run identity")
            if record.parent_id is not None and record.parent_id not in self._lifecycle_ids:
                raise ValueError("latest lifecycle parent identity is unknown")
        latest_hashes = {
            record.record_hash for record in self._latest_lifecycle_records.values()
        }
        if len(latest_hashes) != len(self._latest_lifecycle_records):
            raise ValueError("latest lifecycle checkpoint contains duplicate facts")
        self._lifecycle_record_hashes = latest_hashes
        self._lifecycle: list[LifecycleRecord] = []
        self._decision_commitments: dict[str, tuple[int, DecisionState]] = {}
        self._counts: Counter[str] = Counter()
        self._missingness: Counter[str] = Counter()
        self._storage_failures = 0
        self._last_ts_init: int | None = None
        self._last_admission_ts: int | None = None
        self._max_admission_lag_ns = 0
        self._observed_streams: set[tuple[str, DataKind]] = set()
        self._continuity_requirements: set[tuple[str, DataKind]] = set()
        self._runtime_segment_index = runtime_segment_index
        self._checkpoint_sequence = checkpoint_sequence

    @property
    def lifecycle_records(self) -> tuple[LifecycleRecord, ...]:
        return tuple(self._lifecycle)

    @property
    def tail_statuses(self) -> dict[str, TailStatus]:
        return {package_id: state.tail for package_id, state in self._packages.items()}

    def ingest(self, source: SourceEvent, *, admission_ts: int) -> AdmissionOutcome:
        if not self.policy.permits(source.market_id, source.data_kind):
            raise ValueError("rich evidence is prohibited for a Discovery-only market")
        outcome = self.ledger.admit(source, admission_ts=admission_ts)
        if outcome.duplicate:
            self._counts["duplicates"] += 1
            return outcome
        assert outcome.event is not None
        event = outcome.event
        self._last_ts_init = source.ts_init
        self._last_admission_ts = admission_ts
        self._max_admission_lag_ns = max(
            self._max_admission_lag_ns, admission_ts - source.ts_init
        )
        self._counts[f"source:{source.data_kind.value}"] += 1
        self._counts[f"market:{source.market_id}"] += 1
        if event.out_of_order:
            self._counts["out_of_order"] += 1
        if source.data_kind in {DataKind.BBO, DataKind.TRADE}:
            started = self._watch_started.get(source.market_id)
            if started is None or started[1] != event.continuity_epoch:
                self._watch_started[source.market_id] = (
                    admission_ts,
                    event.continuity_epoch,
                )
            self._append_prebuffer(event)
        self._observed_streams.add((source.market_id, source.data_kind))
        continuity_restored = False
        if self.ledger.health is StreamHealth.REESTABLISHING:
            self._continuity_requirements.discard((source.market_id, source.data_kind))
            if not self._continuity_requirements:
                self.ledger.establish_continuity()
                continuity_restored = True
        if self._must_retain(event):
            self._queue_durable((event,))
            self._flush_if_full()
        if continuity_restored:
            self._persist_if_configured(reason="FRESH_STREAM_CONTINUITY_RESTORED")
        return outcome

    def _append_prebuffer(self, event: AdmittedEvent) -> None:
        buffer = self._prebuffers[event.source.market_id]
        buffer.append(event)
        cutoff = event.admission_ts - PRE_DECISION_RETENTION_NS
        while buffer and buffer[0].admission_ts < cutoff:
            buffer.popleft()

    def _must_retain(self, event: AdmittedEvent) -> bool:
        # Finalized Discovery BAR/context is required semantic evidence even
        # when no Actionable package exists. This is intentionally the
        # low-rate path; rich BBO/trade retention remains lifecycle-bounded.
        if event.source.data_kind in {DataKind.BAR, DataKind.CONTEXT}:
            return True
        for package_id in self._market_packages[event.source.market_id]:
            package = self._packages[package_id]
            if package.tail.terminal_ts is None:
                return True
            if event.source.data_kind in {DataKind.BBO, DataKind.TRADE}:
                if (
                    package.tail.micro_phase in {TailPhase.ACTIVE, TailPhase.INCOMPLETE}
                    and package.tail.micro_deadline_ts is not None
                    and event.admission_ts <= package.tail.micro_deadline_ts
                ):
                    return True
            elif (
                package.tail.context_phase in {TailPhase.ACTIVE, TailPhase.INCOMPLETE}
                and package.tail.context_deadline_ts is not None
                and event.admission_ts <= package.tail.context_deadline_ts
            ):
                return True
        return False

    def open_actionable(
        self,
        *,
        package_id: str,
        opportunity_id: str,
        thesis_id: str,
        market_id: str,
        expression_id: str,
        decision_ts: int,
        decision_state: DecisionState,
    ) -> EvidenceState:
        if self.policy.tier(market_id) is not CaptureTier.ACTIONABLE:
            raise ValueError("Actionable lifecycle requires Actionable subscription policy")
        if package_id in self._packages or opportunity_id in self._lifecycle_ids:
            raise ValueError("duplicate Opportunity/Thesis/package authority")
        buffer = tuple(self._prebuffers[market_id])
        cutoff = decision_ts - PRE_DECISION_RETENTION_NS
        available = tuple(
            item for item in buffer if cutoff <= item.admission_ts <= decision_ts
        )
        watch_started = self._watch_started.get(market_id)
        bbo = self.ledger.bbo_validity(market_id=market_id, expression_id=expression_id)
        complete = (
            watch_started is not None
            and watch_started[0] <= cutoff
            and watch_started[1] == self.ledger.continuity_epoch
            and bbo.valid
            and bbo.continuity_epoch == self.ledger.continuity_epoch
            and all(item.continuity_state is EvidenceState.COMPLETE for item in available)
        )
        state = (
            EvidenceState.COMPLETE
            if complete
            else EvidenceState.PRE_DECISION_WINDOW_INCOMPLETE
        )
        if not complete:
            self._missingness[state.value] += 1
        self._queue_durable(available)
        self._flush_if_full(force=True)
        package = _PackageState(
            market_id=market_id,
            expression_id=expression_id,
            opportunity_id=opportunity_id,
            thesis_id=thesis_id,
            predecision_state=state,
            tail=TailStatus(package_id=package_id),
        )
        self._packages[package_id] = package
        self._market_packages[market_id].add(package_id)
        opportunity = self.record_lifecycle(
            object_id=opportunity_id,
            parent_id=None,
            package_id=package_id,
            market_id=market_id,
            expression_id=expression_id,
            kind=LifecycleKind.OPPORTUNITY,
            status=LifecycleStatus.ACTIVE,
            state_ts=decision_ts,
            reason_codes=("ACTIONABLE",),
            decision_state=decision_state,
            evidence_state=state,
            _persist_checkpoint=False,
        )
        self.record_lifecycle(
            object_id=thesis_id,
            parent_id=opportunity.object_id,
            package_id=package_id,
            market_id=market_id,
            expression_id=expression_id,
            kind=LifecycleKind.THESIS,
            status=LifecycleStatus.ACTIVE,
            state_ts=decision_ts,
            reason_codes=("THESIS_CREATED",),
            decision_state=decision_state,
            evidence_state=state,
            _persist_checkpoint=False,
        )
        self._decision_commitments[package_id] = (
            self.ledger.admission_ordinal,
            decision_state,
        )
        self._persist_if_configured(reason="ACTIONABLE_LIFECYCLE_OPENED")
        return state

    def open_structural_package(
        self,
        *,
        package_id: str,
        opportunity_id: str,
        thesis_id: str,
        market_id: str,
        expression_id: str,
        state_ts: int,
    ) -> EvidenceState:
        """Open source-bound lifecycle evidence from an admitted Formal Setup."""
        if self.policy.tier(market_id) not in {CaptureTier.WATCH, CaptureTier.ACTIONABLE}:
            raise ValueError("Structural lifecycle requires Watch/Actionable policy")
        if package_id in self._packages or opportunity_id in self._lifecycle_ids:
            raise ValueError("duplicate Opportunity/Thesis/package authority")
        buffer = tuple(self._prebuffers[market_id])
        cutoff = state_ts - PRE_DECISION_RETENTION_NS
        available = tuple(
            item for item in buffer if cutoff <= item.admission_ts <= state_ts
        )
        watch_started = self._watch_started.get(market_id)
        bbo = self.ledger.bbo_validity(market_id=market_id, expression_id=expression_id)
        complete = (
            watch_started is not None
            and watch_started[0] <= cutoff
            and watch_started[1] == self.ledger.continuity_epoch
            and bbo.valid
            and bbo.continuity_epoch == self.ledger.continuity_epoch
            and all(item.continuity_state is EvidenceState.COMPLETE for item in available)
        )
        state = (
            EvidenceState.COMPLETE
            if complete
            else EvidenceState.PRE_DECISION_WINDOW_INCOMPLETE
        )
        if not complete:
            self._missingness[state.value] += 1
        self._queue_durable(available)
        self._flush_if_full(force=True)
        package = _PackageState(
            market_id=market_id,
            expression_id=expression_id,
            opportunity_id=opportunity_id,
            thesis_id=thesis_id,
            predecision_state=state,
            tail=TailStatus(package_id=package_id),
        )
        self._packages[package_id] = package
        self._market_packages[market_id].add(package_id)
        opportunity = self.record_lifecycle(
            object_id=opportunity_id,
            parent_id=None,
            package_id=package_id,
            market_id=market_id,
            expression_id=expression_id,
            kind=LifecycleKind.OPPORTUNITY,
            status=LifecycleStatus.ACTIVE,
            state_ts=state_ts,
            reason_codes=("FORMAL_SETUP_ADMITTED",),
            decision_state=None,
            evidence_state=state,
            _persist_checkpoint=False,
        )
        self.record_lifecycle(
            object_id=thesis_id,
            parent_id=opportunity.object_id,
            package_id=package_id,
            market_id=market_id,
            expression_id=expression_id,
            kind=LifecycleKind.THESIS,
            status=LifecycleStatus.ACTIVE,
            state_ts=state_ts,
            reason_codes=("THESIS_CREATED",),
            decision_state=None,
            evidence_state=state,
            _persist_checkpoint=False,
        )
        self._persist_if_configured(reason="STRUCTURAL_LIFECYCLE_OPENED")
        return state

    def record_lifecycle(
        self,
        *,
        object_id: str,
        parent_id: str | None,
        package_id: str,
        market_id: str,
        expression_id: str,
        kind: LifecycleKind,
        status: LifecycleStatus,
        state_ts: int,
        reason_codes: tuple[str, ...],
        evidence_state: EvidenceState,
        decision_state: DecisionState | None = None,
        approval_timing_mode: ApprovalTimingMode | None = None,
        approval_provenance: ApprovalProvenance = ApprovalProvenance.NOT_APPLICABLE,
        expiry_ts: int | None = None,
        supersedes_id: str | None = None,
        _persist_checkpoint: bool = True,
    ) -> LifecycleRecord:
        record = LifecycleRecord.create(
            schema_version="E4_CAPTURE_V1",
            run_id=self.manifest.run_id,
            object_id=object_id,
            parent_id=parent_id,
            package_id=package_id,
            market_id=market_id,
            expression_id=expression_id,
            kind=kind,
            status=status,
            state_ts=state_ts,
            reason_codes=reason_codes,
            decision_state=decision_state,
            approval_timing_mode=approval_timing_mode,
            approval_provenance=approval_provenance,
            expiry_ts=expiry_ts,
            supersedes_id=supersedes_id,
            last_admission_ordinal=self.ledger.admission_ordinal,
            evidence_state=evidence_state,
        )
        if record.record_hash in self._lifecycle_record_hashes:
            raise ValueError("exact duplicate lifecycle fact")
        previous = self._latest_lifecycle_records.get(object_id)
        if object_id in self._lifecycle_ids:
            if previous is None:
                raise ValueError(
                    "latest lifecycle authority unavailable for existing object"
                )
            _validate_lifecycle_successor(previous, record)
        elif parent_id is not None and parent_id not in self._lifecycle_ids:
            raise ValueError("lifecycle parent identity is unknown")
        self._lifecycle_ids.add(object_id)
        self._lifecycle_record_hashes.add(record.record_hash)
        self._latest_lifecycle_records[object_id] = record
        self._lifecycle.append(record)
        if self.evidence_store is not None:
            self.evidence_store.append_lifecycle((record,))
        self._counts[f"lifecycle:{kind.value}"] += 1
        if decision_state is not None:
            self._counts[f"denominator:{decision_state.value}"] += 1
        if _persist_checkpoint:
            self._persist_if_configured(reason="LIFECYCLE_RECORDED")
        return record

    def terminal(
        self, *, package_id: str, terminal_ts: int, decision_state: DecisionState
    ) -> TailStatus:
        package = self._packages[package_id]
        if package.tail.terminal_ts is not None:
            raise ValueError("terminal Thesis state is immutable")
        package.terminal_decision = decision_state
        package.tail = TailStatus(
            package_id=package_id,
            terminal_ts=terminal_ts,
            micro_deadline_ts=terminal_ts + POST_TERMINAL_MICRO_NS,
            context_deadline_ts=terminal_ts + POST_TERMINAL_CONTEXT_NS,
            micro_phase=TailPhase.ACTIVE,
            context_phase=TailPhase.ACTIVE,
            evidence_state=package.predecision_state,
            reason_codes=("TERMINAL_REACHED", decision_state.value),
        )
        self._counts[f"terminal:{decision_state.value}"] += 1
        self._persist_if_configured(reason="TERMINAL_TAIL_STARTED")
        return package.tail

    def advance(self, *, now_ns: int) -> None:
        changed = False
        for package in self._packages.values():
            tail = package.tail
            if tail.terminal_ts is None:
                continue
            micro = tail.micro_phase
            context = tail.context_phase
            if tail.micro_deadline_ts is not None and now_ns >= tail.micro_deadline_ts:
                if micro is TailPhase.ACTIVE:
                    micro = TailPhase.COMPLETE
            if tail.context_deadline_ts is not None and now_ns >= tail.context_deadline_ts:
                if context is TailPhase.ACTIVE:
                    context = TailPhase.COMPLETE
            changed = changed or micro is not tail.micro_phase or context is not tail.context_phase
            package.tail = tail.model_copy(update={"micro_phase": micro, "context_phase": context})
        self._flush_if_full(force=True)
        if changed:
            self._persist_if_configured(reason="TAIL_PHASE_ADVANCED")

    def disconnect(self, *, reason: str) -> None:
        self.ledger.disconnect(reason=reason)
        self._counts[f"gap:{reason}"] += 1
        for package in self._packages.values():
            tail = package.tail
            if tail.terminal_ts is None or (
                tail.micro_phase is TailPhase.ACTIVE or tail.context_phase is TailPhase.ACTIVE
            ):
                package.tail = tail.model_copy(
                    update={
                        "micro_phase": (
                            TailPhase.INCOMPLETE
                            if tail.micro_phase is TailPhase.ACTIVE
                            else tail.micro_phase
                        ),
                        "context_phase": (
                            TailPhase.INCOMPLETE
                            if tail.context_phase is TailPhase.ACTIVE
                            else tail.context_phase
                        ),
                        "evidence_state": EvidenceState.GAPPED,
                        "reason_codes": (*tail.reason_codes, reason),
                    }
                )
                self._missingness[EvidenceState.GAPPED.value] += 1
        self._persist_if_configured(reason="PUBLIC_DATA_DISCONNECTED")

    def reconnect(
        self, *, required_streams: Iterable[tuple[str, DataKind]] = ()
    ) -> str:
        self._continuity_requirements = set(required_streams)
        epoch = self.ledger.reconnect()
        self._persist_if_configured(reason="PUBLIC_DATA_RECONNECTED_AWAITING_EVIDENCE")
        return epoch

    def establish_continuity(self) -> None:
        if self._continuity_requirements:
            raise RuntimeError("fresh subscribed stream evidence is still incomplete")
        self.ledger.establish_continuity()
        self._persist_if_configured(reason="CONTINUITY_ESTABLISHED")

    def await_continuity(
        self, *, required_streams: Iterable[tuple[str, DataKind]]
    ) -> None:
        if self.ledger.health is StreamHealth.REESTABLISHING:
            self._continuity_requirements = set(required_streams)

    def handle_socket_state(
        self,
        state: object,
        *,
        required_streams: Iterable[tuple[str, DataKind]],
    ) -> bool:
        """Map the public Nautilus socket-state callback into causal state.

        Nautilus remains the reconnect/resubscribe owner.  This observer only
        types loss and waits for fresh admitted evidence from every required
        subscription before restoring project continuity.
        """
        raw_name = getattr(state, "name", str(state))
        name = str(raw_name).rsplit(".", maxsplit=1)[-1].upper()
        if name == "DISCONNECTED":
            if self.ledger.health is not StreamHealth.DISCONNECTED:
                self.disconnect(reason="PUBLIC_DATA_SOCKET_DISCONNECTED")
                return True
            return False
        if name == "CONNECTED" and self.ledger.health is StreamHealth.DISCONNECTED:
            self.reconnect(required_streams=required_streams)
            return True
        return False

    def handle_socket_state_event(
        self,
        event: object,
        *,
        expected_client_id: object,
        required_streams: Iterable[tuple[str, DataKind]],
    ) -> bool:
        """Ignore other clients before mapping the provider socket state."""
        if getattr(event, "client_id", None) != expected_client_id:
            return False
        return self.handle_socket_state(
            getattr(event, "state", None),
            required_streams=required_streams,
        )

    @property
    def observed_streams(self) -> frozenset[tuple[str, DataKind]]:
        return frozenset(self._observed_streams)

    def strategy_evidence_state(self, *, package_id: str, ea3: bool) -> EvidenceState:
        state = self._packages[package_id].predecision_state
        if ea3 and state is not EvidenceState.COMPLETE:
            return EvidenceState.NOT_EVALUABLE
        return state

    def decision_commitment(self, package_id: str) -> tuple[int, DecisionState]:
        return self._decision_commitments[package_id]

    def _flush_if_full(
        self,
        *,
        force: bool = False,
        checkpoint_reason: str = "ADMISSION_BATCH_FLUSHED",
    ) -> None:
        if not self._pending or (not force and len(self._pending) < self.batch_size):
            return
        batch = tuple(self._pending)
        self._pending.clear()
        try:
            if self.raw_sink is not None:
                self.raw_sink.write(batch)
            if self.evidence_store is not None:
                self.evidence_store.append_admission_batch(batch)
            self._persist_if_configured(reason=checkpoint_reason)
        except Exception:
            self._storage_failures += 1
            self._missingness["STORAGE_WRITE_FAILURE"] += len(batch)
            raise

    def _queue_durable(self, events: Iterable[AdmittedEvent]) -> None:
        for event in events:
            if event.source_identity in self._durable_source_ids:
                continue
            self._durable_source_ids.add(event.source_identity)
            self._pending.append(event)

    def close(self) -> None:
        self._flush_if_full(force=True)

    def persist_durable_evidence(self, *, reason: str) -> None:
        """Flush retained facts and checkpoint them before a callback returns."""
        self._flush_if_full(force=True, checkpoint_reason=reason)

    def health_summary(self) -> dict[str, object]:
        return {
            "capture_counts": dict(sorted(self._counts.items())),
            "missingness_counts": dict(sorted(self._missingness.items())),
            "duplicates": self.ledger.duplicate_count,
            "out_of_order": self.ledger.out_of_order_count,
            "gaps": self.ledger.gap_count,
            "reconnects": self.ledger.reconnect_count,
            "storage_failures": self._storage_failures,
            "pending_batch_rows": len(self._pending),
            "process_epoch": self.ledger.process_epoch,
            "continuity_epoch": self.ledger.continuity_epoch,
            "stream_health": self.ledger.health.value,
            "continuity_requirements_remaining": len(self._continuity_requirements),
            "admission_epoch": self.ledger.admission_epoch,
            "last_admission_ordinal": self.ledger.admission_ordinal,
            "pit_snapshot_id": self.manifest.pit_snapshot_id,
            "last_source_ts_init": self._last_ts_init,
            "last_admission_ts": self._last_admission_ts,
            "max_admission_lag_ns": self._max_admission_lag_ns,
            "provider_subscription_headroom": "NOT_OBSERVABLE_IN_CURRENT_RC4_CALLBACK_SEAM",
        }

    def operational_artifacts(
        self, *, health_overrides: dict[str, object] | None = None
    ) -> dict[str, dict[str, object]]:
        health = self.health_summary()
        if health_overrides:
            health.update(health_overrides)
        prebuffer = {
            market_id: {
                "event_count": len(events),
                "first_admission_ts": None if not events else events[0].admission_ts,
                "last_admission_ts": None if not events else events[-1].admission_ts,
            }
            for market_id, events in sorted(self._prebuffers.items())
        }
        round_trip = (
            {
                "readable": False,
                "deterministic": False,
                "reason": "EVIDENCE_STORE_NOT_CONFIGURED",
            }
            if self.evidence_store is None
            else self.evidence_store.round_trip_proof()
        )
        return {
            "capture-source-counts.json": {
                "run_id": self.manifest.run_id,
                "counts": health["capture_counts"],
            },
            "causal-order-replay-proof.json": {
                "process_epoch": self.ledger.process_epoch,
                "continuity_epoch": self.ledger.continuity_epoch,
                "admission_epoch": self.ledger.admission_epoch,
                "last_admission_ordinal": self.ledger.admission_ordinal,
                "source_identity_rule": "MARKET_EXPRESSION_EVENT_CONTEXT_BOUND",
                "same_evidence_same_order": True,
                "late_retroactive_rewrite": False,
            },
            "duplicate-gap-reconnect-prebuffer.json": {
                "duplicates": self.ledger.duplicate_count,
                "gaps": self.ledger.gap_count,
                "reconnects": self.ledger.reconnect_count,
                "prebuffer": prebuffer,
                "tails": {
                    package_id: state.tail.model_dump(mode="json")
                    for package_id, state in sorted(self._packages.items())
                },
            },
            "missingness-not-evaluable-counts.json": {
                "counts": health["missingness_counts"]
            },
            "catalog-semantic-round-trip.json": round_trip,
            "capture-health-resource-freshness.json": health,
            "credential-negative-zero-write.json": {
                "real_exec_client_registered": False,
                "signing": False,
                "private_api": False,
                "exchange_write": False,
                "venue_submitted": False,
                "not_submitted": True,
            },
        }

    def write_operational_artifacts(
        self, *, health_overrides: dict[str, object] | None = None
    ) -> None:
        if self.evidence_store is None:
            raise RuntimeError("evidence store is required for operational artifacts")
        self._flush_if_full(force=True)
        self.evidence_store.write_operational_artifacts(
            self.operational_artifacts(health_overrides=health_overrides)
        )

    def interrupt(self, *, reason: str) -> None:
        """Type unfinished active windows without invalidating prior admitted facts."""
        for package in self._packages.values():
            tail = package.tail
            if tail.terminal_ts is None:
                package.tail = tail.model_copy(
                    update={
                        "evidence_state": EvidenceState.INTERRUPTED,
                        "reason_codes": (*tail.reason_codes, reason),
                    }
                )
                self._missingness[EvidenceState.INTERRUPTED.value] += 1
            elif tail.micro_phase is TailPhase.ACTIVE or tail.context_phase is TailPhase.ACTIVE:
                package.tail = tail.model_copy(
                    update={
                        "micro_phase": (
                            TailPhase.INCOMPLETE
                            if tail.micro_phase is TailPhase.ACTIVE
                            else tail.micro_phase
                        ),
                        "context_phase": (
                            TailPhase.INCOMPLETE
                            if tail.context_phase is TailPhase.ACTIVE
                            else tail.context_phase
                        ),
                        "evidence_state": EvidenceState.INTERRUPTED,
                        "reason_codes": (*tail.reason_codes, reason),
                    }
                )
                self._missingness[EvidenceState.INTERRUPTED.value] += 1
        self.close()
        self._persist_if_configured(reason=reason)

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": "E4_CAPTURE_SESSION_CHECKPOINT_V1",
            "ledger": self.ledger.checkpoint(),
            "lifecycle_ids": sorted(self._lifecycle_ids),
            "latest_lifecycle_records": {
                object_id: record.model_dump(mode="json")
                for object_id, record in sorted(self._latest_lifecycle_records.items())
            },
            "packages": {
                package_id: {
                    "market_id": package.market_id,
                    "expression_id": package.expression_id,
                    "opportunity_id": package.opportunity_id,
                    "thesis_id": package.thesis_id,
                    "predecision_state": package.predecision_state.value,
                    "tail": package.tail.model_dump(mode="json"),
                    "terminal_decision": (
                        None
                        if package.terminal_decision is None
                        else package.terminal_decision.value
                    ),
                }
                for package_id, package in self._packages.items()
            },
            "decision_commitments": {
                package_id: (ordinal, decision.value)
                for package_id, (ordinal, decision) in self._decision_commitments.items()
            },
            "durable_source_ids": sorted(self._durable_source_ids),
            "pending": [item.model_dump(mode="json") for item in self._pending],
            "counts": dict(self._counts),
            "missingness": dict(self._missingness),
            "storage_failures": self._storage_failures,
            "last_ts_init": self._last_ts_init,
            "last_admission_ts": self._last_admission_ts,
            "max_admission_lag_ns": self._max_admission_lag_ns,
            "observed_streams": [
                (market_id, data_kind.value)
                for market_id, data_kind in sorted(
                    self._observed_streams, key=lambda item: (item[0], item[1].value)
                )
            ],
        }

    def persist_runtime_checkpoint(self, *, reason: str) -> None:
        if self.evidence_store is None:
            raise RuntimeError("evidence store is required for runtime checkpointing")
        self._checkpoint_sequence += 1
        self.evidence_store.write_runtime_checkpoint(
            manifest=self.manifest,
            state=self.checkpoint(),
            segment_index=self._runtime_segment_index,
            checkpoint_sequence=self._checkpoint_sequence,
            reason=reason,
        )

    def _persist_if_configured(self, *, reason: str) -> None:
        if self.evidence_store is not None:
            self.persist_runtime_checkpoint(reason=reason)

    @classmethod
    def restart_from(
        cls,
        checkpoint: dict[str, Any],
        *,
        manifest: RunManifest,
        policy: SubscriptionPolicy,
        raw_sink: RawCatalogSink | None,
        evidence_store: EvidenceStore | None = None,
        batch_size: int = 128,
        process_epoch: str | None = None,
        continuity_epoch: str | None = None,
        admission_epoch: str | None = None,
        runtime_segment_index: int = 0,
        checkpoint_sequence: int = 0,
    ) -> CaptureSession:
        if checkpoint.get("schema_version") != "E4_CAPTURE_SESSION_CHECKPOINT_V1":
            raise ValueError("unsupported Capture session checkpoint")
        lifecycle_ids = set(checkpoint["lifecycle_ids"])
        raw_latest = checkpoint.get("latest_lifecycle_records")
        latest_lifecycle_records: dict[str, LifecycleRecord] | None = None
        if raw_latest is not None:
            if not isinstance(raw_latest, dict):
                raise ValueError("latest lifecycle checkpoint state must be an object")
            latest_lifecycle_records = {
                object_id: LifecycleRecord.model_validate(raw)
                for object_id, raw in raw_latest.items()
            }
        session = cls(
            manifest=manifest,
            policy=policy,
            raw_sink=raw_sink,
            evidence_store=evidence_store,
            batch_size=batch_size,
            seen_source_ids=set(checkpoint["ledger"]["seen_source_ids"]),
            seen_lifecycle_ids=lifecycle_ids,
            latest_lifecycle_records=latest_lifecycle_records,
            durable_source_ids=set(checkpoint["durable_source_ids"]),
            runtime_segment_index=runtime_segment_index,
            checkpoint_sequence=checkpoint_sequence,
        )
        session.ledger = CausalAdmissionLedger.restart_from(
            checkpoint["ledger"],
            process_epoch=process_epoch or manifest.process_epoch,
            continuity_epoch=continuity_epoch or manifest.continuity_epoch,
            admission_epoch=admission_epoch or manifest.admission_epoch,
        )
        packages = checkpoint["packages"]
        interrupted_packages = 0
        for package_id, raw in packages.items():
            tail = TailStatus.model_validate(raw["tail"])
            if (
                tail.terminal_ts is None
                or tail.micro_phase is TailPhase.ACTIVE
                or tail.context_phase is TailPhase.ACTIVE
            ):
                interrupted_packages += 1
                tail = tail.model_copy(
                    update={
                        "micro_phase": (
                            TailPhase.INCOMPLETE
                            if tail.micro_phase is TailPhase.ACTIVE
                            else tail.micro_phase
                        ),
                        "context_phase": (
                            TailPhase.INCOMPLETE
                            if tail.context_phase is TailPhase.ACTIVE
                            else tail.context_phase
                        ),
                        "evidence_state": EvidenceState.INTERRUPTED,
                        "reason_codes": (*tail.reason_codes, "PROCESS_RESTART"),
                    }
                )
            state = _PackageState(
                market_id=raw["market_id"],
                expression_id=raw["expression_id"],
                opportunity_id=raw["opportunity_id"],
                thesis_id=raw["thesis_id"],
                predecision_state=EvidenceState(raw["predecision_state"]),
                tail=tail,
                terminal_decision=(
                    None
                    if raw["terminal_decision"] is None
                    else DecisionState(raw["terminal_decision"])
                ),
            )
            session._packages[package_id] = state
            session._market_packages[state.market_id].add(package_id)
        session._decision_commitments = {
            package_id: (value[0], DecisionState(value[1]))
            for package_id, value in checkpoint["decision_commitments"].items()
        }
        session._pending = [AdmittedEvent.model_validate(item) for item in checkpoint["pending"]]
        session._counts = Counter(checkpoint["counts"])
        session._missingness = Counter(checkpoint["missingness"])
        session._storage_failures = int(checkpoint["storage_failures"])
        session._last_ts_init = checkpoint["last_ts_init"]
        session._last_admission_ts = checkpoint["last_admission_ts"]
        session._max_admission_lag_ns = int(checkpoint["max_admission_lag_ns"])
        # Probe/continuity observations are segment-local. Prior admitted facts
        # remain durable, but they cannot prove the new process is connected.
        session._observed_streams = set()
        session._missingness[EvidenceState.INTERRUPTED.value] += interrupted_packages
        return session


def recover_capture_session(
    *,
    manifest: RunManifest,
    policy: SubscriptionPolicy,
    raw_sink: RawCatalogSink | None,
    evidence_store: EvidenceStore,
    batch_size: int = 128,
) -> CaptureSession:
    """Start or fail-closed recover one runtime segment from portable evidence."""
    checkpoint = evidence_store.load_runtime_checkpoint(manifest)
    if checkpoint is None:
        session = CaptureSession(
            manifest=manifest,
            policy=policy,
            raw_sink=raw_sink,
            evidence_store=evidence_store,
            batch_size=batch_size,
        )
        evidence_store.append_process_segment(
            {
                "manifest_hash": manifest.manifest_hash,
                "run_id": manifest.run_id,
                "segment_index": 0,
                "process_epoch": manifest.process_epoch,
                "admission_epoch": manifest.admission_epoch,
                "continuity_epoch": manifest.continuity_epoch,
                "predecessor_checkpoint_hash": None,
            }
        )
        session.persist_runtime_checkpoint(reason="INITIAL_RUNTIME_START")
        return session

    state = deepcopy(checkpoint.state)
    persisted_admissions = evidence_store.load_admissions()
    persisted_source_ids = {item.source_identity for item in persisted_admissions}
    state["ledger"]["seen_source_ids"] = sorted(
        set(state["ledger"]["seen_source_ids"]) | persisted_source_ids
    )
    state["durable_source_ids"] = sorted(
        set(state["durable_source_ids"]) | persisted_source_ids
    )
    state["pending"] = [
        item
        for item in state["pending"]
        if item["source_identity"] not in persisted_source_ids
    ]
    persisted_lifecycle = evidence_store.load_lifecycle()
    (
        durable_latest,
        durable_lifecycle_ids,
        _,
        durable_hashes_by_object,
    ) = _fold_lifecycle_records(persisted_lifecycle, run_id=manifest.run_id)
    checkpoint_lifecycle_ids = set(state["lifecycle_ids"])
    raw_checkpoint_latest = state.get("latest_lifecycle_records")
    if raw_checkpoint_latest is not None:
        if not isinstance(raw_checkpoint_latest, dict):
            raise ValueError("latest lifecycle checkpoint state must be an object")
        checkpoint_latest = {
            object_id: LifecycleRecord.model_validate(raw)
            for object_id, raw in raw_checkpoint_latest.items()
        }
        if not set(checkpoint_latest) <= checkpoint_lifecycle_ids:
            raise ValueError("checkpoint latest lifecycle authority lacks lifecycle_id")
        for object_id, record in checkpoint_latest.items():
            if record.object_id != object_id:
                raise ValueError(
                    "checkpoint latest lifecycle key contradicts object identity"
                )
            if record.record_hash not in durable_hashes_by_object.get(object_id, set()):
                raise ValueError(
                    "checkpoint lifecycle authority contradicts durable append history"
                )
    if persisted_lifecycle:
        state["latest_lifecycle_records"] = {
            object_id: record.model_dump(mode="json")
            for object_id, record in sorted(durable_latest.items())
        }
    elif raw_checkpoint_latest:
        raise ValueError("checkpoint lifecycle authority lacks durable append history")
    state["lifecycle_ids"] = sorted(
        checkpoint_lifecycle_ids | durable_lifecycle_ids
    )
    segments = evidence_store.load_process_segments()
    if any(
        item.get("manifest_hash") != manifest.manifest_hash
        or item.get("run_id") != manifest.run_id
        for item in segments
    ):
        raise ValueError("process segment history contradicts immutable run identity")
    last_segment_index = -1 if not segments else int(segments[-1]["segment_index"])
    segment_index = max(checkpoint.segment_index, last_segment_index) + 1
    process_epoch = f"{manifest.process_epoch}.p{segment_index}"
    admission_epoch = f"{manifest.admission_epoch}.p{segment_index}"
    continuity_epoch = f"{manifest.continuity_epoch}.p{segment_index}"
    session = CaptureSession.restart_from(
        state,
        manifest=manifest,
        policy=policy,
        raw_sink=raw_sink,
        evidence_store=evidence_store,
        batch_size=batch_size,
        process_epoch=process_epoch,
        admission_epoch=admission_epoch,
        continuity_epoch=continuity_epoch,
        runtime_segment_index=segment_index,
        checkpoint_sequence=checkpoint.checkpoint_sequence,
    )
    evidence_store.append_process_segment(
        {
            "manifest_hash": manifest.manifest_hash,
            "run_id": manifest.run_id,
            "segment_index": segment_index,
            "process_epoch": process_epoch,
            "admission_epoch": admission_epoch,
            "continuity_epoch": continuity_epoch,
            "predecessor_checkpoint_hash": checkpoint.checkpoint_hash,
        }
    )
    session.persist_runtime_checkpoint(reason="PROCESS_RESTART_RECOVERY")
    return session


def denominator_states() -> frozenset[DecisionState]:
    return frozenset(DecisionState)


def preserve_decision_under_late_evidence(
    commitment: tuple[int, DecisionState], events: Iterable[AdmittedEvent]
) -> tuple[int, DecisionState]:
    """Late evidence is available only to future decisions, never historical rewrites."""
    for event in events:
        if event.admission_ordinal <= commitment[0]:
            raise ValueError("late-evidence set contains already-committed admission")
    return commitment
