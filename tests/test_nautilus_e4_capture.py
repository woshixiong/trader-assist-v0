from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.nautilus_e4.capture import (
    CaptureSession,
    SubscriptionPolicy,
    denominator_states,
    preserve_decision_under_late_evidence,
)
from trader_assist_v0.nautilus_e4.causal import CausalAdmissionLedger
from trader_assist_v0.nautilus_e4.contracts import (
    POST_TERMINAL_CONTEXT_NS,
    POST_TERMINAL_MICRO_NS,
    PRE_DECISION_RETENTION_NS,
    DataKind,
    DecisionState,
    EvidenceState,
    LifecycleKind,
    LifecycleStatus,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
    SourceEvent,
    StreamHealth,
    TailPhase,
)
from trader_assist_v0.nautilus_e4.storage import InMemoryCatalogSink
from trader_assist_v0.nautilus_g4.catalog_bridge import derive_thesis_valid
from trader_assist_v0.vnext_g4.contracts import CausalLineage, DerivationStatus

BASE = 1_000_000_000_000
MARKET_A = sha256_hex(b"HYPERLIQUID|MAIN|ETH")
MARKET_B = sha256_hex(b"HYPERLIQUID|MAIN|BTC")


def _expression(market: str, coin: str) -> MarketExpression:
    return MarketExpression(
        market_id=market,
        dex="MAIN",
        provider_coin=coin,
        instrument_id=f"{coin}-PERP.HYPERLIQUID",
        expression_id=f"expr-{coin}",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash=sha256_hex(f"meta-{coin}".encode()),
    )


def _snapshot() -> PitUniverseSnapshot:
    return PitUniverseSnapshot.create(
        observed_at_ns=BASE,
        expressions=(_expression(MARKET_A, "ETH"), _expression(MARKET_B, "BTC")),
    )


def _manifest(
    *,
    process: str = "process-1",
    continuity: str = "continuity-1",
    admission: str = "admission-1",
) -> RunManifest:
    pit = _snapshot()
    return RunManifest.create(
        run_id="run-e4",
        git_sha="2" * 40,
        git_tree="3" * 40,
        snapshot=pit,
        process_epoch=process,
        continuity_epoch=continuity,
        admission_epoch=admission,
        capture_configuration={
            "expressions": [item.model_dump(mode="json") for item in pit.expressions]
        },
        subscription_policy={
            "discovery": [MARKET_A, MARKET_B],
            "watch": [MARKET_A],
            "actionable": [MARKET_A],
        },
        trial_ledger_id="trial-v1",
    )


def _policy() -> SubscriptionPolicy:
    return SubscriptionPolicy(
        discovery=frozenset({MARKET_A, MARKET_B}),
        watch=frozenset({MARKET_A}),
        actionable=frozenset({MARKET_A}),
    )


def _event(
    index: int,
    *,
    kind: DataKind = DataKind.TRADE,
    market: str = MARKET_A,
    ts_event: int | None = None,
    ts_init: int | None = None,
    tid: str | None = None,
    context: str | None = None,
) -> SourceEvent:
    event_ts = BASE + index * 1_000_000_000 if ts_event is None else ts_event
    init_ts = event_ts + 1 if ts_init is None else ts_init
    coin = "ETH" if market == MARKET_A else "BTC"
    if kind is DataKind.TRADE:
        native = tid or f"tid-{index}"
        side = "BUYER"
    else:
        native = None
        side = None
    return SourceEvent.create(
        market_id=market,
        expression_id=f"expr-{coin}",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=f"{coin}-PERP.HYPERLIQUID",
        data_kind=kind,
        source_event_id=f"source-{kind.value}-{index}",
        native_trade_id=native,
        provider_aggressor_side=side,
        event_context=context or f"block-{index}",
        ts_event=event_ts,
        ts_init=init_ts,
        true_network_receive_ts=None,
        payload={"index": index},
    )


def _session(*, batch_size: int = 128, sink: InMemoryCatalogSink | None = None) -> CaptureSession:
    return CaptureSession(
        manifest=_manifest(),
        policy=_policy(),
        raw_sink=sink or InMemoryCatalogSink(),
        batch_size=batch_size,
    )


