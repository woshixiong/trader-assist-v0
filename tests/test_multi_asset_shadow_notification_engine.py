from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trader_assist_v0.multi_asset_shadow.models import RegistryTier
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    ClaimedOutboxMessage,
    DeliveryState,
    DeliveryTransition,
    EnqueueReceipt,
    NotificationKind,
    NotificationPublisher,
    OutboxDispatcher,
    ResearchNotificationView,
    RetryPolicy,
    ScannerWatchNotificationView,
    SignalNotificationView,
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookDeliveryError,
    WebhookResponse,
    build_envelope,
    format_notification,
)

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def formal(
    *,
    tier: RegistryTier = RegistryTier.P0,
    family: str = "SWEEP_RECLAIM",
    mode: str | None = None,
    side: str = "LONG",
    tp2: Decimal | None = Decimal("110"),
    session_warning: str | None = None,
) -> SignalNotificationView:
    return SignalNotificationView(
        kind=NotificationKind.FORMAL_SIGNAL,
        market_display="BTC-PERP",
        tier=tier,
        setup_family=family,
        setup_mode=mode,
        side=side,
        signal_time=NOW,
        planned_entry=Decimal("100"),
        stop=Decimal("98"),
        tp1=Decimal("104"),
        tp2=tp2,
        entry_quality="IDEAL",
        htf_relation="aligned with 1h structure",
        zone_context="5m demand reclaim",
        reference_risk_sizing="reference-only: 1% / 2% shadow bands",
        liquidity_attribution="L2 snapshot abc123",
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
        signal_id="signal-001",
        shadow_order_id="shadow-001",
        session_warning=session_warning,
    )


def scanner_watch(
    *, kind: NotificationKind = NotificationKind.WATCH, side: str | None = "LONG"
) -> ScannerWatchNotificationView:
    return ScannerWatchNotificationView(
        kind=kind,
        market_display="ETH-PERP",
        tier=RegistryTier.P2,
        side=side,
        observation_time=NOW,
        return_15m=Decimal("1.25"),
        return_30m=Decimal("2.50"),
        return_60m=Decimal("-0.75"),
        rank=3,
        move_atr=Decimal("1.4"),
        relative_volume=Decimal("2.1"),
        prior_level="3,500.00 range high",
        distance_to_level=Decimal("0.35"),
        liquidity_summary="bid liquidity stable; ask sweep observed",
        scanner_r3_state="R3_WATCH",
        session="US overlap",
        scanner_parameter_version="scanner-r3 / 2026-08-03-r1",
        watch_id=f"candidate-watch-{kind.value.lower()}-001",
        do_not_chase=True,
    )


def research() -> ResearchNotificationView:
    return ResearchNotificationView(
        kind=NotificationKind.RESEARCH_FAILED_BREAKOUT,
        market_display="BTC-PERP",
        tier=RegistryTier.P1,
        evidence_time=NOW,
        side="LONG",
        research_id="failed-breakout-research-001",
        source_shadow_order_id="shadow-001",
        outcome_id="outcome-001",
        failed_transition_ids=("failed-transition-001",),
        path_maturity_status="MATURE",
        required_end_ms=7_200_000,
        accepted_reentry_time_ms=180_000,
        reclaim_status="FAILED",
        conflict_count=0,
        has_gap=False,
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
    )


@pytest.mark.parametrize("tier", [RegistryTier.P0, RegistryTier.P1, RegistryTier.P2])
@pytest.mark.parametrize(
    ("family", "mode", "side"),
    [
        ("SWEEP_RECLAIM", None, "LONG"),
        ("BREAKOUT_RETEST", "MICRO_FAST", "SHORT"),
        ("BREAKOUT_RETEST", "STANDARD", "LONG"),
        ("RANGE_EDGE_REJECTION", None, "SHORT"),
    ],
)
def test_every_tier_and_setup_family_receives_a_formal_signal(
    tier: RegistryTier, family: str, mode: str | None, side: str
) -> None:
    rendered = format_notification(formal(tier=tier, family=family, mode=mode, side=side))
    assert "FORMAL SIGNAL — MANUAL REVIEW REQUIRED" in rendered
    assert f"Tier: {tier.value}" in rendered
    assert f"Setup: {family}" + (f" / {mode}" if mode is not None else "") in rendered
    assert f"Side: {side}" in rendered
    assert "NOT_SUBMITTED — NO ORDER SENT" in rendered


