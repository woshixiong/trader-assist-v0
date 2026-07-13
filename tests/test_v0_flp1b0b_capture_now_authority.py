from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, TypeAdapter, ValidationError

from trader_assist_v0.contracts import (
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
)
from trader_assist_v0.contracts.common import canonical_json_bytes

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
        minimal_evidence_summary="capture-only evidence",
    )


def _runtime_identity() -> ProducerIdentityV0:
    return _identity("RUNTIME_CONTROL_ACTOR")


def _mutated_payload(model: BaseModel, **updates: Any) -> dict[str, Any]:
    payload = BaseModel.model_dump(model, mode="python", round_trip=True)
    payload.update(updates)
    return payload


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
        intent_summary="shadow-only observation",
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
    )
    runtime = RuntimeControlEventV0.bind(
        supervisor_or_runtime_actor_identity=_runtime_identity(),
        event_kind="KILL_ENGAGED",
        subject_runtime_ref="capture-runtime-1",
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
            subject_runtime_ref="capture-runtime-1",
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
    entry = CaptureManifestEntryV0.bind(
        entry_index=0,
        record_ref=signal.record_id,
        record_hash=signal.record_hash,
        previous_manifest_entry_hash=None,
    )
    checkpoint = CaptureCheckpointV0.bind(
        terminal_manifest_entry_hash=entry.manifest_entry_hash,
        record_count=1,
    )
    report = CaptureReplayReportV0.bind(
        checkpoint_hash=checkpoint.checkpoint_hash,
        replay_status="PASS",
        verified_record_count=1,
    )
    assert entry.io_authorized is False
    assert checkpoint.io_authorized is False
    assert report.performance_adjudication_authorized is False
    assert report.promotion_judgment_authorized is False
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