def _admit(session: CaptureSession, event: SourceEvent, at: int | None = None):
    return session.ingest(event, admission_ts=at or event.ts_init)


def _open(session: CaptureSession, *, decision_ts: int, package: str = "pkg-001") -> EvidenceState:
    return session.open_actionable(
        package_id=package,
        opportunity_id=f"opp-{package}",
        thesis_id=f"thesis-{package}",
        market_id=MARKET_A,
        expression_id="expr-ETH",
        decision_ts=decision_ts,
        decision_state=DecisionState.TAKE,
    )


def _record_thesis_fact(
    session: CaptureSession,
    *,
    state_ts: int,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
    reason: str = "ACTIVE_VALID",
    **authority_overrides: object,
):
    authority: dict[str, object] = {
        "object_id": "thesis-pkg-001",
        "parent_id": "opp-pkg-001",
        "package_id": "pkg-001",
        "market_id": MARKET_A,
        "expression_id": "expr-ETH",
        "kind": LifecycleKind.THESIS,
    }
    authority.update(authority_overrides)
    return session.record_lifecycle(
        **authority,
        status=status,
        state_ts=state_ts,
        reason_codes=(reason,),
        evidence_state=EvidenceState.COMPLETE,
    )


def test_equal_timestamps_keep_arrival_order_and_source_identity() -> None:
    ledger = CausalAdmissionLedger(
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
    )
    first = ledger.admit(_event(1, ts_event=BASE), admission_ts=BASE + 10).event
    second = ledger.admit(_event(2, ts_event=BASE), admission_ts=BASE + 11).event
    assert first is not None and second is not None
    assert (first.admission_ordinal, second.admission_ordinal) == (1, 2)
    assert first.source_identity != second.source_identity


def test_trade_tick_dedup_binds_native_id_side_market_expression_and_context() -> None:
    ledger = CausalAdmissionLedger(
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
    )
    original = _event(1, tid="same-tid", context="block-1")
    replay = _event(99, tid="same-tid", context="block-1")
    other_market = _event(1, market=MARKET_B, tid="same-tid", context="block-1")
    assert ledger.admit(original, admission_ts=original.ts_init).duplicate is False
    assert ledger.admit(replay, admission_ts=replay.ts_init).duplicate is True
    assert ledger.admit(other_market, admission_ts=other_market.ts_init).duplicate is False
    assert ledger.admission_ordinal == 2


def test_out_of_order_is_admitted_late_without_reordering() -> None:
    session = _session()
    later = _admit(session, _event(2)).event
    late = _admit(session, _event(1), at=BASE + 3_000_000_000).event
    assert later is not None and late is not None
    assert (later.admission_ordinal, late.admission_ordinal) == (1, 2)
    assert late.out_of_order is True


def test_reconnect_replay_duplicate_does_not_change_flow_evidence() -> None:
    session = _session()
    source = _event(1)
    assert _admit(session, source).duplicate is False
    session.disconnect(reason="PUBLIC_WS_DISCONNECT")
    new_epoch = session.reconnect()
    assert new_epoch != "continuity-1"
    assert _admit(session, source, at=source.ts_init + 10).duplicate is True
    assert session.health_summary()["duplicates"] == 1


def test_quiet_bbo_remains_valid_until_continuity_breaks() -> None:
    ledger = CausalAdmissionLedger(
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
    )
    bbo = _event(1, kind=DataKind.BBO)
    ledger.admit(bbo, admission_ts=bbo.ts_init)
    validity = ledger.bbo_validity(market_id=MARKET_A, expression_id="expr-ETH")
    assert validity.valid is True and validity.health is StreamHealth.HEALTHY
    # No wall-clock/event-age argument exists: quiet change-driven BBO is valid.
    assert ledger.bbo_validity(market_id=MARKET_A, expression_id="expr-ETH") == validity
    ledger.disconnect(reason="DISCONNECT")
    assert ledger.bbo_validity(market_id=MARKET_A, expression_id="expr-ETH").valid is False


