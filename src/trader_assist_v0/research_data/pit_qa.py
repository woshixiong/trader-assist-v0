"""Pure, evidence-bound PIT diagnostics. QA eligibility is never an access permit."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, DefaultContext, InvalidOperation, localcontext
from enum import StrEnum
from itertools import pairwise
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, ValidationError

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex

from .contracts import (
    REQUIRED_DATASET_METADATA,
    BoundRecord,
    ControlReplan,
    DatasetManifest,
    ExternalReferenceEvent,
    FrozenModel,
    SourceMode,
)
from .mapping import PitReferenceResolver, ReferenceMappingSnapshot


class QaStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class QaDomain(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class AdjustmentMode(StrEnum):
    UNADJUSTED = "UNADJUSTED"
    SPLIT_ADJUSTED = "SPLIT_ADJUSTED"
    TOTAL_RETURN_ADJUSTED = "TOTAL_RETURN_ADJUSTED"
    UNKNOWN = "UNKNOWN"


class ActionKind(StrEnum):
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    DIVIDEND = "DIVIDEND"
    OTHER = "OTHER"


class EvidenceDisposition(StrEnum):
    PRESENT = "PRESENT"
    EXPLICIT_NOT_APPLICABLE = "EXPLICIT_NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class GapKind(StrEnum):
    SESSION_EXPLAINED = "SESSION_EXPLAINED"
    STATE_EXPLAINED = "STATE_EXPLAINED"
    IN_SESSION_MISSING = "IN_SESSION_MISSING"
    DATA_MISSING_OR_UNKNOWN = "DATA_MISSING_OR_UNKNOWN"
    PARTIAL_BOUNDARY = "PARTIAL_BOUNDARY"


class HistoricalBasis(StrEnum):
    HISTORICAL = "HISTORICAL"
    SYNTHETIC = "SYNTHETIC"


class RevisionState(StrEnum):
    UNREVISED = "UNREVISED"
    REVISED = "REVISED"
    UNKNOWN = "UNKNOWN"


class RowInputKind(StrEnum):
    PACKAGE_A_EVENT = "PACKAGE_A_EVENT"
    DIAGNOSTIC = "DIAGNOSTIC"


class QaEvidenceRef(FrozenModel):
    locator: str = Field(min_length=1)
    content_hash: Sha256Hex
    kind: str = Field(min_length=1)
    version: str = Field(min_length=1)
    known_at_ns: int = Field(gt=0)
    recorded_at_ns: int = Field(gt=0)
    valid_from_ns: int | None = None
    valid_to_ns: int | None = None


class LocalTimeEvidence(FrozenModel):
    local_timestamp: str
    timezone: str
    fold: Literal[0, 1] | None = None
    offset_seconds: int | None = None
    evidence: QaEvidenceRef


class TimeNormalizationResult(FrozenModel):
    status: QaStatus
    reason_code: str
    utc_ns: int | None = None
    evidence: tuple[QaEvidenceRef, ...]


class RowEvidenceKey(FrozenModel):
    input_kind: RowInputKind
    dataset_hash: Sha256Hex
    input_record_hash: Sha256Hex


class HistoricalRevisionFact(FrozenModel):
    state: RevisionState
    revision_id: str = Field(min_length=1)
    predecessor_input_hash: Sha256Hex | None = None
    available_at_ns: int = Field(gt=0)
    evidence: QaEvidenceRef


class HistoricalComparisonFact(FrozenModel):
    disposition: EvidenceDisposition
    comparison_group_id: str | None = None
    counterpart_input_hashes: tuple[Sha256Hex, ...] = ()
    evidence: QaEvidenceRef


class RowProjectionProof(FrozenModel):
    key: RowEvidenceKey
    source_locator: str = Field(min_length=1)
    source_content_hash: Sha256Hex
    row_locator: str = Field(min_length=1)
    projection_version: Literal["PIT_EVENT_PROJECTION_V1"] = "PIT_EVENT_PROJECTION_V1"
    copied_fields_hash: Sha256Hex
    evidence: QaEvidenceRef


SourceRole = Literal["EXECUTION_UNIVERSE_METADATA", "EXTERNAL_REFERENCE", "RESEARCH_IMPORT"]


class HistoricalRowEvidence(BoundRecord):
    key: RowEvidenceKey
    basis: HistoricalBasis
    valid_from_ns: int
    valid_to_ns: int
    known_at_ns: int
    recorded_at_ns: int
    evidence: QaEvidenceRef
    native_symbol: str | None = None
    adjustment_mode: AdjustmentMode | None = None
    adjustment_basis: str | None = None
    revision: HistoricalRevisionFact | None = None
    comparison: HistoricalComparisonFact | None = None
    price_unit: str | None = None
    size_unit: str | None = None
    source_role: SourceRole | None = None
    projection_proof: RowProjectionProof | None = None
    local_time: LocalTimeEvidence | None = None
    finalized_at_ns: int | None = None


ValueName = Literal[
    "open",
    "high",
    "low",
    "close",
    "volume",
    "price",
    "size",
    "bid",
    "ask",
    "bid_size",
    "ask_size",
    "value",
    "oi",
    "oi_ccy",
    "oi_usd",
]


class QaDiagnosticRecord(BoundRecord):
    dataset_hash: Sha256Hex
    mapping_hash: Sha256Hex
    provider: str
    venue: str
    product: str
    instrument_id: str
    source_mode: SourceMode
    native_id: str
    sequence: int | None = None
    source_ts: str
    source_unit: Literal["ns", "ms"]
    event_ns: int
    observed_at_ns: int
    init_ns: int | None = None
    receive_ns: int | None = None
    receive_provenance: str = "NOT_EXPOSED"
    payload_kind: Literal["BAR", "TRADE", "BBO", "CONTEXT", "OI", "DEPTH"]
    values: tuple[tuple[ValueName, str], ...]
    context_field: Literal["MARK", "INDEX", "ORACLE", "PREMIUM", "FUNDING"] | None = None
    intrinsic_units: tuple[tuple[str, str], ...] = ()
    bar_start_ns: int | None = None
    bar_end_ns: int | None = None
    interval_ns: int | None = None
    timestamp_meaning: Literal["OPEN", "CLOSE"] | None = None
    finalized: bool | None = None
    ordinal: int = 0
    source_locator: str | None = None


class QaRow(FrozenModel):
    ordinal: int
    key: RowEvidenceKey
    source: QaDiagnosticRecord
    knowledge_ns: int
    copied_fields_hash: Sha256Hex
    historical: HistoricalRowEvidence | None = None
    bridge_status: QaStatus = QaStatus.INSUFFICIENT_EVIDENCE

    @property
    def native_symbol(self) -> str | None:
        return self.historical.native_symbol if self.historical else None


class QaFinding(FrozenModel):
    domain: QaDomain
    predicate: str
    status: QaStatus
    reason_code: str
    instrument_id: str | None = None
    ordinals: tuple[int, ...] = ()
    interval: tuple[int, int] | None = None
    evidence_locators: tuple[str, ...] = ()


class QaProjection(FrozenModel):
    rows: tuple[QaRow, ...]
    bridge_findings: tuple[QaFinding, ...]
    input_record_hashes: tuple[str, ...]
    accepted_auxiliary_hashes: tuple[str, ...]


class OutlierPolicy(BoundRecord):
    evidence: QaEvidenceRef
    price_unit: str
    minimum_price: str | None = None
    maximum_price: str | None = None
    maximum_adjacent_relative_change: str | None = None
    adjacency: Literal["CONTIGUOUS_SAME_STREAM"] = "CONTIGUOUS_SAME_STREAM"
    compare_across_sessions: bool
    severity: Literal["WARN", "FAIL"]


class PitQaPolicy(BoundRecord):
    evidence: QaEvidenceRef
    duplicate_severity: Literal["WARN", "FAIL"]
    missing_bar_severity: Literal["WARN", "FAIL"]
    sequence_semantics: Literal["CONTIGUOUS", "UNKNOWN", "NOT_APPLICABLE"]
    require_finality_time: Literal[True] = True
    revision_policy: Literal["REJECT_REVISED", "VALIDATE_CHAIN"]
    disagreement_severity: Literal["WARN", "FAIL"]
    comparison_tolerance: str
    adjustment_tolerance: str
    outlier: OutlierPolicy | None = None
    max_rows: int = Field(gt=0, le=100_000)
    max_expected_intervals: int = Field(gt=0, le=100_000)


class SessionInterval(FrozenModel):
    instrument_id: str
    session_id: str
    session_class: str
    open_ns: int
    close_ns: int
    evidence: QaEvidenceRef
    local_open: LocalTimeEvidence | None = None
    local_close: LocalTimeEvidence | None = None


class SessionScheduleEvidence(BoundRecord):
    evidence: QaEvidenceRef
    calendar_version: str
    timezone: str
    start_ns: int
    end_ns: int
    instrument_ids: tuple[str, ...]
    open_intervals: tuple[SessionInterval, ...]
    closed_intervals: tuple[SessionInterval, ...] = ()
    complete: bool
    cadence_ns: int
    grid_origin_ns: int
    boundary_convention: Literal["COMPLETE_HALF_OPEN_BARS"] = "COMPLETE_HALF_OPEN_BARS"


class CorporateActionEvidence(BoundRecord):
    evidence: QaEvidenceRef
    instrument_id: str
    action_id: str
    kind: ActionKind
    effective_ns: int
    known_at_ns: int
    recorded_at_ns: int
    ratio: str | None = None
    price_treatment: Literal["BACKWARD_SPLIT", "UNADJUSTED", "SUPPLIED_OTHER"]
    volume_treatment: Literal["SHARE_VOLUME", "UNCHANGED", "UNKNOWN"]


class AdjustmentEvidence(BoundRecord):
    evidence: QaEvidenceRef
    instrument_id: str
    start_ns: int
    end_ns: int
    mode: AdjustmentMode
    basis: str
    basis_ns: int
    complete: bool
    price_unit: str
    size_unit: str
    # Each tuple binds one original input hash and its supplied raw price/volume.
    raw_pairs: tuple[tuple[str, str, str], ...] = ()
    raw_price_fields: tuple[tuple[str, ValueName, str], ...] = ()
    # Each factor binds an action id, not a guessed discontinuity.
    factors: tuple[tuple[str, str, str], ...] = ()


class UniverseEvidence(BoundRecord):
    evidence: QaEvidenceRef
    basis: HistoricalBasis
    start_ns: int
    end_ns: int
    complete: bool
    survivorship_limits: str
    # Explicit interval state: instrument, start, end, state.
    membership: tuple[tuple[str, int, int, Literal["LISTED", "DELISTED", "HALTED"]], ...]
    # instrument, old native symbol, new native symbol, effective time, evidence.
    continuity: tuple[tuple[str, str, str, int, QaEvidenceRef], ...] = ()


class SourceBindingEvidence(BoundRecord):
    evidence: QaEvidenceRef
    dataset_hash: Sha256Hex
    source_locator: str
    checksum: Sha256Hex
    source_bytes_hex: str | None = None
    projection_proof_hashes: tuple[str, ...]


class PitQaRequest(FrozenModel):
    manifest: DatasetManifest | str
    snapshot: ReferenceMappingSnapshot | str
    events: tuple[ExternalReferenceEvent, ...] | None = None
    diagnostic_records: tuple[QaDiagnosticRecord, ...] | None = None
    historical_evidence: tuple[HistoricalRowEvidence, ...] = ()
    knowledge_ns: int = Field(gt=0)
    policy: PitQaPolicy
    sessions: SessionScheduleEvidence | None = None
    actions: tuple[CorporateActionEvidence, ...] = ()
    adjustments: tuple[AdjustmentEvidence, ...] = ()
    universe: UniverseEvidence | None = None
    source_binding: SourceBindingEvidence | None = None
    synthetic_fixture: bool = False


class QaDomainResult(FrozenModel):
    domain: QaDomain
    findings: tuple[QaFinding, ...]
    status: QaStatus


class CoverageDiagnostic(FrozenModel):
    instrument_id: str
    cut: tuple[int, int]
    expected: int
    present_unique: int
    missing: int
    invalid: int
    duplicates: int
    first_expected_ns: int | None
    last_expected_ns: int | None
    first_observed_ns: int | None
    last_observed_ns: int | None
    gaps: tuple[tuple[int, int, GapKind], ...]


class PitQaResult(BoundRecord):
    evaluator_version: Literal["PIT_QA_V1"] = "PIT_QA_V1"
    domains: tuple[QaDomainResult, ...]
    overall_qa_eligibility: QaStatus
    coverage: tuple[CoverageDiagnostic, ...]
    input_bindings: tuple[tuple[str, str], ...]
    access_permission_granted: Literal[False] = False


_RANK = {
    s: i
    for i, s in enumerate(
        (
            QaStatus.PASS,
            QaStatus.WARN,
            QaStatus.UNKNOWN,
            QaStatus.INSUFFICIENT_EVIDENCE,
            QaStatus.FAIL,
        )
    )
}
_INS = QaStatus.INSUFFICIENT_EVIDENCE


def _aggregate_status(statuses: tuple[QaStatus, ...]) -> QaStatus:
    return max(statuses, key=_RANK.__getitem__) if statuses else _INS


def _digest(value: object) -> str:
    return sha256_hex(canonical_json_bytes(value))


def _finding(
    domain: QaDomain,
    code: str,
    status: QaStatus,
    row: QaRow | None = None,
    *,
    refs: tuple[str | QaEvidenceRef, ...] = (),
    interval: tuple[int, int] | None = None,
) -> QaFinding:
    locator = () if row is None else (row.key.input_record_hash,)
    if row and row.historical and row.historical.projection_proof:
        locator = (row.historical.projection_proof.row_locator,)
    return QaFinding(
        domain=domain,
        predicate=code,
        status=status,
        reason_code=code,
        instrument_id=row.source.instrument_id if row else None,
        ordinals=(row.ordinal,) if row else (),
        interval=interval,
        evidence_locators=tuple(
            sorted(
                {ref.locator if isinstance(ref, QaEvidenceRef) else ref for ref in refs}
                | set(locator)
            )
        ),
    )


def _ref_valid(ref: QaEvidenceRef, knowledge: int, event: int | None = None) -> bool:
    if not 0 < ref.known_at_ns <= ref.recorded_at_ns <= knowledge:
        return False
    if (ref.valid_from_ns is None) != (ref.valid_to_ns is None):
        return False
    if ref.valid_from_ns is not None and ref.valid_to_ns is not None:
        if ref.valid_from_ns >= ref.valid_to_ns:
            return False
        if event is not None and not ref.valid_from_ns <= event < ref.valid_to_ns:
            return False
    return True


def normalize_local_timestamp(value: LocalTimeEvidence) -> TimeNormalizationResult:
    refs = (value.evidence,)

    def result(status: QaStatus, code: str, ns: int | None = None) -> TimeNormalizationResult:
        return TimeNormalizationResult(status=status, reason_code=code, utc_ns=ns, evidence=refs)

    try:
        zone = ZoneInfo(value.timezone)
    except ZoneInfoNotFoundError:
        return result(_INS, "A_TIMEZONE_UNAVAILABLE")
    except ValueError:
        return result(QaStatus.FAIL, "A_TIMEZONE_INVALID")
    try:
        # datetime truncates beyond microseconds; retain the remaining ns explicitly.
        match = re.fullmatch(
            r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?", value.local_timestamp
        )
        if not match:
            raise ValueError("local wall time required")
        fraction = (match[2] or "").ljust(9, "0")
        wall = datetime.fromisoformat(match[1]).replace(microsecond=int(fraction[:6]))
        remainder = int(fraction[6:])
    except ValueError:
        return result(QaStatus.FAIL, "A_LOCAL_TIME_INVALID")
    candidates: dict[int, datetime] = {}
    for fold in (0, 1):
        local = wall.replace(tzinfo=zone, fold=fold)
        utc = local.astimezone(UTC)
        back = utc.astimezone(zone)
        if back.replace(tzinfo=None) == wall and back.fold == fold:
            candidates[fold] = utc
    if not candidates:
        return result(QaStatus.FAIL, "A_LOCAL_TIME_NONEXISTENT")
    if len(set(candidates.values())) > 1 and value.fold is None:
        return result(_INS, "A_LOCAL_TIME_AMBIGUOUS")
    selected_fold: int
    if value.fold is not None:
        selected_fold = value.fold
    else:
        selected_fold = min(candidates)
    if selected_fold not in candidates:
        return result(QaStatus.FAIL, "A_LOCAL_TIME_DECLARATION_CONFLICT")
    utc = candidates[selected_fold]
    offset = utc.astimezone(zone).utcoffset()
    if value.offset_seconds is not None and offset != timedelta(seconds=value.offset_seconds):
        return result(QaStatus.FAIL, "A_LOCAL_TIME_DECLARATION_CONFLICT")
    delta = utc - datetime(1970, 1, 1, tzinfo=UTC)
    ns = (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000
    return result(QaStatus.PASS, "A_LOCAL_TIME_NORMALIZED", ns + remainder)


def _event_source(event: ExternalReferenceEvent) -> QaDiagnosticRecord:
    payload = event.payload
    names: tuple[ValueName, ...] = (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "price",
        "size",
        "bid",
        "ask",
        "bid_size",
        "ask_size",
        "value",
        "oi",
        "oi_ccy",
        "oi_usd",
    )
    values = tuple(
        (name, str(getattr(payload, name)))
        for name in names
        if getattr(payload, name, None) is not None
    )
    ts = event.timestamps
    return QaDiagnosticRecord.create(
        version="1",
        dataset_hash=event.dataset_hash,
        mapping_hash=event.mapping_hash,
        provider=event.provider,
        venue=event.venue,
        product=event.product,
        instrument_id=event.instrument_id,
        source_mode=event.source_mode,
        native_id=event.native_id,
        sequence=event.sequence,
        source_ts=ts.source_ts,
        source_unit=ts.source_unit,
        event_ns=ts.ts_event,
        observed_at_ns=ts.observed_at_ns,
        init_ns=ts.ts_init,
        receive_ns=ts.true_network_receive_ts,
        receive_provenance=ts.receive_provenance,
        payload_kind=payload.kind,
        values=values,
        context_field=payload.field if payload.kind == "CONTEXT" else None,
        intrinsic_units=(("price_unit", payload.unit),)
        if payload.kind == "CONTEXT"
        else ((("size_unit", payload.oi_unit),) if payload.kind == "OI" else ()),
        bar_start_ns=payload.start_ns if payload.kind == "BAR" else None,
        bar_end_ns=payload.end_ns if payload.kind == "BAR" else None,
        interval_ns=payload.interval_minutes * 60_000_000_000 if payload.kind == "BAR" else None,
        timestamp_meaning=payload.timestamp_meaning if payload.kind == "BAR" else None,
        finalized=payload.finalized if payload.kind == "BAR" else None,
    )


def _bind_historical_row_evidence(
    rows: tuple[QaRow, ...], evidence: tuple[HistoricalRowEvidence, ...], *, allow_synthetic: bool
) -> QaProjection:
    findings: list[QaFinding] = []
    grouped: dict[str, list[HistoricalRowEvidence]] = {}
    keys = {r.key.model_dump_json() for r in rows}
    for raw in evidence:
        try:
            aux = HistoricalRowEvidence.model_validate_json(raw.model_dump_json())
        except ValueError:
            findings.append(_finding(QaDomain.F, "F_AUX_HASH_INVALID", QaStatus.FAIL))
            continue
        key = aux.key.model_dump_json()
        if key not in keys:
            findings.append(
                _finding(
                    QaDomain.F, "F_AUX_KEY_UNMATCHED", QaStatus.FAIL, refs=(aux.evidence.locator,)
                )
            )
        grouped.setdefault(key, []).append(aux)
    projected: list[QaRow] = []
    accepted: set[str] = set()
    for row in rows:
        choices = grouped.get(row.key.model_dump_json(), [])
        unique = {a.record_hash: a for a in choices}
        if not choices:
            findings.append(_finding(QaDomain.F, "F_AUX_EVIDENCE_MISSING", _INS, row))
            projected.append(row)
            continue
        if len(unique) != 1:
            findings.append(_finding(QaDomain.F, "F_AUX_CONFLICT", QaStatus.FAIL, row))
            projected.append(row)
            continue
        aux = next(iter(unique.values()))
        errors: list[str] = []
        if len(choices) > 1:
            findings.append(_finding(QaDomain.F, "F_AUX_EXACT_DUPLICATE", QaStatus.WARN, row))
        if not (
            0 < aux.known_at_ns <= aux.recorded_at_ns <= row.knowledge_ns
            and aux.valid_from_ns <= row.source.event_ns < aux.valid_to_ns
        ):
            errors.append("F_AUX_CAUSAL_OR_VALIDITY_CONFLICT")
        if aux.basis == HistoricalBasis.SYNTHETIC and not allow_synthetic:
            errors.append("F_AUX_SYNTHETIC_NOT_AUTHORIZED")
        refs = [aux.evidence]
        if aux.revision:
            refs.append(aux.revision.evidence)
            if not 0 < aux.revision.available_at_ns <= aux.known_at_ns <= row.knowledge_ns:
                errors.append("D_REVISION_FUTURE_KNOWN")
        if aux.comparison:
            refs.append(aux.comparison.evidence)
        if aux.local_time:
            refs.append(aux.local_time.evidence)
        proof = aux.projection_proof
        if proof:
            refs.append(proof.evidence)
            if proof.key != row.key or proof.copied_fields_hash != row.copied_fields_hash:
                errors.append("F_ROW_PROJECTION_BINDING_CONFLICT")
            if proof.evidence.content_hash != proof.source_content_hash:
                errors.append("F_ROW_PROJECTION_SOURCE_CONFLICT")
        if any(not _ref_valid(ref, row.knowledge_ns, row.source.event_ns) for ref in refs):
            errors.append("F_AUX_REFERENCE_BOUNDS_CONFLICT")
        if any(
            ref.known_at_ns > aux.known_at_ns or ref.recorded_at_ns > aux.recorded_at_ns
            for ref in refs
        ):
            errors.append("F_AUX_ENVELOPE_AVAILABILITY_CONFLICT")
        for name, value in row.source.intrinsic_units:
            if name not in {"price_unit", "size_unit"} or (
                getattr(aux, name) is not None and getattr(aux, name) != value
            ):
                errors.append("F_ROW_INTRINSIC_UNIT_CONFLICT")
        if errors:
            findings.extend(
                _finding(QaDomain.F, code, QaStatus.FAIL, row, refs=(aux.evidence.locator,))
                for code in errors
            )
            projected.append(row)
        else:
            projected.append(
                row.model_copy(update={"historical": aux, "bridge_status": QaStatus.PASS})
            )
            accepted.add(aux.record_hash)
    return QaProjection(
        rows=tuple(projected),
        bridge_findings=tuple(findings),
        input_record_hashes=tuple(r.key.input_record_hash for r in rows),
        accepted_auxiliary_hashes=tuple(sorted(accepted)),
    )


def qa_rows_from_events(
    events: tuple[ExternalReferenceEvent, ...],
    *,
    knowledge_ns: int,
    historical_evidence: tuple[HistoricalRowEvidence, ...] = (),
) -> QaProjection:
    """Copy actual event facts only. No manifest or mapping is available to this bridge."""
    rows: list[QaRow] = []
    for ordinal, raw in enumerate(events):
        event = ExternalReferenceEvent.model_validate_json(raw.model_dump_json())
        source = _event_source(event)
        key = RowEvidenceKey(
            input_kind=RowInputKind.PACKAGE_A_EVENT,
            dataset_hash=event.dataset_hash,
            input_record_hash=event.record_hash,
        )
        rows.append(
            QaRow(
                ordinal=ordinal,
                key=key,
                source=source,
                knowledge_ns=knowledge_ns,
                copied_fields_hash=_digest(source.model_dump(mode="json")),
            )
        )
    # Public projection never grants synthetic truth; evaluator supplies the R0 binding below.
    return _bind_historical_row_evidence(tuple(rows), historical_evidence, allow_synthetic=False)


def _project_diagnostic_records(
    records: tuple[QaDiagnosticRecord, ...],
    knowledge_ns: int,
    evidence: tuple[HistoricalRowEvidence, ...],
    allow_synthetic: bool,
) -> QaProjection:
    rows: list[QaRow] = []
    for ordinal, raw in enumerate(records):
        source = QaDiagnosticRecord.model_validate_json(raw.model_dump_json())
        key = RowEvidenceKey(
            input_kind=RowInputKind.DIAGNOSTIC,
            dataset_hash=source.dataset_hash,
            input_record_hash=source.record_hash,
        )
        rows.append(
            QaRow(
                ordinal=ordinal,
                key=key,
                source=source,
                knowledge_ns=knowledge_ns,
                copied_fields_hash=_digest(source.model_dump(mode="json")),
            )
        )
    return _bind_historical_row_evidence(tuple(rows), evidence, allow_synthetic=allow_synthetic)


def _number(value: str | None) -> Decimal | None:
    if value is None or len(value) > 100:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() and abs(number.adjusted()) <= 100 else None


def _stream(row: QaRow) -> tuple[str, ...]:
    s = row.source
    return (s.provider, s.venue, s.product, s.instrument_id, s.payload_kind, s.source_mode.value)


def _validate_input_bindings(
    manifest: DatasetManifest, snapshot: ReferenceMappingSnapshot, rows: tuple[QaRow, ...]
) -> list[QaFinding]:
    findings: list[QaFinding] = []
    if manifest.mapping_hash != snapshot.record_hash:
        findings.append(_finding(QaDomain.F, "F_MAPPING_HASH_CONFLICT", QaStatus.FAIL))
    for row in rows:
        s = row.source
        if s.dataset_hash != manifest.record_hash or s.mapping_hash != snapshot.record_hash:
            findings.append(_finding(QaDomain.F, "F_ROW_HASH_BINDING_CONFLICT", QaStatus.FAIL, row))
        if s.instrument_id not in manifest.instruments or s.venue != manifest.venue:
            findings.append(_finding(QaDomain.C, "C_DATASET_IDENTITY_CONFLICT", QaStatus.FAIL, row))
        in_cut = manifest.start_ns <= s.event_ns < manifest.end_ns
        if s.payload_kind == "BAR" and s.timestamp_meaning == "CLOSE":
            in_cut = (
                s.bar_start_ns is not None
                and s.bar_end_ns is not None
                and manifest.start_ns <= s.bar_start_ns < s.bar_end_ns <= manifest.end_ns
            )
        if not in_cut:
            findings.append(_finding(QaDomain.A, "A_EVENT_OUTSIDE_CUT", QaStatus.FAIL, row))
        datatype: str = s.payload_kind
        if s.payload_kind == "CONTEXT":
            datatype = s.context_field or "CONTEXT"
        if s.payload_kind == "BAR" and s.interval_ns in (60_000_000_000, 300_000_000_000):
            datatype = f"BAR_{s.interval_ns // 60_000_000_000}M"
        if datatype not in manifest.datatypes:
            findings.append(_finding(QaDomain.F, "F_DATATYPE_CONFLICT", QaStatus.FAIL, row))
    return findings


def _check_time_sessions(
    req: PitQaRequest, manifest: DatasetManifest, rows: tuple[QaRow, ...]
) -> list[QaFinding]:
    out: list[QaFinding] = []
    try:
        ZoneInfo(manifest.timezone)
    except ZoneInfoNotFoundError:
        out.append(_finding(QaDomain.A, "A_TIMEZONE_UNAVAILABLE", _INS))
    except ValueError:
        out.append(_finding(QaDomain.A, "A_TIMEZONE_INVALID", QaStatus.FAIL))
    schedule = req.sessions
    if schedule is None:
        out.append(_finding(QaDomain.A, "A_SESSION_EVIDENCE_MISSING", _INS))
    else:
        if schedule.timezone != manifest.timezone or not _ref_valid(
            schedule.evidence, req.knowledge_ns
        ):
            out.append(_finding(QaDomain.A, "A_SESSION_DECLARATION_CONFLICT", QaStatus.FAIL))
        for interval in (*schedule.open_intervals, *schedule.closed_intervals):
            if interval.open_ns >= interval.close_ns or not _ref_valid(
                interval.evidence, req.knowledge_ns
            ):
                out.append(_finding(QaDomain.A, "A_SESSION_INTERVAL_INVALID", QaStatus.FAIL))
            for local, boundary in (
                (interval.local_open, interval.open_ns),
                (interval.local_close, interval.close_ns),
            ):
                if local:
                    normalized = normalize_local_timestamp(local)
                    if (
                        normalized.status != QaStatus.PASS
                        or normalized.utc_ns != boundary
                        or not _ref_valid(local.evidence, req.knowledge_ns, boundary)
                    ):
                        out.append(
                            _finding(QaDomain.A, "A_SESSION_LOCAL_BOUNDARY_CONFLICT", QaStatus.FAIL)
                        )
        intervals = (*schedule.open_intervals, *schedule.closed_intervals)
        for i, left in enumerate(intervals):
            for right in intervals[i + 1 :]:
                if left.instrument_id == right.instrument_id and max(
                    left.open_ns, right.open_ns
                ) < min(left.close_ns, right.close_ns):
                    out.append(_finding(QaDomain.A, "A_SESSION_OVERLAP", QaStatus.FAIL))
    latest: dict[tuple[str, ...], int] = {}
    for row in rows:
        s, aux = row.source, row.historical
        if (
            not s.source_ts.isascii()
            or not s.source_ts.isdecimal()
            or (int(s.source_ts) * (1 if s.source_unit == "ns" else 1_000_000) != s.event_ns)
        ):
            out.append(_finding(QaDomain.A, "A_SOURCE_TIMESTAMP_CONFLICT", QaStatus.FAIL, row))
        if not 0 < s.event_ns <= s.observed_at_ns <= row.knowledge_ns:
            out.append(_finding(QaDomain.A, "A_CAUSAL_CLOCK_CONFLICT", QaStatus.FAIL, row))
        if s.receive_ns is None and s.receive_provenance != "NOT_EXPOSED":
            out.append(_finding(QaDomain.A, "A_RECEIVE_PROVENANCE_CONFLICT", QaStatus.FAIL, row))
        if s.receive_ns is not None and (
            s.receive_ns < s.event_ns or s.receive_ns > row.knowledge_ns
        ):
            out.append(_finding(QaDomain.A, "A_RECEIVE_CLOCK_CONFLICT", QaStatus.FAIL, row))
        if s.init_ns is not None and (s.init_ns < s.event_ns or s.init_ns > row.knowledge_ns):
            out.append(_finding(QaDomain.A, "A_INIT_CLOCK_CONFLICT", QaStatus.FAIL, row))
        stream = _stream(row)
        if s.event_ns < latest.get(stream, s.event_ns):
            out.append(_finding(QaDomain.A, "A_TIMESTAMP_REVERSAL", QaStatus.FAIL, row))
        latest[stream] = max(s.event_ns, latest.get(stream, s.event_ns))
        if aux and aux.local_time:
            normalized = normalize_local_timestamp(aux.local_time)
            if normalized.status != QaStatus.PASS:
                out.append(_finding(QaDomain.A, normalized.reason_code, normalized.status, row))
            elif normalized.utc_ns != s.event_ns or aux.local_time.timezone != manifest.timezone:
                out.append(_finding(QaDomain.A, "A_LOCAL_EVENT_CONFLICT", QaStatus.FAIL, row))
        if s.payload_kind == "BAR":
            start, end = s.bar_start_ns, s.bar_end_ns
            if start is None or end is None or start >= end or s.interval_ns != end - start:
                out.append(_finding(QaDomain.A, "A_BAR_BOUNDARY_CONFLICT", QaStatus.FAIL, row))
                continue
            if s.event_ns != (start if s.timestamp_meaning == "OPEN" else end):
                out.append(_finding(QaDomain.A, "A_TIMESTAMP_MEANING_CONFLICT", QaStatus.FAIL, row))
            if s.finalized is not True:
                out.append(_finding(QaDomain.A, "A_BAR_NOT_FINAL", QaStatus.FAIL, row))
            if aux is None or aux.finalized_at_ns is None:
                out.append(_finding(QaDomain.A, "A_FINALITY_EVIDENCE_MISSING", _INS, row))
            elif not end <= aux.finalized_at_ns <= s.observed_at_ns:
                out.append(_finding(QaDomain.A, "A_FINALITY_CAUSAL_CONFLICT", QaStatus.FAIL, row))
            if schedule and not any(
                i.instrument_id == s.instrument_id and i.open_ns <= start < end <= i.close_ns
                for i in schedule.open_intervals
            ):
                out.append(_finding(QaDomain.A, "A_BAR_OUTSIDE_SESSION", QaStatus.FAIL, row))
        elif schedule and not any(
            i.instrument_id == s.instrument_id and i.open_ns <= s.event_ns < i.close_ns
            for i in schedule.open_intervals
        ):
            out.append(_finding(QaDomain.A, "A_EVENT_OUTSIDE_SESSION", QaStatus.FAIL, row))
    return out


def _check_corporate_actions(request: PitQaRequest, rows: tuple[QaRow, ...]) -> list[QaFinding]:
    out: list[QaFinding] = []
    tolerance = _number(request.policy.adjustment_tolerance)
    if tolerance is None or tolerance < 0:
        return [_finding(QaDomain.B, "B_TOLERANCE_INVALID", QaStatus.FAIL)]
    actions: dict[str, CorporateActionEvidence] = {}
    for action in request.actions:
        if action.action_id in actions:
            out.append(_finding(QaDomain.B, "B_ACTION_ID_CONFLICT", QaStatus.FAIL))
        actions[action.action_id] = action
        if not (
            action.effective_ns > 0
            and 0 < action.known_at_ns <= action.recorded_at_ns <= request.knowledge_ns
            and action.evidence.known_at_ns <= action.known_at_ns
            and action.evidence.recorded_at_ns <= action.recorded_at_ns
            and _ref_valid(action.evidence, request.knowledge_ns, action.effective_ns)
        ):
            out.append(
                _finding(
                    QaDomain.B, "B_ACTION_CAUSAL_CONFLICT", QaStatus.FAIL, refs=(action.evidence,)
                )
            )
        ratio = _number(action.ratio)
        if action.kind in (ActionKind.SPLIT, ActionKind.REVERSE_SPLIT):
            if (
                ratio is None
                or ratio <= 0
                or (action.kind == ActionKind.SPLIT and ratio <= 1)
                or (action.kind == ActionKind.REVERSE_SPLIT and ratio >= 1)
            ):
                out.append(
                    _finding(
                        QaDomain.B, "B_SPLIT_RATIO_INVALID", QaStatus.FAIL, refs=(action.evidence,)
                    )
                )
        else:
            # This foundation has no dividend convention owner. A supplied OTHER
            # label without its executable transformation is not numerical proof.
            out.append(
                _finding(
                    QaDomain.B, "B_ACTION_TRANSFORMATION_UNPROVEN", _INS, refs=(action.evidence,)
                )
            )
    modes: dict[tuple[str, ...], set[tuple[AdjustmentMode, str]]] = {}
    for row in rows:
        aux, s = row.historical, row.source
        if aux is None or aux.adjustment_mode in (None, AdjustmentMode.UNKNOWN):
            out.append(_finding(QaDomain.B, "B_ROW_ADJUSTMENT_UNKNOWN", QaStatus.UNKNOWN, row))
            continue
        if not aux.adjustment_basis:
            out.append(_finding(QaDomain.B, "B_ROW_BASIS_MISSING", _INS, row))
            continue
        assert aux.adjustment_mode is not None
        modes.setdefault(_stream(row), set()).add((aux.adjustment_mode, aux.adjustment_basis))
        candidates = [
            a
            for a in request.adjustments
            if a.instrument_id == s.instrument_id and a.start_ns <= s.event_ns < a.end_ns
        ]
        if len(candidates) != 1:
            out.append(
                _finding(
                    QaDomain.B,
                    "B_ADJUSTMENT_COVERAGE_MISSING",
                    _INS if not candidates else QaStatus.FAIL,
                    row,
                )
            )
            continue
        adjustment = candidates[0]
        if not adjustment.complete:
            out.append(_finding(QaDomain.B, "B_ACTION_COVERAGE_INCOMPLETE", _INS, row))
        if not _ref_valid(adjustment.evidence, request.knowledge_ns, s.event_ns):
            out.append(_finding(QaDomain.B, "B_ADJUSTMENT_CAUSAL_CONFLICT", QaStatus.FAIL, row))
        if (adjustment.mode, adjustment.basis, adjustment.price_unit, adjustment.size_unit) != (
            aux.adjustment_mode,
            aux.adjustment_basis,
            aux.price_unit,
            aux.size_unit,
        ):
            out.append(
                _finding(QaDomain.B, "B_ADJUSTMENT_DECLARATION_CONFLICT", QaStatus.FAIL, row)
            )
        if adjustment.basis_ns > request.knowledge_ns or adjustment.basis_ns < adjustment.start_ns:
            out.append(_finding(QaDomain.B, "B_BASIS_TIME_CONFLICT", QaStatus.FAIL, row))
        if adjustment.mode == AdjustmentMode.TOTAL_RETURN_ADJUSTED:
            out.append(_finding(QaDomain.B, "B_DIVIDEND_CONVENTION_UNPROVEN", _INS, row))
            continue
        applicable = sorted(
            (
                a
                for a in request.actions
                if a.instrument_id == s.instrument_id
                and adjustment.start_ns <= a.effective_ns <= adjustment.basis_ns
            ),
            key=lambda a: (a.effective_ns, a.action_id),
        )
        factors = {key: (p, v) for key, p, v in adjustment.factors}
        if len(factors) != len(adjustment.factors) or set(factors) != {
            a.action_id for a in applicable
        }:
            out.append(_finding(QaDomain.B, "B_FACTOR_ACTION_BINDING_CONFLICT", QaStatus.FAIL, row))
        price_factor, volume_factor = Decimal(1), Decimal(1)
        for action in applicable:
            pair = factors.get(action.action_id)
            p, v = (_number(pair[0]), _number(pair[1])) if pair else (None, None)
            ratio = _number(action.ratio)
            if p is None or v is None or ratio is None or ratio <= 0:
                out.append(_finding(QaDomain.B, "B_FACTOR_INVALID", QaStatus.FAIL, row))
                continue
            if adjustment.mode == AdjustmentMode.UNADJUSTED:
                expected_p, expected_v = Decimal(1), Decimal(1)
                correct_treatment = action.price_treatment == "UNADJUSTED"
            else:
                expected_p = Decimal(1) / ratio
                expected_v = ratio if action.volume_treatment == "SHARE_VOLUME" else Decimal(1)
                correct_treatment = action.price_treatment == "BACKWARD_SPLIT"
                if action.volume_treatment == "UNKNOWN" or (
                    action.volume_treatment == "SHARE_VOLUME" and adjustment.size_unit != "SHARES"
                ):
                    out.append(_finding(QaDomain.B, "B_VOLUME_TREATMENT_UNPROVEN", _INS, row))
            if (
                not correct_treatment
                or abs(p - expected_p) > tolerance
                or abs(v - expected_v) > tolerance
            ):
                out.append(_finding(QaDomain.B, "B_FACTOR_CONFLICT", QaStatus.FAIL, row))
            if s.event_ns < action.effective_ns:
                price_factor *= p
                volume_factor *= v
        if adjustment.mode == AdjustmentMode.SPLIT_ADJUSTED:
            price_names = {
                "BAR": {"open", "high", "low", "close"},
                "TRADE": {"price"},
                "BBO": {"bid", "ask"},
                "CONTEXT": {"value"},
            }.get(s.payload_kind)
            raw_fields = [
                (name, value)
                for key, name, value in adjustment.raw_price_fields
                if key == row.key.input_record_hash
            ]
            if price_names is None or {name for name, _ in raw_fields} != price_names:
                out.append(_finding(QaDomain.B, "B_ALL_PRICE_FIELDS_PROOF_MISSING", _INS, row))
            elif len(raw_fields) != len(price_names):
                out.append(_finding(QaDomain.B, "B_RAW_PRICE_FIELDS_CONFLICT", QaStatus.FAIL, row))
            else:
                supplied_values = dict(s.values)
                for name, raw_value in raw_fields:
                    raw_decimal, actual_decimal = (
                        _number(raw_value),
                        _number(supplied_values.get(name)),
                    )
                    if (
                        raw_decimal is None
                        or actual_decimal is None
                        or abs(raw_decimal * price_factor - actual_decimal) > tolerance
                    ):
                        out.append(
                            _finding(QaDomain.B, "B_RAW_PRICE_FIELDS_CONFLICT", QaStatus.FAIL, row)
                        )
            pairs = [pair for pair in adjustment.raw_pairs if pair[0] == row.key.input_record_hash]
            if len(pairs) != 1:
                out.append(
                    _finding(
                        QaDomain.B,
                        "B_RAW_ADJUSTED_PROOF_MISSING",
                        _INS if not pairs else QaStatus.FAIL,
                        row,
                    )
                )
            else:
                raw_price, raw_volume = _number(pairs[0][1]), _number(pairs[0][2])
                values = dict(s.values)
                price = _number(values.get("close", values.get("price", values.get("bid"))))
                volume = _number(values.get("volume", values.get("size", values.get("bid_size"))))
                if None in (raw_price, raw_volume, price, volume):
                    out.append(
                        _finding(QaDomain.B, "B_RAW_ADJUSTED_PROOF_INVALID", QaStatus.FAIL, row)
                    )
                elif (
                    raw_price is not None
                    and raw_volume is not None
                    and price is not None
                    and volume is not None
                    and (
                        abs(raw_price * price_factor - price) > tolerance
                        or abs(raw_volume * volume_factor - volume) > tolerance
                    )
                ):
                    out.append(_finding(QaDomain.B, "B_RAW_ADJUSTED_CONFLICT", QaStatus.FAIL, row))
    if any(len(values) > 1 for values in modes.values()):
        out.append(_finding(QaDomain.B, "B_ADJUSTMENT_MIXING", QaStatus.FAIL))
    return out


def _check_pit_identity_universe(
    request: PitQaRequest,
    manifest: DatasetManifest,
    snapshot: ReferenceMappingSnapshot,
    rows: tuple[QaRow, ...],
) -> list[QaFinding]:
    out: list[QaFinding] = []
    universe = request.universe
    if universe is None:
        out.append(_finding(QaDomain.C, "C_UNIVERSE_EVIDENCE_MISSING", _INS))
    else:
        if (
            not universe.complete
            or not universe.survivorship_limits
            or (universe.start_ns > manifest.start_ns or universe.end_ns < manifest.end_ns)
        ):
            out.append(_finding(QaDomain.C, "C_UNIVERSE_INCOMPLETE", _INS))
        if not _ref_valid(universe.evidence, request.knowledge_ns):
            out.append(_finding(QaDomain.C, "C_UNIVERSE_CAUSAL_CONFLICT", QaStatus.FAIL))
        if universe.basis == HistoricalBasis.SYNTHETIC and not (
            request.synthetic_fixture and manifest.source_tier == "R0"
        ):
            out.append(_finding(QaDomain.C, "C_UNIVERSE_BASIS_UNPROVEN", _INS))
        for instrument in manifest.instruments:
            intervals = sorted(
                (start, end) for name, start, end, _ in universe.membership if name == instrument
            )
            cursor = manifest.start_ns
            for start, end in intervals:
                if start >= end:
                    out.append(_finding(QaDomain.C, "C_STATE_INTERVAL_INVALID", QaStatus.FAIL))
                if start > cursor:
                    out.append(_finding(QaDomain.C, "C_STATE_COVERAGE_MISSING", _INS))
                if start < cursor and cursor != manifest.start_ns:
                    out.append(_finding(QaDomain.C, "C_STATE_OVERLAP", QaStatus.FAIL))
                cursor = max(cursor, end)
            if cursor < manifest.end_ns:
                out.append(_finding(QaDomain.C, "C_STATE_COVERAGE_MISSING", _INS))
        for _, _, _, effective, ref in universe.continuity:
            if not _ref_valid(ref, request.knowledge_ns, effective):
                out.append(_finding(QaDomain.C, "C_CONTINUITY_CAUSAL_CONFLICT", QaStatus.FAIL))
    resolver = PitReferenceResolver(snapshot)
    for row in rows:
        s, aux = row.source, row.historical
        if aux is None or not aux.native_symbol:
            out.append(_finding(QaDomain.C, "C_NATIVE_SYMBOL_EVIDENCE_MISSING", _INS, row))
        if aux is None or not aux.price_unit or not aux.size_unit or not aux.source_role:
            out.append(_finding(QaDomain.C, "C_ROW_UNITS_ROLE_EVIDENCE_MISSING", _INS, row))
        try:
            mapping = resolver.resolve(
                s.provider,
                s.instrument_id,
                s.event_ns,
                request.knowledge_ns,
                production=not (request.synthetic_fixture and manifest.source_tier == "R0"),
            )
        except ControlReplan:
            out.append(_finding(QaDomain.C, "C_MAPPING_SUPPORT_UNPROVEN", _INS, row))
            continue
        except (ValueError, PermissionError):
            out.append(
                _finding(QaDomain.C, "C_MAPPING_MISSING_AMBIGUOUS_OR_STATE", QaStatus.FAIL, row)
            )
            continue
        if (
            aux
            and aux.native_symbol
            and (
                mapping.native_symbol != aux.native_symbol
                or mapping.venue != s.venue
                or mapping.product != s.product
                or (aux.price_unit is not None and mapping.price_unit != aux.price_unit)
                or (aux.size_unit is not None and mapping.size_unit != aux.size_unit)
                or (aux.source_role is not None and mapping.source_role != aux.source_role)
            )
        ):
            out.append(_finding(QaDomain.C, "C_MAPPING_ROW_CONFLICT", QaStatus.FAIL, row))
        if mapping.metadata_basis == "PROSPECTIVE" and s.event_ns < mapping.known_at:
            out.append(_finding(QaDomain.C, "C_CURRENT_METADATA_BACKFILL", QaStatus.FAIL, row))
        if universe:
            states = [
                state
                for name, start, end, state in universe.membership
                if name == s.instrument_id and start <= s.event_ns < end
            ]
            if len(states) != 1:
                out.append(
                    _finding(
                        QaDomain.C,
                        "C_ROW_STATE_EVIDENCE_MISSING",
                        _INS if not states else QaStatus.FAIL,
                        row,
                    )
                )
            elif states[0] != "LISTED":
                out.append(_finding(QaDomain.C, "C_ROW_NOT_LISTED", QaStatus.FAIL, row))
    # A symbol change is asserted by historical mapping intervals, not inferred
    # from missing row symbols or a present-day roster.
    for instrument in manifest.instruments:
        mappings = sorted(
            (
                m
                for m in snapshot.records
                if m.instrument_id == instrument
                and m.valid_from < manifest.end_ns
                and m.valid_to > manifest.start_ns
            ),
            key=lambda m: (m.provider, m.valid_from, m.record_hash),
        )
        for left, right in pairwise(mappings):
            if left.provider == right.provider and left.native_symbol != right.native_symbol:
                if universe is None or not any(
                    name == instrument
                    and old == left.native_symbol
                    and new == right.native_symbol
                    and effective == right.valid_from
                    for name, old, new, effective, _ in universe.continuity
                ):
                    out.append(_finding(QaDomain.C, "C_SYMBOL_CONTINUITY_MISSING", _INS))
    return out


def _market_fact(row: QaRow) -> tuple[object, ...]:
    s = row.source
    return (
        s.values,
        s.sequence,
        s.source_ts,
        s.source_unit,
        s.bar_start_ns,
        s.bar_end_ns,
        s.timestamp_meaning,
    )


def _check_rows(request: PitQaRequest, rows: tuple[QaRow, ...]) -> list[QaFinding]:
    out: list[QaFinding] = []
    native: dict[tuple[object, ...], QaRow] = {}
    bars: dict[tuple[object, ...], QaRow] = {}
    latest: dict[tuple[str, ...], QaRow] = {}
    outlier_latest: dict[tuple[str, ...], tuple[QaRow, int]] = {}
    sequence_runs: dict[tuple[str, ...], int] = {}
    by_hash = {r.key.input_record_hash: r for r in rows}
    tolerance = _number(request.policy.comparison_tolerance)
    if tolerance is None or tolerance < 0:
        out.append(_finding(QaDomain.D, "D_COMPARISON_TOLERANCE_INVALID", QaStatus.FAIL))
    outlier = request.policy.outlier
    if outlier is None:
        out.append(_finding(QaDomain.D, "D_OUTLIER_POLICY_UNKNOWN", QaStatus.UNKNOWN))
    elif not _ref_valid(outlier.evidence, request.knowledge_ns):
        out.append(_finding(QaDomain.D, "D_OUTLIER_POLICY_CAUSAL_CONFLICT", QaStatus.FAIL))
    thresholds = (
        tuple(
            _number(v) if v is not None else None
            for v in (
                outlier.minimum_price,
                outlier.maximum_price,
                outlier.maximum_adjacent_relative_change,
            )
        )
        if outlier
        else (None, None, None)
    )
    if outlier and (
        any(
            v is not None and _number(v) is None
            for v in (
                outlier.minimum_price,
                outlier.maximum_price,
                outlier.maximum_adjacent_relative_change,
            )
        )
        or (
            thresholds[0] is not None
            and thresholds[1] is not None
            and thresholds[0] > thresholds[1]
        )
        or (thresholds[2] is not None and thresholds[2] < 0)
    ):
        out.append(_finding(QaDomain.D, "D_OUTLIER_POLICY_INVALID", QaStatus.FAIL))
    required: dict[str, set[str]] = {
        "BAR": {"open", "high", "low", "close", "volume"},
        "TRADE": {"price", "size"},
        "BBO": {"bid", "ask", "bid_size", "ask_size"},
        "CONTEXT": {"value"},
        "OI": {"oi", "oi_ccy", "oi_usd"},
    }
    for row in rows:
        s, aux = row.source, row.historical
        identity = (*_stream(row), s.native_id)
        previous = native.get(identity)
        if previous:
            if _market_fact(previous) == _market_fact(row):
                out.append(
                    _finding(
                        QaDomain.D,
                        "D_EXACT_DUPLICATE",
                        QaStatus(request.policy.duplicate_severity),
                        row,
                    )
                )
            else:
                out.append(_finding(QaDomain.D, "D_CONFLICTING_DUPLICATE", QaStatus.FAIL, row))
            old = previous.historical
            if (
                old
                and aux
                and (
                    old.native_symbol,
                    old.adjustment_mode,
                    old.adjustment_basis,
                    old.price_unit,
                    old.size_unit,
                    old.source_role,
                )
                != (
                    aux.native_symbol,
                    aux.adjustment_mode,
                    aux.adjustment_basis,
                    aux.price_unit,
                    aux.size_unit,
                    aux.source_role,
                )
            ):
                out.append(_finding(QaDomain.D, "D_AUXILIARY_FACT_CONFLICT", QaStatus.FAIL, row))
        native[identity] = row
        if s.payload_kind == "BAR":
            slot = (*_stream(row), s.bar_start_ns, s.bar_end_ns, s.timestamp_meaning)
            if slot in bars and bars[slot].source.native_id != s.native_id:
                out.append(_finding(QaDomain.D, "D_BAR_SLOT_CONFLICT", QaStatus.FAIL, row))
            bars[slot] = row
        values: dict[str, Decimal | None] = {k: _number(v) for k, v in s.values}
        if len(values) != len(s.values) or set(values) != required.get(s.payload_kind):
            out.append(_finding(QaDomain.D, "D_PAYLOAD_FIELDS_INVALID", QaStatus.FAIL, row))
        if any(v is None for v in values.values()):
            out.append(_finding(QaDomain.D, "D_NONFINITE_OR_MALFORMED", QaStatus.FAIL, row))
        for key, value in values.items():
            if value is None:
                continue
            if key in {"open", "high", "low", "close", "price", "bid", "ask"} and value <= 0:
                out.append(_finding(QaDomain.D, "D_NONPOSITIVE_PRICE", QaStatus.FAIL, row))
            if (
                key in {"volume", "size", "bid_size", "ask_size", "oi", "oi_ccy", "oi_usd"}
                and value < 0
            ):
                out.append(_finding(QaDomain.D, "D_NEGATIVE_SIZE", QaStatus.FAIL, row))
        if s.payload_kind == "BAR" and all(
            values.get(k) is not None for k in ("open", "high", "low", "close")
        ):
            low, high, opening, close = (values[k] for k in ("low", "high", "open", "close"))
            assert (
                low is not None and high is not None and opening is not None and close is not None
            )
            if not low <= min(opening, close) <= max(opening, close) <= high:
                out.append(_finding(QaDomain.D, "D_OHLC_CONFLICT", QaStatus.FAIL, row))
        if s.payload_kind == "CONTEXT":
            if s.context_field is None:
                out.append(_finding(QaDomain.D, "D_CONTEXT_SEMANTICS_MISSING", _INS, row))
            elif s.context_field in {"MARK", "INDEX", "ORACLE"} and values.get("value") is not None:
                context_price = values["value"]
                if context_price is not None and context_price <= 0:
                    out.append(_finding(QaDomain.D, "D_NONPOSITIVE_PRICE", QaStatus.FAIL, row))
        if s.payload_kind == "BBO":
            bid, ask = values.get("bid"), values.get("ask")
            if bid is not None and ask is not None and bid > ask:
                out.append(_finding(QaDomain.D, "D_CROSSED_BBO", QaStatus.FAIL, row))
        prior = latest.get(_stream(row))
        if request.policy.sequence_semantics == "UNKNOWN":
            out.append(_finding(QaDomain.D, "D_SEQUENCE_UNKNOWN", QaStatus.UNKNOWN, row))
        elif request.policy.sequence_semantics == "CONTIGUOUS":
            if s.sequence is None:
                out.append(_finding(QaDomain.D, "D_SEQUENCE_EVIDENCE_MISSING", _INS, row))
            elif (
                prior
                and prior.source.sequence is not None
                and s.sequence != prior.source.sequence + 1
            ):
                out.append(_finding(QaDomain.D, "D_SEQUENCE_DISCONTINUITY", QaStatus.FAIL, row))
        if aux is None or not aux.price_unit or not aux.size_unit:
            out.append(_finding(QaDomain.D, "D_ROW_UNITS_EVIDENCE_MISSING", _INS, row))
        if aux is None or aux.revision is None:
            out.append(_finding(QaDomain.D, "D_REVISION_EVIDENCE_MISSING", _INS, row))
        else:
            rev = aux.revision
            if rev.state == RevisionState.UNKNOWN:
                out.append(_finding(QaDomain.D, "D_REVISION_UNKNOWN", QaStatus.UNKNOWN, row))
            elif rev.state == RevisionState.UNREVISED and rev.predecessor_input_hash is not None:
                out.append(
                    _finding(QaDomain.D, "D_REVISION_ASSERTION_CONFLICT", QaStatus.FAIL, row)
                )
            elif rev.state == RevisionState.REVISED:
                predecessor = by_hash.get(rev.predecessor_input_hash or "")
                if request.policy.revision_policy == "REJECT_REVISED":
                    out.append(_finding(QaDomain.D, "D_REVISED_ROW_REJECTED", QaStatus.FAIL, row))
                elif (
                    predecessor is None
                    or predecessor is row
                    or _stream(predecessor) != _stream(row)
                    or predecessor.source.event_ns != s.event_ns
                    or predecessor.historical is None
                    or predecessor.historical.revision is None
                    or predecessor.historical.revision.available_at_ns >= rev.available_at_ns
                ):
                    out.append(
                        _finding(QaDomain.D, "D_REVISION_CHAIN_CONFLICT", QaStatus.FAIL, row)
                    )
        if aux is None or aux.comparison is None:
            out.append(_finding(QaDomain.D, "D_COMPARISON_EVIDENCE_MISSING", _INS, row))
        else:
            comparison = aux.comparison
            if comparison.disposition == EvidenceDisposition.UNKNOWN:
                out.append(_finding(QaDomain.D, "D_COMPARISON_UNKNOWN", QaStatus.UNKNOWN, row))
            elif comparison.disposition == EvidenceDisposition.EXPLICIT_NOT_APPLICABLE:
                if (
                    comparison.comparison_group_id is not None
                    or comparison.counterpart_input_hashes
                ):
                    out.append(
                        _finding(
                            QaDomain.D, "D_COMPARISON_APPLICABILITY_CONFLICT", QaStatus.FAIL, row
                        )
                    )
            elif not comparison.comparison_group_id or not comparison.counterpart_input_hashes:
                out.append(_finding(QaDomain.D, "D_COMPARISON_IDENTITY_MISSING", _INS, row))
            else:
                for counterpart_hash in comparison.counterpart_input_hashes:
                    counterpart = by_hash.get(counterpart_hash)
                    other = counterpart.historical if counterpart else None
                    if counterpart is None or other is None or other.comparison is None:
                        out.append(
                            _finding(QaDomain.D, "D_COMPARISON_COUNTERPART_MISSING", _INS, row)
                        )
                        continue
                    if (
                        counterpart.source.provider == s.provider
                        or counterpart.source.instrument_id != s.instrument_id
                        or counterpart.source.event_ns != s.event_ns
                        or counterpart.source.payload_kind != s.payload_kind
                        or other.comparison.comparison_group_id != comparison.comparison_group_id
                        or row.key.input_record_hash
                        not in other.comparison.counterpart_input_hashes
                        or (
                            aux.price_unit,
                            aux.size_unit,
                            aux.adjustment_mode,
                            aux.adjustment_basis,
                        )
                        != (
                            other.price_unit,
                            other.size_unit,
                            other.adjustment_mode,
                            other.adjustment_basis,
                        )
                    ):
                        out.append(
                            _finding(
                                QaDomain.D, "D_COMPARISON_BINDING_CONFLICT", QaStatus.FAIL, row
                            )
                        )
                        continue
                    for name, value in values.items():
                        other_values: dict[str, str] = dict(counterpart.source.values)
                        other_value = _number(other_values.get(name))
                        if value is None or other_value is None or tolerance is None:
                            out.append(
                                _finding(QaDomain.D, "D_COMPARISON_VALUES_UNPROVEN", _INS, row)
                            )
                        elif abs(value - other_value) > tolerance:
                            out.append(
                                _finding(
                                    QaDomain.D,
                                    "D_PROVIDER_DISAGREEMENT",
                                    QaStatus(request.policy.disagreement_severity),
                                    row,
                                )
                            )
        price_fields = {
            "BAR": ("open", "high", "low", "close"),
            "TRADE": ("price",),
            "BBO": ("bid", "ask"),
        }.get(s.payload_kind, ())
        if s.payload_kind == "CONTEXT" and s.context_field in {"MARK", "INDEX", "ORACLE"}:
            price_fields = ("value",)
        stream = _stream(row)
        sequence_run = sequence_runs.get(stream, 0)
        if prior and (
            s.sequence is None
            or prior.source.sequence is None
            or s.sequence != prior.source.sequence + 1
        ):
            sequence_run += 1
        sequence_runs[stream] = sequence_run
        price_stream = (*stream, (s.context_field or "") if s.payload_kind == "CONTEXT" else "")
        price_history = outlier_latest.get(price_stream)
        price_prior = price_history[0] if price_history else None
        if outlier and price_fields:
            if aux is None or aux.price_unit != outlier.price_unit:
                out.append(_finding(QaDomain.D, "D_OUTLIER_UNITS_UNPROVEN", _INS, row))
            lower, upper, relative = thresholds
            for field in price_fields:
                price = values.get(field)
                if price is not None and (
                    (lower is not None and price < lower) or (upper is not None and price > upper)
                ):
                    out.append(
                        _finding(QaDomain.D, "D_OUTLIER_BOUND", QaStatus(outlier.severity), row)
                    )
            if price_prior and relative is not None:
                if s.payload_kind == "BAR":
                    contiguous = price_prior.source.bar_end_ns == s.bar_start_ns
                elif s.payload_kind == "CONTEXT":
                    # Same-context history selects the predecessor; only the shared run
                    # proves continuity across all intervening CONTEXT observations.
                    contiguous = price_history is not None and price_history[1] == sequence_run
                else:
                    contiguous = (
                        s.sequence is not None
                        and price_prior.source.sequence is not None
                        and s.sequence == price_prior.source.sequence + 1
                    )
                same_session = bool(
                    request.sessions
                    and any(
                        i.instrument_id == s.instrument_id
                        and i.open_ns <= price_prior.source.event_ns <= s.event_ns < i.close_ns
                        for i in request.sessions.open_intervals
                    )
                )
                if contiguous and (outlier.compare_across_sessions or same_session):
                    old_values: dict[str, str] = dict(price_prior.source.values)
                    adjacent_fields = ("close",) if s.payload_kind == "BAR" else price_fields
                    for field in adjacent_fields:
                        price, old_price = values.get(field), _number(old_values.get(field))
                        if price is not None and old_price is not None and old_price > 0:
                            if abs(price / old_price - 1) > relative:
                                out.append(
                                    _finding(
                                        QaDomain.D,
                                        "D_OUTLIER_ADJACENT",
                                        QaStatus(outlier.severity),
                                        row,
                                    )
                                )
        if price_fields:
            outlier_latest[price_stream] = (row, sequence_run)
        latest[_stream(row)] = row
    return out


def _check_gaps(
    request: PitQaRequest,
    manifest: DatasetManifest,
    rows: tuple[QaRow, ...],
) -> tuple[list[QaFinding], tuple[CoverageDiagnostic, ...]]:
    out: list[QaFinding] = []
    diagnostics: list[CoverageDiagnostic] = []
    schedule = request.sessions
    if schedule is None:
        return [_finding(QaDomain.E, "E_CALENDAR_EVIDENCE_MISSING", _INS)], ()
    if (
        not schedule.complete
        or schedule.start_ns > manifest.start_ns
        or schedule.end_ns < manifest.end_ns
        or set(schedule.instrument_ids) != set(manifest.instruments)
    ):
        out.append(_finding(QaDomain.E, "E_CALENDAR_COVERAGE_INCOMPLETE", _INS))
    if schedule.cadence_ns <= 0:
        return [_finding(QaDomain.E, "E_CADENCE_INVALID", QaStatus.FAIL)], ()
    if any(r.source.payload_kind != "BAR" for r in rows):
        # A timestamp gap alone cannot establish continuity of trades or quotes.
        out.append(_finding(QaDomain.E, "E_NONBAR_CONTINUITY_UNPROVEN", _INS))
    total_expected = 0
    for instrument in manifest.instruments:
        expected: set[tuple[int, int]] = set()
        gaps: list[tuple[int, int, GapKind]] = []
        intervals = sorted(
            (
                i
                for i in (*schedule.open_intervals, *schedule.closed_intervals)
                if i.instrument_id == instrument
            ),
            key=lambda i: (i.open_ns, i.close_ns, i.session_id),
        )
        cursor = manifest.start_ns
        for interval in intervals:
            start, end = (
                max(interval.open_ns, manifest.start_ns),
                min(interval.close_ns, manifest.end_ns),
            )
            if start >= end:
                continue
            if start > cursor:
                gaps.append((cursor, start, GapKind.DATA_MISSING_OR_UNKNOWN))
                out.append(
                    _finding(
                        QaDomain.E, "E_UNEXPLAINED_CALENDAR_SPACE", _INS, interval=(cursor, start)
                    )
                )
            cursor = max(cursor, end)
            if interval in schedule.closed_intervals:
                gaps.append((start, end, GapKind.SESSION_EXPLAINED))
                out.append(
                    _finding(
                        QaDomain.E,
                        "E_SESSION_EXPLAINED_GAP",
                        QaStatus.PASS,
                        refs=(interval.evidence,),
                        interval=(start, end),
                    )
                )
                continue
            cadence = schedule.cadence_ns
            first = start + (schedule.grid_origin_ns - start) % cadence
            if first != start or (end - schedule.grid_origin_ns) % cadence:
                gaps.append((start, end, GapKind.PARTIAL_BOUNDARY))
                out.append(_finding(QaDomain.E, "E_PARTIAL_BOUNDARY", _INS, interval=(start, end)))
            count = max(0, (end - first) // cadence)
            total_expected += count
            if total_expected > request.policy.max_expected_intervals:
                return [*out, _finding(QaDomain.E, "E_RESOURCE_BOUND_EXCEEDED", _INS)], tuple(
                    diagnostics
                )
            for left in range(first, first + count * cadence, cadence):
                right = left + cadence
                states = (
                    [
                        state
                        for name, a, b, state in request.universe.membership
                        if name == instrument and a <= left < right <= b
                    ]
                    if request.universe
                    else []
                )
                if len(states) == 1 and states[0] in ("HALTED", "DELISTED"):
                    gaps.append((left, right, GapKind.STATE_EXPLAINED))
                    out.append(
                        _finding(
                            QaDomain.E,
                            "E_STATE_EXPLAINED_GAP",
                            QaStatus.PASS,
                            interval=(left, right),
                        )
                    )
                else:
                    expected.add((left, right))
        if cursor < manifest.end_ns:
            gaps.append((cursor, manifest.end_ns, GapKind.DATA_MISSING_OR_UNKNOWN))
            out.append(
                _finding(
                    QaDomain.E,
                    "E_UNEXPLAINED_CALENDAR_SPACE",
                    _INS,
                    interval=(cursor, manifest.end_ns),
                )
            )
        observed: set[tuple[int, int]] = set()
        invalid = duplicates = 0
        for row in rows:
            s = row.source
            if s.instrument_id != instrument or s.payload_kind != "BAR":
                continue
            row_left, row_right = s.bar_start_ns, s.bar_end_ns
            if row_left is None or row_right is None:
                invalid += 1
                continue
            slot = (row_left, row_right)
            numeric = dict(s.values)
            parsed: dict[str, Decimal | None] = {k: _number(v) for k, v in numeric.items()}
            valid = (
                slot in expected
                and s.interval_ns == schedule.cadence_ns
                and s.finalized is True
                and set(parsed) == {"open", "high", "low", "close", "volume"}
                and all(v is not None for v in parsed.values())
            )
            if valid:
                low, high, opening, close, volume = (
                    parsed[k] for k in ("low", "high", "open", "close", "volume")
                )
                assert (
                    low is not None
                    and high is not None
                    and opening is not None
                    and close is not None
                    and volume is not None
                )
                valid = (
                    0 < low <= min(opening, close) <= max(opening, close) <= high and volume >= 0
                )
            if not valid:
                invalid += 1
                out.append(
                    _finding(QaDomain.E, "E_ROW_GRID_OR_INTEGRITY_CONFLICT", QaStatus.FAIL, row)
                )
            elif slot in observed:
                duplicates += 1
            else:
                observed.add(slot)
        for missing in sorted(expected - observed):
            gaps.append((*missing, GapKind.IN_SESSION_MISSING))
            out.append(
                _finding(
                    QaDomain.E,
                    "E_IN_SESSION_MISSING",
                    QaStatus(request.policy.missing_bar_severity),
                    interval=missing,
                )
            )
        diagnostics.append(
            CoverageDiagnostic(
                instrument_id=instrument,
                cut=(manifest.start_ns, manifest.end_ns),
                expected=len(expected),
                present_unique=len(observed),
                missing=len(expected - observed),
                invalid=invalid,
                duplicates=duplicates,
                first_expected_ns=min((a for a, _ in expected), default=None),
                last_expected_ns=max((b for _, b in expected), default=None),
                first_observed_ns=min((a for a, _ in observed), default=None),
                last_observed_ns=max((b for _, b in observed), default=None),
                gaps=tuple(sorted(gaps)),
            )
        )
    return out, tuple(diagnostics)


def _check_provenance(
    request: PitQaRequest,
    manifest: DatasetManifest,
    rows: tuple[QaRow, ...],
) -> list[QaFinding]:
    out: list[QaFinding] = []
    metadata = dict(manifest.metadata)
    if set(metadata) != REQUIRED_DATASET_METADATA:
        out.append(_finding(QaDomain.F, "F_METADATA_KEYS_INCOMPLETE", QaStatus.FAIL))
    for _key, value in manifest.metadata:
        if value.upper().startswith("UNKNOWN"):
            out.append(_finding(QaDomain.F, "F_METADATA_UNKNOWN", QaStatus.UNKNOWN, refs=()))
        elif value.upper().startswith(("N/A", "NOT_APPLICABLE")):
            out.append(_finding(QaDomain.F, "F_METADATA_APPLICABILITY_UNPROVEN", _INS))
    # These declarations are references to evidence, never facts copied into rows.
    declarations = {
        "symbol_mapping": manifest.mapping_hash,
        "session_calendar_version": request.sessions.calendar_version if request.sessions else None,
        "missing_bar_policy": request.policy.missing_bar_severity,
        "duplicate_policy": request.policy.duplicate_severity,
        "provider_disagreement_policy": request.policy.disagreement_severity,
        "bad_tick_policy": request.policy.outlier.record_hash if request.policy.outlier else None,
        "point_in_time_universe": request.universe.record_hash if request.universe else None,
        "delisting_status": request.universe.record_hash if request.universe else None,
        "trading_halt_status": request.universe.record_hash if request.universe else None,
        "data_revision_status": request.policy.revision_policy,
        "timezone_dst_policy": "EXPLICIT_FOLD_OFFSET_ROUNDTRIP",
        "dividend_policy": "NO_DIVIDEND_TRANSFORMATION_PROVEN",
        "corporate_action_policy": "EXPLICIT_ACTION_COVERAGE",
        "split_adjustment_policy": ",".join(sorted({a.mode.value for a in request.adjustments})),
    }
    for key, actual in declarations.items():
        if actual is not None and metadata.get(key) != actual:
            out.append(_finding(QaDomain.F, "F_METADATA_EVIDENCE_CONFLICT", QaStatus.FAIL))
    if not _ref_valid(request.policy.evidence, request.knowledge_ns):
        out.append(_finding(QaDomain.F, "F_POLICY_CAUSAL_CONFLICT", QaStatus.FAIL))
    binding = request.source_binding
    if binding is None:
        out.append(_finding(QaDomain.F, "F_SOURCE_BINDING_MISSING", _INS))
    else:
        if (
            binding.dataset_hash != manifest.record_hash
            or binding.checksum != manifest.checksum
            or binding.source_locator != manifest.source_locator
            or binding.evidence.content_hash != manifest.checksum
        ):
            out.append(_finding(QaDomain.F, "F_SOURCE_BINDING_CONFLICT", QaStatus.FAIL))
        if not _ref_valid(binding.evidence, request.knowledge_ns):
            out.append(_finding(QaDomain.F, "F_SOURCE_CAUSAL_CONFLICT", QaStatus.FAIL))
        if binding.source_bytes_hex is None:
            out.append(_finding(QaDomain.F, "F_SOURCE_CHECKSUM_UNVERIFIED", _INS))
        else:
            try:
                raw = bytes.fromhex(binding.source_bytes_hex)
                if sha256_hex(raw) != binding.checksum:
                    out.append(_finding(QaDomain.F, "F_SOURCE_CHECKSUM_CONFLICT", QaStatus.FAIL))
            except ValueError:
                out.append(_finding(QaDomain.F, "F_SOURCE_BYTES_INVALID", QaStatus.FAIL))
    for row in rows:
        aux = row.historical
        if aux is None or aux.projection_proof is None:
            out.append(_finding(QaDomain.F, "F_ROW_PROJECTION_EVIDENCE_MISSING", _INS, row))
        else:
            proof = aux.projection_proof
            if (
                binding is None
                or _digest(proof.model_dump(mode="json")) not in binding.projection_proof_hashes
            ):
                out.append(_finding(QaDomain.F, "F_PROJECTION_SUPPORT_MISSING", _INS, row))
            if (
                proof.source_locator != manifest.source_locator
                or proof.source_content_hash != manifest.checksum
            ):
                out.append(_finding(QaDomain.F, "F_PROJECTION_SOURCE_CONFLICT", QaStatus.FAIL, row))
        if aux is None or not aux.price_unit or not aux.size_unit or not aux.source_role:
            out.append(_finding(QaDomain.F, "F_ROW_UNITS_ROLE_EVIDENCE_MISSING", _INS, row))
    return out


def _build_result(
    findings: list[QaFinding],
    coverage: tuple[CoverageDiagnostic, ...],
    bindings: tuple[tuple[str, str], ...],
) -> PitQaResult:
    domains: list[QaDomainResult] = []
    for domain in QaDomain:
        selected = [f for f in findings if f.domain == domain]
        if not selected:
            selected = [
                _finding(domain, f"{domain.value}_REQUIRED_CHECKS_ESTABLISHED", QaStatus.PASS)
            ]
        selected.sort(
            key=lambda f: (
                f.predicate,
                f.instrument_id or "",
                f.interval or (0, 0),
                f.ordinals,
                f.reason_code,
                f.evidence_locators,
            )
        )
        domains.append(
            QaDomainResult(
                domain=domain,
                findings=tuple(selected),
                status=_aggregate_status(tuple(f.status for f in selected)),
            )
        )
    return PitQaResult.create(
        version="PIT_QA_V1",
        domains=tuple(domains),
        overall_qa_eligibility=_aggregate_status(tuple(d.status for d in domains)),
        coverage=coverage,
        input_bindings=bindings,
    )


def evaluate_pit_qa(request: PitQaRequest) -> PitQaResult:
    """Evaluate caller-supplied metadata/rows; never open a locator or grant access.

    Invalid bound input returns a deterministic failed receipt. Schema violations
    are rejected by the closed request contract before evaluation.
    """
    bindings: tuple[tuple[str, str], ...] = (("request", _digest(request.model_dump(mode="json"))),)
    try:
        request = PitQaRequest.model_validate_json(request.model_dump_json())
        manifest = (
            DatasetManifest.model_validate_json(request.manifest)
            if isinstance(request.manifest, str)
            else request.manifest
        )
        snapshot = (
            ReferenceMappingSnapshot.model_validate_json(request.snapshot)
            if isinstance(request.snapshot, str)
            else request.snapshot
        )
    except (ValidationError, ValueError):
        return _build_result(
            [_finding(QaDomain.F, "F_BOUND_INPUT_INVALID", QaStatus.FAIL)]
            + [
                _finding(d, f"{d.value}_INPUT_UNAVAILABLE", _INS)
                for d in QaDomain
                if d != QaDomain.F
            ],
            (),
            bindings,
        )
    if bool(request.events) == bool(request.diagnostic_records):
        return _build_result(
            [_finding(d, f"{d.value}_ROW_SURFACE_MISSING_OR_AMBIGUOUS", _INS) for d in QaDomain],
            (),
            bindings,
        )
    if len(request.events or ()) + len(request.diagnostic_records or ()) > request.policy.max_rows:
        return _build_result(
            [_finding(d, f"{d.value}_RESOURCE_BOUND_EXCEEDED", _INS) for d in QaDomain],
            (),
            bindings,
        )
    synthetic = request.synthetic_fixture and manifest.source_tier == "R0"
    if request.events:
        original = qa_rows_from_events(request.events, knowledge_ns=request.knowledge_ns)
        projection = _bind_historical_row_evidence(
            original.rows, request.historical_evidence, allow_synthetic=synthetic
        )
    else:
        projection = _project_diagnostic_records(
            request.diagnostic_records or (),
            request.knowledge_ns,
            request.historical_evidence,
            synthetic,
        )
    rows = projection.rows
    findings = list(projection.bridge_findings)
    findings.extend(_validate_input_bindings(manifest, snapshot, rows))
    with localcontext(DefaultContext) as context:
        context.prec = 50
        context.Emax = 30_000_000
        context.Emin = -30_000_000
        context.rounding = ROUND_HALF_EVEN
        findings.extend(_check_time_sessions(request, manifest, rows))
        findings.extend(_check_corporate_actions(request, rows))
        findings.extend(_check_pit_identity_universe(request, manifest, snapshot, rows))
        findings.extend(_check_rows(request, rows))
        gaps, coverage = _check_gaps(request, manifest, rows)
        findings.extend(gaps)
        findings.extend(_check_provenance(request, manifest, rows))
    bindings += tuple((f"input/{n}", h) for n, h in enumerate(projection.input_record_hashes))
    bindings += tuple(
        (f"auxiliary/{n}", a.record_hash) for n, a in enumerate(request.historical_evidence)
    )
    bindings += tuple((f"action/{n}", a.record_hash) for n, a in enumerate(request.actions))
    bindings += tuple((f"adjustment/{n}", a.record_hash) for n, a in enumerate(request.adjustments))
    for name, bound in (
        ("sessions", request.sessions),
        ("universe", request.universe),
        ("source", request.source_binding),
    ):
        if bound is not None:
            bindings += ((name, bound.record_hash),)
    bindings += (
        ("manifest", manifest.record_hash),
        ("mapping", snapshot.record_hash),
        ("policy", request.policy.record_hash),
        ("projection", _digest(projection.model_dump(mode="json"))),
    )
    return _build_result(findings, coverage, bindings)
