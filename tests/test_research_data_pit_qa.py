"""Synthetic/adversarial QA evidence only; no performance or production data."""

from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError
from test_research_data_contracts import H, dataset
from test_research_data_mapping import mapping, snapshot

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.research_data.contracts import (
    BarPayload,
    ExternalReferenceEvent,
    TimestampProvenance,
)
from trader_assist_v0.research_data.pit_qa import (
    AdjustmentEvidence,
    CorporateActionEvidence,
    EvidenceDisposition,
    HistoricalComparisonFact,
    HistoricalRevisionFact,
    HistoricalRowEvidence,
    LocalTimeEvidence,
    OutlierPolicy,
    PitQaPolicy,
    PitQaRequest,
    PitQaResult,
    QaEvidenceRef,
    QaStatus,
    RevisionState,
    RowEvidenceKey,
    RowProjectionProof,
    SessionInterval,
    SessionScheduleEvidence,
    SourceBindingEvidence,
    UniverseEvidence,
    _aggregate_status,
    _digest,
    _project_diagnostic_records,
    evaluate_pit_qa,
    normalize_local_timestamp,
    qa_rows_from_events,
)

S = 1_704_067_200_000_000_000
STEP = 60_000_000_000
END = S + 2 * STEP
K = END + 1_000_000_000_000
RAW = b"synthetic supplied source, two one-minute bars"
CHECKSUM = sha256_hex(RAW)


def replace_bound(record, **changes):
    fields = record.model_dump()
    fields.pop("record_hash")
    fields.update(changes)
    return type(record).create(**fields)


def ref(name="assertion", **changes):
    fields = dict(
        locator=f"synthetic://{name}",
        content_hash=H,
        kind=name,
        version="toy-v1",
        known_at_ns=S - 10,
        recorded_at_ns=END + 1,
    )
    fields.update(changes)
    return QaEvidenceRef(**fields)


def fixture():
    m = mapping(
        native_symbol="NATIVE-OLD",
        instrument_id="STABLE-ID",
        product="EQUITY",
        price_unit="USD",
        size_unit="SHARES",
        source_role="RESEARCH_IMPORT",
        valid_from=S,
        valid_to=END,
        known_at=S - 10,
        recorded_at=S - 9,
    )
    maps = snapshot(m)
    universe = UniverseEvidence.create(
        version="toy-v1",
        evidence=ref("universe"),
        basis="SYNTHETIC",
        start_ns=S,
        end_ns=END,
        complete=True,
        survivorship_limits="complete synthetic roster only",
        membership=(("STABLE-ID", S, END, "LISTED"),),
    )
    outlier = OutlierPolicy.create(
        version="toy-v1",
        evidence=ref("bounds"),
        price_unit="USD",
        minimum_price="1",
        maximum_price="1000",
        maximum_adjacent_relative_change="1",
        compare_across_sessions=False,
        severity="FAIL",
    )
    policy = PitQaPolicy.create(
        version="toy-v1",
        evidence=ref("policy"),
        duplicate_severity="WARN",
        missing_bar_severity="FAIL",
        sequence_semantics="NOT_APPLICABLE",
        revision_policy="VALIDATE_CHAIN",
        disagreement_severity="WARN",
        comparison_tolerance="0.01",
        adjustment_tolerance="0.000001",
        outlier=outlier,
        max_rows=100,
        max_expected_intervals=100,
    )
    sessions = SessionScheduleEvidence.create(
        version="toy-v1",
        evidence=ref("sessions"),
        calendar_version="supplied-toy-calendar-v1",
        timezone="UTC",
        start_ns=S,
        end_ns=END,
        instrument_ids=("STABLE-ID",),
        complete=True,
        cadence_ns=STEP,
        grid_origin_ns=S,
        open_intervals=(
            SessionInterval(
                instrument_id="STABLE-ID",
                session_id="toy-session",
                session_class="REGULAR",
                open_ns=S,
                close_ns=END,
                evidence=ref("session"),
            ),
        ),
    )
    adjustment = AdjustmentEvidence.create(
        version="toy-v1",
        evidence=ref("adjustment"),
        instrument_id="STABLE-ID",
        start_ns=S,
        end_ns=END,
        mode="UNADJUSTED",
        basis="raw-provider-v1",
        basis_ns=END,
        complete=True,
        price_unit="USD",
        size_unit="SHARES",
    )
    metadata = {k: "explicit synthetic declaration" for k, _ in dataset().metadata}
    metadata.update(
        symbol_mapping=maps.record_hash,
        session_calendar_version=sessions.calendar_version,
        missing_bar_policy="FAIL",
        duplicate_policy="WARN",
        provider_disagreement_policy="WARN",
        bad_tick_policy=outlier.record_hash,
        point_in_time_universe=universe.record_hash,
        corporate_action_policy="EXPLICIT_ACTION_COVERAGE",
        split_adjustment_policy="UNADJUSTED",
        delisting_status=universe.record_hash,
        trading_halt_status=universe.record_hash,
        data_revision_status="VALIDATE_CHAIN",
        timezone_dst_policy="EXPLICIT_FOLD_OFFSET_ROUNDTRIP",
        dividend_policy="NO_DIVIDEND_TRANSFORMATION_PROVEN",
    )
    manifest = dataset(
        source="BINANCE",
        venue="BINANCE",
        asset_class="EQUITY",
        instruments=("STABLE-ID",),
        start_ns=S,
        end_ns=END,
        resolution="1M",
        datatypes=("BAR_1M",),
        checksum=CHECKSUM,
        mapping_hash=maps.record_hash,
        metadata=tuple(sorted(metadata.items())),
    )
    events = tuple(
        ExternalReferenceEvent.create(
            version="toy-v1",
            provider="BINANCE",
            venue="BINANCE",
            product="EQUITY",
            instrument_id="STABLE-ID",
            mapping_hash=maps.record_hash,
            dataset_hash=manifest.record_hash,
            capability_hash=H,
            rights_hash=manifest.rights.record_hash,
            source_mode="HISTORY",
            native_id=f"bar-{n}",
            timestamps=TimestampProvenance(
                source_ts=str(S + n * STEP),
                source_unit="ns",
                ts_event=S + n * STEP,
                observed_at_ns=S + (n + 1) * STEP + 1,
                receive_provenance="NOT_EXPOSED",
            ),
            payload=BarPayload(
                interval_minutes=1,
                start_ns=S + n * STEP,
                end_ns=S + (n + 1) * STEP,
                timestamp_meaning="OPEN",
                aggregation_origin="provider",
                finalized=True,
                open="100",
                high="101",
                low="99",
                close="100",
                volume="10",
            ),
        )
        for n in range(2)
    )
    request = PitQaRequest(
        manifest=manifest,
        snapshot=maps,
        events=events,
        knowledge_ns=K,
        policy=policy,
        sessions=sessions,
        adjustments=(adjustment,),
        universe=universe,
        synthetic_fixture=True,
    )
    return evidence_for(request)