def test_formatter_is_deterministic_and_handles_missing_optional_tp2_and_session_warning() -> None:
    view = formal(tp2=None, session_warning="external reference session closing soon")
    assert format_notification(view) == format_notification(view)
    rendered = format_notification(view)
    assert "TP1: 104" in rendered
    assert "TP2:" not in rendered
    assert "SESSION WARNING: external reference session closing soon" in rendered
    assert "Reference risk sizing: reference-only: 1% / 2% shadow bands" in rendered


def test_directional_scanner_watch_is_complete_and_visibly_non_actionable() -> None:
    watch = format_notification(scanner_watch())
    assert watch.startswith("WATCH — NOT ACTIONABLE")
    assert "NOT_YET_SETUP_CONFIRMED" in watch
    for field in (
        "Market: ETH-PERP",
        "Tier: P2",
        "Side: LONG",
        "Observation time:",
        "15m return: 1.25",
        "30m return: 2.50",
        "60m return: -0.75",
        "Rank: 3",
        "Move ATR: 1.4",
        "Relative volume: 2.1",
        "Prior level: 3,500.00 range high",
        "Distance to level: 0.35",
        "Liquidity: bid liquidity stable; ask sweep observed",
        "Scanner R3 state: R3_WATCH",
        "Session: US overlap",
        "Scanner / parameters: scanner-r3 / 2026-08-03-r1",
        "Watch ID: candidate-watch-watch-001",
        "DO_NOT_CHASE",
    ):
        assert field in watch
    assert "FORMAL SIGNAL" not in watch
    for forbidden in ("Planned entry", "Stop:", "TP1", "TP2", "ShadowOrder", "order instruction"):
        assert forbidden not in watch


def test_watch_new_market_allows_no_side_but_directional_watch_does_not() -> None:
    watch = format_notification(scanner_watch(kind=NotificationKind.WATCH_NEW_MARKET, side=None))
    assert "Side:" not in watch
    with pytest.raises(ValueError, match="directional WATCH side"):
        scanner_watch(side=None)


def test_failed_breakout_research_is_constructible_distinct_and_non_actionable() -> None:
    view = research()
    rendered = format_notification(view)
    assert rendered.startswith("RESEARCH / FAILED_BREAKOUT EVIDENCE\nNOT ACTIONABLE")
    assert "NOT A FORMAL SIGNAL" in rendered
    assert "FORMAL SIGNAL — MANUAL REVIEW REQUIRED" not in rendered
    assert "WATCH — NOT ACTIONABLE" not in rendered
    assert {
        "evidence_summary",
        "outcome_summary",
        "planned_entry",
        "stop",
        "tp1",
        "tp2",
        "reference_execution_quantity",
        "order_submission_instruction",
    }.isdisjoint(vars(view))
    assert all(
        forbidden not in rendered
        for forbidden in ("Planned entry:", "Stop:", "TP1:", "TP2:", "Order instruction:")
    )
    envelope = build_envelope(view=view, created_at=NOW)
    assert envelope.kind is NotificationKind.RESEARCH_FAILED_BREAKOUT
    assert envelope.idempotency_key == build_envelope(view=view, created_at=NOW).idempotency_key
    assert envelope.idempotency_key != build_envelope(view=formal(), created_at=NOW).idempotency_key