def test_bbo_invalid_after_reconnect_until_new_epoch_state_reestablished() -> None:
    ledger = CausalAdmissionLedger(
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
    )
    first = _event(1, kind=DataKind.BBO)
    ledger.admit(first, admission_ts=first.ts_init)
    ledger.disconnect(reason="DISCONNECT")
    ledger.reconnect()
    assert ledger.bbo_validity(market_id=MARKET_A, expression_id="expr-ETH").valid is False
    ledger.establish_continuity()
    fresh = _event(2, kind=DataKind.BBO)
    admitted = ledger.admit(fresh, admission_ts=fresh.ts_init).event
    assert admitted is not None
    validity = ledger.bbo_validity(market_id=MARKET_A, expression_id="expr-ETH")
    assert validity.valid is True
    assert validity.continuity_epoch == admitted.continuity_epoch


def test_native_socket_mapping_requires_fresh_full_subscription_observation() -> None:
    session = _session()
    initial_bbo = _event(1, kind=DataKind.BBO)
    _admit(session, initial_bbo)
    _open(session, decision_ts=BASE + 2_000_000_000)
    session.terminal(
        package_id="pkg-001",
        terminal_ts=BASE + 3_000_000_000,
        decision_state=DecisionState.WAIT,
    )
    commitment = session.decision_commitment("pkg-001")
    required = {(MARKET_A, DataKind.BBO), (MARKET_A, DataKind.TRADE)}

    assert session.handle_socket_state("DISCONNECTED", required_streams=required)
    assert session.ledger.health is StreamHealth.DISCONNECTED
    assert session.tail_statuses["pkg-001"].evidence_state is EvidenceState.GAPPED
    assert session.handle_socket_state("CONNECTED", required_streams=required)
    assert session.ledger.health is StreamHealth.REESTABLISHING
    assert session.ledger.bbo_validity(
        market_id=MARKET_A, expression_id="expr-ETH"
    ).valid is False

    fresh_bbo = _admit(session, _event(10, kind=DataKind.BBO)).event
    assert fresh_bbo is not None
    assert fresh_bbo.continuity_state is EvidenceState.GAPPED
    assert session.ledger.health is StreamHealth.REESTABLISHING
    fresh_trade = _admit(session, _event(11, kind=DataKind.TRADE)).event
    assert fresh_trade is not None
    assert fresh_trade.continuity_state is EvidenceState.GAPPED
    assert session.ledger.health is StreamHealth.HEALTHY

    restored_bbo = _admit(session, _event(12, kind=DataKind.BBO)).event
    assert restored_bbo is not None
    assert restored_bbo.continuity_state is EvidenceState.COMPLETE
    assert session.decision_commitment("pkg-001") == commitment
    assert session.tail_statuses["pkg-001"].evidence_state is EvidenceState.GAPPED


def test_duplicate_native_socket_states_do_not_create_false_epochs() -> None:
    session = _session()
    required = {(MARKET_A, DataKind.BBO)}
    assert session.handle_socket_state("SocketState.DISCONNECTED", required_streams=required)
    assert not session.handle_socket_state("DISCONNECTED", required_streams=required)
    assert session.handle_socket_state("SocketState.CONNECTED", required_streams=required)
    epoch = session.ledger.continuity_epoch
    assert not session.handle_socket_state("CONNECTED", required_streams=required)
    assert session.ledger.continuity_epoch == epoch
    assert session.health_summary()["gaps"] == 1
    assert session.health_summary()["reconnects"] == 1


def test_irrelevant_socket_event_cannot_change_continuity_authority() -> None:
    session = _session()
    required = {(MARKET_A, DataKind.BBO)}
    irrelevant = SimpleNamespace(client_id="OTHER", state="DISCONNECTED")
    assert not session.handle_socket_state_event(
        irrelevant,
        expected_client_id="HYPERLIQUID",
        required_streams=required,
    )
    assert session.ledger.health is StreamHealth.HEALTHY
    assert session.health_summary()["gaps"] == 0

    relevant = SimpleNamespace(client_id="HYPERLIQUID", state="DISCONNECTED")
    assert session.handle_socket_state_event(
        relevant,
        expected_client_id="HYPERLIQUID",
        required_streams=required,
    )
    assert session.ledger.health is StreamHealth.DISCONNECTED


