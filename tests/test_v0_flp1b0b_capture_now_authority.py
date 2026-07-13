from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, TypeAdapter, ValidationError

from trader_assist_v0.contracts import (
    CAPTURE_CONTRACT_VERSION,
    CaptureCheckpointV0,
    CaptureEndpointAllowlistV0,
    CaptureKillStateV0,
    CaptureLifecycleEventV0,
    CaptureLocalSafetyPolicyV0,
    CaptureManifestEntryV0,
    CapturePlanV0,
    CaptureRecordV0,
    CaptureReplayReportV0,
    HumanObservationV0,
    MarketPathEvidenceV0,
    ProducerIdentityV0,
    RuntimeControlEventV0,
    ShadowOrderIntentV0,
    SignalCaptureV0,
    build_capture_replay_report,
    validate_capture_checkpoint,
    validate_capture_checkpoint_advance,
    validate_capture_manifest_chain,
    validate_capture_record_graph,
    validate_capture_replay_report,
)
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_SCHEMA_PATH = ROOT / "schemas" / "v0" / "CaptureRecordV0.schema.json"

EXPECTED_OBJECTS = (
    "ProducerIdentityV0",
    "SignalCaptureV0",
    "CapturePlanV0",
    "ShadowOrderIntentV0",
    "HumanObservationV0",
    "MarketPathEvidenceV0",
    "CaptureLifecycleEventV0",
    "RuntimeControlEventV0",
    "CaptureRecordV0",
    "CaptureManifestEntryV0",
    "CaptureCheckpointV0",
    "CaptureReplayReportV0",
    "CaptureLocalSafetyPolicyV0",
    "CaptureEndpointAllowlistV0",
    "CaptureKillStateV0",
)


def _identity(domain: str) -> ProducerIdentityV0:
    return ProducerIdentityV0.bind(
        identity_domain=domain,
        producer_id=f"{domain.lower()}-1",
        display_name=domain,
    )


def _signal(kind: str = "LONG") -> SignalCaptureV0:
    return SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind=kind,
        observed_at_utc="2026-07-13T00:00:00Z",
    )


def _plan(kind: str = "LONG") -> CapturePlanV0:
    signal = _signal(kind)
    return CapturePlanV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_record_ref=signal.record_id,
        signal_kind=kind,
        evidence_refs=("evidence-1",),
    )


def _runtime_identity() -> ProducerIdentityV0:
    return _identity("RUNTIME_CONTROL_ACTOR")


def _mutated_payload(model: BaseModel, **updates: Any) -> dict[str, Any]:
    payload = BaseModel.model_dump(model, mode="python", round_trip=True)
    payload.update(updates)
    return payload


def _rebind_record(model: BaseModel, **updates: Any) -> Any:
    payload = BaseModel.model_dump(model, mode="python", round_trip=True)
    payload.pop("record_id")
    payload.pop("record_hash")
    payload.update(updates)
    return type(model).bind(**payload)


def _rebind_hash_model(model: BaseModel, **updates: Any) -> Any:
    payload = BaseModel.model_dump(model, mode="python", round_trip=True)
    payload.pop(type(model).hash_field)
    payload.update(updates)
    return type(model).bind(**payload)


def _market(
    *,
    series: str = "eth-series-1",
    sequence: int = 0,
    start: int = 0,
    end: int = 10,
    correction: str | None = None,
    supersession: str | None = None,
    source_identity: ProducerIdentityV0 | None = None,
) -> MarketPathEvidenceV0:
    return MarketPathEvidenceV0.bind(
        source_identity=source_identity or _identity("MARKET_PATH_SOURCE"),
        source_record_refs=(f"raw-{series}-{sequence}",),
        market_path_series_ref=series,
        window_start_ms=start,
        window_end_ms=end,
        chunk_sequence=sequence,
        correction_of_record_id=correction,
        supersedes_record_id=supersession,
    )


def _linked_signal_plan_shadow() -> tuple[
    MarketPathEvidenceV0,
    SignalCaptureV0,
    CapturePlanV0,
    ShadowOrderIntentV0,
]:
    evidence = _market()
    signal_seed = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T00:00:00Z",
        evidence_refs=(evidence.record_id,),
    )
    plan = CapturePlanV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_record_ref=signal_seed.record_id,
        signal_kind="LONG",
        evidence_refs=(evidence.record_id,),
    )
    shadow = ShadowOrderIntentV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        plan_record_ref=plan.record_id,
        evidence_refs=(evidence.record_id,),
    )
    signal = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T00:00:00Z",
        evidence_refs=(evidence.record_id,),
        plan_record_refs=(plan.record_id,),
        shadow_intent_refs=(shadow.record_id,),
    )
    assert signal.record_id == signal_seed.record_id
    return evidence, signal, plan, shadow


def _same_id_signal_versions() -> tuple[
    MarketPathEvidenceV0,
    SignalCaptureV0,
    SignalCaptureV0,
    CapturePlanV0,
]:
    evidence = _market()
    first = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T00:00:00Z",
        evidence_refs=(evidence.record_id,),
    )
    plan = CapturePlanV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_record_ref=first.record_id,
        signal_kind="LONG",
        evidence_refs=(evidence.record_id,),
    )
    second = _rebind_record(first, plan_record_refs=(plan.record_id,))
    assert first.record_id == second.record_id
    assert first.record_hash != second.record_hash
    return evidence, first, second, plan


def _manifest(
    entry_records: tuple[Any, ...],
    *,
    slots: tuple[str, ...] | None = None,
    classifications: tuple[str, ...] | None = None,
    writer_epoch: int = 7,
    writer_authority_ref: str = "capture-writer-1",
) -> tuple[CaptureManifestEntryV0, ...]:
    if slots is None:
        slots = tuple(f"slot-{index}" for index in range(len(entry_records)))
    seen_slots: dict[str, tuple[str, str]] = {}
    entries: list[CaptureManifestEntryV0] = []
    for index, (record, slot) in enumerate(zip(entry_records, slots, strict=True)):
        identity = (record.record_id, record.record_hash)
        expected = (
            "UNIQUE"
            if slot not in seen_slots
            else "EXACT_DUPLICATE"
            if seen_slots[slot] == identity
            else "CONFLICTING_DUPLICATE"
        )
        classification = expected if classifications is None else classifications[index]
        entry = CaptureManifestEntryV0.bind(
            entry_index=index,
            observation_slot_ref=slot,
            writer_epoch=writer_epoch,
            writer_authority_ref=writer_authority_ref,
            record_ref=record.record_id,
            record_hash=record.record_hash,
            duplicate_classification=classification,
            previous_manifest_entry_hash=(
                None if not entries else entries[-1].manifest_entry_hash
            ),
        )
        entries.append(entry)
        seen_slots.setdefault(slot, identity)
    return tuple(entries)


