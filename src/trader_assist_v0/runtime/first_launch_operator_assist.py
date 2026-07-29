"""Deterministic public-frame protocol and in-memory strategy lifecycle.

This module deliberately owns neither a network connection nor any persistence.
It admits a small public transport surface and retains already-issued strategy
authority only for the lifetime of the current process.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Final, Literal, cast

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.market_data import DataQualityState, StrategySnapshot
from trader_assist_v0.first_launch.strategy import (
    PreparedSetup,
    Signal,
    SignalState,
    StrategyOutput,
    _validated_prepared_setup,
    _validated_strategy_output,
    advance_prepare,
    lifecycle_state,
)

SubscriptionIdentity = Literal["ETH_CANDLE_5M", "ETH_CANDLE_15M", "ETH_ACTIVE_ASSET_CTX"]
UtcClock = Callable[[], datetime]
MonotonicClock = Callable[[], float]

_EMISSION_HASH_DOMAIN: Final = b"trader-assist-v0/first-launch/lifecycle-emission/v1"
_SETUP_ID_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_CANDLE_INTERVAL_MILLISECONDS: Final[dict[str, int]] = {
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
}
_CANDLE_REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
    {"t", "T", "s", "i", "o", "h", "l", "c", "v", "n"}
)


class OperatorAssistRuntimeError(RuntimeError):
    pass


class PublicTransportError(OperatorAssistRuntimeError):
    pass


class ProtocolAcknowledgementError(PublicTransportError):
    pass


class PublicFrameError(PublicTransportError):
    pass


class SessionTimeoutError(PublicTransportError):
    pass


class SessionStateError(PublicTransportError):
    pass


class LifecycleRuntimeError(OperatorAssistRuntimeError):
    pass


class LifecycleTransitionError(LifecycleRuntimeError):
    pass


@dataclass(frozen=True)
class PublicSubscriptionSpec:
    identity: SubscriptionIdentity
    subscription_type: Literal["candle", "activeAssetCtx"]
    coin: Literal["ETH"]
    interval: Literal["5m", "15m"] | None

    @property
    def subscription(self) -> dict[str, str]:
        result: dict[str, str] = {"type": self.subscription_type, "coin": self.coin}
        if self.interval is not None:
            result["interval"] = self.interval
        return result

    @property
    def request(self) -> dict[str, object]:
        return {"method": "subscribe", "subscription": self.subscription}

    @property
    def request_text(self) -> str:
        return canonical_json_bytes(self.request).decode("utf-8")


REQUIRED_PUBLIC_SUBSCRIPTIONS: Final[
    tuple[PublicSubscriptionSpec, PublicSubscriptionSpec, PublicSubscriptionSpec]
] = (
    PublicSubscriptionSpec("ETH_CANDLE_5M", "candle", "ETH", "5m"),
    PublicSubscriptionSpec("ETH_CANDLE_15M", "candle", "ETH", "15m"),
    PublicSubscriptionSpec("ETH_ACTIVE_ASSET_CTX", "activeAssetCtx", "ETH", None),
)


class PublicSessionState(StrEnum):
    NEW = "NEW"
    AWAITING_ACKNOWLEDGEMENTS = "AWAITING_ACKNOWLEDGEMENTS"
    ACTIVE = "ACTIVE"
    TIMED_OUT = "TIMED_OUT"
    DISCONNECTED = "DISCONNECTED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


_TERMINAL_SESSION_STATES = frozenset(
    {
        PublicSessionState.TIMED_OUT,
        PublicSessionState.DISCONNECTED,
        PublicSessionState.CLOSED,
        PublicSessionState.FAILED,
    }
)


@dataclass(frozen=True)
class AcceptedPublicFrame:
    raw_text: str
    received_at: datetime
    receive_sequence: int
    connection_id: str
    channel: Literal["candle", "activeAssetCtx"]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON value")


def _strict_json(raw: str) -> object:
    try:
        return json.loads(
            raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("strict JSON is required") from exc


def _exact_utc(value: object, error: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise ValueError(error)
    return value


def _finite_positive(value: object) -> float:
    if type(value) not in {int, float} or isinstance(value, bool):
        raise ValueError("timeout must be a finite positive number")
    result = float(cast(int | float, value))
    if not math.isfinite(result) or result <= 0:
        raise ValueError("timeout must be a finite positive number")
    return result


def _wire_decimal(
    value: object,
    name: str,
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> Decimal:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{name} must be a base-10 decimal string")
    if "e" in value.lower():
        raise ValueError(f"{name} must not use exponent notation")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} is not decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    if non_negative and result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _wire_non_negative_integer(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _validate_candle_payload(payload: dict[str, object]) -> int:
    if not _CANDLE_REQUIRED_KEYS.issubset(payload):
        raise ValueError("candle frame is incomplete")
    if payload.get("s") != "ETH":
        raise ValueError("candle identity is invalid")
    interval = payload.get("i")
    if type(interval) is not str or interval not in _CANDLE_INTERVAL_MILLISECONDS:
        raise ValueError("candle interval is invalid")
    open_time = _wire_non_negative_integer(payload.get("t"), "candle open time")
    close_time = _wire_non_negative_integer(payload.get("T"), "candle close time")
    _wire_non_negative_integer(payload.get("n"), "candle trade count")
    if close_time - open_time != _CANDLE_INTERVAL_MILLISECONDS[interval] - 1:
        raise ValueError("candle interval boundary is invalid")
    open_price = _wire_decimal(payload.get("o"), "open", positive=True)
    high = _wire_decimal(payload.get("h"), "high", positive=True)
    low = _wire_decimal(payload.get("l"), "low", positive=True)
    close = _wire_decimal(payload.get("c"), "close", positive=True)
    _wire_decimal(payload.get("v"), "volume", non_negative=True)
    if low > min(open_price, close) or high < max(open_price, close):
        raise ValueError("candle OHLC range is invalid")
    return close_time


def _validate_context_payload(payload: dict[str, object]) -> None:
    if payload.get("coin") != "ETH":
        raise ValueError("active asset identity is invalid")
    nested = payload.get("ctx")
    context = cast(dict[str, object], nested) if type(nested) is dict else payload
    _wire_decimal(context.get("markPx"), "markPx", positive=True)
    mid = context.get("midPx")
    if mid is not None:
        _wire_decimal(mid, "midPx", positive=True)
    _wire_decimal(context.get("openInterest"), "openInterest", non_negative=True)
    _wire_decimal(context.get("funding"), "funding")
    source_time = context.get("time")
    if source_time is not None:
        _wire_non_negative_integer(source_time, "context time")


def _public_identity_parts(
    value: object,
) -> tuple[Literal["candle", "activeAssetCtx"], dict[str, object]]:
    if type(value) is not dict or set(value) != {"channel", "data"}:
        raise ValueError("public frame shape is invalid")
    document = cast(dict[str, object], value)
    channel = document["channel"]
    data = document["data"]
    if channel not in {"candle", "activeAssetCtx"} or type(data) is not dict:
        raise ValueError("public frame channel is invalid")
    payload = cast(dict[str, object], data)
    if channel == "candle":
        if payload.get("s") != "ETH" or payload.get("i") not in {"5m", "15m"}:
            raise ValueError("candle identity is invalid")
    elif payload.get("coin") != "ETH":
        raise ValueError("active asset identity is invalid")
    return cast(Literal["candle", "activeAssetCtx"], channel), payload


@dataclass
class PublicRuntimeProtocol:
    connection_id: str
    utc_now: UtcClock
    monotonic_now: MonotonicClock
    acknowledgement_timeout_seconds: float = 20.0
    session_timeout_seconds: float = 21600.0
    _state: PublicSessionState = field(init=False, default=PublicSessionState.NEW)
    _receive_sequence: int = field(init=False, default=0)
    _acknowledged: set[SubscriptionIdentity] = field(init=False, default_factory=set)
    _acknowledgement_deadline: float | None = field(init=False, default=None)
    _session_deadline: float | None = field(init=False, default=None)

    @property
    def state(self) -> PublicSessionState:
        return self._state

    @property
    def receive_sequence(self) -> int:
        return self._receive_sequence

    @property
    def acknowledged_subscriptions(self) -> frozenset[SubscriptionIdentity]:
        return frozenset(self._acknowledged)

    @property
    def remaining_subscriptions(self) -> tuple[SubscriptionIdentity, ...]:
        return tuple(
            item.identity
            for item in REQUIRED_PUBLIC_SUBSCRIPTIONS
            if item.identity not in self._acknowledged
        )

    def _failed(self, error: type[PublicTransportError], message: str) -> None:
        self._state = PublicSessionState.FAILED
        raise error(message)

    def _monotonic_sample(self) -> float:
        try:
            value = self.monotonic_now()
            if type(value) not in {int, float} or isinstance(value, bool):
                raise ValueError
            result = float(cast(int | float, value))
        except (TypeError, ValueError) as exc:
            self._state = PublicSessionState.FAILED
            raise SessionStateError("monotonic clock is invalid") from exc
        if not math.isfinite(result):
            self._state = PublicSessionState.FAILED
            raise SessionStateError("monotonic clock is invalid")
        return result

    def _enforce_timeout(self) -> None:
        if self._state in _TERMINAL_SESSION_STATES:
            raise SessionStateError("session is terminal")
        if self._state is PublicSessionState.NEW:
            return
        now = self._monotonic_sample()
        if self._state is PublicSessionState.AWAITING_ACKNOWLEDGEMENTS:
            acknowledgement_deadline = self._acknowledgement_deadline
            if acknowledgement_deadline is None:
                self._failed(SessionStateError, "acknowledgement deadline is unavailable")
                raise AssertionError("unreachable")
            if now >= acknowledgement_deadline:
                self._state = PublicSessionState.TIMED_OUT
                raise SessionTimeoutError("acknowledgement timeout")
        elif self._state is PublicSessionState.ACTIVE:
            session_deadline = self._session_deadline
            if session_deadline is None:
                self._failed(SessionStateError, "session deadline is unavailable")
                raise AssertionError("unreachable")
            if now >= session_deadline:
                self._state = PublicSessionState.TIMED_OUT
                raise SessionTimeoutError("session timeout")

    def start(self) -> tuple[str, str, str]:
        if self._state is not PublicSessionState.NEW:
            raise SessionStateError("session has already started")
        if (
            type(self.connection_id) is not str
            or not self.connection_id
            or self.connection_id.strip() != self.connection_id
        ):
            self._failed(SessionStateError, "connection identity is invalid")
        if not callable(self.utc_now) or not callable(self.monotonic_now):
            self._failed(SessionStateError, "session clocks are invalid")
        try:
            acknowledgement_timeout = _finite_positive(self.acknowledgement_timeout_seconds)
            session_timeout = _finite_positive(self.session_timeout_seconds)
        except ValueError as exc:
            self._failed(SessionStateError, str(exc))
            raise AssertionError("unreachable") from exc
        if session_timeout < acknowledgement_timeout:
            self._failed(
                SessionStateError, "session timeout is shorter than acknowledgement timeout"
            )
        started = self._monotonic_sample()
        self._acknowledgement_deadline = started + acknowledgement_timeout
        self._session_deadline = started + session_timeout
        self._state = PublicSessionState.AWAITING_ACKNOWLEDGEMENTS
        return cast(
            tuple[str, str, str], tuple(item.request_text for item in REQUIRED_PUBLIC_SUBSCRIPTIONS)
        )

    def _acknowledgement_identity(self, value: object) -> SubscriptionIdentity:
        if type(value) is not dict or set(value) != {"channel", "data"}:
            raise ValueError("acknowledgement shape is invalid")
        document = cast(dict[str, object], value)
        if document["channel"] != "subscriptionResponse":
            raise ValueError("acknowledgement channel is invalid")
        data = document["data"]
        if type(data) is not dict or set(data) != {"method", "subscription"}:
            raise ValueError("acknowledgement data is invalid")
        payload = cast(dict[str, object], data)
        if payload["method"] != "subscribe" or type(payload["subscription"]) is not dict:
            raise ValueError("acknowledgement subscription is invalid")
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
            if payload["subscription"] == spec.subscription:
                return spec.identity
        raise ValueError("acknowledgement subscription is unknown")

    def accept_frame(self, frame: str | bytes) -> AcceptedPublicFrame | None:
        if self._state is PublicSessionState.NEW:
            self._state = PublicSessionState.FAILED
            raise SessionStateError("session has not started")
        self._enforce_timeout()
        acknowledgement_phase = self._state is PublicSessionState.AWAITING_ACKNOWLEDGEMENTS
        error = ProtocolAcknowledgementError if acknowledgement_phase else PublicFrameError
        if type(frame) is not str:
            self._failed(error, "binary public frame is prohibited")
            raise AssertionError("unreachable")
        try:
            value = _strict_json(frame)
        except ValueError as exc:
            self._failed(error, "public frame is malformed")
            raise AssertionError("unreachable") from exc
        if acknowledgement_phase:
            if (
                type(value) is dict
                and set(value) == {"channel", "data"}
                and value.get("channel") == "subscriptionResponse"
            ):
                try:
                    identity = self._acknowledgement_identity(value)
                except ValueError as exc:
                    self._failed(ProtocolAcknowledgementError, str(exc))
                    raise AssertionError("unreachable") from exc
                if identity in self._acknowledged:
                    self._failed(ProtocolAcknowledgementError, "duplicate acknowledgement")
                self._receive_sequence += 1
                self._acknowledged.add(identity)
                if len(self._acknowledged) == len(REQUIRED_PUBLIC_SUBSCRIPTIONS):
                    self._state = PublicSessionState.ACTIVE
                return None
            try:
                channel, payload = _public_identity_parts(value)
                if channel == "candle":
                    _validate_candle_payload(payload)
                else:
                    _validate_context_payload(payload)
            except ValueError as exc:
                self._failed(ProtocolAcknowledgementError, str(exc))
                raise AssertionError("unreachable") from exc
            # Hyperliquid may interleave authorized public data with subscription
            # responses. Before all acknowledgements arrive, validate and ignore
            # those frames without issuing sequence or market-data authority.
            return None
        try:
            channel, payload = _public_identity_parts(value)
        except ValueError as exc:
            self._failed(PublicFrameError, str(exc))
            raise AssertionError("unreachable") from exc
        try:
            received_at = _exact_utc(self.utc_now(), "UTC clock is invalid")
        except ValueError as exc:
            self._failed(PublicFrameError, str(exc))
            raise AssertionError("unreachable") from exc
        if channel == "candle":
            try:
                close_time = _validate_candle_payload(payload)
            except ValueError:
                # Preserve the established protocol/runtime layering: malformed
                # authorized-identity frames continue to the market-data parser,
                # which withdraws READY and fails closed with its original error.
                close_time = None
            if close_time is not None and close_time >= int(received_at.timestamp() * 1000):
                # A structurally valid current candle is ordinary non-authoritative
                # transport traffic until its inclusive close timestamp has passed.
                return None
        self._receive_sequence += 1
        return AcceptedPublicFrame(
            frame,
            received_at,
            self._receive_sequence,
            self.connection_id,
            channel,
        )

    def check_timeout(self) -> None:
        self._enforce_timeout()

    def disconnect(self) -> None:
        if self._state in _TERMINAL_SESSION_STATES:
            return
        self._state = PublicSessionState.DISCONNECTED

    def close(self) -> bool:
        if self._state in _TERMINAL_SESSION_STATES:
            return False
        self._state = PublicSessionState.CLOSED
        return True


@dataclass(frozen=True)
class LifecycleEmission:
    setup_id: str
    state: SignalState
    speed: Literal["FAST", "STANDARD"] | None
    emitted_at: datetime
    emission_id: str
    output: StrategyOutput | None


def _setup_id(value: object) -> str:
    if type(value) is not str or _SETUP_ID_RE.fullmatch(value) is None:
        raise LifecycleTransitionError("setup identity is invalid")
    return value


def _signal_is_ignored(value: Signal) -> bool:
    if type(value.reason) is not str or not value.reason or value.reason.strip() != value.reason:
        return False
    if value.state is SignalState.WATCH:
        return value.side is None and value.speed is None and value.setup_id is None
    if value.state is SignalState.WAIT:
        if value.side is not None or value.speed is not None:
            return False
        if value.setup_id is None:
            return True
        return (
            value.reason == "SETUP_ALREADY_DECIDED"
            and type(value.setup_id) is str
            and _SETUP_ID_RE.fullmatch(value.setup_id) is not None
        )
    return False


@dataclass
class InMemorySignalLifecycle:
    utc_now: UtcClock
    _states: dict[str, SignalState] = field(init=False, default_factory=dict)
    _prepared: dict[str, PreparedSetup] = field(init=False, default_factory=dict)
    _outputs: dict[str, StrategyOutput] = field(init=False, default_factory=dict)
    _emitted_ids: set[str] = field(init=False, default_factory=set)

    def _container_snapshot(
        self,
    ) -> tuple[
        dict[str, SignalState],
        dict[str, PreparedSetup],
        dict[str, StrategyOutput],
        set[str],
    ]:
        return self._states, self._prepared, self._outputs, self._emitted_ids

    def _require_current_containers(
        self,
        expected: tuple[
            dict[str, SignalState],
            dict[str, PreparedSetup],
            dict[str, StrategyOutput],
            set[str],
        ],
    ) -> None:
        expected_states, expected_prepared, expected_outputs, expected_emitted_ids = expected
        if (
            self._states is not expected_states
            or self._prepared is not expected_prepared
            or self._outputs is not expected_outputs
            or self._emitted_ids is not expected_emitted_ids
        ):
            raise LifecycleTransitionError("lifecycle changed during external callback")

    def _timestamp(self) -> datetime:
        try:
            return _exact_utc(self.utc_now(), "UTC clock is invalid")
        except (TypeError, ValueError) as exc:
            raise LifecycleTransitionError("UTC clock is invalid") from exc

    def _emission_payload(
        self, setup_id: str, state: SignalState, value: PreparedSetup | StrategyOutput | None
    ) -> dict[str, object]:
        if type(state) is not SignalState:
            raise LifecycleTransitionError("emission state is invalid")
        if state is SignalState.PREPARE:
            if type(value) is not PreparedSetup:
                raise LifecycleTransitionError("prepare emission authority is invalid")
            return {
                "setup_id": setup_id,
                "state": "PREPARE",
                "expires_after_open_time_ms": value.expires_after_open_time_ms,
            }
        if state in {SignalState.TRIGGERED_FAST, SignalState.TRIGGERED_STANDARD}:
            if type(value) is not StrategyOutput:
                raise LifecycleTransitionError("output emission authority is invalid")
            return {
                "setup_id": value.setup_id,
                "state": value.state.value,
                "speed": value.speed,
                "decision_trigger_identity": value.decision_trigger_identity,
                "decision_trigger_canonical_hash": value.decision_trigger_canonical_hash,
            }
        return {"setup_id": setup_id, "state": state.value}

    def _build_emission(
        self,
        setup_id: str,
        state: SignalState,
        value: PreparedSetup | StrategyOutput | None,
        *,
        emitted_at: datetime | None = None,
    ) -> LifecycleEmission | None:
        payload = self._emission_payload(setup_id, state, value)
        emission_id = hashlib.sha256(
            _EMISSION_HASH_DOMAIN + b"\0" + canonical_json_bytes(payload)
        ).hexdigest()
        if emission_id in self._emitted_ids:
            return None
        try:
            timestamp = (
                self._timestamp()
                if emitted_at is None
                else _exact_utc(emitted_at, "UTC clock is invalid")
            )
        except (TypeError, ValueError) as exc:
            raise LifecycleTransitionError("UTC clock is invalid") from exc
        output = value if type(value) is StrategyOutput else None
        speed = output.speed if output is not None else None
        return LifecycleEmission(setup_id, state, speed, timestamp, emission_id, output)

    def _commit_transition(
        self,
        emission: LifecycleEmission,
        state: SignalState,
        expected: tuple[
            dict[str, SignalState],
            dict[str, PreparedSetup],
            dict[str, StrategyOutput],
            set[str],
        ],
        *,
        prepared: PreparedSetup | None = None,
        output: StrategyOutput | None = None,
        remove_prepared: bool = False,
    ) -> LifecycleEmission:
        self._require_current_containers(expected)
        try:
            next_states = self._states.copy()
            next_prepared = self._prepared.copy()
            next_outputs = self._outputs.copy()
            next_emitted_ids = self._emitted_ids.copy()
            if emission.emission_id in next_emitted_ids:
                raise LifecycleTransitionError("emission conflicts with retained identity")
            next_states[emission.setup_id] = state
            if remove_prepared:
                del next_prepared[emission.setup_id]
            elif prepared is not None:
                next_prepared[emission.setup_id] = prepared
            if output is not None:
                next_outputs[emission.setup_id] = output
            next_emitted_ids.add(emission.emission_id)
        except MemoryError as exc:
            raise LifecycleTransitionError("lifecycle transition planning failed") from exc
        self._states = next_states
        self._prepared = next_prepared
        self._outputs = next_outputs
        self._emitted_ids = next_emitted_ids
        return emission

    def _validate_prepared(self, value: object) -> PreparedSetup:
        try:
            return _validated_prepared_setup(value)
        except (TypeError, ValueError) as exc:
            raise LifecycleTransitionError("prepared setup authority is invalid") from exc

    def _validate_output(self, value: object) -> StrategyOutput:
        try:
            return _validated_strategy_output(cast(StrategyOutput, value))
        except (TypeError, ValueError) as exc:
            raise LifecycleTransitionError("strategy output authority is invalid") from exc

    def state_for(self, setup_id: str) -> SignalState | None:
        return self._states.get(_setup_id(setup_id))

    def accept(self, value: Signal | PreparedSetup | StrategyOutput) -> LifecycleEmission | None:
        if type(value) is Signal:
            if type(value.state) is not SignalState:
                raise LifecycleTransitionError("external signal state is invalid")
            if not _signal_is_ignored(value):
                raise LifecycleTransitionError("external signal transition authority is invalid")
            return None
        if type(value) is PreparedSetup:
            setup = self._validate_prepared(value)
            setup_id = _setup_id(setup.setup_id)
            current = self._states.get(setup_id)
            if current is None:
                expected = self._container_snapshot()
                emission = self._build_emission(setup_id, SignalState.PREPARE, setup)
                if emission is None:
                    raise LifecycleTransitionError(
                        "prepare emission conflicts with retained identity"
                    )
                return self._commit_transition(
                    emission, SignalState.PREPARE, expected, prepared=setup
                )
            if current is SignalState.PREPARE and self._prepared.get(setup_id) == setup:
                return None
            raise LifecycleTransitionError("prepared setup conflicts with lifecycle state")
        output = self._validate_output(value)
        setup_id = _setup_id(output.setup_id)
        if output.speed == "STANDARD":
            raise LifecycleTransitionError("direct standard promotion is prohibited")
        if output.speed != "FAST" or output.state is not SignalState.TRIGGERED_FAST:
            raise LifecycleTransitionError("strategy output transition is invalid")
        current = self._states.get(setup_id)
        if current is None:
            expected = self._container_snapshot()
            emission = self._build_emission(setup_id, SignalState.TRIGGERED_FAST, output)
            if emission is None:
                raise LifecycleTransitionError("fast emission conflicts with retained identity")
            return self._commit_transition(
                emission, SignalState.TRIGGERED_FAST, expected, output=output
            )
        if current is SignalState.TRIGGERED_FAST and self._outputs.get(setup_id) == output:
            return None
        raise LifecycleTransitionError("fast output conflicts with lifecycle state")

    def advance(self, setup_id: str, snapshot: StrategySnapshot) -> LifecycleEmission | None:
        setup_id = _setup_id(setup_id)
        if self._states.get(setup_id) is not SignalState.PREPARE or setup_id not in self._prepared:
            raise LifecycleTransitionError("advance requires retained prepare")
        retained = self._validate_prepared(self._prepared[setup_id])
        expected = self._container_snapshot()
        try:
            result = advance_prepare(retained, snapshot)
        except (TypeError, ValueError) as exc:
            raise LifecycleTransitionError("prepare advance failed") from exc
        self._require_current_containers(expected)
        if type(result) is Signal:
            if (
                type(result.state) is not SignalState
                or result.setup_id != setup_id
                or result.side is not retained.provenance.side
                or result.speed != "STANDARD"
                or result.state
                not in {
                    SignalState.PREPARE,
                    SignalState.EXPIRED,
                    SignalState.INVALIDATED,
                    SignalState.REJECTED,
                }
                or type(result.reason) is not str
                or not result.reason
                or result.reason.strip() != result.reason
            ):
                raise LifecycleTransitionError("advance signal is inconsistent")
            if result.state is SignalState.PREPARE:
                return None
            emission = self._build_emission(setup_id, result.state, None)
            if emission is None:
                raise LifecycleTransitionError("terminal emission conflicts with retained identity")
            return self._commit_transition(emission, result.state, expected, remove_prepared=True)
        if type(result) is not StrategyOutput:
            raise LifecycleTransitionError("advance returned an invalid type")
        output = self._validate_output(result)
        if (
            output.speed != "STANDARD"
            or output.state is not SignalState.TRIGGERED_STANDARD
            or output.setup_id != setup_id
            or output.provenance != retained.provenance
        ):
            raise LifecycleTransitionError("standard promotion is inconsistent")
        emission = self._build_emission(setup_id, SignalState.TRIGGERED_STANDARD, output)
        if emission is None:
            raise LifecycleTransitionError("standard emission conflicts with retained identity")
        return self._commit_transition(
            emission,
            SignalState.TRIGGERED_STANDARD,
            expected,
            output=output,
            remove_prepared=True,
        )

    def observe(
        self, setup_id: str, *, reference: Decimal, quality: DataQualityState
    ) -> LifecycleEmission | None:
        setup_id = _setup_id(setup_id)
        current = self._states.get(setup_id)
        if current not in {SignalState.TRIGGERED_FAST, SignalState.TRIGGERED_STANDARD}:
            raise LifecycleTransitionError("observe requires an active output")
        if type(reference) is not Decimal or not reference.is_finite() or reference <= 0:
            raise LifecycleTransitionError("reference is invalid")
        if type(quality) is not DataQualityState:
            raise LifecycleTransitionError("quality is invalid")
        output = self._validate_output(self._outputs[setup_id])
        expected = self._container_snapshot()
        now = self._timestamp()
        self._require_current_containers(expected)
        try:
            next_state = lifecycle_state(output, now=now, reference=reference, quality=quality)
        except (TypeError, ValueError) as exc:
            raise LifecycleTransitionError("output observation failed") from exc
        self._require_current_containers(expected)
        if type(next_state) is not SignalState:
            raise LifecycleTransitionError("output observation returned an invalid state")
        if next_state is current:
            return None
        if next_state not in {SignalState.EXPIRED, SignalState.INVALIDATED}:
            raise LifecycleTransitionError("output observation returned an invalid state")
        emission = self._build_emission(setup_id, next_state, None, emitted_at=now)
        if emission is None:
            raise LifecycleTransitionError("terminal emission conflicts with retained identity")
        return self._commit_transition(emission, next_state, expected)

    def terminate(self, setup_id: str, terminal: SignalState) -> LifecycleEmission | None:
        setup_id = _setup_id(setup_id)
        if type(terminal) is not SignalState:
            raise LifecycleTransitionError("terminal state is invalid")
        if terminal not in {SignalState.TAKEN, SignalState.SKIPPED, SignalState.REJECTED}:
            raise LifecycleTransitionError("terminal state is invalid")
        current = self._states.get(setup_id)
        if current in {SignalState.TRIGGERED_FAST, SignalState.TRIGGERED_STANDARD}:
            expected = self._container_snapshot()
            emission = self._build_emission(setup_id, terminal, None)
            if emission is None:
                raise LifecycleTransitionError("terminal emission conflicts with retained identity")
            return self._commit_transition(emission, terminal, expected)
        if current is terminal:
            return None
        raise LifecycleTransitionError("terminal transition is invalid")