def evidence_for(request, **aux_changes):
    if request.events:
        projected = qa_rows_from_events(request.events, knowledge_ns=request.knowledge_ns)
    else:
        projected = _project_diagnostic_records(
            request.diagnostic_records or (), request.knowledge_ns, (), True
        )
    evidence = []
    proofs = []
    for row in projected.rows:
        proof = RowProjectionProof(
            key=row.key,
            source_locator=request.manifest.source_locator,
            source_content_hash=request.manifest.checksum,
            row_locator=f"synthetic://row/{row.ordinal}",
            copied_fields_hash=row.copied_fields_hash,
            evidence=ref("source", content_hash=request.manifest.checksum),
        )
        proofs.append(_digest(proof.model_dump(mode="json")))
        fields = dict(
            version="toy-v1",
            key=row.key,
            basis="SYNTHETIC",
            valid_from_ns=S,
            valid_to_ns=END,
            known_at_ns=END + 1,
            recorded_at_ns=END + 10,
            evidence=ref("historical-row"),
            native_symbol="NATIVE-OLD",
            adjustment_mode="UNADJUSTED",
            adjustment_basis="raw-provider-v1",
            price_unit="USD",
            size_unit="SHARES",
            source_role="RESEARCH_IMPORT",
            projection_proof=proof,
            finalized_at_ns=row.source.bar_end_ns,
            revision=HistoricalRevisionFact(
                state="UNREVISED",
                revision_id="r0",
                available_at_ns=END + 1,
                evidence=ref("unrevised"),
            ),
            comparison=HistoricalComparisonFact(
                disposition="EXPLICIT_NOT_APPLICABLE", evidence=ref("single-provider")
            ),
        )
        fields.update(aux_changes)
        evidence.append(HistoricalRowEvidence.create(**fields))
    binding = SourceBindingEvidence.create(
        version="toy-v1",
        evidence=ref("source", content_hash=request.manifest.checksum),
        dataset_hash=request.manifest.record_hash,
        source_locator=request.manifest.source_locator,
        checksum=request.manifest.checksum,
        source_bytes_hex=RAW.hex(),
        projection_proof_hashes=tuple(proofs),
    )
    return request.model_copy(
        update=dict(historical_evidence=tuple(evidence), source_binding=binding)
    )


def diagnostic(request, **changes):
    sources = list(qa_rows_from_events(request.events, knowledge_ns=K).rows)
    records = [r.source for r in sources]
    records[0] = replace_bound(records[0], **changes)
    return evidence_for(
        request.model_copy(update=dict(events=None, diagnostic_records=tuple(records)))
    )


def result(request):
    return evaluate_pit_qa(request)


def codes(request):
    return {f.reason_code for d in result(request).domains for f in d.findings}


def update_aux(request, index=0, **changes):
    records = list(request.historical_evidence)
    records[index] = replace_bound(records[index], **changes)
    return request.model_copy(update={"historical_evidence": tuple(records)})


def with_manifest(request, **changes):
    manifest = replace_bound(request.manifest, **changes)
    if request.events:
        events = tuple(replace_bound(e, dataset_hash=manifest.record_hash) for e in request.events)
        request = request.model_copy(update={"manifest": manifest, "events": events})
    else:
        records = tuple(
            replace_bound(r, dataset_hash=manifest.record_hash) for r in request.diagnostic_records
        )
        request = request.model_copy(update={"manifest": manifest, "diagnostic_records": records})
    return evidence_for(request)


def test_complete_synthetic_pass():
    observed = result(fixture())
    assert observed.overall_qa_eligibility == QaStatus.PASS
    assert len(observed.domains) == 6 and all(d.status == QaStatus.PASS for d in observed.domains)
    assert observed.coverage[0].expected == observed.coverage[0].present_unique == 2
    assert observed.access_permission_granted is False


def test_event_only_projection_is_lossless_and_incomplete():
    req = fixture()
    projection = qa_rows_from_events(req.events, knowledge_ns=K)
    assert projection.rows[0].key.input_record_hash == req.events[0].record_hash
    assert projection.rows[0].source.values == tuple(
        (k, getattr(req.events[0].payload, k)) for k in ("open", "high", "low", "close", "volume")
    )
    assert all(r.historical is None and r.native_symbol is None for r in projection.rows)
    incomplete = result(req.model_copy(update={"historical_evidence": ()}))
    assert all(d.status != QaStatus.PASS for d in incomplete.domains if d.domain.value in "ABCDF")


def test_instrument_id_never_substitutes_native_symbol():
    req = fixture()
    assert req.events[0].instrument_id != req.historical_evidence[0].native_symbol
    assert "C_NATIVE_SYMBOL_EVIDENCE_MISSING" in codes(update_aux(req, native_symbol=None))


def test_metadata_cannot_fill_bridge_facts():
    req = fixture().model_copy(update={"historical_evidence": ()})
    assert "C_NATIVE_SYMBOL_EVIDENCE_MISSING" in codes(req)
    assert "B_ROW_ADJUSTMENT_UNKNOWN" in codes(req)
    assert "D_REVISION_EVIDENCE_MISSING" in codes(req)


@pytest.mark.parametrize(
    "change,reason",
    [
        (
            {
                "key": RowEvidenceKey(
                    input_kind="PACKAGE_A_EVENT", dataset_hash=H, input_record_hash=H
                )
            },
            "F_AUX_KEY_UNMATCHED",
        ),
        ({"projection_proof": None}, "F_ROW_PROJECTION_EVIDENCE_MISSING"),
    ],
)
def test_auxiliary_binding_integrity(change, reason):
    assert reason in codes(update_aux(fixture(), **change))