def _checkpoint(
    records: tuple[Any, ...],
    manifest: tuple[CaptureManifestEntryV0, ...],
) -> CaptureCheckpointV0:
    return CaptureCheckpointV0.bind(
        manifest_root_hash=manifest[0].manifest_entry_hash,
        terminal_manifest_entry_hash=manifest[-1].manifest_entry_hash,
        terminal_entry_index=manifest[-1].entry_index,
        manifest_entry_count=len(manifest),
        record_count=len({(record.record_id, record.record_hash) for record in records}),
        writer_epoch=manifest[0].writer_epoch,
        writer_authority_ref=manifest[0].writer_authority_ref,
    )


def test_exports_and_capture_record_schema_defs() -> None:
    import trader_assist_v0.contracts as contracts

    for name in EXPECTED_OBJECTS:
        assert getattr(contracts, name).__name__ == name

    schema = json.loads(CAPTURE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(EXPECTED_OBJECTS) <= set(schema["$defs"])
    assert schema["discriminator"]["propertyName"] == "record_type"

    record_types = {
        branch["$ref"].rsplit("/", 1)[-1] for branch in schema["oneOf"]
    }
    assert record_types == {
        "SignalCaptureV0",
        "CapturePlanV0",
        "ShadowOrderIntentV0",
        "HumanObservationV0",
        "MarketPathEvidenceV0",
        "CaptureLifecycleEventV0",
        "RuntimeControlEventV0",
        "CaptureKillStateV0",
    }


def test_signal_plan_shadow_wait_and_non_execution_boundaries() -> None:
    plan = _plan("LONG")
    assert plan.actionable is False
    assert plan.executable is False
    assert plan.exchange_submission_authorized is False
    assert CaptureRecordV0.model_validate(plan).root.record_type == "CAPTURE_PLAN"

    shadow = ShadowOrderIntentV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        plan_record_ref=plan.record_id,
        evidence_refs=("evidence-1",),
    )
    assert shadow.shadow_only is True
    assert shadow.executable is False
    assert shadow.exchange_submission_authorized is False

    wait = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="WAIT",
        observed_at_utc="2026-07-13T00:00:00Z",
        plan_record_refs=(plan.record_id,),
    )
    assert wait.signal_kind == "WAIT"

    with pytest.raises(ValidationError):
        SignalCaptureV0.bind(
            producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
            signal_kind="WAIT",
            observed_at_utc="2026-07-13T00:00:00Z",
            shadow_intent_refs=(shadow.record_id,),
        )
    with pytest.raises(ValidationError):
        CapturePlanV0.model_validate(_mutated_payload(plan, size="1"))
    with pytest.raises(ValidationError):
        ShadowOrderIntentV0.model_validate(_mutated_payload(shadow, real_order_id="abc"))


def test_identity_domains_are_separated() -> None:
    signal = _signal()
    with pytest.raises(ValidationError):
        SignalCaptureV0.bind(
            producer_identity=_identity("HUMAN_OPERATOR"),
            signal_kind="LONG",
            observed_at_utc="2026-07-13T00:00:00Z",
        )

    human = HumanObservationV0.bind(
        operator_identity=_identity("HUMAN_OPERATOR"),
        observed_record_refs=(signal.record_id,),
        observation_kind="NOTE",
        observation_text="operator note",
    )
    assert CaptureRecordV0.model_validate(human).root.record_type == "HUMAN_OBSERVATION"
    with pytest.raises(ValidationError):
        HumanObservationV0.bind(
            operator_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
            observed_record_refs=(signal.record_id,),
            observation_kind="NOTE",
            observation_text="bad identity",
        )

    market = MarketPathEvidenceV0.bind(
        source_identity=_identity("MARKET_PATH_SOURCE"),
        source_record_refs=(signal.record_id,),
        market_path_series_ref="eth-series-1",
        window_start_ms=1,
        window_end_ms=10,
        chunk_sequence=0,
        missing_ranges_ms=((3, 4), (7, 8)),
    )
    assert market.finalized_append_only_window is True
    with pytest.raises(ValidationError):
        MarketPathEvidenceV0.model_validate(_mutated_payload(market, pnl="1"))
    with pytest.raises(ValidationError):
        MarketPathEvidenceV0.bind(
            source_identity=_identity("MARKET_PATH_SOURCE"),
            source_record_refs=(signal.record_id,),
            market_path_series_ref="eth-series-1",
            window_start_ms=1,
            window_end_ms=10,
            chunk_sequence=0,
            missing_ranges_ms=((5, 7), (6, 8)),
        )


def test_lifecycle_runtime_control_and_kill_resume_are_separate() -> None:
    signal = _signal()
    lifecycle = CaptureLifecycleEventV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        event_kind="CAPTURE_RECORD_CREATED",
        subject_record_ref=signal.record_id,
        subject_record_type="SIGNAL_CAPTURE",
    )
    runtime = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="KILL_ENGAGED",
        runtime_scope_ref="capture-runtime-1",
        kill_state_ref="kill-state-1",
    )
    assert lifecycle.record_type != runtime.record_type
    assert lifecycle.record_hash != runtime.record_hash

    with pytest.raises(ValidationError):
        CaptureLifecycleEventV0.model_validate(
            _mutated_payload(lifecycle, event_kind="KILL_ENGAGED")
        )
    with pytest.raises(ValidationError):
        RuntimeControlEventV0.bind(
            supervisor_or_runtime_actor_identity=_runtime_identity(),
            event_kind="RESUME_PERMIT_ISSUED",
            runtime_scope_ref="capture-runtime-1",
        )

    killed = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        kill_state="KILLED_FAIL_CLOSED",
    )
    assert killed.fail_closed is True
    assert killed.runtime_authorized is False
    with pytest.raises(ValidationError):
        CaptureKillStateV0.bind(
            supervisor_or_runtime_actor_identity=_runtime_identity(),
            kill_state="RESUME_PERMITTED_AFTER_INTEGRITY_CHECK",
        )
    resumed = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        kill_state="RESUME_PERMITTED_AFTER_INTEGRITY_CHECK",
        single_use_permit_ref="permit-1",
        integrity_check_ref="integrity-1",
        runtime_control_event_ref=runtime.record_id,
    )
    assert resumed.resume_requires_single_use_permit is True


