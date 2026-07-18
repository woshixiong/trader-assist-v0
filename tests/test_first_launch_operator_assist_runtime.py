from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trader_assist_v0.first_launch.market_data import DataQualityState
from trader_assist_v0.first_launch.strategy import (
    PlanError,
    PreparedSetup,
    SetupFamily,
    Side,
    Signal,
    SignalState,
    StrategyOutput,
    evaluate_signal,
)
from trader_assist_v0.runtime.first_launch_operator_assist import (
    REQUIRED_PUBLIC_SUBSCRIPTIONS,
    InMemorySignalLifecycle,
    LifecycleTransitionError,
    ProtocolAcknowledgementError,
    PublicFrameError,
    PublicRuntimeProtocol,
    PublicSessionState,
    SessionStateError,
    SessionTimeoutError,
)


class Clocks:
    def __init__(self) -> None:
        self.utc_calls = 0
        self.monotonic = 0.0
        self.value = datetime(2026, 7, 19, tzinfo=UTC)

    def utc(self) -> datetime:
        self.utc_calls += 1
        return self.value

    def mono(self) -> float:
        return self.monotonic


def _ack(spec: object) -> str:
    return json.dumps(
        {"channel": "subscriptionResponse", "data": {"method": "subscribe", "subscription": spec}},
        separators=(",", ":"),
    )


def _active(protocol: PublicRuntimeProtocol) -> None:
    protocol.start()
    for spec in reversed(REQUIRED_PUBLIC_SUBSCRIPTIONS):
        assert protocol.accept_frame(_ack(spec.subscription)) is None
    assert protocol.state is PublicSessionState.ACTIVE


def _candle_frame() -> str:
    return '{"channel":"candle","data":{"s":"ETH","i":"5m","t":0}}'


def test_protocol_has_exact_frozen_subscriptions_and_canonical_requests() -> None:
    assert [spec.identity for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS] == [
        "ETH_CANDLE_5M",
        "ETH_CANDLE_15M",
        "ETH_ACTIVE_ASSET_CTX",
    ]
    assert [spec.request for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS] == [
        {
            "method": "subscribe",
            "subscription": {"type": "candle", "coin": "ETH", "interval": "5m"},
        },
        {
            "method": "subscribe",
            "subscription": {"type": "candle", "coin": "ETH", "interval": "15m"},
        },
        {"method": "subscribe", "subscription": {"type": "activeAssetCtx", "coin": "ETH"}},
    ]
    assert all(
        spec.request_text == json.dumps(spec.request, sort_keys=True, separators=(",", ":"))
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS
    )


def test_protocol_acknowledges_in_any_order_then_issues_exact_utc_frames() -> None:
    clocks = Clocks()
    protocol = PublicRuntimeProtocol("connection-1", clocks.utc, clocks.mono)
    assert protocol.receive_sequence == 0
    assert protocol.start() == tuple(spec.request_text for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS)
    for sequence, spec in enumerate(reversed(REQUIRED_PUBLIC_SUBSCRIPTIONS), 1):
        assert protocol.accept_frame(_ack(spec.subscription)) is None
        assert protocol.receive_sequence == sequence
    assert clocks.utc_calls == 0
    frame = protocol.accept_frame(_candle_frame())
    assert frame is not None and frame.raw_text == _candle_frame()
    assert frame.receive_sequence == 4 and frame.received_at.tzinfo is UTC
    assert clocks.utc_calls == 1
    second = protocol.accept_frame('{"channel":"activeAssetCtx","data":{"coin":"ETH"}}')
    assert second is not None and second.receive_sequence == 5


@pytest.mark.parametrize(
    "bad",
    [
        b"binary",
        '{"channel":"candle","channel":"candle","data":{}}',
        '{"channel":"candle","data":{"s":"BTC","i":"5m"}}',
    ],
)
def test_protocol_rejected_frames_fail_closed_without_sequence_increment(bad: str | bytes) -> None:
    clocks = Clocks()
    protocol = PublicRuntimeProtocol("connection-1", clocks.utc, clocks.mono)
    _active(protocol)
    with pytest.raises(PublicFrameError):
        protocol.accept_frame(bad)
    assert protocol.state is PublicSessionState.FAILED
    assert protocol.receive_sequence == 3 and clocks.utc_calls == 0
    with pytest.raises(SessionStateError):
        protocol.accept_frame(_candle_frame())


