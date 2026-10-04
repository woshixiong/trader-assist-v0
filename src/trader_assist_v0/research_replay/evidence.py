"""Read-only projections composed outside Package A's raw authority namespace."""

from pathlib import Path

from trader_assist_v0.multi_asset_shadow.shadow_records.records import (
    Candidate,
    FormalizationDisposition,
    FormalSignal,
    ImmutableRecord,
    MarketEvent,
    ScannerEvidence,
    StrategyEvaluation,
)
from trader_assist_v0.nautilus_e4.contracts import AdmittedEvent
from trader_assist_v0.nautilus_e4.storage import EvidenceStore
from trader_assist_v0.research_data.admission import AdmissionObservation
from trader_assist_v0.research_data.contracts import DatasetManifest
from trader_assist_v0.research_data.storage import ReferenceReplayReader

from .contracts import EvidenceRef, Observation, Opportunity


def require_pipeline(dataset: DatasetManifest) -> DatasetManifest:
    checked = DatasetManifest.model_validate_json(dataset.model_dump_json())
    checked.require_access("PIPELINE_CORRECTNESS_ONLY")
    return checked


def bind_domain_records(
    opportunity: Opportunity,
    records: tuple[ImmutableRecord, ...],
    dataset: DatasetManifest,
) -> Opportunity:
    """Retain lawful original domain IDs/hashes without manufacturing a FormalSignal."""
    require_pipeline(dataset)
    opportunity = Opportunity.model_validate_json(opportunity.model_dump_json())
    supported = {
        MarketEvent,
        ScannerEvidence,
        Candidate,
        StrategyEvaluation,
        FormalSignal,
        FormalizationDisposition,
    }
    refs: dict[str, ImmutableRecord] = {}
    for record in records:
        if type(record) not in supported:
            raise ValueError("unsupported domain evidence owner")
        checked = type(record).create(identity=record.identity, **record.payload)
        if checked.record_id != record.record_id or checked.canonical_hash != record.canonical_hash:
            raise ValueError("domain record identity mismatch")
        if checked.payload.get("market_id", opportunity.market_id) != opportunity.market_id:
            raise ValueError("domain market mismatch")
        if checked.record_type in refs:
            raise ValueError("ambiguous domain record")
        refs[checked.record_type] = checked
    if "market_event" not in refs or refs["market_event"].record_id != opportunity.market_event_id:
        raise ValueError("retained MarketEvent required; do not fabricate missing opportunity")
    updates: dict[str, object] = {}
    for kind, field in (
        ("scanner_evidence", "scanner_id"),
        ("strategy_evaluation", "evaluation_id"),
        ("formal_signal", "formal_signal_id"),
        ("formalization_disposition", "disposition_id"),
    ):
        existing = getattr(opportunity, field)
        linked = refs.get(kind)
        if existing is not None and (linked is None or linked.record_id != existing):
            raise ValueError("original domain identifier mismatch")
        if linked:
            updates[field] = linked.record_id
    signal = refs.get("formal_signal")
    if signal and (
        signal.payload["market_event_id"] != opportunity.market_event_id
        or signal.payload["setup_family"] != opportunity.setup
        or signal.payload["side"] != opportunity.side
    ):
        raise ValueError("FormalSignal opportunity lineage mismatch")
    updates["domain_hashes"] = tuple(r.canonical_hash for r in records)
    return Opportunity.create(**{**opportunity.model_dump(exclude={"record_hash"}), **updates})


def read_external(
    reader: ReferenceReplayReader, path: Path, checksum: str, registry_hash: str
) -> tuple[Observation, ...]:
    require_pipeline(reader.admission.dataset)
    return tuple(
        project_external(reader, raw, registry_hash)
        for raw in reader.read(path, checksum)
        if raw.admitted and not raw.duplicate
    )