def test_manifest_checkpoint_replay_are_integrity_only() -> None:
    signal = _signal()
    records = (signal,)
    manifest = _manifest(records)
    entry = manifest[0]
    checkpoint = _checkpoint(records, manifest)
    report = build_capture_replay_report(records, manifest, checkpoint)
    assert entry.io_authorized is False
    assert checkpoint.io_authorized is False
    assert report.performance_adjudication_authorized is False
    assert report.promotion_judgment_authorized is False
    with pytest.raises(TypeError):
        CaptureReplayReportV0.bind(
            checkpoint_hash=checkpoint.checkpoint_hash,
            replay_status="PASS",
            verified_record_count=1,
        )
    with pytest.raises(ValidationError):
        CaptureReplayReportV0.model_validate(_mutated_payload(report, pnl="1"))


def test_local_safety_policy_and_endpoint_allowlist_are_exact() -> None:
    policy = CaptureLocalSafetyPolicyV0.bind()
    assert policy.policy_kind == "LOCAL_SAFETY_POLICY_NOT_OFFICIAL_FACT"
    assert policy.max_active_ws_connections == 1
    assert policy.connection_attempts_per_start_permit == 1
    assert policy.start_permit_manual is True
    assert policy.start_permit_single_use is True
    assert policy.start_permit_durable is True
    assert policy.start_permit_non_replayable is True
    assert policy.automatic_reconnect is False
    assert policy.automatic_backfill is False
    assert policy.active_network_probes is False
    assert policy.info_http_requests is False
    assert policy.official_hyperliquid_fact is False
    with pytest.raises(ValidationError):
        CaptureLocalSafetyPolicyV0.model_validate(_mutated_payload(policy, cooldown_seconds=1))

    allowlist = CaptureEndpointAllowlistV0.bind()
    assert allowlist.source_catalog_version == "hyperliquid-public-mainnet.0.1.0"
    assert allowlist.source_catalog_hash == (
        "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
    )
    assert allowlist.endpoint == "hl-ws-mainnet-public"
    assert allowlist.operation == "candle"
    assert allowlist.coin == "ETH"
    assert allowlist.intervals == ("5m", "15m")
    assert allowlist.runtime_authorized is False

    forbidden_updates = (
        {"coin": "BTC"},
        {"operation": "candleSnapshot"},
        {"intervals": ("1m", "5m")},
        {"runtime_authorized": True},
        {"endpoint": "hl-info-mainnet-public"},
        {"info_http_requests": True},
        {"backfill": True},
    )
    for update in forbidden_updates:
        with pytest.raises(ValidationError):
            CaptureEndpointAllowlistV0.model_validate(_mutated_payload(allowlist, **update))


def test_canonical_json_duplicate_bypass_and_hash_tampering_are_rejected() -> None:
    signal = _signal()
    canonical = canonical_json_bytes(signal)
    assert SignalCaptureV0.model_validate_json(canonical) == signal
    with pytest.raises(ValueError, match="canonical"):
        SignalCaptureV0.model_validate_json(canonical.replace(b":", b": ", 1))
    duplicate = canonical.replace(
        b'"record_type":"SIGNAL_CAPTURE"',
        b'"record_type":"SIGNAL_CAPTURE","record_type":"SIGNAL_CAPTURE"',
    )
    with pytest.raises(ValueError, match="duplicate"):
        SignalCaptureV0.model_validate_json(duplicate)

    with pytest.raises(TypeError):
        SignalCaptureV0.model_construct()
    with pytest.raises(TypeError):
        signal.model_copy()
    with pytest.raises(ValidationError):
        SignalCaptureV0.model_validate(_mutated_payload(signal, record_hash="0" * 64))
    with pytest.raises((TypeError, ValidationError, ValueError)):
        TypeAdapter(SignalCaptureV0).validate_json(canonical)
    stale = BaseModel.model_construct.__func__(
        SignalCaptureV0,
        **_mutated_payload(signal, observed_at_utc="2026-07-13T00:01:00Z"),
    )
    with pytest.raises(ValidationError):
        SignalCaptureV0.model_validate(stale)


def test_capture_schema_is_exact_and_plan_shadow_have_no_text_authority() -> None:
    schema = json.loads(CAPTURE_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(schema["$defs"]) == set(EXPECTED_OBJECTS)
    assert len(schema["$defs"]) == 15
    plan_properties = schema["$defs"]["CapturePlanV0"]["properties"]
    shadow_properties = schema["$defs"]["ShadowOrderIntentV0"]["properties"]
    assert "minimal_evidence_summary" not in plan_properties
    assert "intent_summary" not in shadow_properties
    assert "evidence_refs" in plan_properties
    assert "evidence_refs" in shadow_properties
    assert "hypothesis_kind" in shadow_properties
    for definition in schema["$defs"].values():
        if "properties" in definition:
            assert definition.get("additionalProperties") is False


@pytest.mark.parametrize(
    "field,value",
    (
        ("minimal_evidence_summary", "old text"),
        ("minimalEvidenceSummary", "alias"),
        ("metadata", {"entry": "1"}),
        ("parameters", '{"size":"1"}'),
        ("size", "1"),
        ("leverage", "2"),
        ("entry", "1"),
        ("SL", "1"),
        ("TP", "2"),
        ("order", "market"),
        ("submit", True),
        ("permit", "permit-1"),
    ),
)
def test_plan_rejects_free_text_aliases_metadata_and_execution_fields(
    field: str,
    value: Any,
) -> None:
    plan = _plan()
    with pytest.raises(ValidationError):
        CapturePlanV0.model_validate(_mutated_payload(plan, **{field: value}))


@pytest.mark.parametrize(
    "field,value",
    (
        ("intent_summary", "old text"),
        ("intentSummary", "alias"),
        ("metadata", {"order": "market"}),
        ("parameters", '{"permit":"x"}'),
        ("size", "1"),
        ("leverage", "2"),
        ("entry", "1"),
        ("SL", "1"),
        ("TP", "2"),
        ("order", "market"),
        ("submit", True),
        ("permit", "permit-1"),
    ),
)
def test_shadow_rejects_free_text_aliases_metadata_and_execution_fields(
    field: str,
    value: Any,
) -> None:
    shadow = ShadowOrderIntentV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        plan_record_ref="plan-1",
        evidence_refs=("evidence-1",),
    )
    with pytest.raises(ValidationError):
        ShadowOrderIntentV0.model_validate(_mutated_payload(shadow, **{field: value}))