@pytest.mark.parametrize(
    "changes",
    [
        {"known_at_ns": K + 1, "recorded_at_ns": K + 2},
        {"recorded_at_ns": S - 20},
        {"valid_from_ns": END},
        {"valid_to_ns": S},
        {"valid_from_ns": END, "valid_to_ns": S},
    ],
)
def test_auxiliary_historical_causality(changes):
    assert "F_AUX_CAUSAL_OR_VALIDITY_CONFLICT" in codes(update_aux(fixture(), **changes))


def test_auxiliary_duplicate_and_conflict():
    req = fixture()
    duplicate = req.model_copy(
        update={"historical_evidence": (*req.historical_evidence, req.historical_evidence[0])}
    )
    assert "F_AUX_EXACT_DUPLICATE" in codes(duplicate)
    assert result(duplicate).overall_qa_eligibility == QaStatus.WARN
    conflict = req.model_copy(
        update={
            "historical_evidence": (
                *req.historical_evidence,
                replace_bound(req.historical_evidence[0], native_symbol="OTHER"),
            )
        }
    )
    assert "F_AUX_CONFLICT" in codes(conflict)
    assert result(conflict).overall_qa_eligibility == QaStatus.FAIL


@pytest.mark.parametrize(
    "field,reason",
    [
        ("native_symbol", "C_NATIVE_SYMBOL_EVIDENCE_MISSING"),
        ("adjustment_mode", "B_ROW_ADJUSTMENT_UNKNOWN"),
        ("adjustment_basis", "B_ROW_BASIS_MISSING"),
        ("revision", "D_REVISION_EVIDENCE_MISSING"),
        ("comparison", "D_COMPARISON_EVIDENCE_MISSING"),
        ("price_unit", "C_ROW_UNITS_ROLE_EVIDENCE_MISSING"),
        ("size_unit", "D_ROW_UNITS_EVIDENCE_MISSING"),
        ("source_role", "F_ROW_UNITS_ROLE_EVIDENCE_MISSING"),
        ("projection_proof", "F_ROW_PROJECTION_EVIDENCE_MISSING"),
        ("finalized_at_ns", "A_FINALITY_EVIDENCE_MISSING"),
    ],
)
def test_bridge_required_fact_matrix(field, reason):
    req = update_aux(fixture(), **{field: None})
    assert reason in codes(req)
    assert result(req).overall_qa_eligibility != QaStatus.PASS


def test_bridge_unknown_and_applicability():
    req = fixture()
    assert result(req).overall_qa_eligibility == QaStatus.PASS
    comparison = req.historical_evidence[0].comparison.model_copy(
        update={"disposition": EvidenceDisposition.UNKNOWN}
    )
    assert "D_COMPARISON_UNKNOWN" in codes(update_aux(req, comparison=comparison))
    with pytest.raises(ValidationError):
        replace_bound(req.historical_evidence[0], basis="PROSPECTIVE")


def test_auxiliary_cross_row_conflict():
    req = fixture()
    events = (
        req.events[0],
        replace_bound(
            req.events[0],
            timestamps=req.events[0].timestamps.model_copy(update={"observed_at_ns": END + 5}),
        ),
    )
    req = evidence_for(req.model_copy(update={"events": events}))
    assert "D_AUXILIARY_FACT_CONFLICT" in codes(update_aux(req, index=1, price_unit="EUR"))


def test_projection_recomputed_from_inputs():
    req = fixture()
    proof = req.historical_evidence[0].projection_proof.model_copy(update={"copied_fields_hash": H})
    assert "F_ROW_PROJECTION_BINDING_CONFLICT" in codes(update_aux(req, projection_proof=proof))
    with pytest.raises(ValidationError):
        PitQaRequest(
            **{**req.model_dump(), "projection": qa_rows_from_events(req.events, knowledge_ns=K)}
        )


@pytest.mark.parametrize(
    "wall,fold,status",
    [
        ("2024-03-10T02:30:00", None, "FAIL"),
        ("2024-11-03T01:30:00", None, "INSUFFICIENT_EVIDENCE"),
        ("2024-11-03T01:30:00", 0, "PASS"),
        ("2024-11-03T01:30:00", 1, "PASS"),
        ("2024-03-10T03:30:00", None, "PASS"),
    ],
)
def test_dst_and_local_time_resolution(wall, fold, status):
    assert (
        normalize_local_timestamp(
            LocalTimeEvidence(
                local_timestamp=wall, timezone="America/New_York", fold=fold, evidence=ref()
            )
        ).status.value
        == status
    )


def test_timezone_evidence_fail_closed(monkeypatch):
    value = LocalTimeEvidence(local_timestamp="2024-01-01T00:00:00", timezone="UTC", evidence=ref())
    assert (
        normalize_local_timestamp(value.model_copy(update={"offset_seconds": 100})).status
        == QaStatus.FAIL
    )
    assert (
        normalize_local_timestamp(value.model_copy(update={"timezone": "/invalid"})).status
        == QaStatus.FAIL
    )
    assert (
        normalize_local_timestamp(value.model_copy(update={"timezone": "No/Such_Zone"})).status
        != QaStatus.PASS
    )


def test_supplied_session_boundaries():
    req = fixture()
    records = tuple(
        replace_bound(
            r.source,
            event_ns=r.source.bar_end_ns,
            source_ts=str(r.source.bar_end_ns),
            timestamp_meaning="CLOSE",
        )
        for r in qa_rows_from_events(req.events, knowledge_ns=K).rows
    )
    # Expand the manifest cut one ns, while retaining explicitly supplied session close.
    close_req = evidence_for(req.model_copy(update={"events": None, "diagnostic_records": records}))
    assert "A_BAR_OUTSIDE_SESSION" not in codes(close_req)
    interval = req.sessions.open_intervals[0].model_copy(update={"close_ns": S + STEP // 2})
    sessions = replace_bound(req.sessions, open_intervals=(interval,))
    assert "A_BAR_OUTSIDE_SESSION" in codes(req.model_copy(update={"sessions": sessions}))


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"finalized_at_ns": S}, "A_FINALITY_CAUSAL_CONFLICT"),
        ({"finalized_at_ns": K + 1}, "A_FINALITY_CAUSAL_CONFLICT"),
    ],
)
def test_finality_and_causal_order(change, reason):
    assert reason in codes(update_aux(fixture(), **change))