@pytest.mark.parametrize("name", ("Idempotency-Key", "idempotency-key", "IDEMPOTENCY-KEY"))
def test_webhook_reserves_internal_idempotency_header(name: str) -> None:
    with pytest.raises(ValueError, match="reserved"):
        WebhookConfig(
            url="https://notifications.example.test/formal",
            authorization_header_name=name,
            authorization_header_value="forbidden",
        )


@pytest.mark.parametrize("mode", ["STANDARD_DEEP", "STANDARD_SHALLOW", "FAST", "MICRO"])
def test_formal_contract_rejects_unapproved_breakout_modes(mode: str) -> None:
    with pytest.raises(ValueError, match="approved breakout mode"):
        formal(family="BREAKOUT_RETEST", mode=mode)


def test_formal_contract_rejects_fake_non_breakout_mode_and_unknown_family() -> None:
    with pytest.raises(ValueError, match="non-breakout setups"):
        formal(family="SWEEP_RECLAIM", mode="STANDARD")
    with pytest.raises(ValueError, match="approved formal family"):
        formal(family="UNKNOWN", mode=None)


def test_idempotency_is_deterministic_and_does_not_depend_on_formatting_time() -> None:
    one = build_envelope(view=formal(), created_at=NOW)
    two = build_envelope(view=formal(), created_at=NOW + timedelta(minutes=1))
    assert one.idempotency_key == two.idempotency_key
    assert one.idempotency_key.startswith("masn-v1-")
    assert one.content == two.content


class FakeOutbox:
    def __init__(self, claims: tuple[ClaimedOutboxMessage, ...] = ()) -> None:
        self.envelopes: dict[str, object] = {}
        self.claims = claims
        self.completed: list[tuple[str, DeliveryTransition]] = []
        self.claim_calls: list[tuple[datetime, int, int]] = []

    def enqueue(self, envelope: object) -> EnqueueReceipt:
        key = envelope.idempotency_key  # type: ignore[attr-defined]
        existing = self.envelopes.get(key)
        if existing is not None:
            return EnqueueReceipt(envelope=existing, coalesced=True)  # type: ignore[arg-type]
        self.envelopes[key] = envelope
        return EnqueueReceipt(envelope=envelope, coalesced=False)  # type: ignore[arg-type]

    def claim_due(
        self, *, now: datetime, limit: int, lease_seconds: int
    ) -> tuple[ClaimedOutboxMessage, ...]:
        self.claim_calls.append((now, limit, lease_seconds))
        return self.claims[:limit]

    def complete(self, *, claim_token: str, transition: DeliveryTransition) -> None:
        self.completed.append((claim_token, transition))


@pytest.mark.parametrize(
    "view",
    (
        scanner_watch(),
        scanner_watch(kind=NotificationKind.WATCH_NEW_MARKET),
        research(),
    ),
)
def test_ordinary_publish_coalesces_non_formal_at_outbox_boundary(
    view: ScannerWatchNotificationView | ResearchNotificationView,
) -> None:
    outbox = FakeOutbox()
    publisher = NotificationPublisher(outbox)
    envelope = build_envelope(view=view, created_at=NOW)
    assert not publisher.publish(envelope).coalesced
    assert publisher.publish(envelope).coalesced
    assert len(outbox.envelopes) == 1


def test_notification_publisher_rejects_fabricated_formal_signal() -> None:
    outbox = FakeOutbox()
    envelope = build_envelope(view=formal(), created_at=NOW)

    with pytest.raises(ValueError, match="publish_formal_bundle"):
        NotificationPublisher(outbox).publish(envelope)

    assert not outbox.envelopes