def test_structured_signal_plan_shadow_graph_and_human_note_boundary() -> None:
    records = _linked_signal_plan_shadow()
    human = HumanObservationV0.bind(
        operator_identity=_identity("HUMAN_OPERATOR"),
        observed_record_refs=(records[1].record_id,),
        observation_kind="NOTE",
        observation_text="size=999 leverage=100 submit now",
    )
    all_records = (*records, human)
    manifest = _manifest(all_records)
    validate_capture_manifest_chain(all_records, manifest)
    validate_capture_record_graph(all_records, manifest)

    signal = records[1]
    broken_signal = _rebind_record(signal, plan_record_refs=())
    broken_records = (records[0], broken_signal, records[2], records[3], human)
    with pytest.raises(ValueError):
        validate_capture_record_graph(broken_records, _manifest(broken_records))

    wait_seed = _signal("WAIT")
    wait_plan = CapturePlanV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_record_ref=wait_seed.record_id,
        signal_kind="WAIT",
        evidence_refs=(records[0].record_id,),
    )
    wait_signal = _rebind_record(wait_seed, plan_record_refs=(wait_plan.record_id,))
    wait_shadow = ShadowOrderIntentV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        plan_record_ref=wait_plan.record_id,
        evidence_refs=(records[0].record_id,),
    )
    attacked = (records[0], wait_signal, wait_plan, wait_shadow)
    with pytest.raises(ValueError):
        validate_capture_record_graph(attacked, _manifest(attacked))

    missing_evidence_signal = _rebind_record(signal, evidence_refs=("missing-evidence",))
    missing_records = (
        records[0],
        missing_evidence_signal,
        records[2],
        records[3],
    )
    with pytest.raises(ValueError, match="signal evidence"):
        validate_capture_record_graph(missing_records, _manifest(missing_records))


def test_aggregate_apis_require_exact_tuples_and_concrete_models() -> None:
    records = (_signal(),)
    manifest = _manifest(records)
    checkpoint = _checkpoint(records, manifest)
    with pytest.raises(TypeError, match="exact tuple"):
        validate_capture_manifest_chain(list(records), manifest)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact tuple"):
        validate_capture_manifest_chain(records, list(manifest))  # type: ignore[arg-type]

    class SignalSubclass(SignalCaptureV0):
        pass

    subclass = BaseModel.model_construct.__func__(
        SignalSubclass,
        **BaseModel.model_dump(records[0], mode="python", round_trip=True),
    )
    with pytest.raises(TypeError, match="exact concrete"):
        validate_capture_manifest_chain((subclass,), manifest)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact CaptureCheckpointV0"):
        validate_capture_checkpoint(records, manifest, object())  # type: ignore[arg-type]
    assert build_capture_replay_report(records, manifest, checkpoint).replay_status == "PASS"


def test_manifest_chain_duplicate_semantics_and_fail_closed_attacks() -> None:
    first = _signal()
    second = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="SHORT",
        observed_at_utc="2026-07-13T00:01:00Z",
    )
    records = (first, second)
    manifest = _manifest(
        (first, first, second),
        slots=("slot-a", "slot-a", "slot-a"),
    )
    assert tuple(entry.duplicate_classification for entry in manifest) == (
        "UNIQUE",
        "EXACT_DUPLICATE",
        "CONFLICTING_DUPLICATE",
    )
    validate_capture_manifest_chain(records, manifest)

    wrong_classification = list(manifest)
    wrong_classification[1] = _rebind_hash_model(
        wrong_classification[1],
        duplicate_classification="UNIQUE",
    )
    with pytest.raises(ValueError, match="classification"):
        validate_capture_manifest_chain(records, tuple(wrong_classification))

    slot_escape = _manifest((first, first), slots=("slot-a", "slot-b"))
    with pytest.raises(ValueError, match="changing slot"):
        validate_capture_manifest_chain((first,), slot_escape)
    with pytest.raises(ValueError, match="duplicate record VERSION_KEY"):
        validate_capture_manifest_chain((first, first), _manifest((first,)))


def test_manifest_chain_rejects_position_link_writer_record_and_set_attacks() -> None:
    first, second = _signal(), _signal("SHORT")
    records = (first, second)
    manifest = _manifest(records)
    with pytest.raises(ValidationError):
        CaptureManifestEntryV0.bind(
            entry_index=0,
            observation_slot_ref="slot-0",
            writer_epoch=7,
            writer_authority_ref="writer",
            record_ref=first.record_id,
            record_hash=first.record_hash,
            duplicate_classification="UNIQUE",
            previous_manifest_entry_hash="0" * 64,
        )
    with pytest.raises(ValidationError):
        CaptureManifestEntryV0.bind(
            entry_index=1,
            observation_slot_ref="slot-1",
            writer_epoch=7,
            writer_authority_ref="writer",
            record_ref=second.record_id,
            record_hash=second.record_hash,
            duplicate_classification="UNIQUE",
            previous_manifest_entry_hash=None,
        )

    attacks = (
        (1, {"entry_index": 2}),
        (1, {"previous_manifest_entry_hash": "0" * 64}),
        (1, {"writer_epoch": 8}),
        (1, {"writer_authority_ref": "other-writer"}),
        (1, {"record_hash": first.record_hash}),
    )
    for index, update in attacks:
        attacked = list(manifest)
        attacked[index] = _rebind_hash_model(attacked[index], **update)
        with pytest.raises(ValueError):
            validate_capture_manifest_chain(records, tuple(attacked))
    with pytest.raises(ValueError, match="record-version set mismatch"):
        validate_capture_manifest_chain(records, _manifest((first,)))