def test_timestamp_precision():
    value = LocalTimeEvidence(
        local_timestamp="2024-01-01T00:00:00.000000123", timezone="UTC", evidence=ref()
    )
    assert normalize_local_timestamp(value).utc_ns == S + 123
    assert "A_SOURCE_TIMESTAMP_CONFLICT" in codes(diagnostic(fixture(), source_unit="ms"))


def with_maps(req, maps):
    metadata = dict(req.manifest.metadata)
    metadata["symbol_mapping"] = maps.record_hash
    manifest = replace_bound(
        req.manifest, mapping_hash=maps.record_hash, metadata=tuple(sorted(metadata.items()))
    )
    events = tuple(
        replace_bound(e, mapping_hash=maps.record_hash, dataset_hash=manifest.record_hash)
        for e in req.events
    )
    return evidence_for(
        req.model_copy(update={"manifest": manifest, "snapshot": maps, "events": events})
    )


def test_future_known_mapping():
    req = fixture()
    m = replace_bound(req.snapshot.records[0], known_at=K + 1, recorded_at=K + 2)
    assert "C_MAPPING_MISSING_AMBIGUOUS_OR_STATE" in codes(with_maps(req, snapshot(m)))


def test_ticker_reuse_boundaries():
    req = fixture()
    old = replace_bound(req.snapshot.records[0], valid_to=S + STEP)
    new = replace_bound(old, valid_from=S + STEP, valid_to=END, instrument_id="OTHER-ID")
    assert "C_MAPPING_MISSING_AMBIGUOUS_OR_STATE" in codes(with_maps(req, snapshot(old, new)))
    from trader_assist_v0.research_data.mapping import PitReferenceResolver

    resolver = PitReferenceResolver(snapshot(old, new))
    assert (
        resolver.resolve("BINANCE", "OTHER-ID", S + STEP, K, production=False).native_symbol
        == "NATIVE-OLD"
    )
    with pytest.raises(ValueError):
        resolver.resolve("BINANCE", "STABLE-ID", S + STEP, K, production=False)


def test_mapping_owner_fail_closed():
    req = fixture()
    with pytest.raises(ValueError):
        snapshot(req.snapshot.records[0], req.snapshot.records[0])
    ambiguous = replace_bound(req.snapshot.records[0], native_symbol="ANOTHER")
    assert "C_MAPPING_MISSING_AMBIGUOUS_OR_STATE" in codes(
        with_maps(req, snapshot(req.snapshot.records[0], ambiguous))
    )
    unsupported = replace_bound(req.snapshot.records[0], support_state="CAPABILITY_UNPROVEN")
    assert "C_MAPPING_SUPPORT_UNPROVEN" in codes(with_maps(req, snapshot(unsupported)))
    assert "F_BOUND_INPUT_INVALID" in codes(
        req.model_copy(update={"snapshot": req.snapshot.model_copy(update={"record_hash": H})})
    )


@pytest.mark.parametrize("state", ["HALTED", "DELISTED"])
def test_instrument_state_boundaries(state):
    req = fixture()
    universe = replace_bound(req.universe, membership=(("STABLE-ID", S, END, state),))
    assert "C_ROW_NOT_LISTED" in codes(req.model_copy(update={"universe": universe}))
    assert "C_ROW_STATE_EVIDENCE_MISSING" in codes(
        req.model_copy(update={"universe": replace_bound(req.universe, membership=())})
    )


def test_symbol_change_evidence():
    req = fixture()
    old = replace_bound(req.snapshot.records[0], valid_to=S + STEP)
    new = replace_bound(old, native_symbol="NEW-NATIVE", valid_from=S + STEP, valid_to=END)
    changed = update_aux(with_maps(req, snapshot(old, new)), index=1, native_symbol="NEW-NATIVE")
    assert "C_SYMBOL_CONTINUITY_MISSING" in codes(changed)
    universe = replace_bound(
        req.universe,
        continuity=(("STABLE-ID", "NATIVE-OLD", "NEW-NATIVE", S + STEP, ref("continuity")),),
    )
    assert "C_SYMBOL_CONTINUITY_MISSING" not in codes(
        changed.model_copy(update={"universe": universe})
    )


def test_survivorship_evidence():
    req = fixture()
    assert "C_UNIVERSE_INCOMPLETE" in codes(
        req.model_copy(update={"universe": replace_bound(req.universe, complete=False)})
    )
    assert "C_UNIVERSE_CAUSAL_CONFLICT" in codes(
        req.model_copy(
            update={
                "universe": replace_bound(
                    req.universe,
                    evidence=ref("current-roster", known_at_ns=K + 1, recorded_at_ns=K + 2),
                )
            }
        )
    )


def split_request(ratio="2", kind="SPLIT"):
    req = fixture()
    action = CorporateActionEvidence.create(
        version="toy-v1",
        evidence=ref("action"),
        instrument_id="STABLE-ID",
        action_id="split-1",
        kind=kind,
        effective_ns=S + STEP,
        known_at_ns=S - 10,
        recorded_at_ns=END + 1,
        ratio=ratio,
        price_treatment="BACKWARD_SPLIT",
        volume_treatment="SHARE_VOLUME",
    )
    factor = str(1 / float(ratio))
    rows = qa_rows_from_events(req.events, knowledge_ns=K).rows
    raw_pairs = tuple(
        (
            row.key.input_record_hash,
            str(100 * float(ratio)) if i == 0 else "100",
            str(10 / float(ratio)) if i == 0 else "10",
        )
        for i, row in enumerate(rows)
    )
    adjustment = replace_bound(
        req.adjustments[0],
        mode="SPLIT_ADJUSTED",
        basis="post-split",
        factors=(("split-1", factor, ratio),),
        raw_pairs=raw_pairs,
    )
    metadata = dict(req.manifest.metadata)
    metadata["split_adjustment_policy"] = "SPLIT_ADJUSTED"
    req = with_manifest(req, metadata=tuple(sorted(metadata.items())))
    rows = qa_rows_from_events(req.events, knowledge_ns=K).rows
    raw_pairs = tuple(
        (
            row.key.input_record_hash,
            str(100 * float(ratio)) if i == 0 else "100",
            str(10 / float(ratio)) if i == 0 else "10",
        )
        for i, row in enumerate(rows)
    )
    raw_fields = tuple(
        (
            e.record_hash,
            name,
            str(Decimal(getattr(e.payload, name)) * (Decimal(ratio) if n == 0 else 1)),
        )
        for n, e in enumerate(req.events)
        for name in ("open", "high", "low", "close")
    )
    adjustment = replace_bound(adjustment, raw_pairs=raw_pairs, raw_price_fields=raw_fields)
    req = req.model_copy(update={"actions": (action,), "adjustments": (adjustment,)})
    return evidence_for(req, adjustment_mode="SPLIT_ADJUSTED", adjustment_basis="post-split")


