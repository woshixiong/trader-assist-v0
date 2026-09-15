"""Deterministic causal admission and BBO continuity semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
    StreamHealth,
)


@dataclass(frozen=True)
class AdmissionOutcome:
    event: AdmittedEvent | None
    duplicate: bool


@dataclass(frozen=True)
class BboValidity:
    valid: bool
    health: StreamHealth
    continuity_epoch: str
    state_identity: str | None
    reason: str | None


class CausalAdmissionLedger:
    """Append-only arrival ordering with cross-reconnect replay deduplication."""

    def __init__(
        self,
        *,
        process_epoch: str,
        continuity_epoch: str,
        admission_epoch: str,
        seen_source_ids: set[str] | None = None,
    ) -> None:
        self.process_epoch = process_epoch
        self.continuity_epoch = continuity_epoch
        self.admission_epoch = admission_epoch
        self._continuity_root = continuity_epoch
        self._continuity_index = 0
        self._ordinal = 0
        self._largest_ts_event = 0
        self._seen = set() if seen_source_ids is None else set(seen_source_ids)
        self._health = StreamHealth.HEALTHY
        self._bbo: dict[tuple[str, str], BboValidity] = {}
        self.duplicate_count = 0
        self.out_of_order_count = 0
        self.gap_count = 0
        self.reconnect_count = 0

    @property
    def admission_ordinal(self) -> int:
        return self._ordinal

    @property
    def seen_source_ids(self) -> frozenset[str]:
        return frozenset(self._seen)

    @property
    def health(self) -> StreamHealth:
        return self._health

    def admit(self, source: SourceEvent, *, admission_ts: int) -> AdmissionOutcome:
        identity = source.replay_identity
        if identity in self._seen:
            self.duplicate_count += 1
            return AdmissionOutcome(event=None, duplicate=True)
        self._seen.add(identity)
        self._ordinal += 1
        out_of_order = source.ts_event < self._largest_ts_event
        if out_of_order:
            self.out_of_order_count += 1
        self._largest_ts_event = max(self._largest_ts_event, source.ts_event)
        continuity_state = (
            EvidenceState.COMPLETE
            if self._health is StreamHealth.HEALTHY
            else EvidenceState.GAPPED
        )
        event = AdmittedEvent.create(
            schema_version="E4_CAPTURE_V1",
            process_epoch=self.process_epoch,
            continuity_epoch=self.continuity_epoch,
            admission_epoch=self.admission_epoch,
            admission_ordinal=self._ordinal,
            admission_ts=admission_ts,
            source_identity=identity,
            out_of_order=out_of_order,
            continuity_state=continuity_state,
            source=source,
        )
        if source.data_kind is DataKind.BBO:
            key = (source.market_id, source.expression_id)
            self._bbo[key] = BboValidity(
                valid=self._health is StreamHealth.HEALTHY,
                health=self._health,
                continuity_epoch=self.continuity_epoch,
                state_identity=identity,
                reason=None if self._health is StreamHealth.HEALTHY else "CONTINUITY_AMBIGUOUS",
            )
        return AdmissionOutcome(event=event, duplicate=False)

    def disconnect(self, *, reason: str) -> None:
        self._health = StreamHealth.DISCONNECTED
        self.gap_count += 1
        self._invalidate_bbo(reason)

    def reconnect(self) -> str:
        self._continuity_index += 1
        self.continuity_epoch = f"{self._continuity_root}.r{self._continuity_index}"
        self._health = StreamHealth.REESTABLISHING
        self.reconnect_count += 1
        self._invalidate_bbo("RECONNECT_STATE_NOT_REESTABLISHED")
        return self.continuity_epoch

    def establish_continuity(self) -> None:
        self._health = StreamHealth.HEALTHY

    def bbo_validity(self, *, market_id: str, expression_id: str) -> BboValidity:
        return self._bbo.get(
            (market_id, expression_id),
            BboValidity(
                valid=False,
                health=self._health,
                continuity_epoch=self.continuity_epoch,
                state_identity=None,
                reason="BBO_STATE_NOT_ESTABLISHED",
            ),
        )

    def _invalidate_bbo(self, reason: str) -> None:
        self._bbo = {
            key: BboValidity(
                valid=False,
                health=self._health,
                continuity_epoch=self.continuity_epoch,
                state_identity=value.state_identity,
                reason=reason,
            )
            for key, value in self._bbo.items()
        }

    def checkpoint(self) -> dict[str, Any]:
        return {
            "process_epoch": self.process_epoch,
            "continuity_epoch": self.continuity_epoch,
            "admission_epoch": self.admission_epoch,
            "seen_source_ids": sorted(self._seen),
            "ordinal": self._ordinal,
            "largest_ts_event": self._largest_ts_event,
            "duplicate_count": self.duplicate_count,
            "out_of_order_count": self.out_of_order_count,
            "gap_count": self.gap_count,
            "reconnect_count": self.reconnect_count,
        }

    @classmethod
    def restart_from(
        cls,
        checkpoint: dict[str, Any],
        *,
        process_epoch: str,
        admission_epoch: str,
        continuity_epoch: str,
    ) -> CausalAdmissionLedger:
        ledger = cls(
            process_epoch=process_epoch,
            continuity_epoch=continuity_epoch,
            admission_epoch=admission_epoch,
            seen_source_ids=set(checkpoint["seen_source_ids"]),
        )
        ledger._ordinal = int(checkpoint["ordinal"])
        ledger._largest_ts_event = int(checkpoint["largest_ts_event"])
        ledger.duplicate_count = int(checkpoint["duplicate_count"])
        ledger.out_of_order_count = int(checkpoint["out_of_order_count"])
        ledger.gap_count = int(checkpoint["gap_count"]) + 1
        ledger.reconnect_count = int(checkpoint["reconnect_count"]) + 1
        # A new process can never inherit an uninterrupted transport claim.
        # Provider-owned reconnect/replay must produce fresh subscribed data
        # before the project ledger returns to HEALTHY.
        ledger._health = StreamHealth.REESTABLISHING
        return ledger
