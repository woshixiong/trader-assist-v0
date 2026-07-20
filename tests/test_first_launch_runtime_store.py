"""Durable SQLite persistence tests for the restricted public runtime.

Covers Section 16 categories F (Persistence) and parts of G (Notification):
- required tables and constraints;
- atomic linked publication bundle;
- unique signal/plan/shadow/notification identities;
- crash before send leaves pending;
- restart does not duplicate publication;
- restart retries the same notification identity.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from trader_assist_v0.first_launch.configuration import RiskConfiguration
from trader_assist_v0.first_launch.market_data import (
    DataQualityState,
    EthMarketData,
    candle_from_websocket,
    context_from_websocket,
    evidence_from_raw,
    metadata_from_info,
)
from trader_assist_v0.first_launch.operator_review import (
    build_operator_card,
    create_shadow_order,
)
from trader_assist_v0.first_launch.signal_context import ContextSeries
from trader_assist_v0.first_launch.strategy import (
    SetupFamily,
    Side,
    apply_volatility_overlay,
    build_plan,
    evaluate_signal,
    wilder_atr14,
)
from trader_assist_v0.runtime.first_launch_runtime_store import (
    PersistenceAuthorityError,
    PublicationConflictError,
    RuntimeStore,
    RuntimeStoreError,
    _register_tradeplan_proof,
    notification_id_for_plan,
    publication_bundle_hash,
)

NOW = datetime(2026, 7, 14, tzinfo=UTC)


def _candle(
    open_time: int,
    *,
    open: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    volume: str = "10",
    interval: str = "5m",
) -> object:
    width = 300_000 if interval == "5m" else 900_000
    latest_index = 26 if interval == "5m" else 10
    if open_time < 10_000_000_000:
        actual_open_time = (
            int(NOW.timestamp() * 1000) - 1_000 - ((latest_index + 1) * width) + open_time
        )
    else:
        actual_open_time = open_time
    open_value, high_value, low_value, close_value = map(Decimal, (open, high, low, close))
    high_value = max(high_value, open_value, close_value)
    low_value = min(low_value, open_value, close_value)
    raw = json.dumps(
        {
            "channel": "candle",
            "data": {
                "s": "ETH",
                "i": interval,
                "t": actual_open_time,
                "T": actual_open_time + width,
                "o": str(open_value),
                "h": str(high_value),
                "l": str(low_value),
                "c": str(close_value),
                "v": volume,
                "n": 0,
            },
        },
        separators=(",", ":"),
    )
    evidence = evidence_from_raw(
        raw,
        operation="WebSocket",
        received_at=max(
            NOW,
            datetime.fromtimestamp((actual_open_time + width + 1_000) / 1_000, tz=UTC),
        ),
        receive_sequence=max(0, actual_open_time // width),
        connection_id="store-test",
    )
    return candle_from_websocket(raw, evidence)


def _snapshot(candles_5m: tuple[object, ...], candles_15m: tuple[object, ...]) -> object:
    data = EthMarketData()
    data.begin_connection()
    for candle in (*candles_5m, *candles_15m):
        assert data.accept_candle(candle) == "ACCEPTED"
    evaluated_at = max(candle.evidence.received_at for candle in (*candles_5m, *candles_15m))
    context_raw = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"100","openInterest":"1","funding":"0"}}}'
    )
    data.accept_context(
        context_from_websocket(
            context_raw,
            evidence_from_raw(
                context_raw,
                operation="WebSocket",
                received_at=evaluated_at,
                receive_sequence=90,
                connection_id="store-test",
            ),
        )
    )
    metadata_raw = '{"universe":[{"name":"ETH","szDecimals":3}]}'
    data.accept_metadata(
        metadata_from_info(
            metadata_raw,
            evidence_from_raw(
                metadata_raw,
                operation="metaAndAssetCtxs",
                received_at=evaluated_at,
                receive_sequence=91,
                connection_id="store-test",
            ),
        )
    )
    snapshot = data.strategy_snapshot(evaluated_at)
    assert snapshot.quality.state is DataQualityState.READY
    return snapshot


def _history(
    family: SetupFamily, side: Side, fast: bool
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    c5 = [_candle(i * 300_000) for i in range(-37, 26)]
    volume = "20" if fast else "13"
    if family is SetupFamily.SWEEP_RECLAIM:
        trigger = _candle(
            26 * 300_000,
            high="101" if side is Side.LONG else "102",
            low="98" if side is Side.LONG else "99",
            close="100",
            volume=volume,
        )
        c15 = tuple(
            _candle(
                i * 900_000, close=str(100 + i if side is Side.LONG else 100 - i), interval="15m"
            )
            for i in range(-9, 11)
        )
    elif side is Side.LONG:
        trigger = _candle(26 * 300_000, high="102", low="100", close="102", volume=volume)
        c15 = tuple(_candle(i * 900_000, close=str(90 + i), interval="15m") for i in range(-9, 11))
    else:
        trigger = _candle(26 * 300_000, high="100", low="98", close="98", volume=volume)
        c15 = tuple(_candle(i * 900_000, close=str(110 - i), interval="15m") for i in range(-9, 11))
    return tuple([*c5, trigger]), c15


def _confirmed_output(
    family: SetupFamily = SetupFamily.SWEEP_RECLAIM,
    side: Side = Side.LONG,
    fast: bool = True,
) -> object:
    c5, c15 = _history(family, side, fast)
    snapshot = _snapshot(c5, c15)
    result = evaluate_signal(snapshot)
    assert type(result).__name__ == "StrategyOutput"
    return result


def _risk_configuration() -> RiskConfiguration:
    return RiskConfiguration.from_json(
        '{"CONFIGURATION_VERSION":"r3.0","ACCOUNT_EQUITY_USD":"1000.00",'
        '"RISK_PER_TRADE_PCT":"0.5000","MAX_NOTIONAL_USD":null}'
    )


def _context_summary(now: datetime) -> object:
    series = ContextSeries()
    raw_0 = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"100","openInterest":"1","funding":"0"}}}'
    )
    raw_1 = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"100","openInterest":"1","funding":"0"}}}'
    )
    series.accept(
        context_from_websocket(
            raw_0,
            evidence_from_raw(
                raw_0,
                operation="WebSocket",
                received_at=now - timedelta(minutes=20),
                receive_sequence=1,
                connection_id="store-test",
            ),
        )
    )
    series.accept(
        context_from_websocket(
            raw_1,
            evidence_from_raw(
                raw_1,
                operation="WebSocket",
                received_at=now - timedelta(minutes=1),
                receive_sequence=2,
                connection_id="store-test",
            ),
        )
    )
    summary = series.summary_at(now)
    assert summary is not None
    return summary


def _full_publication_chain(now: datetime) -> dict[str, object]:
    c5, c15 = _history(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    snapshot = _snapshot(c5, c15)
    output = evaluate_signal(snapshot)
    assert type(output).__name__ == "StrategyOutput"
    reference_price = output.raw_entry_low
    volatility = wilder_atr14(snapshot.candles_5m[-64:])
    overlay = apply_volatility_overlay(
        output, volatility, snapshot.candles_5m[-64:], reference_price
    )
    assert overlay.actionable, "overlay must be actionable for publication"
    context_raw = json.dumps(
        {
            "channel": "activeAssetCtx",
            "data": {
                "coin": "ETH",
                "ctx": {
                    "markPx": str(reference_price),
                    "midPx": str(reference_price),
                    "openInterest": "1",
                    "funding": "0",
                },
            },
        },
        separators=(",", ":"),
    )
    series = ContextSeries()
    series.accept(
        context_from_websocket(
            context_raw,
            evidence_from_raw(
                context_raw,
                operation="WebSocket",
                received_at=now - timedelta(minutes=1),
                receive_sequence=1,
                connection_id="store-test",
            ),
        )
    )
    context_summary = series.summary_at(now)
    assert context_summary is not None
    plan = build_plan(
        strategy_output=output,
        reference=reference_price,
        sz_decimals=3,
        configuration=_risk_configuration(),
        volatility=volatility,
        overlay=overlay,
        context_summary=context_summary,
    )
    # GA-04: register the process-local issuance proof binding the exact
    # TradePlan object identity (its id()) to its plan_id, canonical_hash
    # and the exact embedded StrategyOutput / VolatilitySnapshot /
    # OverlayDecision identity. The proof is private to the P3B runtime
    # store, never serialized or persisted, and removed by the weakref
    # callback when the plan is garbage-collected. The store validates the
    # proof at the start of persist_publication_bundle, before any SQLite
    # mutation. This mirrors the production RestrictedPublicRuntime flow.
    _register_tradeplan_proof(
        plan,
        strategy_output=output,
        volatility_snapshot=volatility,
        overlay_decision=overlay,
    )
    card = build_operator_card(plan, now=now, quality=DataQualityState.READY)
    shadow = create_shadow_order(card)
    return {
        "output": output,
        "volatility": volatility,
        "overlay": overlay,
        "plan": plan,
        "card": card,
        "shadow": shadow,
    }


def _open_store(tmp_path: Path) -> RuntimeStore:
    return RuntimeStore.open(tmp_path / "test_runtime.db")


def _record_session(store: RuntimeStore, *, now: datetime, database_path: Path) -> str:
    session_id = uuid4().hex
    store.record_runtime_session(
        session_id=session_id,
        runtime_mode="RESTRICTED_PUBLIC_LIVE_SHADOW",
        scope="ETH_ONLY",
        process_start_time=now,
        configuration_hash=_risk_configuration().configuration_hash,
        database_path=database_path,
        manual_only_authority=True,
        not_submitted_authority=True,
        now=now,
    )
    return session_id


def test_required_tables_and_constraints(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        rows = store._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert {
            "runtime_sessions",
            "publication_bundles",
            "notification_outbox",
            "health_events",
        } <= names
        info = store._connection.execute("PRAGMA table_info(publication_bundles)").fetchall()
        columns = {row["name"] for row in info}
        assert {"signal_id", "plan_id", "shadow_order_id", "notification_id"} <= columns
    finally:
        store.close()


def test_runtime_session_record_and_close(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(store, now=now, database_path=tmp_path / "test_runtime.db")
        sessions = store.list_runtime_sessions()
        assert len(sessions) == 1
        record = sessions[0]
        assert record.session_id == session_id
        assert record.runtime_mode == "RESTRICTED_PUBLIC_LIVE_SHADOW"
        assert record.scope == "ETH_ONLY"
        assert record.manual_only_authority is True
        assert record.not_submitted_authority is True
        assert record.closed_at is None
        store.close_runtime_session(session_id=session_id, now=now + timedelta(seconds=1))
        sessions = store.list_runtime_sessions()
        assert sessions[0].closed_at is not None
    finally:
        store.close()


def test_persist_publication_bundle_is_atomic_and_pending(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(store, now=now, database_path=tmp_path / "test_runtime.db")
        chain = _full_publication_chain(now)
        bundle, outbox = store.persist_publication_bundle(
            session_id=session_id,
            strategy_output=chain["output"],
            volatility_snapshot=chain["volatility"],
            overlay_decision=chain["overlay"],
            trade_plan=chain["plan"],
            operator_review_card=chain["card"],
            shadow_order=chain["shadow"],
            now=now,
        )
        assert bundle.signal_id == chain["output"].setup_id
        assert bundle.plan_id == chain["plan"].plan_id
        assert bundle.shadow_order_id == chain["shadow"].shadow_order_id
        assert bundle.notification_id == notification_id_for_plan(bundle.plan_id)
        assert outbox.status == "PENDING"
        assert outbox.attempt_count == 0
        assert outbox.delivered_at is None
        assert store.publication_exists_for_signal(bundle.signal_id) is True
        assert store.publication_exists_for_plan(bundle.plan_id) is True
        pending = store.list_pending_notifications()
        assert len(pending) == 1
        assert pending[0].notification_id == bundle.notification_id
    finally:
        store.close()


def test_crash_before_send_leaves_pending(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(store, now=now, database_path=tmp_path / "test_runtime.db")
        chain = _full_publication_chain(now)
        bundle, outbox = store.persist_publication_bundle(
            session_id=session_id,
            strategy_output=chain["output"],
            volatility_snapshot=chain["volatility"],
            overlay_decision=chain["overlay"],
            trade_plan=chain["plan"],
            operator_review_card=chain["card"],
            shadow_order=chain["shadow"],
            now=now,
        )
        assert outbox.status == "PENDING"
        store.close()
        reopened = _open_store(tmp_path)
        try:
            pending = reopened.list_pending_notifications()
            assert len(pending) == 1
            assert pending[0].notification_id == bundle.notification_id
            assert pending[0].status == "PENDING"
        finally:
            reopened.close()
    finally:
        pass


def test_restart_does_not_duplicate_publication(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(store, now=now, database_path=tmp_path / "test_runtime.db")
        chain = _full_publication_chain(now)
        bundle, _ = store.persist_publication_bundle(
            session_id=session_id,
            strategy_output=chain["output"],
            volatility_snapshot=chain["volatility"],
            overlay_decision=chain["overlay"],
            trade_plan=chain["plan"],
            operator_review_card=chain["card"],
            shadow_order=chain["shadow"],
            now=now,
        )
        with pytest.raises(PublicationConflictError):
            store.persist_publication_bundle(
                session_id=session_id,
                strategy_output=chain["output"],
                volatility_snapshot=chain["volatility"],
                overlay_decision=chain["overlay"],
                trade_plan=chain["plan"],
                operator_review_card=chain["card"],
                shadow_order=chain["shadow"],
                now=now,
            )
        pending = store.list_pending_notifications()
        assert len(pending) == 1
        assert pending[0].notification_id == bundle.notification_id
    finally:
        store.close()


def test_notification_id_is_deterministic_per_plan() -> None:
    plan_id = "a" * 64
    first = notification_id_for_plan(plan_id)
    second = notification_id_for_plan(plan_id)
    assert first == second
    other = notification_id_for_plan("b" * 64)
    assert first != other


def test_notification_status_transitions(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(store, now=now, database_path=tmp_path / "test_runtime.db")
        chain = _full_publication_chain(now)
        bundle, _ = store.persist_publication_bundle(
            session_id=session_id,
            strategy_output=chain["output"],
            volatility_snapshot=chain["volatility"],
            overlay_decision=chain["overlay"],
            trade_plan=chain["plan"],
            operator_review_card=chain["card"],
            shadow_order=chain["shadow"],
            now=now,
        )
        attempt = store.begin_notification_attempt(
            notification_id=bundle.notification_id, now=now
        )
        assert attempt.attempt_count == 1
        delivered = store.mark_notification_delivered(
            notification_id=bundle.notification_id, now=now
        )
        assert delivered.status == "DELIVERED"
        assert delivered.delivered_at is not None
        assert store.list_pending_notifications() == ()
        with pytest.raises(RuntimeStoreError):
            store.mark_notification_delivered(
                notification_id=bundle.notification_id, now=now
            )
    finally:
        store.close()


def test_notification_configuration_failed_is_terminal(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(store, now=now, database_path=tmp_path / "test_runtime.db")
        chain = _full_publication_chain(now)
        bundle, _ = store.persist_publication_bundle(
            session_id=session_id,
            strategy_output=chain["output"],
            volatility_snapshot=chain["volatility"],
            overlay_decision=chain["overlay"],
            trade_plan=chain["plan"],
            operator_review_card=chain["card"],
            shadow_order=chain["shadow"],
            now=now,
        )
        failed = store.mark_notification_configuration_failed(
            notification_id=bundle.notification_id, now=now
        )
        assert failed.status == "FAILED_CONFIGURATION"
        assert store.list_pending_notifications() == ()
    finally:
        store.close()


def test_health_events_are_recorded(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(store, now=now, database_path=tmp_path / "test_runtime.db")
        event = store.record_health_event(
            session_id=session_id,
            from_state="STARTING",
            to_state="WARMING",
            reason="begin-warmup",
            now=now,
        )
        assert event.from_state == "STARTING"
        assert event.to_state == "WARMING"
        events = store.list_health_events(session_id=session_id)
        assert len(events) == 1
        assert events[0].event_id == event.event_id
    finally:
        store.close()


def test_publication_bundle_hash_is_deterministic() -> None:
    signal_id = "a" * 64
    plan_id = "b" * 64
    shadow_order_id = "c" * 64
    notification_id = "d" * 64
    evidence: dict[str, object] = {"setup_id": signal_id}
    first = publication_bundle_hash(
        signal_id=signal_id,
        plan_id=plan_id,
        shadow_order_id=shadow_order_id,
        notification_id=notification_id,
        session_id="session-1",
        strategy_output_evidence=evidence,
        volatility_snapshot_hash="e" * 64,
        overlay_decision_hash="f" * 64,
        trade_plan_canonical_hash="0" * 64,
        operator_review_card_id="1" * 64,
    )
    second = publication_bundle_hash(
        signal_id=signal_id,
        plan_id=plan_id,
        shadow_order_id=shadow_order_id,
        notification_id=notification_id,
        session_id="session-1",
        strategy_output_evidence=evidence,
        volatility_snapshot_hash="e" * 64,
        overlay_decision_hash="f" * 64,
        trade_plan_canonical_hash="0" * 64,
        operator_review_card_id="1" * 64,
    )
    assert first == second


def test_invalid_runtime_mode_is_rejected(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        with pytest.raises(RuntimeStoreError):
            store.record_runtime_session(
                session_id="x",
                runtime_mode="UNAUTHORIZED_MODE",
                scope="ETH_ONLY",
                process_start_time=NOW,
                configuration_hash=None,
                database_path=tmp_path,
                manual_only_authority=True,
                not_submitted_authority=True,
                now=NOW,
            )
    finally:
        store.close()


def test_invalid_scope_is_rejected(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        with pytest.raises(RuntimeStoreError):
            store.record_runtime_session(
                session_id="x",
                runtime_mode="RESTRICTED_PUBLIC_LIVE_SHADOW",
                scope="BTC_ONLY",
                process_start_time=NOW,
                configuration_hash=None,
                database_path=tmp_path,
                manual_only_authority=True,
                not_submitted_authority=True,
                now=NOW,
            )
    finally:
        store.close()


def test_database_user_version_is_set(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        version = store._connection.execute("PRAGMA user_version").fetchone()[0]
        assert version == 1
        reopened = _open_store(tmp_path)
        try:
            version = reopened._connection.execute("PRAGMA user_version").fetchone()[0]
            assert version == 1
        finally:
            reopened.close()
    finally:
        store.close()


# ============================================================
# GA-04: publication authority validation
# ============================================================


def _row_counts(store: RuntimeStore) -> tuple[int, int]:
    pubs = store._connection.execute(
        "SELECT COUNT(*) FROM publication_bundles"
    ).fetchone()[0]
    outbox = store._connection.execute(
        "SELECT COUNT(*) FROM notification_outbox"
    ).fetchone()[0]
    return pubs, outbox


def _persist_chain(
    store: RuntimeStore,
    session_id: str,
    chain: dict[str, object],
    now: datetime,
) -> object:
    return store.persist_publication_bundle(
        session_id=session_id,
        strategy_output=chain["output"],  # type: ignore[arg-type]
        volatility_snapshot=chain["volatility"],  # type: ignore[arg-type]
        overlay_decision=chain["overlay"],  # type: ignore[arg-type]
        trade_plan=chain["plan"],  # type: ignore[arg-type]
        operator_review_card=chain["card"],  # type: ignore[arg-type]
        shadow_order=chain["shadow"],  # type: ignore[arg-type]
        now=now,
    )


def _reconstruct_authority(original: object) -> object:
    """Construct a new instance of the same type with identical init field values.

    This bypasses the process-local issuance registry: the new object has the
    correct canonical hash (``__post_init__`` re-validates it) but is not
    registered in ``_ISSUED``, so the reuse-only validators reject it.
    """
    fields = dataclasses.fields(original)
    kwargs = {f.name: getattr(original, f.name) for f in fields if f.init}
    return type(original)(**kwargs)


def test_ga04_legitimate_issued_chain_persists(tmp_path: Path) -> None:
    """The legitimate issuance chain persists successfully (baseline)."""
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        bundle, outbox = _persist_chain(store, session_id, chain, now)  # type: ignore[misc]
        assert bundle.signal_id == chain["output"].setup_id  # type: ignore[attr-defined]
        assert outbox.status == "PENDING"  # type: ignore[union-attr]
        pubs, outbox_rows = _row_counts(store)
        assert pubs == 1
        assert outbox_rows == 1
    finally:
        store.close()


@pytest.mark.parametrize(
    "authority_key, transform_name",
    [
        ("output", "replace"),
        ("volatility", "replace"),
        ("overlay", "replace"),
        ("card", "replace"),
        ("shadow", "replace"),
        ("output", "copy"),
        ("volatility", "copy"),
        ("overlay", "copy"),
        ("card", "copy"),
        ("shadow", "copy"),
        ("output", "deepcopy"),
        ("volatility", "deepcopy"),
        ("overlay", "deepcopy"),
        ("card", "deepcopy"),
        ("shadow", "deepcopy"),
        ("output", "reconstruct"),
        ("volatility", "reconstruct"),
        ("overlay", "reconstruct"),
        ("card", "reconstruct"),
        ("shadow", "reconstruct"),
    ],
)
def test_ga04_rejects_unissued_authority(
    tmp_path: Path, authority_key: str, transform_name: str
) -> None:
    """Direct constructor / replace / copy / deepcopy / coherent reconstruction are rejected."""
    if transform_name == "replace":

        def transform(o: object) -> object:
            return dataclasses.replace(o)

    elif transform_name == "copy":
        transform = copy.copy
    elif transform_name == "deepcopy":
        transform = copy.deepcopy
    else:
        transform = _reconstruct_authority

    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        original = chain[authority_key]
        tampered_authority = transform(original)  # type: ignore[arg-type]
        assert tampered_authority is not original, (
            f"{transform_name} did not create a new object for {authority_key}"
        )
        tampered_chain = dict(chain)
        tampered_chain[authority_key] = tampered_authority
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before, (
            f"row counts changed after rejecting {transform_name} on {authority_key}"
        )
    finally:
        store.close()


@pytest.mark.parametrize(
    "authority_key",
    ["output", "volatility", "overlay"],
)
def test_ga04_rejects_cross_bundle_substitution(
    tmp_path: Path, authority_key: str
) -> None:
    """A legitimately issued authority from a different chain is rejected by
    identity correspondence (plan's embedded authority must be the very same
    object passed at the top level)."""
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain_a = _full_publication_chain(now)
        chain_b = _full_publication_chain(now)
        substitute = chain_b[authority_key]
        assert substitute is not chain_a[authority_key], (
            "chain B authority must be a different object"
        )
        tampered_chain = dict(chain_a)
        tampered_chain[authority_key] = substitute
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before
    finally:
        store.close()


# ============================================================
# GA-04: TradePlan object identity proof (Packet-required assertions)
# ============================================================
#
# The reuse-only validators already reject reconstructions of StrategyOutput,
# VolatilitySnapshot, OverlayDecision, OperatorReviewCard and ShadowOrder.
# They do NOT, however, distinguish the exact TradePlan object returned by
# build_plan() from any coherent reconstruction with identical values and
# hashes (dataclasses.replace with no field changes, copy.copy, copy.deepcopy
# with the same legitimate embedded authorities, or a freshly-built plan with
# the same legitimate embedded authorities). The P3B-local weakref proof
# registry closes this hole by binding the plan's own object identity.


def _plan_only_chain_with_transform(
    base_chain: dict[str, object], transformed_plan: object
) -> dict[str, object]:
    """Return a chain that swaps only the TradePlan object, keeping the
    same issued embedded authorities at the top level."""
    tampered = dict(base_chain)
    tampered["plan"] = transformed_plan
    return tampered


def test_ga04_direct_constructor_rejected(tmp_path: Path) -> None:
    """GA04_DIRECT_CONSTRUCTOR_REJECTED.

    A TradePlan constructed directly via ``type(plan)(**fields)`` (bypassing
    build_plan and the P3B-local proof registration) is rejected even when its
    plan_id, canonical_hash and embedded authorities are all legitimately
    issued and identical to the registered chain.
    """
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        original_plan = chain["plan"]
        direct_constructed = _reconstruct_authority(original_plan)
        assert direct_constructed is not original_plan
        # The direct constructor preserves plan_id / canonical_hash because
        # __post_init__ re-derives them deterministically from the same
        # embedded authorities.
        assert direct_constructed.plan_id == original_plan.plan_id  # type: ignore[attr-defined]
        assert direct_constructed.canonical_hash == original_plan.canonical_hash  # type: ignore[attr-defined]
        tampered_chain = _plan_only_chain_with_transform(chain, direct_constructed)
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before
    finally:
        store.close()


def test_ga04_dataclasses_replace_rejected(tmp_path: Path) -> None:
    """GA04_DATACLASSES_REPLACE_REJECTED."""
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        original_plan = chain["plan"]
        replaced = dataclasses.replace(original_plan)  # type: ignore[arg-type]
        assert replaced is not original_plan
        tampered_chain = _plan_only_chain_with_transform(chain, replaced)
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before
    finally:
        store.close()


def test_ga04_shallow_copy_rejected(tmp_path: Path) -> None:
    """GA04_SHALLOW_COPY_REJECTED."""
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        original_plan = chain["plan"]
        shallow = copy.copy(original_plan)  # type: ignore[arg-type]
        assert shallow is not original_plan
        tampered_chain = _plan_only_chain_with_transform(chain, shallow)
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before
    finally:
        store.close()


def test_ga04_deep_copy_rejected(tmp_path: Path) -> None:
    """GA04_DEEP_COPY_REJECTED.

    Deep copy creates a new plan AND new embedded authorities; the rejection
    can occur either at the embedded-authority identity check or at the
    TradePlan proof check. Both raise PersistenceAuthorityError.
    """
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        original_plan = chain["plan"]
        deep = copy.deepcopy(original_plan)  # type: ignore[arg-type]
        assert deep is not original_plan
        # The tampered chain passes the ORIGINAL embedded authorities at the
        # top level, but the deep-copied plan embeds its own copies. The
        # ``is`` checks and the proof check together reject this.
        tampered_chain = _plan_only_chain_with_transform(chain, deep)
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before
    finally:
        store.close()


def test_ga04_coherent_reconstruction_rejected(tmp_path: Path) -> None:
    """GA04_COHERENT_RECONSTRUCTION_REJECTED.

    A freshly-built TradePlan that shares the SAME legitimately issued
    embedded StrategyOutput / VolatilitySnapshot / OverlayDecision objects
    (so all reuse-only validators pass and the ``is`` checks succeed) but is
    NOT the exact object returned by build_plan() must still be rejected by
    the P3B-local weakref proof.
    """
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        original_plan = chain["plan"]
        # Coherent reconstruction: rebuild with the same fields, which means
        # the same embedded authorities (still issued). __post_init__ succeeds
        # and the plan_id/canonical_hash match the original. Only the proof
        # check can reject this.
        coherent = _reconstruct_authority(original_plan)
        assert coherent is not original_plan
        assert coherent.strategy_output is original_plan.strategy_output  # type: ignore[attr-defined]
        assert coherent.volatility_snapshot is original_plan.volatility_snapshot  # type: ignore[attr-defined]
        assert coherent.overlay is original_plan.overlay  # type: ignore[attr-defined]
        tampered_chain = _plan_only_chain_with_transform(chain, coherent)
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before
    finally:
        store.close()


def test_ga04_cross_bundle_substitution_rejected(tmp_path: Path) -> None:
    """GA04_CROSS_BUNDLE_SUBSTITUTION_REJECTED.

    A legitimately issued TradePlan from chain B (registered with chain B's
    embedded authorities) is rejected when substituted into chain A, even
    though the chain B plan itself is a legitimately issued plan object.
    """
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain_a = _full_publication_chain(now)
        chain_b = _full_publication_chain(now)
        plan_b = chain_b["plan"]
        assert plan_b is not chain_a["plan"]
        # Mix chain_a's embedded authorities with chain_b's plan: chain_b's
        # plan is registered with chain_b's embedded authorities, but we pass
        # chain_a's embedded authorities at the top level. The proof check
        # rejects because chain_a's authority identities differ from the
        # identities recorded in plan_b's proof entry.
        tampered_chain = {
            "output": chain_a["output"],
            "volatility": chain_a["volatility"],
            "overlay": chain_a["overlay"],
            "plan": plan_b,
            "card": chain_a["card"],
            "shadow": chain_a["shadow"],
        }
        before = _row_counts(store)
        with pytest.raises(PersistenceAuthorityError):
            _persist_chain(store, session_id, tampered_chain, now)
        after = _row_counts(store)
        assert after == before
    finally:
        store.close()


def test_ga04_rejection_zero_db_mutation(tmp_path: Path) -> None:
    """GA04_REJECTION_ZERO_DB_MUTATION.

    Every plan-identity rejection must occur before transaction mutation and
    leave publication_bundles and notification_outbox unchanged. Verifies
    across all four transforms in a single store instance.
    """
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        original_plan = chain["plan"]
        before = _row_counts(store)
        for transform in (
            lambda p: _reconstruct_authority(p),
            lambda p: dataclasses.replace(p),  # type: ignore[arg-type]
            copy.copy,
            copy.deepcopy,
        ):
            tampered_plan = transform(original_plan)
            assert tampered_plan is not original_plan
            tampered_chain = _plan_only_chain_with_transform(chain, tampered_plan)
            with pytest.raises(PersistenceAuthorityError):
                _persist_chain(store, session_id, tampered_chain, now)
            after = _row_counts(store)
            assert after == before, (
                f"row counts changed after rejecting {transform.__name__} on plan"
            )
    finally:
        store.close()


def test_ga04_failed_transaction_proof_retry_valid(tmp_path: Path) -> None:
    """GA04_FAILED_TRANSACTION_PROOF_RETRY_VALID.

    A failed persistence transaction (e.g. PublicationConflictError on a
    duplicate identity) must NOT invalidate the proof. The same exact TradePlan
    object must remain persistable on retry against a fresh store.
    """
    store_a = RuntimeStore.open(tmp_path / "store_a.db")
    store_b = RuntimeStore.open(tmp_path / "store_b.db")
    try:
        now = NOW
        session_a = _record_session(
            store_a, now=now, database_path=tmp_path / "store_a.db"
        )
        session_b = _record_session(
            store_b, now=now, database_path=tmp_path / "store_b.db"
        )
        chain = _full_publication_chain(now)
        # First successful persist on store_a.
        bundle_a, _outbox_a = _persist_chain(store_a, session_a, chain, now)  # type: ignore[misc]
        # Second persist on store_a with the same identities must raise
        # PublicationConflictError (IntegrityError -> PublicationConflictError).
        with pytest.raises(PublicationConflictError):
            _persist_chain(store_a, session_a, chain, now)
        # The proof must still be valid: the same exact plan object can be
        # persisted on a fresh store_b without re-registering the proof.
        bundle_b, outbox_b = _persist_chain(store_b, session_b, chain, now)  # type: ignore[misc]
        assert bundle_b.plan_id == bundle_a.plan_id
        assert outbox_b.status == "PENDING"  # type: ignore[union-attr]
    finally:
        store_a.close()
        store_b.close()


def test_ga04_legitimate_exact_plan_persists(tmp_path: Path) -> None:
    """GA04_LEGITIMATE_EXACT_PLAN_PERSISTS.

    The exact TradePlan object returned by build_plan() and registered with
    the P3B-local proof persists successfully (positive baseline).
    """
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        plan = chain["plan"]
        # Sanity: the plan object is registered in the proof registry.
        from trader_assist_v0.runtime.first_launch_runtime_store import (
            _TRADEPLAN_PROOF_REGISTRY,
        )

        entry = _TRADEPLAN_PROOF_REGISTRY.get(id(plan))
        assert entry is not None
        ref, _proof = entry
        assert ref() is plan
        # Persist succeeds.
        bundle, outbox = _persist_chain(store, session_id, chain, now)  # type: ignore[misc]
        assert bundle.plan_id == plan.plan_id  # type: ignore[attr-defined]
        assert outbox.status == "PENDING"  # type: ignore[union-attr]
        pubs, outbox_rows = _row_counts(store)
        assert pubs == 1
        assert outbox_rows == 1
    finally:
        store.close()


# ============================================================
# GA-06: non-IntegrityError rollback
# ============================================================


class _GA06InjectingStore(RuntimeStore):
    """RuntimeStore subclass that injects a non-IntegrityError on the outbox INSERT."""

    inject_failure: bool = False

    def _execute(
        self, sql: str, parameters: tuple[object, ...] = ()
    ) -> sqlite3.Cursor:
        if (
            type(self).inject_failure
            and "INSERT INTO notification_outbox" in sql
        ):
            raise sqlite3.OperationalError("injected GA-06 failure")
        return super()._execute(sql, parameters)


def test_ga06_non_integrity_error_rolls_back_atomically(tmp_path: Path) -> None:
    """A non-IntegrityError after the bundle insert but before the outbox insert
    rolls back the entire transaction, leaving zero new rows and a usable connection."""
    _GA06InjectingStore.inject_failure = True
    store = _GA06InjectingStore.open(tmp_path / "test_runtime.db")
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        before = _row_counts(store)
        with pytest.raises(sqlite3.OperationalError, match="injected GA-06 failure"):
            _persist_chain(store, session_id, chain, now)
        after = _row_counts(store)
        assert after == before, "partial insert must be rolled back"
        # The connection remains usable after rollback.
        assert store._connection.execute("SELECT 1").fetchone()[0] == 1
        # A subsequent legitimate transaction succeeds.
        _GA06InjectingStore.inject_failure = False
        bundle, outbox = _persist_chain(store, session_id, chain, now)  # type: ignore[misc]
        assert bundle.signal_id == chain["output"].setup_id  # type: ignore[attr-defined]
        assert outbox.status == "PENDING"  # type: ignore[union-attr]
        final_pubs, final_outbox = _row_counts(store)
        assert final_pubs == before[0] + 1
        assert final_outbox == before[1] + 1
    finally:
        store.close()
        _GA06InjectingStore.inject_failure = False


def test_ga06_integrity_error_remains_atomic_and_pending(tmp_path: Path) -> None:
    """An IntegrityError (duplicate identity) still rolls back atomically and
    leaves exactly one pending notification from the first successful insert."""
    store = _open_store(tmp_path)
    try:
        now = NOW
        session_id = _record_session(
            store, now=now, database_path=tmp_path / "test_runtime.db"
        )
        chain = _full_publication_chain(now)
        bundle, _outbox = _persist_chain(store, session_id, chain, now)  # type: ignore[misc]
        before = _row_counts(store)
        with pytest.raises(PublicationConflictError):
            _persist_chain(store, session_id, chain, now)
        after = _row_counts(store)
        assert after == before, "duplicate insert must not add rows"
        pending = store.list_pending_notifications()
        assert len(pending) == 1
        assert pending[0].notification_id == bundle.notification_id
    finally:
        store.close()