def test_generic_correction_supersession_graph_rejects_invalid_relations() -> None:
    original = _signal()
    corrected = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T00:01:00Z",
        correction_of_record_id=original.record_id,
    )
    records = (original, corrected)
    validate_capture_record_graph(records, _manifest(records))

    missing = _rebind_record(corrected, correction_of_record_id="missing-record")
    with pytest.raises(ValueError):
        validate_capture_record_graph((original, missing), _manifest((original, missing)))
    cross_type_target = _market()
    cross_type = _rebind_record(corrected, correction_of_record_id=cross_type_target.record_id)
    attacked = (cross_type_target, original, cross_type)
    with pytest.raises(ValueError, match="same record_type"):
        validate_capture_record_graph(attacked, _manifest(attacked))
    both = _rebind_record(
        corrected,
        supersedes_record_id=original.record_id,
    )
    with pytest.raises(ValueError, match="cannot both"):
        validate_capture_record_graph((original, both), _manifest((original, both)))
    with pytest.raises(ValueError):
        validate_capture_record_graph((corrected, original), _manifest((corrected, original)))


def test_market_path_series_normal_and_correction_rules() -> None:
    first = _market()
    second = _market(sequence=1, start=10, end=20)
    correction = _market(
        sequence=1,
        start=10,
        end=20,
        correction=second.record_id,
    )
    records = (first, second, correction)
    validate_capture_record_graph(records, _manifest(records))

    attacks = (
        _market(sequence=2, start=10, end=20),
        _market(sequence=1, start=9, end=20),
        _market(
            sequence=1,
            start=10,
            end=21,
            correction=second.record_id,
        ),
        _market(
            series="other-series",
            sequence=1,
            start=10,
            end=20,
            correction=second.record_id,
        ),
        _market(
            sequence=1,
            start=10,
            end=20,
            correction=second.record_id,
            source_identity=ProducerIdentityV0.bind(
                identity_domain="MARKET_PATH_SOURCE",
                producer_id="other-source",
                display_name="other-source",
            ),
        ),
    )
    for attacked_record in attacks:
        attacked_records = (first, second, attacked_record)
        with pytest.raises(ValueError):
            validate_capture_record_graph(attacked_records, _manifest(attacked_records))


def test_checkpoint_validation_and_append_only_advance() -> None:
    first = _signal()
    old_records = (first,)
    old_manifest = _manifest(old_records)
    old_checkpoint = _checkpoint(old_records, old_manifest)
    validate_capture_checkpoint(old_records, old_manifest, old_checkpoint)
    validate_capture_checkpoint_advance(
        old_checkpoint,
        old_checkpoint,
        old_manifest,
        old_manifest,
        old_records,
        old_records,
    )

    second = _signal("SHORT")
    new_records = (first, second)
    new_manifest = _manifest(new_records)
    new_checkpoint = _checkpoint(new_records, new_manifest)
    validate_capture_checkpoint_advance(
        old_checkpoint,
        new_checkpoint,
        old_manifest,
        new_manifest,
        old_records,
        new_records,
    )

    checkpoint_attacks = (
        {"manifest_root_hash": "0" * 64},
        {"terminal_manifest_entry_hash": "0" * 64},
        {"record_count": 99},
        {"writer_epoch": 8},
        {"writer_authority_ref": "other-writer"},
    )
    for update in checkpoint_attacks:
        with pytest.raises(ValueError):
            validate_capture_checkpoint(
                old_records,
                old_manifest,
                _rebind_hash_model(old_checkpoint, **update),
            )
    with pytest.raises(ValidationError):
        _rebind_hash_model(old_checkpoint, manifest_entry_count=2)

    with pytest.raises(ValueError, match="truncate"):
        validate_capture_checkpoint_advance(
            new_checkpoint,
            old_checkpoint,
            new_manifest,
            old_manifest,
            new_records,
            old_records,
        )
    rewritten_manifest = _manifest(new_records, slots=("rewritten", "slot-1"))
    rewritten_checkpoint = _checkpoint(new_records, rewritten_manifest)
    with pytest.raises(ValueError, match="rewrite"):
        validate_capture_checkpoint_advance(
            old_checkpoint,
            rewritten_checkpoint,
            old_manifest,
            rewritten_manifest,
            old_records,
            new_records,
        )


def test_replay_report_is_deterministic_revalidated_and_conflict_fail_closed() -> None:
    records = (_signal(),)
    manifest = _manifest(records)
    checkpoint = _checkpoint(records, manifest)
    first_report = build_capture_replay_report(records, manifest, checkpoint)
    second_report = build_capture_replay_report(records, manifest, checkpoint)
    assert first_report == second_report
    assert first_report.replay_status == "PASS"
    assert first_report.deterministic_replay is True
    validate_capture_replay_report(first_report, records, manifest, checkpoint)

    payload = BaseModel.model_dump(first_report, mode="python", round_trip=True)
    payload["verified_record_count"] = 99
    payload.pop("replay_report_hash")
    domain = f"{CAPTURE_CONTRACT_VERSION}/replay-report".encode()
    payload["replay_report_hash"] = sha256_hex(domain + b"\0" + canonical_json_bytes(payload))
    forged = CaptureReplayReportV0.model_validate(payload)
    with pytest.raises(ValueError, match="deterministic"):
        validate_capture_replay_report(forged, records, manifest, checkpoint)

    conflicting = _signal("SHORT")
    conflict_records = (records[0], conflicting)
    conflict_manifest = _manifest(
        conflict_records,
        slots=("same-slot", "same-slot"),
    )
    conflict_checkpoint = _checkpoint(conflict_records, conflict_manifest)
    report = build_capture_replay_report(
        conflict_records,
        conflict_manifest,
        conflict_checkpoint,
    )
    assert report.replay_status == "FAIL"
    assert report.conflicting_duplicate_count == 1