@pytest.mark.parametrize("ratio,kind", [("2", "SPLIT"), ("0.5", "REVERSE_SPLIT")])
def test_split_adjustment_semantics(ratio, kind):
    req = split_request(ratio, kind)
    assert result(req).overall_qa_eligibility == QaStatus.PASS
    bad = replace_bound(req.adjustments[0], factors=(("split-1", "1", ratio),))
    assert "B_FACTOR_CONFLICT" in codes(req.model_copy(update={"adjustments": (bad,)}))


def test_adjustment_mixing():
    assert "B_ADJUSTMENT_MIXING" in codes(update_aux(fixture(), adjustment_mode="SPLIT_ADJUSTED"))


def test_adjustment_requires_evidence():
    req = split_request()
    assert "B_RAW_ADJUSTED_PROOF_MISSING" in codes(
        req.model_copy(update={"adjustments": (replace_bound(req.adjustments[0], raw_pairs=()),)})
    )
    assert "B_ADJUSTMENT_COVERAGE_MISSING" in codes(
        fixture().model_copy(update={"adjustments": ()})
    )


def test_adjustment_basis_and_units():
    req = split_request()
    action = replace_bound(req.actions[0], volume_treatment="UNKNOWN")
    assert "B_VOLUME_TREATMENT_UNPROVEN" in codes(req.model_copy(update={"actions": (action,)}))
    action = replace_bound(req.actions[0], kind="DIVIDEND")
    assert "B_ACTION_TRANSFORMATION_UNPROVEN" in codes(
        req.model_copy(update={"actions": (action,)})
    )
    bad = replace_bound(req.adjustments[0], basis_ns=K + 1)
    assert "B_BASIS_TIME_CONFLICT" in codes(req.model_copy(update={"adjustments": (bad,)}))


def test_adjustment_causal_availability():
    req = split_request()
    action = replace_bound(req.actions[0], known_at_ns=K + 1, recorded_at_ns=K + 2)
    assert "B_ACTION_CAUSAL_CONFLICT" in codes(req.model_copy(update={"actions": (action,)}))


def test_duplicate_classification():
    req = fixture()
    duplicate = evidence_for(
        req.model_copy(update={"events": (req.events[0], req.events[0], req.events[1])})
    )
    assert "D_EXACT_DUPLICATE" in codes(duplicate)
    assert duplicate.events == (req.events[0], req.events[0], req.events[1])
    payload = req.events[0].payload.model_copy(update={"close": "101"})
    conflicting = evidence_for(
        req.model_copy(
            update={"events": (req.events[0], replace_bound(req.events[0], payload=payload))}
        )
    )
    assert "D_CONFLICTING_DUPLICATE" in codes(conflicting)


def test_fact_and_bar_identity():
    req = fixture()
    same = replace_bound(
        req.events[0],
        timestamps=req.events[0].timestamps.model_copy(update={"observed_at_ns": END + 5}),
    )
    assert "D_EXACT_DUPLICATE" in codes(
        evidence_for(req.model_copy(update={"events": (req.events[0], same)}))
    )
    different = replace_bound(req.events[0], native_id="second-native")
    assert "D_BAR_SLOT_CONFLICT" in codes(
        evidence_for(req.model_copy(update={"events": (req.events[0], different)}))
    )


@pytest.mark.parametrize(
    "value,reason",
    [
        ("NaN", "D_NONFINITE_OR_MALFORMED"),
        ("Infinity", "D_NONFINITE_OR_MALFORMED"),
        ("nonsense", "D_NONFINITE_OR_MALFORMED"),
        ("-1", "D_NONPOSITIVE_PRICE"),
        ("0", "D_NONPOSITIVE_PRICE"),
        ("1e999", "D_NONFINITE_OR_MALFORMED"),
    ],
)
def test_numeric_integrity(value, reason):
    values = tuple(
        (k, value if k == "close" else v)
        for k, v in qa_rows_from_events(fixture().events, knowledge_ns=K).rows[0].source.values
    )
    assert reason in codes(diagnostic(fixture(), values=values))


def test_payload_integrity():
    req = fixture()
    values = (("open", "100"), ("high", "90"), ("low", "99"), ("close", "100"), ("volume", "-1"))
    assert {"D_OHLC_CONFLICT", "D_NEGATIVE_SIZE"} <= codes(diagnostic(req, values=values))
    bbo = diagnostic(
        req,
        payload_kind="BBO",
        values=(("bid", "102"), ("ask", "101"), ("bid_size", "1"), ("ask_size", "1")),
    )
    assert "D_CROSSED_BBO" in codes(bbo)
    context = diagnostic(req, payload_kind="CONTEXT", values=(("value", "-0.01"),))
    assert "D_NONPOSITIVE_PRICE" not in codes(context)


def test_original_order_continuity():
    req = fixture()
    reverse = evidence_for(req.model_copy(update={"events": tuple(reversed(req.events))}))
    assert "A_TIMESTAMP_REVERSAL" in codes(reverse)
    assert "D_SEQUENCE_UNKNOWN" in codes(
        req.model_copy(update={"policy": replace_bound(req.policy, sequence_semantics="UNKNOWN")})
    )
    assert "D_SEQUENCE_EVIDENCE_MISSING" in codes(
        req.model_copy(
            update={"policy": replace_bound(req.policy, sequence_semantics="CONTIGUOUS")}
        )
    )


