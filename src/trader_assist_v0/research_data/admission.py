"""Deterministic external evidence admission and quality; no E4 authority."""

from pydantic import Field

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .contracts import (
    BoundRecord,
    CapabilityState,
    DatasetManifest,
    ExternalReferenceEvent,
    ProviderCapability,
    ReferenceQuality,
    SourceMode,
)
from .mapping import PitReferenceResolver


def event_datatype(event: ExternalReferenceEvent) -> str:
    payload = event.payload
    if payload.kind == "BAR":
        return f"BAR_{payload.interval_minutes}M"
    if payload.kind == "CONTEXT":
        return payload.field
    if payload.kind == "DEPTH":
        return payload.shape
    return payload.kind


class AdmissionPolicy(BoundRecord):
    stale_after_ns: int = Field(gt=0)
    sequence_semantics: str = Field(pattern="^(CONTIGUOUS|UNKNOWN)$")
    max_observations: int = Field(gt=0, le=100_000)


class AdmissionObservation(BoundRecord):
    ordinal: int = Field(ge=0)
    event: ExternalReferenceEvent
    admitted: bool
    duplicate: bool
    out_of_order: bool
    evaluated_at_ns: int = Field(gt=0)
    quality: ReferenceQuality


class ExternalReferenceAdmission:
    def __init__(
        self,
        dataset: DatasetManifest,
        resolver: PitReferenceResolver,
        capabilities: tuple[ProviderCapability, ...],
        policy: AdmissionPolicy,
        *,
        production: bool = True,
        satisfied: frozenset[str] = frozenset(),
    ) -> None:
        self.dataset = DatasetManifest.model_validate_json(dataset.model_dump_json())
        self.resolver = resolver
        self.policy = AdmissionPolicy.model_validate_json(policy.model_dump_json())
        self.capabilities = tuple(
            ProviderCapability.model_validate_json(c.model_dump_json()) for c in capabilities
        )
        self.production = production
        self.satisfied = satisfied
        self.dataset.require_access("PIPELINE_CORRECTNESS_ONLY", satisfied)
        if self.dataset.mapping_hash != resolver.snapshot.record_hash:
            raise ValueError("dataset mapping binding mismatch")
        keys = [
            (c.provider, c.venue, c.product, c.source_mode, c.datatype) for c in self.capabilities
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate capability matrix key")
        for capability in self.capabilities:
            capability.require_core_proof()

    def validate(self, event: ExternalReferenceEvent, knowledge_ns: int) -> ExternalReferenceEvent:
        event = ExternalReferenceEvent.model_validate_json(event.model_dump_json())
        self.dataset.require_access("PIPELINE_CORRECTNESS_ONLY", self.satisfied)
        rights = self.dataset.rights
        assert rights is not None
        if (
            event.dataset_hash != self.dataset.record_hash
            or event.rights_hash != rights.record_hash
            or event.mapping_hash != self.resolver.snapshot.record_hash
        ):
            raise ValueError("external event evidence binding mismatch")
        if event.instrument_id not in self.dataset.instruments or event.venue != self.dataset.venue:
            raise ValueError("event outside dataset identity")
        if not self.dataset.start_ns <= event.timestamps.ts_event < self.dataset.end_ns:
            raise ValueError("event outside dataset cut")
        mapping = self.resolver.resolve(
            event.provider,
            event.instrument_id,
            event.timestamps.ts_event,
            knowledge_ns,
            production=self.production,
        )
        if mapping.product != event.product or mapping.venue != event.venue:
            raise ValueError("event mapping product/venue mismatch")
        datatype = event_datatype(event)
        matches = [
            c
            for c in self.capabilities
            if (c.provider, c.venue, c.product, c.source_mode, c.datatype)
            == (event.provider, event.venue, event.product, event.source_mode, datatype)
        ]
        if len(matches) != 1 or matches[0].record_hash != event.capability_hash:
            raise ValueError("missing exact capability binding; no provider substitution")
        capability = matches[0]
        capability.require_core_proof()
        if capability.adapter_state != CapabilityState.AVAILABLE_VERIFIED or not capability.enabled:
            raise ValueError("capability not enabled/verified")
        if datatype not in self.dataset.datatypes:
            raise ValueError("datatype outside dataset")
        return event


class ExternalReferenceLedger:
    """Bounded evidence annotations, not a reconnect or order-book engine."""

    def __init__(self, admission: ExternalReferenceAdmission) -> None:
        self.admission = admission
        self.observations: list[AdmissionObservation] = []
        self._seen: dict[tuple[str, ...], str] = {}
        self._latest: dict[tuple[str, ...], ExternalReferenceEvent] = {}
        self._quality: dict[tuple[str, ...], tuple[CapabilityState, ...]] = {}

    def observe(
        self, event: ExternalReferenceEvent, *, evaluated_at_ns: int
    ) -> AdmissionObservation:
        if len(self.observations) >= self.admission.policy.max_observations:
            raise ValueError("bounded observation limit exceeded")
        event = self.admission.validate(event, evaluated_at_ns)
        if evaluated_at_ns < event.timestamps.observed_at_ns:
            raise ValueError("evaluation predates observation")
        stream = (
            event.provider,
            event.venue,
            event.product,
            event.instrument_id,
            event.source_mode.value,
            event_datatype(event),
        )
        identity = (*stream, event.native_id)
        # Observation/init time differs for a repeated fact; preserve each observation separately.
        fact_hash = sha256_hex(
            canonical_json_bytes(
                {
                    "payload": event.payload.model_dump(mode="json"),
                    "sequence": event.sequence,
                    "source_ts": event.timestamps.source_ts,
                    "source_unit": event.timestamps.source_unit,
                }
            )
        )
        prior_hash = self._seen.get(identity)
        if prior_hash is not None and prior_hash != fact_hash:
            raise ValueError("conflicting native identity: INVALID_EVIDENCE")
        duplicate = prior_hash is not None
        previous = self._latest.get(stream)
        late = previous is not None and event.timestamps.ts_event < previous.timestamps.ts_event
        states: list[CapabilityState] = []
        if CapabilityState.GAP in self._quality.get(stream, ()):
            states.append(CapabilityState.GAP)
        if (
            event.source_mode == SourceMode.LIVE
            and evaluated_at_ns - event.timestamps.ts_event > self.admission.policy.stale_after_ns
        ):
            states.append(CapabilityState.STALE)
        if event.timestamps.ts_event > evaluated_at_ns:
            raise ValueError("event occurs after observation/evaluation")
        if self.admission.policy.sequence_semantics == "UNKNOWN" or event.sequence is None:
            states.append(CapabilityState.CONTINUITY_UNKNOWN)
        elif previous is not None and previous.sequence is not None and not duplicate:
            if event.sequence > previous.sequence + 1:
                if CapabilityState.GAP not in states:
                    states.append(CapabilityState.GAP)
            if event.sequence <= previous.sequence:
                late = True
        if not states:
            states.append(CapabilityState.AVAILABLE_VERIFIED)
        observation = AdmissionObservation.create(
            version="1",
            ordinal=len(self.observations),
            event=event,
            admitted=not duplicate,
            duplicate=duplicate,
            out_of_order=late,
            evaluated_at_ns=evaluated_at_ns,
            quality=ReferenceQuality(
                states=tuple(states), reason="recorded external evidence only"
            ),
        )
        self.observations.append(observation)
        if not duplicate:
            self._seen[identity] = fact_hash
            if not late:
                self._latest[stream] = event
                self._quality[stream] = observation.quality.states
        return observation

    def current(
        self, provider: str, instrument_id: str, datatype: str, *, evaluated_at_ns: int
    ) -> ReferenceQuality:
        matches = [
            (key, event)
            for key, event in self._latest.items()
            if key[0] == provider
            and key[3] == instrument_id
            and key[-1] == datatype
            and event.source_mode == SourceMode.LIVE
        ]
        if len(matches) != 1:
            return ReferenceQuality(
                states=(CapabilityState.RUNTIME_UNAVAILABLE,),
                reason="no unique live external observation",
            )
        key, event = matches[0]
        if evaluated_at_ns < event.timestamps.observed_at_ns:
            raise ValueError("evaluation predates observation")
        states: list[CapabilityState] = [
            s
            for s in self._quality[key]
            if s != CapabilityState.AVAILABLE_VERIFIED and s != CapabilityState.STALE
        ]
        if evaluated_at_ns - event.timestamps.ts_event > self.admission.policy.stale_after_ns:
            states.append(CapabilityState.STALE)
        return ReferenceQuality(
            states=tuple(states or [CapabilityState.AVAILABLE_VERIFIED]),
            reason="external quality/freshness only",
        )