def test_lifecycle_event_specific_transitions_and_graph_attacks() -> None:
    original = _signal()
    created = CaptureLifecycleEventV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        event_kind="CAPTURE_RECORD_CREATED",
        subject_record_ref=original.record_id,
        subject_record_type="SIGNAL_CAPTURE",
    )
    corrected = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T00:01:00Z",
        correction_of_record_id=original.record_id,
    )
    corrected_event = CaptureLifecycleEventV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        event_kind="CAPTURE_RECORD_CORRECTED",
        subject_record_ref=corrected.record_id,
        subject_record_type="SIGNAL_CAPTURE",
        reference_record_refs=(original.record_id,),
        correction_of_record_id=original.record_id,
    )
    superseded = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T00:02:00Z",
        supersedes_record_id=original.record_id,
    )
    superseded_event = CaptureLifecycleEventV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        event_kind="CAPTURE_RECORD_SUPERSEDED",
        subject_record_ref=superseded.record_id,
        subject_record_type="SIGNAL_CAPTURE",
        reference_record_refs=(original.record_id,),
        supersedes_record_id=original.record_id,
    )
    market = _market()
    finalized = CaptureLifecycleEventV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        event_kind="CAPTURE_WINDOW_FINALIZED",
        subject_record_ref=market.record_id,
        subject_record_type="MARKET_PATH_EVIDENCE",
    )
    records = (
        original,
        created,
        corrected,
        corrected_event,
        superseded,
        superseded_event,
        market,
        finalized,
    )
    validate_capture_record_graph(records, _manifest(records))

    with pytest.raises(ValidationError):
        CaptureLifecycleEventV0.bind(
            producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
            event_kind="CAPTURE_RECORD_CORRECTED",
            subject_record_ref=corrected.record_id,
            subject_record_type="SIGNAL_CAPTURE",
            correction_of_record_id=original.record_id,
        )
    wrong_type = _rebind_record(created, subject_record_type="CAPTURE_PLAN")
    attacked = (original, wrong_type)
    with pytest.raises(ValueError, match="subject_record_type"):
        validate_capture_record_graph(attacked, _manifest(attacked))
    runtime_subject = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="START_PERMIT_ISSUED",
        runtime_scope_ref="runtime-subject-scope",
        single_use_permit_ref="runtime-subject-permit",
    )
    lifecycle_for_runtime = _rebind_record(
        created,
        subject_record_ref=runtime_subject.record_id,
    )
    prohibited_subject_records = (runtime_subject, lifecycle_for_runtime)
    with pytest.raises(ValueError, match="cannot be lifecycle"):
        validate_capture_record_graph(
            prohibited_subject_records,
            _manifest(prohibited_subject_records),
        )


def _runtime_resume_ledger() -> tuple[tuple[Any, ...], tuple[CaptureManifestEntryV0, ...]]:
    killed = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        kill_state="KILLED_FAIL_CLOSED",
    )
    start = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="START_PERMIT_ISSUED",
        runtime_scope_ref="runtime-1",
        single_use_permit_ref="start-permit-1",
    )
    kill = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="KILL_ENGAGED",
        runtime_scope_ref="runtime-1",
        kill_state_ref=killed.record_id,
    )
    integrity = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="INTEGRITY_CHECK_COMPLETED",
        runtime_scope_ref="runtime-1",
        integrity_check_ref="integrity-1",
    )
    resume = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="RESUME_PERMIT_ISSUED",
        runtime_scope_ref="runtime-1",
        single_use_permit_ref="resume-permit-1",
        integrity_check_ref="integrity-1",
        kill_state_ref=killed.record_id,
    )
    permitted = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        kill_state="RESUME_PERMITTED_AFTER_INTEGRITY_CHECK",
        single_use_permit_ref="resume-permit-1",
        integrity_check_ref="integrity-1",
        runtime_control_event_ref=resume.record_id,
    )
    records = (killed, start, kill, integrity, resume, permitted)
    return records, _manifest(records)


def test_runtime_control_kill_resume_chain_and_attacks() -> None:
    records, manifest = _runtime_resume_ledger()
    validate_capture_record_graph(records, manifest)

    reused = _rebind_record(records[4], single_use_permit_ref="start-permit-1")
    attacked = (*records[:4], reused, records[5])
    with pytest.raises(ValueError, match="single-use"):
        validate_capture_record_graph(attacked, _manifest(attacked))

    no_kill = (records[0], records[1], records[3], records[4], records[5])
    with pytest.raises(ValueError, match="unresolved kill"):
        validate_capture_record_graph(no_kill, _manifest(no_kill))

    stale_state = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=ProducerIdentityV0.bind(
            identity_domain="RUNTIME_CONTROL_ACTOR",
            producer_id="stale-runtime-actor",
            display_name="stale-runtime-actor",
        ),
        kill_state="KILLED_FAIL_CLOSED",
    )
    stale_resume = _rebind_record(records[4], kill_state_ref=stale_state.record_id)
    stale_records = (stale_state, *records[:4], stale_resume, records[5])
    with pytest.raises(ValueError, match="current unresolved kill"):
        validate_capture_record_graph(stale_records, _manifest(stale_records))

    double_resume = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="RESUME_PERMIT_ISSUED",
        runtime_scope_ref="runtime-1",
        single_use_permit_ref="resume-permit-2",
        integrity_check_ref="integrity-1",
        kill_state_ref=records[0].record_id,
    )
    doubled = (*records, double_resume)
    with pytest.raises(ValueError, match="unresolved kill"):
        validate_capture_record_graph(doubled, _manifest(doubled))

    integrity_before_kill = (
        records[0],
        records[1],
        records[3],
        records[2],
        records[4],
        records[5],
    )
    with pytest.raises(ValueError, match="completed|after kill"):
        validate_capture_record_graph(
            integrity_before_kill,
            _manifest(integrity_before_kill),
        )

    integrity_after_resume = (
        records[0],
        records[1],
        records[2],
        records[4],
        records[3],
        records[5],
    )
    with pytest.raises(ValueError, match="completed|after kill"):
        validate_capture_record_graph(
            integrity_after_resume,
            _manifest(integrity_after_resume),
        )

    cross_domain_kill = _rebind_record(records[2], kill_state_ref=_signal().record_id)
    cross_records = (_signal(), records[0], records[1], cross_domain_kill)
    with pytest.raises(ValueError):
        validate_capture_record_graph(cross_records, _manifest(cross_records))