def test_revision_and_disagreement():
    req = fixture()
    revised = req.historical_evidence[0].revision.model_copy(
        update={"state": RevisionState.REVISED, "predecessor_input_hash": H}
    )
    assert "D_REVISION_CHAIN_CONFLICT" in codes(update_aux(req, revision=revised))
    comparison = req.historical_evidence[0].comparison.model_copy(
        update={
            "disposition": EvidenceDisposition.PRESENT,
            "comparison_group_id": "g1",
            "counterpart_input_hashes": (H,),
        }
    )
    assert "D_COMPARISON_COUNTERPART_MISSING" in codes(update_aux(req, comparison=comparison))


def test_outlier_policy_fail_closed():
    req = fixture()
    assert "D_OUTLIER_POLICY_UNKNOWN" in codes(
        req.model_copy(update={"policy": replace_bound(req.policy, outlier=None)})
    )
    bounds = replace_bound(req.policy.outlier, maximum_price="99")
    assert "D_OUTLIER_BOUND" in codes(
        req.model_copy(update={"policy": replace_bound(req.policy, outlier=bounds)})
    )


def test_gap_classification():
    req = fixture()
    missing = evidence_for(req.model_copy(update={"events": (req.events[0],)}))
    assert "E_IN_SESSION_MISSING" in codes(missing)
    assert result(missing).coverage[0].missing == 1
    opened = req.sessions.open_intervals[0].model_copy(update={"close_ns": S + STEP})
    closed = opened.model_copy(
        update={"open_ns": S + STEP, "close_ns": END, "session_id": "supplied-break"}
    )
    sessions = replace_bound(req.sessions, open_intervals=(opened,), closed_intervals=(closed,))
    explained = missing.model_copy(update={"sessions": sessions})
    assert "E_SESSION_EXPLAINED_GAP" in codes(explained)
    assert "E_IN_SESSION_MISSING" not in codes(explained)


def test_coverage_boundaries():
    req = fixture()
    assert "E_CALENDAR_COVERAGE_INCOMPLETE" in codes(
        req.model_copy(update={"sessions": replace_bound(req.sessions, complete=False)})
    )
    assert "E_PARTIAL_BOUNDARY" in codes(
        req.model_copy(update={"sessions": replace_bound(req.sessions, grid_origin_ns=S + 1)})
    )
    assert "E_ROW_GRID_OR_INTEGRITY_CONFLICT" in codes(diagnostic(req, bar_start_ns=S + 1))
    assert "E_CALENDAR_EVIDENCE_MISSING" in codes(req.model_copy(update={"sessions": None}))


@pytest.mark.parametrize(
    "changes", [{"events": ()}, {"events": None}, {"events": None, "diagnostic_records": ()}]
)
def test_no_vacuous_pass(changes):
    assert result(fixture().model_copy(update=changes)).overall_qa_eligibility != QaStatus.PASS


def test_provenance_completeness():
    req = fixture()
    for declaration, reason in [
        ("UNKNOWN: absent", "F_METADATA_UNKNOWN"),
        ("N/A: unproven", "F_METADATA_APPLICABILITY_UNPROVEN"),
    ]:
        metadata = dict(req.manifest.metadata)
        metadata["known_gaps"] = declaration
        assert reason in codes(with_manifest(req, metadata=tuple(sorted(metadata.items()))))
    with pytest.raises(ValidationError):
        replace_bound(req.manifest, metadata=())


def test_provenance_binding():
    req = fixture()
    assert "F_SOURCE_CHECKSUM_CONFLICT" in codes(
        req.model_copy(
            update={
                "source_binding": replace_bound(
                    req.source_binding, source_bytes_hex=b"tamper".hex()
                )
            }
        )
    )
    assert "F_SOURCE_BINDING_MISSING" in codes(req.model_copy(update={"source_binding": None}))
    proof = req.historical_evidence[0].projection_proof.model_copy(
        update={"source_locator": "synthetic://wrong"}
    )
    assert "F_PROJECTION_SOURCE_CONFLICT" in codes(update_aux(req, projection_proof=proof))


@pytest.mark.parametrize("status", list(QaStatus))
def test_fail_closed_aggregation(status):
    assert _aggregate_status((QaStatus.PASS, status)) == status
    assert _aggregate_status(()) == QaStatus.INSUFFICIENT_EVIDENCE
    assert _aggregate_status(tuple(QaStatus)) == QaStatus.FAIL


def test_deterministic_result():
    req = fixture()
    first = result(req)
    with localcontext() as ctx:
        ctx.prec = 3
        second = result(req)
    assert first.model_dump_json() == second.model_dump_json()
    assert PitQaResult.model_validate_json(first.model_dump_json()) == first
    assert result(update_aux(req, native_symbol=None)).record_hash != first.record_hash


def test_inputs_unchanged():
    req = fixture()
    before = canonical_json_bytes(req.model_dump(mode="json"))
    result(req)
    assert canonical_json_bytes(req.model_dump(mode="json")) == before


def test_pure_authority_and_performance_boundary(monkeypatch):
    req = fixture()
    import builtins

    def forbidden(*args, **kwargs):
        raise AssertionError("QA must not open supplied locators")

    # ZoneInfo has already resolved the supplied UTC zone in previous tests.
    monkeypatch.setattr(builtins, "open", forbidden)
    assert result(req).access_permission_granted is False
    with pytest.raises(ValidationError):
        PitQaRequest(**{**req.model_dump(), "sharpe": "1"})


def test_package_a_compatibility():
    req = fixture()
    before = tuple(e.model_dump_json() for e in req.events)
    manifest = req.manifest.model_dump_json()
    result(req)
    assert tuple(e.model_dump_json() for e in req.events) == before
    assert req.manifest.model_dump_json() == manifest
    with pytest.raises(PermissionError):
        req.manifest.require_access("PERFORMANCE")