def test_acknowledgement_errors_timeout_disconnect_and_close_are_terminal() -> None:
    clocks = Clocks()
    protocol = PublicRuntimeProtocol(
        "connection-1",
        clocks.utc,
        clocks.mono,
        acknowledgement_timeout_seconds=1,
        session_timeout_seconds=2,
    )
    protocol.start()
    with pytest.raises(ProtocolAcknowledgementError):
        protocol.accept_frame(
            '{"channel":"subscriptionResponse","data":{"method":"subscribe","subscription":{"type":"candle","coin":"ETH","interval":"1m"}}}'
        )
    assert protocol.receive_sequence == 0 and clocks.utc_calls == 0

    clocks = Clocks()
    protocol = PublicRuntimeProtocol(
        "connection-1",
        clocks.utc,
        clocks.mono,
        acknowledgement_timeout_seconds=1,
        session_timeout_seconds=2,
    )
    protocol.start()
    clocks.monotonic = 1
    with pytest.raises(SessionTimeoutError, match="acknowledgement timeout"):
        protocol.check_timeout()
    with pytest.raises(SessionStateError):
        protocol.check_timeout()

    protocol = PublicRuntimeProtocol("connection-2", clocks.utc, clocks.mono)
    protocol.disconnect()
    protocol.disconnect()
    assert protocol.state is PublicSessionState.DISCONNECTED and protocol.close() is False
    with pytest.raises(SessionStateError):
        protocol.accept_frame(_candle_frame())
    protocol = PublicRuntimeProtocol("connection-3", clocks.utc, clocks.mono)
    assert protocol.close() is True and protocol.close() is False


def test_protocol_rejects_utc_normalization_and_repeated_start() -> None:
    clocks = Clocks()
    protocol = PublicRuntimeProtocol("connection-1", lambda: datetime(2026, 7, 19), clocks.mono)
    _active(protocol)
    with pytest.raises(PublicFrameError):
        protocol.accept_frame(_candle_frame())
    protocol = PublicRuntimeProtocol("connection-2", clocks.utc, clocks.mono)
    protocol.start()
    with pytest.raises(SessionStateError):
        protocol.start()


def _strategy_value(*, fast: bool) -> PreparedSetup | StrategyOutput:
    from tests.test_first_launch_strategy import _history, _snapshot

    c5, c15 = _history(SetupFamily.SWEEP_RECLAIM, Side.LONG, fast)
    result = evaluate_signal(_snapshot(c5, c15))
    assert type(result) is (StrategyOutput if fast else PreparedSetup)
    return result


def test_lifecycle_requires_issued_authority_and_suppresses_only_valid_duplicates() -> None:
    clocks = Clocks()
    lifecycle = InMemorySignalLifecycle(clocks.utc)
    fast = _strategy_value(fast=True)
    assert type(fast) is StrategyOutput
    emission = lifecycle.accept(fast)
    assert emission is not None and emission.output is fast
    assert lifecycle.accept(fast) is None and clocks.utc_calls == 1
    direct = StrategyOutput(*fast.__dict__.values())
    with pytest.raises(LifecycleTransitionError):
        lifecycle.accept(direct)
    assert lifecycle.state_for(fast.setup_id) is SignalState.TRIGGERED_FAST
    with pytest.raises(PlanError):
        lifecycle.accept(replace(fast, speed="STANDARD"))