def test_discovery_does_not_subscribe_or_retain_rich_data() -> None:
    session = _session()
    with pytest.raises(ValueError, match="Discovery-only"):
        _admit(session, _event(1, market=MARKET_B, kind=DataKind.BBO))
    assert _admit(session, _event(1, market=MARKET_B, kind=DataKind.BAR)).duplicate is False


def test_incomplete_prebuffer_flushes_available_order_and_ea3_is_not_evaluable() -> None:
    sink = InMemoryCatalogSink()
    session = _session(sink=sink)
    for index in (1, 2, 3):
        _admit(session, _event(index))
    state = _open(session, decision_ts=BASE + 4_000_000_000)
    assert state is EvidenceState.PRE_DECISION_WINDOW_INCOMPLETE
    assert [item.admission_ordinal for item in sink.events] == [1, 2, 3]
    assert session.strategy_evidence_state(package_id="pkg-001", ea3=True) is (
        EvidenceState.NOT_EVALUABLE
    )
    assert session.strategy_evidence_state(package_id="pkg-001", ea3=False) is state


def test_full_60_second_prebuffer_is_complete_and_causal() -> None:
    sink = InMemoryCatalogSink()
    session = _session(sink=sink)
    first = _event(0, kind=DataKind.BBO)
    last = _event(60)
    _admit(session, first, at=BASE + 1)
    _admit(session, last, at=BASE + PRE_DECISION_RETENTION_NS + 1)
    decision_ts = BASE + PRE_DECISION_RETENTION_NS + 1
    assert _open(session, decision_ts=decision_ts) is EvidenceState.COMPLETE
    assert [item.source.data_kind for item in sink.events] == [DataKind.BBO, DataKind.TRADE]


def test_new_package_does_not_duplicate_already_durable_precursor() -> None:
    sink = InMemoryCatalogSink()
    session = _session(sink=sink)
    event = _event(1, kind=DataKind.BBO)
    _admit(session, event)
    _open(session, decision_ts=BASE + 2_000_000_000, package="pkg-one")
    session.terminal(
        package_id="pkg-one",
        terminal_ts=BASE + 3_000_000_000,
        decision_state=DecisionState.PASS,
    )
    _open(session, decision_ts=BASE + 4_000_000_000, package="pkg-two")
    assert [item.source_identity for item in sink.events] == [event.replay_identity]


def test_late_evidence_cannot_rewrite_prior_decision() -> None:
    session = _session()
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000)
    commitment = session.decision_commitment("pkg-001")
    late = _admit(
        session,
        _event(0, ts_event=BASE - 10),
        at=BASE + 3_000_000_000,
    ).event
    assert late is not None and late.out_of_order
    assert preserve_decision_under_late_evidence(commitment, (late,)) == commitment


def test_restart_creates_new_epochs_marks_active_window_interrupted_and_dedups() -> None:
    source = _event(1)
    first = _session()
    _admit(first, source)
    _open(first, decision_ts=BASE + 2_000_000_000)
    checkpoint = first.checkpoint()
    restarted = CaptureSession.restart_from(
        checkpoint,
        manifest=_manifest(
            process="process-2", continuity="continuity-2", admission="admission-2"
        ),
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
    )
    assert restarted.ledger.process_epoch == "process-2"
    assert restarted.ledger.admission_epoch == "admission-2"
    assert restarted.tail_statuses["pkg-001"].evidence_state is EvidenceState.INTERRUPTED
    assert _admit(restarted, source, at=source.ts_init + 10).duplicate is True
    with pytest.raises(ValueError, match="duplicate"):
        _open(restarted, decision_ts=BASE + 3_000_000_000)


def test_guard_fail_valid_thesis_requires_fresh_package_and_stale_package_cannot_rearm() -> None:
    session = _session()
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000, package="pkg-old")
    session.terminal(
        package_id="pkg-old",
        terminal_ts=BASE + 3_000_000_000,
        decision_state=DecisionState.NO_SUBMIT,
    )
    with pytest.raises(ValueError, match="duplicate"):
        _open(session, decision_ts=BASE + 4_000_000_000, package="pkg-old")
    fresh = _open(session, decision_ts=BASE + 5_000_000_000, package="pkg-fresh")
    assert fresh is EvidenceState.PRE_DECISION_WINDOW_INCOMPLETE
    assert "pkg-fresh" in session.tail_statuses