def test_auxiliary_hash_and_envelope_binding():
    req = fixture()
    tampered = req.historical_evidence[0].model_copy(update={"record_hash": H})
    assert "F_BOUND_INPUT_INVALID" in codes(
        req.model_copy(update={"historical_evidence": (tampered,)})
    )
    # Knowledge inside a fact cannot be hidden behind an earlier envelope.
    comparison = HistoricalComparisonFact(
        disposition="EXPLICIT_NOT_APPLICABLE",
        evidence=ref("later-fact", known_at_ns=END + 2, recorded_at_ns=END + 3),
    )
    assert "F_AUX_ENVELOPE_AVAILABILITY_CONFLICT" in codes(update_aux(req, comparison=comparison))
    revised = HistoricalRevisionFact(
        state="UNREVISED", revision_id="r0", available_at_ns=K + 1, evidence=ref()
    )
    assert "D_REVISION_FUTURE_KNOWN" in codes(update_aux(req, revision=revised))
    assert "F_AUX_SYNTHETIC_NOT_AUTHORIZED" in codes(
        req.model_copy(update={"synthetic_fixture": False})
    )


def test_actual_row_clock_adversaries():
    req = fixture()
    for changes, expected in [
        ({"observed_at_ns": S - 1}, "A_CAUSAL_CLOCK_CONFLICT"),
        ({"receive_ns": K + 1}, "A_RECEIVE_CLOCK_CONFLICT"),
        ({"init_ns": S - 1}, "A_INIT_CLOCK_CONFLICT"),
        ({"source_ts": "bad"}, "A_SOURCE_TIMESTAMP_CONFLICT"),
        ({"timestamp_meaning": "CLOSE"}, "A_TIMESTAMP_MEANING_CONFLICT"),
        ({"finalized": False}, "A_BAR_NOT_FINAL"),
        ({"bar_end_ns": S}, "A_BAR_BOUNDARY_CONFLICT"),
    ]:
        assert expected in codes(diagnostic(req, **changes))


def test_close_at_cut_and_overnight_supplied_evidence():
    req = fixture()
    maps = snapshot(replace_bound(req.snapshot.records[0], valid_to=END + 1))
    req = with_maps(req, maps)
    sources = qa_rows_from_events(req.events, knowledge_ns=K).rows
    records = tuple(
        replace_bound(
            row.source,
            event_ns=row.source.bar_end_ns,
            source_ts=str(row.source.bar_end_ns),
            timestamp_meaning="CLOSE",
        )
        for row in sources
    )
    adjustment = replace_bound(req.adjustments[0], end_ns=END + 1)
    req = req.model_copy(
        update={"events": None, "diagnostic_records": records, "adjustments": (adjustment,)}
    )
    universe = replace_bound(req.universe, membership=(("STABLE-ID", S, END + 1, "LISTED"),))
    metadata = dict(req.manifest.metadata)
    for key in ("point_in_time_universe", "delisting_status", "trading_halt_status"):
        metadata[key] = universe.record_hash
    req = with_manifest(
        req.model_copy(update={"universe": universe}), metadata=tuple(sorted(metadata.items()))
    )
    req = evidence_for(req, valid_to_ns=END + 1)
    assert result(req).overall_qa_eligibility == QaStatus.PASS
    session = req.sessions.open_intervals[0].model_copy(
        update={
            "local_open": LocalTimeEvidence(
                local_timestamp="2023-12-31T19:00:00",
                timezone="America/New_York",
                evidence=ref("overnight-open"),
            ),
            "local_close": LocalTimeEvidence(
                local_timestamp="2023-12-31T19:02:00",
                timezone="America/New_York",
                evidence=ref("overnight-close"),
            ),
        }
    )
    assert "A_SESSION_LOCAL_BOUNDARY_CONFLICT" not in codes(
        req.model_copy(update={"sessions": replace_bound(req.sessions, open_intervals=(session,))})
    )


@pytest.mark.parametrize(
    "ratio,kind", [("0", "SPLIT"), ("NaN", "SPLIT"), ("0.5", "SPLIT"), ("2", "REVERSE_SPLIT")]
)
def test_invalid_action_ratios(ratio, kind):
    req = split_request()
    action = replace_bound(req.actions[0], ratio=ratio, kind=kind)
    assert "B_SPLIT_RATIO_INVALID" in codes(req.model_copy(update={"actions": (action,)}))


def test_multiple_actions_and_effective_boundary():
    req = split_request()
    second = replace_bound(
        req.actions[0], action_id="split-2", ratio="4", effective_ns=S + STEP + 1
    )
    pairs = tuple(
        (e.record_hash, "800" if n == 0 else "400", "1.25" if n == 0 else "2.5")
        for n, e in enumerate(req.events)
    )
    adjustment = replace_bound(
        req.adjustments[0],
        factors=(("split-1", "0.5", "2"), ("split-2", "0.25", "4")),
        raw_pairs=pairs,
        raw_price_fields=tuple(
            (e.record_hash, name, str(Decimal(getattr(e.payload, name)) * (8 if n == 0 else 4)))
            for n, e in enumerate(req.events)
            for name in ("open", "high", "low", "close")
        ),
    )
    req = req.model_copy(update={"actions": (*req.actions, second), "adjustments": (adjustment,)})
    assert result(req).overall_qa_eligibility == QaStatus.PASS
    wrong = replace_bound(adjustment, raw_pairs=((req.events[1].record_hash, "800", "1.25"),))
    assert "B_RAW_ADJUSTED_CONFLICT" in codes(req.model_copy(update={"adjustments": (wrong,)}))


def test_current_mapping_cannot_backfill_missing_row_symbol():
    req = fixture()
    prospective = replace_bound(
        req.snapshot.records[0], metadata_basis="PROSPECTIVE", known_at=S, recorded_at=S
    )
    req = with_maps(req, snapshot(prospective))
    assert "C_NATIVE_SYMBOL_EVIDENCE_MISSING" in codes(update_aux(req, native_symbol=None))


def test_sequence_and_native_market_fact_conflict():
    req = fixture()
    records = tuple(
        replace_bound(row.source, sequence=sequence)
        for row, sequence in zip(
            qa_rows_from_events(req.events, knowledge_ns=K).rows, (4, 6), strict=True
        )
    )
    req = evidence_for(
        req.model_copy(
            update={
                "events": None,
                "diagnostic_records": records,
                "policy": replace_bound(req.policy, sequence_semantics="CONTIGUOUS"),
            }
        )
    )
    assert "D_SEQUENCE_DISCONTINUITY" in codes(req)
    records = (records[0], replace_bound(records[0], sequence=5))
    assert "D_CONFLICTING_DUPLICATE" in codes(
        evidence_for(req.model_copy(update={"diagnostic_records": records}))
    )