def test_wait_watch_are_ignored_without_clock_or_state_mutation() -> None:
    clocks = Clocks()
    lifecycle = InMemorySignalLifecycle(clocks.utc)
    for signal in (
        Signal(SignalState.WAIT, None, None, None, "DATA_WARMING"),
        Signal(SignalState.WATCH, None, None, None, "LOOKING"),
        Signal(SignalState.WAIT, None, None, "a" * 64, "SETUP_ALREADY_DECIDED"),
    ):
        assert lifecycle.accept(signal) is None
    assert clocks.utc_calls == 0
    with pytest.raises(LifecycleTransitionError):
        lifecycle.accept(Signal(SignalState.WAIT, None, None, "a" * 64, "OTHER"))
    with pytest.raises(LifecycleTransitionError):
        lifecycle.accept(Signal(SignalState.PREPARE, Side.LONG, "STANDARD", "a" * 64, "FORGED"))


def test_prepare_advances_only_through_strategy_and_terminal_paths_are_immutable() -> None:
    clocks = Clocks()
    lifecycle = InMemorySignalLifecycle(clocks.utc)
    prepared = _strategy_value(fast=False)
    assert type(prepared) is PreparedSetup
    assert lifecycle.accept(prepared) is not None
    assert lifecycle.accept(prepared) is None
    direct = PreparedSetup(prepared.provenance, prepared.expires_after_open_time_ms)
    with pytest.raises(LifecycleTransitionError):
        lifecycle.accept(direct)
    with pytest.raises(LifecycleTransitionError):
        lifecycle.terminate(prepared.setup_id, SignalState.TAKEN)

    from tests.test_first_launch_strategy import _history, _snapshot

    c5, c15 = _history(SetupFamily.SWEEP_RECLAIM, Side.LONG, False)
    boundary = prepared.provenance.boundary
    from tests.test_first_launch_strategy import _candle

    retest = _candle(
        27 * 300_000,
        open=str(boundary),
        high=str(boundary + 1),
        low=str(boundary),
        close=str(boundary + 1),
        volume="10",
    )
    emission = lifecycle.advance(prepared.setup_id, _snapshot((*c5, retest), c15))
    assert emission is not None and emission.state is SignalState.TRIGGERED_STANDARD
    assert lifecycle.terminate(prepared.setup_id, SignalState.TAKEN) is not None
    assert lifecycle.terminate(prepared.setup_id, SignalState.TAKEN) is None
    with pytest.raises(LifecycleTransitionError):
        lifecycle.terminate(prepared.setup_id, SignalState.SKIPPED)
    with pytest.raises(LifecycleTransitionError):
        lifecycle.advance(prepared.setup_id, _snapshot((*c5, retest), c15))


def test_observe_uses_exact_utc_clock_and_emission_identity_is_deterministic() -> None:
    clocks = Clocks()
    lifecycle = InMemorySignalLifecycle(clocks.utc)
    fast = _strategy_value(fast=True)
    assert type(fast) is StrategyOutput
    first = lifecycle.accept(fast)
    assert first is not None
    clocks.value = fast.expires_at
    terminal = lifecycle.observe(
        fast.setup_id, reference=fast.raw_entry_low, quality=DataQualityState.READY
    )
    assert terminal is not None and terminal.state is SignalState.EXPIRED
    expected = hashlib.sha256(
        b"trader-assist-v0/first-launch/lifecycle-emission/v1\0"
        + json.dumps(
            {"setup_id": fast.setup_id, "state": "EXPIRED"}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert terminal.emission_id == expected


def test_private_import_boundary_and_no_transport_owner_surface() -> None:
    source = Path("src/trader_assist_v0/runtime/first_launch_operator_assist.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    private_strategy = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "trader_assist_v0.first_launch.strategy"
        for alias in node.names
        if alias.name.startswith("_")
    }
    private_market = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "trader_assist_v0.first_launch.market_data"
        for alias in node.names
        if alias.name.startswith("_")
    }
    assert private_strategy == {"_validated_prepared_setup", "_validated_strategy_output"}
    assert private_market == set()
    assert "PublicWebSocketConnection" not in source
    for forbidden in (
        "websockets",
        "build_plan",
        "TradePlan",
        "permit",
        "shadow",
        "private_key",
        "nonce",
    ):
        assert forbidden not in source