@pytest.mark.parametrize(
    "kind,fields",
    (
        ("START_PERMIT_ISSUED", {}),
        ("KILL_ENGAGED", {}),
        ("INTEGRITY_CHECK_COMPLETED", {}),
        ("RESUME_PERMIT_ISSUED", {"single_use_permit_ref": "permit-only"}),
    ),
)
def test_runtime_control_event_kinds_reject_missing_or_irrelevant_refs(
    kind: str,
    fields: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        RuntimeControlEventV0.bind(
            supervisor_or_runtime_actor_identity=_runtime_identity(),
            event_kind=kind,
            runtime_scope_ref="runtime-1",
            **fields,
        )


def test_kill_state_three_states_reject_invalid_reference_combinations() -> None:
    with pytest.raises(ValidationError):
        CaptureKillStateV0.bind(
            supervisor_or_runtime_actor_identity=_runtime_identity(),
            kill_state="KILLED_FAIL_CLOSED",
            integrity_check_ref="integrity-1",
        )
    with pytest.raises(ValidationError):
        CaptureKillStateV0.bind(
            supervisor_or_runtime_actor_identity=_runtime_identity(),
            kill_state="RESUME_BLOCKED_PENDING_PERMIT",
            single_use_permit_ref="permit-1",
        )
    with pytest.raises(ValidationError):
        CaptureKillStateV0.bind(
            supervisor_or_runtime_actor_identity=_runtime_identity(),
            kill_state="RESUME_PERMITTED_AFTER_INTEGRITY_CHECK",
            single_use_permit_ref="permit-1",
            integrity_check_ref="integrity-1",
        )


def test_same_id_different_hash_manifest_checkpoint_and_replay_are_version_aware() -> None:
    evidence, first, second, plan = _same_id_signal_versions()
    records = (evidence, first, second, plan)
    manifest = _manifest(
        records,
        slots=("evidence-slot", "signal-slot", "signal-slot", "plan-slot"),
    )
    assert manifest[1].duplicate_classification == "UNIQUE"
    assert manifest[2].duplicate_classification == "CONFLICTING_DUPLICATE"
    validate_capture_manifest_chain(records, manifest)
    with pytest.raises(ValueError, match="ambiguous"):
        validate_capture_record_graph(records, manifest)

    checkpoint = _checkpoint(records, manifest)
    assert checkpoint.record_count == 4
    validate_capture_checkpoint(records, manifest, checkpoint)
    report = build_capture_replay_report(records, manifest, checkpoint)
    assert report.replay_status == "FAIL"
    assert report.chain_integrity is False
    assert report.checkpoint_integrity is True
    assert report.conflicting_duplicate_count == 1
    assert report.missing_reference_count == 0
    validate_capture_replay_report(report, records, manifest, checkpoint)

    with pytest.raises(ValueError, match="duplicate record VERSION_KEY"):
        validate_capture_manifest_chain((evidence, first, first), _manifest((evidence, first)))

    observer = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="SHORT",
        observed_at_utc="2026-07-13T00:03:00Z",
        evidence_refs=(first.record_id,),
    )
    ambiguous_evidence_records = (evidence, first, second, observer, plan)
    ambiguous_evidence_manifest = _manifest(
        ambiguous_evidence_records,
        slots=(
            "evidence-slot",
            "signal-slot",
            "signal-slot",
            "observer-slot",
            "plan-slot",
        ),
    )
    with pytest.raises(ValueError, match="signal evidence target is ambiguous"):
        validate_capture_record_graph(
            ambiguous_evidence_records,
            ambiguous_evidence_manifest,
        )


def test_same_id_version_slot_escape_and_ambiguous_relations_fail_closed() -> None:
    evidence, first, second, plan = _same_id_signal_versions()
    records = (evidence, first, second, plan)
    escaped = _manifest(
        records,
        slots=("evidence-slot", "signal-a", "signal-b", "plan-slot"),
    )
    with pytest.raises(ValueError, match="record ID conflict"):
        validate_capture_manifest_chain(records, escaped)

    corrected = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T00:02:00Z",
        correction_of_record_id=first.record_id,
    )
    correction_records = (*records, corrected)
    correction_manifest = _manifest(
        correction_records,
        slots=(
            "evidence-slot",
            "signal-slot",
            "signal-slot",
            "plan-slot",
            "corrected-slot",
        ),
    )
    validate_capture_manifest_chain(correction_records, correction_manifest)
    with pytest.raises(ValueError, match="correction target is ambiguous"):
        validate_capture_record_graph(correction_records, correction_manifest)