def test_full_lifecycle_ids_parents_timestamps_and_reasons_are_portable() -> None:
    session = _session()
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000)
    parent = "thesis-pkg-001"
    for offset, (kind, object_id) in enumerate(
        (
            (LifecycleKind.ELIGIBILITY, "eligibility-001"),
            (LifecycleKind.ARMED, "armed-001"),
            (LifecycleKind.ACTIVATION, "activation-001"),
            (LifecycleKind.ATTEMPT, "attempt-001"),
            (LifecycleKind.WINNER, "winner-001"),
            (LifecycleKind.EXIT, "exit-001"),
        ),
        start=1,
    ):
        record = session.record_lifecycle(
            object_id=object_id,
            parent_id=parent,
            package_id="pkg-001",
            market_id=MARKET_A,
            expression_id="expr-ETH",
            kind=kind,
            status=(
                LifecycleStatus.TERMINAL
                if kind is LifecycleKind.EXIT
                else LifecycleStatus.ACTIVE
            ),
            state_ts=BASE + (2 + offset) * 1_000_000_000,
            reason_codes=(kind.value,),
            evidence_state=EvidenceState.PRE_DECISION_WINDOW_INCOMPLETE,
            approval_timing_mode=(
                None
                if kind is not LifecycleKind.ARMED
                else "PREAUTHORIZED_ARMED"
            ),
        )
        assert record.parent_id == parent
        parent = record.object_id
    assert [item.kind for item in session.lifecycle_records[-6:]] == [
        LifecycleKind.ELIGIBILITY,
        LifecycleKind.ARMED,
        LifecycleKind.ACTIVATION,
        LifecycleKind.ATTEMPT,
        LifecycleKind.WINNER,
        LifecycleKind.EXIT,
    ]


def test_same_thesis_created_then_active_is_append_only_and_g4_evaluable() -> None:
    session = _session()
    _admit(session, _event(0, kind=DataKind.BBO), at=BASE + 1)
    _admit(
        session,
        _event(60),
        at=BASE + PRE_DECISION_RETENTION_NS + 1,
    )
    decision_ts = BASE + PRE_DECISION_RETENTION_NS + 1
    _open(session, decision_ts=decision_ts)
    created = session.lifecycle_records[-1]
    active = _record_thesis_fact(
        session,
        state_ts=decision_ts + 1,
    )

    assert created.object_id == active.object_id == "thesis-pkg-001"
    assert created.record_hash != active.record_hash
    assert session.lifecycle_records[-2:] == (created, active)

    causal_lineage = CausalLineage.create(
        source_e4_manifest_hash="1" * 64,
        source_pit_snapshot_hash="2" * 64,
        source_structural_artifact_hash="3" * 64,
        structural_component_manifest_hash="4" * 64,
        market_id=MARKET_A,
        instrument_id="ETH-PERP.HYPERLIQUID",
        formal_setup_id="setup-1",
        formal_setup_admission_ordinal=1,
        formal_setup_admission_ts=decision_ts - 1,
        thesis_id="thesis-pkg-001",
        activation_sequence_id="activation-1",
        attempt_lineage_id="attempt-1",
        restart_reference_id="restart-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash=sha256_hex(b"meta-ETH"),
        validation_reference_id="validation-v1",
        validation_reference_hash="5" * 64,
    )
    derived = derive_thesis_valid(
        formal_setup_confirmed=True,
        lineage=causal_lineage,
        records=(created, active),
    )
    assert derived.status is DerivationStatus.EVALUABLE
    assert derived.value is True


@pytest.mark.parametrize(
    "terminal_status",
    (
        LifecycleStatus.TERMINAL,
        LifecycleStatus.EXPIRED,
        LifecycleStatus.SUPERSEDED,
    ),
)
def test_active_may_repeat_or_enter_terminal_family_once(
    terminal_status: LifecycleStatus,
) -> None:
    session = _session()
    _open(session, decision_ts=BASE + 2_000_000_000)
    repeated = _record_thesis_fact(session, state_ts=BASE + 3_000_000_000)
    terminal = _record_thesis_fact(
        session,
        state_ts=BASE + 4_000_000_000,
        status=terminal_status,
        reason=terminal_status.value,
    )
    assert repeated.status is LifecycleStatus.ACTIVE
    assert terminal.status is terminal_status
    with pytest.raises(ValueError, match="terminal-family"):
        _record_thesis_fact(session, state_ts=BASE + 5_000_000_000)