def test_valid_and_invalid_revision_chains():
    req = fixture()
    row = qa_rows_from_events(req.events, knowledge_ns=K).rows[0].source
    first = replace_bound(
        row, payload_kind="TRADE", native_id="old", values=(("price", "100"), ("size", "1"))
    )
    second = replace_bound(first, native_id="revision")
    req = evidence_for(
        req.model_copy(update={"events": None, "diagnostic_records": (first, second)})
    )
    revision = HistoricalRevisionFact(
        state="REVISED",
        revision_id="r1",
        predecessor_input_hash=first.record_hash,
        available_at_ns=END + 2,
        evidence=ref("revision"),
    )
    req = update_aux(req, index=1, revision=revision, known_at_ns=END + 3)
    assert "D_REVISION_CHAIN_CONFLICT" not in codes(req)
    assert next(d for d in result(req).domains if d.domain.value == "D").status == QaStatus.PASS
    assert "D_REVISED_ROW_REJECTED" in codes(
        req.model_copy(
            update={"policy": replace_bound(req.policy, revision_policy="REJECT_REVISED")}
        )
    )


def compared_request(price="100"):
    req = fixture()
    other = replace_bound(req.snapshot.records[0], provider="OKX")
    req = with_maps(req, snapshot(req.snapshot.records[0], other))
    one = req.events[0]
    two = replace_bound(
        one,
        provider="OKX",
        native_id="other-provider",
        payload=one.payload.model_copy(update={"close": price}),
    )
    req = evidence_for(req.model_copy(update={"events": (one, two, req.events[1])}))
    for index, counterpart in ((0, two), (1, one)):
        comparison = HistoricalComparisonFact(
            disposition="PRESENT",
            comparison_group_id="same-slot",
            counterpart_input_hashes=(counterpart.record_hash,),
            evidence=ref("comparison"),
        )
        req = update_aux(req, index=index, comparison=comparison)
    return req


def test_provider_comparison_and_disagreement():
    assert result(compared_request()).overall_qa_eligibility == QaStatus.PASS
    req = compared_request("101")
    assert "D_PROVIDER_DISAGREEMENT" in codes(req)
    assert result(req).overall_qa_eligibility == QaStatus.WARN
    comparison = req.historical_evidence[1].comparison.model_copy(
        update={"comparison_group_id": "wrong"}
    )
    assert "D_COMPARISON_BINDING_CONFLICT" in codes(update_aux(req, index=1, comparison=comparison))


def test_gap_explanations_require_own_coverage():
    req = fixture()
    first = req.sessions.open_intervals[0].model_copy(update={"close_ns": S + STEP})
    sessions = replace_bound(req.sessions, open_intervals=(first,))
    missing = evidence_for(
        req.model_copy(update={"events": (req.events[0],), "sessions": sessions})
    )
    assert "E_UNEXPLAINED_CALENDAR_SPACE" in codes(missing)
    universe = replace_bound(
        req.universe,
        membership=(("STABLE-ID", S, S + STEP, "LISTED"), ("STABLE-ID", S + STEP, END, "HALTED")),
    )
    missing = missing.model_copy(update={"sessions": req.sessions, "universe": universe})
    assert "E_STATE_EXPLAINED_GAP" in codes(missing)
    assert "E_IN_SESSION_MISSING" not in codes(missing)


def test_resource_bounds_and_surface_conflict():
    req = fixture()
    assert (
        result(
            req.model_copy(update={"policy": replace_bound(req.policy, max_rows=1)})
        ).overall_qa_eligibility
        != QaStatus.PASS
    )
    assert "E_RESOURCE_BOUND_EXCEEDED" in codes(
        req.model_copy(update={"policy": replace_bound(req.policy, max_expected_intervals=1)})
    )
    record = qa_rows_from_events(req.events, knowledge_ns=K).rows[0].source
    assert (
        result(req.model_copy(update={"diagnostic_records": (record,)})).overall_qa_eligibility
        != QaStatus.PASS
    )


def test_intrinsic_source_unit_and_signed_context():
    req = fixture()
    req = diagnostic(
        req,
        payload_kind="CONTEXT",
        context_field="FUNDING",
        intrinsic_units=(("price_unit", "RATE"),),
        values=(("value", "-0.01"),),
    )
    assert "F_ROW_INTRINSIC_UNIT_CONFLICT" in codes(req)
    req = evidence_for(req, price_unit="RATE")
    assert "D_NONPOSITIVE_PRICE" not in codes(req)
    req = diagnostic(
        fixture(), payload_kind="CONTEXT", context_field="MARK", values=(("value", "-1"),)
    )
    assert "D_NONPOSITIVE_PRICE" in codes(req)


def test_adjacent_outlier_requires_frozen_contiguous_session_rule():
    req = fixture()
    bounds = replace_bound(req.policy.outlier, maximum_adjacent_relative_change="0.005")
    events = (
        req.events[0],
        replace_bound(
            req.events[1], payload=req.events[1].payload.model_copy(update={"close": "101"})
        ),
    )
    req = evidence_for(
        req.model_copy(
            update={"events": events, "policy": replace_bound(req.policy, outlier=bounds)}
        )
    )
    assert "D_OUTLIER_ADJACENT" in codes(req)


def test_every_adjusted_price_field_needs_raw_proof():
    req = split_request()
    adjustment = replace_bound(req.adjustments[0], raw_price_fields=())
    assert "B_ALL_PRICE_FIELDS_PROOF_MISSING" in codes(
        req.model_copy(update={"adjustments": (adjustment,)})
    )
    fields = list(req.adjustments[0].raw_price_fields)
    key, name, _ = fields[0]
    fields[0] = (key, name, "1")
    adjustment = replace_bound(req.adjustments[0], raw_price_fields=tuple(fields))
    assert "B_RAW_PRICE_FIELDS_CONFLICT" in codes(
        req.model_copy(update={"adjustments": (adjustment,)})
    )