class FakeWebhook:
    def __init__(self, response: WebhookResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def post(
        self, *, url: str, payload: bytes, headers: dict[str, str], timeout_seconds: float
    ) -> WebhookResponse:
        self.calls.append(
            {"url": url, "payload": payload, "headers": headers, "timeout": timeout_seconds}
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def dispatcher_for(
    *, attempt: int, response: WebhookResponse | Exception, max_attempts: int = 5
) -> tuple[FakeOutbox, FakeWebhook, OutboxDispatcher]:
    envelope = build_envelope(view=formal(), created_at=NOW)
    outbox = FakeOutbox((ClaimedOutboxMessage(envelope, attempt, f"claim-{attempt}"),))
    client = FakeWebhook(response)
    adapter = WebhookDeliveryAdapter(
        client=client,
        config=WebhookConfig(
            url="https://notifications.example.test/formal",
            authorization_header_name="Authorization",
            authorization_header_value="never-in-content",
        ),
    )
    return (
        outbox,
        client,
        OutboxDispatcher(
            outbox=outbox,
            adapter=adapter,
            retry_policy=RetryPolicy(
                max_attempts=max_attempts, base_delay_seconds=30, max_delay_seconds=60
            ),
        ),
    )


def test_transient_failure_retries_with_bounded_backoff() -> None:
    outbox, _, dispatcher = dispatcher_for(attempt=1, response=WebhookResponse(503))
    result = dispatcher.dispatch_due(now=NOW)
    transition = result[0].transition
    assert transition.state is DeliveryState.PENDING
    assert transition.reason == "retryable-status"
    assert transition.next_attempt_at == NOW + timedelta(seconds=30)
    assert outbox.completed == [("claim-1", transition)]


def test_permanent_failure_does_not_retry() -> None:
    outbox, _, dispatcher = dispatcher_for(attempt=1, response=WebhookResponse(422))
    transition = dispatcher.dispatch_due(now=NOW)[0].transition
    assert transition.state is DeliveryState.PERMANENT_FAILURE
    assert transition.reason == "permanent-status"
    assert transition.response_status == 422
    assert outbox.completed == [("claim-1", transition)]


def test_restart_facing_protocol_reclaims_a_durable_claim_for_a_new_dispatcher() -> None:
    # The Evidence implementation owns the expired-lease reclaim. A fresh dispatcher
    # receives the same durable envelope under a new token and can finish it safely.
    outbox, _, first_dispatcher = dispatcher_for(
        attempt=2, response=WebhookDeliveryError("connection reset")
    )
    first = first_dispatcher.dispatch_due(now=NOW)[0].transition
    assert first.state is DeliveryState.PENDING
    _, _, restarted_dispatcher = dispatcher_for(attempt=3, response=WebhookResponse(204))
    restarted_outbox = restarted_dispatcher._outbox  # type: ignore[attr-defined]
    assert isinstance(restarted_outbox, FakeOutbox)
    finished = restarted_dispatcher.dispatch_due(now=NOW + timedelta(minutes=2))[0].transition
    assert finished.state is DeliveryState.DELIVERED
    assert outbox.claim_calls[0] == (NOW, 100, 60)


def test_webhook_seam_is_injected_and_does_not_leak_secret_into_message_or_config_repr() -> None:
    outbox, client, dispatcher = dispatcher_for(attempt=1, response=WebhookResponse(200))
    result = dispatcher.dispatch_due(now=NOW)
    assert result[0].transition.state is DeliveryState.DELIVERED
    payload = client.calls[0]["payload"]
    assert isinstance(payload, bytes)
    assert json.loads(payload) == {"content": build_envelope(view=formal(), created_at=NOW).content}
    assert b"never-in-content" not in payload
    assert b"notifications.example.test" not in payload
    assert b"idempotency_key" not in payload
    assert b"schema_version" not in payload
    assert b"kind" not in payload
    headers = client.calls[0]["headers"]
    assert isinstance(headers, dict)
    assert "Idempotency-Key" not in headers
    assert "never-in-content" not in repr(dispatcher._adapter._config)  # type: ignore[attr-defined]
    assert len(client.calls) == 1  # fake client only: no real network transport is constructed.
    assert outbox.completed[0][1].response_status == 200