@pytest.mark.parametrize(
    "authority_override",
    (
        {"kind": LifecycleKind.ATTEMPT},
        {"parent_id": None},
        {"package_id": "pkg-other"},
        {"market_id": MARKET_B},
        {"expression_id": "expr-other"},
    ),
)
def test_existing_object_rejects_cross_identity_reuse(
    authority_override: dict[str, object],
) -> None:
    session = _session()
    _open(session, decision_ts=BASE + 2_000_000_000)
    with pytest.raises(ValueError, match="authority contradicts"):
        _record_thesis_fact(
            session,
            state_ts=BASE + 3_000_000_000,
            **authority_override,
        )


def test_lifecycle_rejects_unknown_parent_duplicate_and_nonmonotonic_fact() -> None:
    session = _session()
    with pytest.raises(ValueError, match="parent identity is unknown"):
        session.record_lifecycle(
            object_id="attempt-orphan",
            parent_id="missing-thesis",
            package_id="pkg-001",
            market_id=MARKET_A,
            expression_id="expr-ETH",
            kind=LifecycleKind.ATTEMPT,
            status=LifecycleStatus.ACTIVE,
            state_ts=BASE + 1,
            reason_codes=("ATTEMPT_CREATED",),
            evidence_state=EvidenceState.COMPLETE,
        )

    _open(session, decision_ts=BASE + 2_000_000_000)
    first = _record_thesis_fact(session, state_ts=BASE + 3_000_000_000)
    with pytest.raises(ValueError, match="exact duplicate"):
        _record_thesis_fact(session, state_ts=first.state_ts)
    with pytest.raises(ValueError, match="strictly increasing"):
        _record_thesis_fact(
            session,
            state_ts=first.state_ts - 1,
            reason="ACTIVE_VALID_AGAIN",
        )


def test_restart_restores_latest_fact_authority() -> None:
    session = _session()
    _open(session, decision_ts=BASE + 2_000_000_000)
    latest = _record_thesis_fact(session, state_ts=BASE + 3_000_000_000)
    checkpoint = session.checkpoint()
    assert checkpoint["latest_lifecycle_records"][latest.object_id]["record_hash"] == (
        latest.record_hash
    )

    restarted = CaptureSession.restart_from(
        checkpoint,
        manifest=_manifest(
            process="process-2", continuity="continuity-2", admission="admission-2"
        ),
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
    )
    terminal = _record_thesis_fact(
        restarted,
        state_ts=BASE + 4_000_000_000,
        status=LifecycleStatus.TERMINAL,
        reason="STRUCTURAL_THESIS_INVALIDATION",
    )
    assert terminal.object_id == latest.object_id


def test_legacy_checkpoint_without_history_fails_closed_only_for_existing_object() -> None:
    session = _session()
    _open(session, decision_ts=BASE + 2_000_000_000)
    checkpoint = session.checkpoint()
    checkpoint.pop("latest_lifecycle_records")
    restarted = CaptureSession.restart_from(
        checkpoint,
        manifest=_manifest(
            process="process-2", continuity="continuity-2", admission="admission-2"
        ),
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
    )
    with pytest.raises(ValueError, match="authority unavailable"):
        _record_thesis_fact(restarted, state_ts=BASE + 3_000_000_000)

    unseen = restarted.record_lifecycle(
        object_id="new-root-object",
        parent_id=None,
        package_id="pkg-new",
        market_id=MARKET_A,
        expression_id="expr-ETH",
        kind=LifecycleKind.OPPORTUNITY,
        status=LifecycleStatus.ACTIVE,
        state_ts=BASE + 3_000_000_001,
        reason_codes=("NEW_OBJECT",),
        evidence_state=EvidenceState.COMPLETE,
    )
    assert unseen.object_id == "new-root-object"