def project_external(
    reader: ReferenceReplayReader, raw: AdmissionObservation, registry_hash: str
) -> Observation:
    ds = require_pipeline(reader.admission.dataset)
    raw = AdmissionObservation.model_validate_json(raw.model_dump_json())
    event = reader.admission.validate(raw.event, raw.evaluated_at_ns)
    if not raw.admitted or raw.duplicate:
        raise ValueError("only admitted unique facts are projected")
    mapping = reader.admission.resolver.resolve(
        event.provider,
        event.instrument_id,
        event.timestamps.ts_event,
        raw.evaluated_at_ns,
        production=reader.admission.production,
    )
    p = event.payload
    flat: tuple[tuple[str, str], ...]
    values = p.model_dump(mode="json")
    values.pop("kind")
    # Preserve nested depth rather than rebuilding provider books.
    if p.kind == "DEPTH":
        from trader_assist_v0.contracts.common import canonical_json_bytes

        flat = (("native_depth", canonical_json_bytes(values).decode()),)
    else:
        flat = tuple(sorted((k, str(v)) for k, v in values.items() if v is not None))
    ref = EvidenceRef.create(
        version="B_INPUT_V1",
        owner="EXTERNAL_REFERENCE",
        source_hash=event.record_hash,
        dataset_hash=ds.record_hash,
        mapping_hash=event.mapping_hash,
        interval_hash=mapping.record_hash,
        registry_hash=registry_hash,
        provider=event.provider,
        instrument=event.instrument_id,
        expression=mapping.association or event.instrument_id,
        price_unit=mapping.price_unit,
        size_unit=mapping.size_unit,
        source_mode=event.source_mode,
        source_tier=ds.source_tier,
        exposure_state=ds.exposure_state,
        capability_hash=event.capability_hash,
        rights_hash=event.rights_hash,
        source_locator=ds.source_locator,
        valid_from=mapping.valid_from,
        valid_to=mapping.valid_to,
        mapping_known_at=mapping.known_at,
        mapping_recorded_at=mapping.recorded_at,
        coverage_start=ds.start_ns,
        coverage_end=ds.end_ns,
    )
    ts = event.timestamps
    return Observation.create(
        version="B_OBSERVATION_V1",
        evidence=ref,
        kind=p.kind,
        ts_event=ts.ts_event,
        known_at=max(ts.observed_at_ns, raw.evaluated_at_ns),
        ts_init=ts.ts_init,
        ts_receive=ts.true_network_receive_ts,
        ordinal=raw.ordinal,
        continuity_epoch="EXTERNAL_ACCEPTED_LEDGER",
        quality=tuple(raw.quality.states),
        values=flat,
        bar_end=p.end_ns if p.kind == "BAR" else None,
        receive_provenance=ts.receive_provenance,
    )


def read_e4(
    store: EvidenceStore,
    dataset: DatasetManifest,
    expected_manifest: str,
    expected_snapshot: str,
    registry_hash: str,
) -> tuple[Observation, ...]:
    ds = require_pipeline(dataset)  # before manifest/catalog/market evidence I/O
    manifest = store.load_manifest()
    snapshot = store.load_snapshot()
    if manifest.manifest_hash != expected_manifest or snapshot.snapshot_hash != expected_snapshot:
        raise ValueError("E4 manifest/PIT binding mismatch")
    if manifest.pit_snapshot_id != snapshot.snapshot_id:
        raise ValueError("E4 manifest snapshot mismatch")
    expressions = {e.instrument_id: e for e in snapshot.expressions}
    result = []
    for event in store.load_admissions():
        raw = AdmittedEvent.model_validate_json(event.model_dump_json())
        source = raw.source
        expression = expressions.get(source.instrument_id)
        if expression is None or expression.market_id != source.market_id:
            raise ValueError("E4 event outside PIT expression")
        if source.instrument_id not in ds.instruments:
            raise ValueError("E4 event outside dataset instruments")
        if not ds.start_ns <= source.ts_event < ds.end_ns:
            raise ValueError("E4 event outside authorized cut")
        ref = EvidenceRef.create(
            version="B_INPUT_V1",
            owner="HL_E4",
            source_hash=raw.admission_hash,
            dataset_hash=ds.record_hash,
            mapping_hash=snapshot.snapshot_hash,
            interval_hash=expression.instrument_metadata_hash,
            registry_hash=registry_hash,
            provider=source.provider_id,
            instrument=source.instrument_id,
            expression=source.market_id,
            price_unit="NATIVE_PRICE",
            size_unit="NATIVE_SIZE",
            source_mode="LIVE",
            source_tier=ds.source_tier,
            exposure_state=ds.exposure_state,
            source_locator=ds.source_locator,
            rights_hash=ds.rights.record_hash if ds.rights else None,
            valid_from=snapshot.observed_at_ns,
            valid_to=ds.end_ns,
            mapping_known_at=snapshot.observed_at_ns,
            mapping_recorded_at=snapshot.observed_at_ns,
            coverage_start=ds.start_ns,
            coverage_end=ds.end_ns,
        )
        payload = dict(source.payload)
        if source.data_kind.value == "BBO":
            payload["bid"] = payload.pop("bid_price")
            payload["ask"] = payload.pop("ask_price")
        if source.data_kind.value == "TRADE":
            payload["aggressor"] = source.provider_aggressor_side
        if source.data_kind.value == "BAR" and payload.get("finalized") is not True:
            raise ValueError("unfinalized E4 bar")
        kind = "DEPTH" if source.data_kind.value == "DEPTH10" else source.data_kind.value
        values: tuple[tuple[str, str], ...]
        if kind == "DEPTH":
            from trader_assist_v0.contracts.common import canonical_json_bytes

            values = (("native_depth", canonical_json_bytes(payload).decode()),)
        else:
            values = tuple(sorted((k, str(v)) for k, v in payload.items() if v is not None))
        result.append(
            Observation.create(
                version="B_OBSERVATION_V1",
                evidence=ref,
                kind=kind,
                ts_event=source.ts_event,
                known_at=raw.admission_ts,
                ts_init=source.ts_init,
                ts_receive=source.true_network_receive_ts,
                ordinal=raw.admission_ordinal,
                continuity_epoch=raw.continuity_epoch,
                quality=(raw.continuity_state.value,),
                values=values,
                bar_end=source.ts_event if kind == "BAR" else None,
                receive_provenance="PROVIDER_EXPOSED"
                if source.true_network_receive_ts
                else "NOT_EXPOSED",
            )
        )
    return tuple(result)