def test_machine_evidence_requires_unique_earlier_market_path_record() -> None:
    base = _linked_signal_plan_shadow()
    human = HumanObservationV0.bind(
        operator_identity=_identity("HUMAN_OPERATOR"),
        observed_record_refs=(base[1].record_id,),
        observation_kind="NOTE",
        observation_text='{"order":"ignored operator note"}',
    )
    lifecycle = CaptureLifecycleEventV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        event_kind="CAPTURE_RECORD_CREATED",
        subject_record_ref=base[1].record_id,
        subject_record_type="SIGNAL_CAPTURE",
    )
    killed = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        kill_state="KILLED_FAIL_CLOSED",
    )
    runtime = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="START_PERMIT_ISSUED",
        runtime_scope_ref="evidence-test-runtime",
        single_use_permit_ref="evidence-test-permit",
    )
    prefix = (*base, human, lifecycle, killed, runtime)
    validate_capture_record_graph(prefix, _manifest(prefix))

    forbidden_targets = (
        base[1],
        base[2],
        base[3],
        human,
        lifecycle,
        runtime,
        killed,
    )
    for index, target in enumerate(forbidden_targets):
        attacked_signal = SignalCaptureV0.bind(
            producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
            signal_kind="SHORT",
            observed_at_utc=f"2026-07-13T00:1{index}:00Z",
            evidence_refs=(target.record_id,),
        )
        attacked = (*prefix, attacked_signal)
        with pytest.raises(ValueError, match="MarketPathEvidenceV0"):
            validate_capture_record_graph(attacked, _manifest(attacked))

    future_market = _market(series="future-evidence")
    early_signal = SignalCaptureV0.bind(
        producer_identity=_identity("SIGNAL_PLAN_SHADOW_PRODUCER"),
        signal_kind="LONG",
        observed_at_utc="2026-07-13T01:00:00Z",
        evidence_refs=(future_market.record_id,),
    )
    future_records = (early_signal, future_market)
    with pytest.raises(ValueError, match="earlier"):
        validate_capture_record_graph(future_records, _manifest(future_records))


def _owned_runtime_chain(scope: str, suffix: str) -> tuple[Any, ...]:
    actor = ProducerIdentityV0.bind(
        identity_domain="RUNTIME_CONTROL_ACTOR",
        producer_id=f"runtime-actor-{suffix}",
        display_name=f"runtime-actor-{suffix}",
    )
    killed = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=actor,
        kill_state="KILLED_FAIL_CLOSED",
    )
    kill = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=actor,
        event_kind="KILL_ENGAGED",
        runtime_scope_ref=scope,
        kill_state_ref=killed.record_id,
    )
    integrity = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=actor,
        event_kind="INTEGRITY_CHECK_COMPLETED",
        runtime_scope_ref=scope,
        integrity_check_ref=f"integrity-{suffix}",
    )
    resume = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=actor,
        event_kind="RESUME_PERMIT_ISSUED",
        runtime_scope_ref=scope,
        single_use_permit_ref=f"resume-permit-{suffix}",
        integrity_check_ref=f"integrity-{suffix}",
        kill_state_ref=killed.record_id,
    )
    permitted = CaptureKillStateV0.bind(
        supervisor_or_runtime_actor_identity=actor,
        kill_state="RESUME_PERMITTED_AFTER_INTEGRITY_CHECK",
        single_use_permit_ref=f"resume-permit-{suffix}",
        integrity_check_ref=f"integrity-{suffix}",
        runtime_control_event_ref=resume.record_id,
    )
    return killed, kill, integrity, resume, permitted


def test_global_kill_and_integrity_ownership_allows_independent_scopes() -> None:
    records = (*_owned_runtime_chain("scope-a", "a"), *_owned_runtime_chain("scope-b", "b"))
    validate_capture_record_graph(records, _manifest(records))


def test_global_kill_ownership_rejects_cross_scope_and_resolved_reuse() -> None:
    chain = _owned_runtime_chain("scope-a", "a")
    other_actor = ProducerIdentityV0.bind(
        identity_domain="RUNTIME_CONTROL_ACTOR",
        producer_id="runtime-actor-b",
        display_name="runtime-actor-b",
    )
    second_engagement = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=other_actor,
        event_kind="KILL_ENGAGED",
        runtime_scope_ref="scope-b",
        kill_state_ref=chain[0].record_id,
    )
    active_conflict = (chain[0], chain[1], second_engagement)
    with pytest.raises(ValueError, match="only one runtime scope"):
        validate_capture_record_graph(active_conflict, _manifest(active_conflict))

    resolved_reengagement = (*chain, second_engagement)
    with pytest.raises(ValueError, match="resolved kill"):
        validate_capture_record_graph(
            resolved_reengagement,
            _manifest(resolved_reengagement),
        )
    cross_scope_resume = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=other_actor,
        event_kind="RESUME_PERMIT_ISSUED",
        runtime_scope_ref="scope-b",
        single_use_permit_ref="resume-permit-b",
        integrity_check_ref="integrity-a",
        kill_state_ref=chain[0].record_id,
    )
    resolved_resume_records = (*chain, cross_scope_resume)
    with pytest.raises(ValueError, match="unresolved kill|resolved kill"):
        validate_capture_record_graph(
            resolved_resume_records,
            _manifest(resolved_resume_records),
        )


@pytest.mark.parametrize("second_scope", ("scope-a", "scope-b"))
def test_global_integrity_ownership_rejects_duplicate_completion(
    second_scope: str,
) -> None:
    first_actor = _runtime_identity()
    second_actor = ProducerIdentityV0.bind(
        identity_domain="RUNTIME_CONTROL_ACTOR",
        producer_id=f"second-{second_scope}",
        display_name=f"second-{second_scope}",
    )
    first = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=first_actor,
        event_kind="INTEGRITY_CHECK_COMPLETED",
        runtime_scope_ref="scope-a",
        integrity_check_ref="shared-integrity",
    )
    second = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=second_actor,
        event_kind="INTEGRITY_CHECK_COMPLETED",
        runtime_scope_ref=second_scope,
        integrity_check_ref="shared-integrity",
    )
    records = (first, second)
    with pytest.raises(ValueError, match="exactly once"):
        validate_capture_record_graph(records, _manifest(records))


def test_resume_rejects_integrity_owned_by_another_scope() -> None:
    chain = _owned_runtime_chain("scope-a", "a")
    foreign_integrity = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=ProducerIdentityV0.bind(
            identity_domain="RUNTIME_CONTROL_ACTOR",
            producer_id="runtime-actor-b",
            display_name="runtime-actor-b",
        ),
        event_kind="INTEGRITY_CHECK_COMPLETED",
        runtime_scope_ref="scope-b",
        integrity_check_ref="foreign-integrity",
    )
    attacked_resume = _rebind_record(
        chain[3],
        integrity_check_ref="foreign-integrity",
    )
    records = (chain[0], chain[1], foreign_integrity, attacked_resume)
    with pytest.raises(ValueError, match="another runtime scope"):
        validate_capture_record_graph(records, _manifest(records))