def test_full_denominator_states_are_retained() -> None:
    assert denominator_states() == frozenset(DecisionState)
    assert {
        DecisionState.BLOCKED,
        DecisionState.WAIT,
        DecisionState.PASS,
        DecisionState.NO_SUBMIT,
        DecisionState.NONFILL,
        DecisionState.NOT_EVALUABLE,
    } <= denominator_states()


@pytest.mark.parametrize(
    "decision",
    (
        DecisionState.TAKE,
        DecisionState.WAIT,
        DecisionState.PASS,
        DecisionState.NO_SUBMIT,
        DecisionState.NOT_EVALUABLE,
    ),
)
def test_every_terminal_denominator_gets_micro_and_context_tails(
    decision: DecisionState,
) -> None:
    session = _session()
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000)
    terminal_ts = BASE + 3_000_000_000
    tail = session.terminal(
        package_id="pkg-001", terminal_ts=terminal_ts, decision_state=decision
    )
    assert tail.micro_deadline_ts == terminal_ts + POST_TERMINAL_MICRO_NS
    assert tail.context_deadline_ts == terminal_ts + POST_TERMINAL_CONTEXT_NS
    assert tail.micro_phase is tail.context_phase is TailPhase.ACTIVE


def test_accelerated_tail_boundaries_close_at_30m_and_6h() -> None:
    session = _session()
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000)
    terminal_ts = BASE + 3_000_000_000
    session.terminal(
        package_id="pkg-001", terminal_ts=terminal_ts, decision_state=DecisionState.PASS
    )
    session.advance(now_ns=terminal_ts + POST_TERMINAL_MICRO_NS - 1)
    tail = session.tail_statuses["pkg-001"]
    assert tail.micro_phase is TailPhase.ACTIVE
    session.advance(now_ns=terminal_ts + POST_TERMINAL_MICRO_NS)
    tail = session.tail_statuses["pkg-001"]
    assert tail.micro_phase is TailPhase.COMPLETE
    assert tail.context_phase is TailPhase.ACTIVE
    session.advance(now_ns=terminal_ts + POST_TERMINAL_CONTEXT_NS)
    assert session.tail_statuses["pkg-001"].context_phase is TailPhase.COMPLETE


def test_disconnect_in_tail_marks_both_tails_gapped_without_backfill() -> None:
    session = _session()
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000)
    session.terminal(
        package_id="pkg-001",
        terminal_ts=BASE + 3_000_000_000,
        decision_state=DecisionState.WAIT,
    )
    session.disconnect(reason="TAIL_DISCONNECT")
    tail = session.tail_statuses["pkg-001"]
    assert tail.micro_phase is TailPhase.INCOMPLETE
    assert tail.context_phase is TailPhase.INCOMPLETE
    assert tail.evidence_state is EvidenceState.GAPPED
    session.reconnect()
    session.establish_continuity()
    next_event = _event(10, kind=DataKind.BBO)
    _admit(session, next_event)
    session.close()


class _FailingSink:
    def write(self, events: Sequence[object]) -> None:
        raise OSError("disk full")


def test_storage_backpressure_failure_is_observable_and_not_silent() -> None:
    session = CaptureSession(
        manifest=_manifest(), policy=_policy(), raw_sink=_FailingSink(), batch_size=1
    )
    with pytest.raises(OSError, match="disk full"):
        _open_after_one_event(session)
    health = session.health_summary()
    assert health["storage_failures"] == 1
    assert health["missingness_counts"]["STORAGE_WRITE_FAILURE"] == 1
    assert health["missingness_counts"]["PRE_DECISION_WINDOW_INCOMPLETE"] == 1


def _open_after_one_event(session: CaptureSession) -> None:
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000)


def test_teardown_flushes_established_evidence_and_cannot_erase_it() -> None:
    sink = InMemoryCatalogSink()
    session = _session(sink=sink)
    _admit(session, _event(1))
    _open(session, decision_ts=BASE + 2_000_000_000)
    before = sink.events
    session.interrupt(reason="APPLICATION_STOP")
    assert sink.events == before
    assert session.tail_statuses["pkg-001"].evidence_state is EvidenceState.INTERRUPTED
