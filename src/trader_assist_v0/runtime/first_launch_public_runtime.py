"""Restricted public First Launch runtime composition.

This module composes the already-existing and already-reviewed authorities into
one runnable, default-off, restricted public First Launch runtime:

    public market data
      -> strategy evaluation
      -> volatility snapshot
      -> volatility overlay
      -> valid actionable overlay
      -> TradePlan
      -> OperatorReviewCard
      -> NOT_SUBMITTED ShadowOrder
      -> durable publication bundle
      -> durable notification outbox
      -> configured HTTPS webhook delivery

The runtime is a synchronous state machine driven by an external transport
loop (see ``scripts/run_first_launch_public_runtime.py``). It owns neither a
WebSocket connection nor an HTTP client; it only accepts already-validated
frames and snapshots, feeds them through the reuse-only authorities, and
persists the resulting publication bundle and notification outbox row before
any webhook send is attempted.

Authority boundary (always enforced):

    ETH_ONLY = TRUE
    PUBLIC_ENDPOINTS_ONLY = TRUE
    MANUAL_EXECUTION_REQUIRED = TRUE
    SUBMISSION_STATUS = NOT_SUBMITTED

No AWS access. No LIVE_SHADOW activation. No account or exchange writes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal
from uuid import uuid4

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.configuration import RiskConfiguration
from trader_assist_v0.first_launch.market_data import (
    DataQualityState,
    EthMarketData,
    StrategySnapshot,
    candle_from_websocket,
    candles_from_snapshot,
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
    PreparedSetup,
    Signal,
    StrategyOutput,
    apply_volatility_overlay,
    build_plan,
    evaluate_signal,
    wilder_atr14,
)
from trader_assist_v0.runtime.first_launch_notification import (
    NotificationConfig,
    NotificationDeliveryResult,
    NotificationDispatcher,
)
from trader_assist_v0.runtime.first_launch_operator_assist import (
    REQUIRED_PUBLIC_SUBSCRIPTIONS,
    AcceptedPublicFrame,
    InMemorySignalLifecycle,
    LifecycleEmission,
    PublicRuntimeProtocol,
    PublicSessionState,
)
from trader_assist_v0.runtime.first_launch_runtime_store import (
    PublicationBundleRecord,
    RuntimeStore,
    RuntimeStoreError,
)

_RUNTIME_MODE: Final[Literal["RESTRICTED_PUBLIC_LIVE_SHADOW"]] = (
    "RESTRICTED_PUBLIC_LIVE_SHADOW"
)
_SCOPE: Final[Literal["ETH_ONLY"]] = "ETH_ONLY"
_DEFAULT_RECONNECT_DELAYS: Final[tuple[float, ...]] = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0)
_MAX_RECONNECT_ATTEMPTS: Final[int] = len(_DEFAULT_RECONNECT_DELAYS)
_HTTP_OPERATION_CANDLE_SNAPSHOT: Final[Literal["candleSnapshot"]] = "candleSnapshot"
_HTTP_OPERATION_METADATA: Final[Literal["metaAndAssetCtxs"]] = "metaAndAssetCtxs"
_SOURCE_ID_HTTP: Final[str] = "hyperliquid-public-http"
_SOURCE_ID_WS: Final[str] = "hyperliquid-public-websocket"


class RestrictedRuntimeError(RuntimeError):
    """Raised when the restricted public runtime rejects an operation."""


class RuntimeNotActivatedError(RestrictedRuntimeError):
    """Raised when an operation is attempted before activation."""


class RuntimeAlreadyActivatedError(RestrictedRuntimeError):
    """Raised when activation is attempted on an already-active runtime."""


class RuntimeShutdownError(RestrictedRuntimeError):
    """Raised when an operation is attempted after shutdown."""


class HealthTransitionViolation(RestrictedRuntimeError):
    """Raised when a health transition is illegal."""


class RuntimeHealthState(StrEnum):
    STARTING = "STARTING"
    WARMING = "WARMING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    NOT_READY = "NOT_READY"
    DISCONNECTED = "DISCONNECTED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


_LEGAL_HEALTH_TRANSITIONS: Final[dict[RuntimeHealthState, frozenset[RuntimeHealthState]]] = {
    RuntimeHealthState.STARTING: frozenset(
        {RuntimeHealthState.STARTING, RuntimeHealthState.WARMING, RuntimeHealthState.STOPPING}
    ),
    RuntimeHealthState.WARMING: frozenset(
        {
            RuntimeHealthState.WARMING,
            RuntimeHealthState.READY,
            RuntimeHealthState.NOT_READY,
            RuntimeHealthState.DISCONNECTED,
            RuntimeHealthState.STOPPING,
        }
    ),
    RuntimeHealthState.READY: frozenset(
        {
            RuntimeHealthState.READY,
            RuntimeHealthState.DEGRADED,
            RuntimeHealthState.NOT_READY,
            RuntimeHealthState.DISCONNECTED,
            RuntimeHealthState.STOPPING,
        }
    ),
    RuntimeHealthState.DEGRADED: frozenset(
        {
            RuntimeHealthState.DEGRADED,
            RuntimeHealthState.READY,
            RuntimeHealthState.NOT_READY,
            RuntimeHealthState.DISCONNECTED,
            RuntimeHealthState.STOPPING,
        }
    ),
    RuntimeHealthState.NOT_READY: frozenset(
        {
            RuntimeHealthState.NOT_READY,
            RuntimeHealthState.WARMING,
            RuntimeHealthState.READY,
            RuntimeHealthState.DEGRADED,
            RuntimeHealthState.DISCONNECTED,
            RuntimeHealthState.STOPPING,
        }
    ),
    RuntimeHealthState.DISCONNECTED: frozenset(
        {
            RuntimeHealthState.DISCONNECTED,
            RuntimeHealthState.WARMING,
            RuntimeHealthState.NOT_READY,
            RuntimeHealthState.STOPPING,
        }
    ),
    RuntimeHealthState.STOPPING: frozenset(
        {RuntimeHealthState.STOPPING, RuntimeHealthState.STOPPED}
    ),
    RuntimeHealthState.STOPPED: frozenset({RuntimeHealthState.STOPPED}),
}

_BLOCKING_HEALTH_STATES: Final[frozenset[RuntimeHealthState]] = frozenset(
    {
        RuntimeHealthState.NOT_READY,
        RuntimeHealthState.DISCONNECTED,
        RuntimeHealthState.STOPPING,
        RuntimeHealthState.STOPPED,
    }
)


@dataclass(frozen=True)
class RestrictedPublicRuntimeConfig:
    """Explicitly configured, testable restricted public runtime configuration.

    No credentials are embedded in code, fixtures, logs, or Git history by this
    module. The SQLite database path, HTTPS notification webhook, and bounded
    reconnect settings are all explicit and testable.
    """

    database_path: Path
    risk_configuration: RiskConfiguration
    notification_config: NotificationConfig
    acknowledgement_timeout_seconds: float = 30.0
    session_timeout_seconds: float = 21600.0
    reconnect_delays_seconds: tuple[float, ...] = _DEFAULT_RECONNECT_DELAYS
    sz_decimals: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.database_path, Path):
            raise RestrictedRuntimeError("database path must be a Path")
        if type(self.risk_configuration) is not RiskConfiguration:
            raise RestrictedRuntimeError("risk configuration is invalid")
        if type(self.notification_config) is not NotificationConfig:
            raise RestrictedRuntimeError("notification config is invalid")
        if (
            type(self.acknowledgement_timeout_seconds) not in {int, float}
            or isinstance(self.acknowledgement_timeout_seconds, bool)
            or self.acknowledgement_timeout_seconds <= 0
        ):
            raise RestrictedRuntimeError("acknowledgement timeout is invalid")
        if (
            type(self.session_timeout_seconds) not in {int, float}
            or isinstance(self.session_timeout_seconds, bool)
            or self.session_timeout_seconds <= 0
        ):
            raise RestrictedRuntimeError("session timeout is invalid")
        if self.session_timeout_seconds < self.acknowledgement_timeout_seconds:
            raise RestrictedRuntimeError("session timeout is shorter than acknowledgement timeout")
        if (
            type(self.reconnect_delays_seconds) is not tuple
            or not self.reconnect_delays_seconds
            or len(self.reconnect_delays_seconds) > 10
        ):
            raise RestrictedRuntimeError("reconnect schedule is invalid")
        for delay in self.reconnect_delays_seconds:
            if (
                type(delay) not in {int, float}
                or isinstance(delay, bool)
                or delay <= 0
                or delay > 300
            ):
                raise RestrictedRuntimeError("reconnect delay is invalid")
        if type(self.sz_decimals) is not int or self.sz_decimals < 0 or self.sz_decimals > 8:
            raise RestrictedRuntimeError("sz_decimals is invalid")


UtcClock = Callable[[], datetime]
MonotonicClock = Callable[[], float]


@dataclass(frozen=True)
class EvaluationOutcome:
    """The durable outcome of one evaluation cycle for one closed 5m identity."""

    signal_id: str | None
    plan_id: str | None
    shadow_order_id: str | None
    notification_id: str | None
    publication_bundle: PublicationBundleRecord | None
    notification_result: NotificationDeliveryResult | None
    skipped_reason: str


@dataclass
class RestrictedPublicRuntime:
    """One default-off restricted public First Launch runtime process.

    The runtime is a synchronous state machine. An external transport loop
    (CLI script) drives it by:

    1. Calling ``activate`` once after validating the default-off flags.
    2. Calling ``begin_warmup`` to start the public connection.
    3. Recovering the HTTP snapshot via ``recover_public_snapshot``.
    4. Forwarding WebSocket subscription acknowledgements via
       ``accept_acknowledgement``.
    5. Forwarding WebSocket public frames via ``accept_public_frame``.
    6. Calling ``dispatch_pending_notifications`` periodically.
    7. Calling ``mark_disconnected`` / ``begin_reconnect`` on transport events.
    8. Calling ``shutdown`` for deterministic termination.
    """

    config: RestrictedPublicRuntimeConfig
    utc_now: UtcClock
    monotonic_now: MonotonicClock
    store: RuntimeStore
    dispatcher: NotificationDispatcher
    session_id: str = field(init=False, default="")
    _health_state: RuntimeHealthState = field(init=False, default=RuntimeHealthState.STOPPED)
    _market_data: EthMarketData = field(init=False, default_factory=EthMarketData)
    _context_series: ContextSeries = field(init=False, default_factory=ContextSeries)
    _lifecycle: InMemorySignalLifecycle = field(init=False)
    _protocol: PublicRuntimeProtocol = field(init=False)
    _connection_id: str = field(init=False, default="")
    _last_evaluated_5m_identity: tuple[str, str, int] | None = field(init=False, default=None)
    _reconnect_attempt: int = field(init=False, default=0)
    _shutdown: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if not callable(self.utc_now) or not callable(self.monotonic_now):
            raise RestrictedRuntimeError("clocks must be callable")
        self._lifecycle = InMemorySignalLifecycle(utc_now=self.utc_now)

    @property
    def health_state(self) -> RuntimeHealthState:
        return self._health_state

    @property
    def is_ready(self) -> bool:
        return self._health_state is RuntimeHealthState.READY

    @property
    def is_shutdown(self) -> bool:
        return self._shutdown

    @property
    def acknowledged_subscriptions(self) -> frozenset[str]:
        if self._connection_id == "":
            return frozenset()
        return self._protocol.acknowledged_subscriptions

    @property
    def remaining_subscriptions(self) -> tuple[str, ...]:
        if self._connection_id == "":
            return tuple(item.identity for item in REQUIRED_PUBLIC_SUBSCRIPTIONS)
        return self._protocol.remaining_subscriptions

    @property
    def next_reconnect_delay_seconds(self) -> float | None:
        if self._reconnect_attempt >= len(self.config.reconnect_delays_seconds):
            return None
        return self.config.reconnect_delays_seconds[self._reconnect_attempt]

    def _timestamp(self) -> datetime:
        value = self.utc_now()
        if type(value) is not datetime or value.tzinfo is not UTC:
            raise RestrictedRuntimeError("UTC clock is invalid")
        return value

    def _transition_health(
        self, *, to: RuntimeHealthState, reason: str, now: datetime
    ) -> None:
        if self._shutdown and to not in (
            RuntimeHealthState.STOPPING,
            RuntimeHealthState.STOPPED,
        ):
            raise RuntimeShutdownError("runtime is shutting down")
        current = self._health_state
        if to not in _LEGAL_HEALTH_TRANSITIONS[current]:
            raise HealthTransitionViolation(
                f"illegal health transition: {current.value} -> {to.value}"
            )
        self._health_state = to
        self.store.record_health_event(
            session_id=self.session_id,
            from_state=current.value,
            to_state=to.value,
            reason=reason,
            now=now,
        )

    def activate(self, *, now: datetime) -> str:
        """Activate the runtime: record the session and transition to STARTING.

        This method is only valid before the runtime has been activated. It
        creates a stable runtime session identity and records it durably. No
        network connection is opened here.
        """
        if self._health_state is not RuntimeHealthState.STOPPED:
            raise RuntimeAlreadyActivatedError("runtime has already been activated")
        if self._shutdown:
            raise RuntimeShutdownError("runtime has been shut down")
        timestamp = self._validate_now(now)
        session_id = uuid4().hex
        self.session_id = session_id
        self.store.record_runtime_session(
            session_id=session_id,
            runtime_mode=_RUNTIME_MODE,
            scope=_SCOPE,
            process_start_time=timestamp,
            configuration_hash=self.config.risk_configuration.configuration_hash,
            database_path=self.config.database_path,
            manual_only_authority=True,
            not_submitted_authority=True,
            now=timestamp,
        )
        # The initial STOPPED -> STARTING transition is the activation gate;
        # it bypasses _LEGAL_HEALTH_TRANSITIONS because the default STOPPED
        # state represents "not yet activated", not a real terminal shutdown.
        self._health_state = RuntimeHealthState.STARTING
        self.store.record_health_event(
            session_id=session_id,
            from_state=RuntimeHealthState.STOPPED.value,
            to_state=RuntimeHealthState.STARTING.value,
            reason="activate",
            now=timestamp,
        )
        return session_id

    def begin_warmup(self, *, connection_id: str, now: datetime) -> tuple[str, str, str]:
        """Begin the public connection warm-up: open a new connection identity.

        Returns the three exact subscription request texts that the transport
        loop must send before any public frame is accepted.
        """
        timestamp = self._validate_now(now)
        if self._shutdown:
            raise RuntimeShutdownError("runtime has been shut down")
        if self.session_id == "":
            raise RuntimeNotActivatedError("runtime has not been activated")
        if type(connection_id) is not str or not connection_id:
            raise RestrictedRuntimeError("connection identity is invalid")
        if self._connection_id != "":
            raise RestrictedRuntimeError("warmup has already begun")
        self._connection_id = connection_id
        self._market_data.begin_connection()
        self._protocol = PublicRuntimeProtocol(
            connection_id=connection_id,
            utc_now=self.utc_now,
            monotonic_now=self.monotonic_now,
            acknowledgement_timeout_seconds=self.config.acknowledgement_timeout_seconds,
            session_timeout_seconds=self.config.session_timeout_seconds,
        )
        requests = self._protocol.start()
        if self._health_state is RuntimeHealthState.STARTING:
            self._transition_health(
                to=RuntimeHealthState.WARMING, reason="begin-warmup", now=timestamp
            )
        elif self._health_state in (
            RuntimeHealthState.DISCONNECTED,
            RuntimeHealthState.NOT_READY,
        ):
            self._transition_health(
                to=RuntimeHealthState.WARMING, reason="reconnect-warmup", now=timestamp
            )
        self._reconnect_attempt = 0
        return requests

    def accept_acknowledgement(self, *, frame_text: str, now: datetime) -> None:
        """Accept one subscriptionResponse frame from the transport loop."""
        timestamp = self._validate_now(now)
        if self._connection_id == "":
            raise RuntimeNotActivatedError("warmup has not begun")
        if self._shutdown:
            raise RuntimeShutdownError("runtime has been shut down")
        try:
            self._protocol.check_timeout()
            result = self._protocol.accept_frame(frame_text)
            if result is not None:
                raise RestrictedRuntimeError("acknowledgement frame produced a data frame")
        except BaseException:
            # GA-02: acknowledgement validation failure must atomically withdraw
            # from READY/WARMING/DEGRADED to a blocking non-ready state before
            # the error is re-raised.  Do not swallow the original exception.
            self._withdraw_on_frame_rejection(timestamp)
            raise
        if (
            self._protocol.state is PublicSessionState.ACTIVE
            and self._health_state is RuntimeHealthState.WARMING
        ):
            self._try_promote_to_ready(now=timestamp)

    def recover_public_snapshot(
        self,
        *,
        raw_5m: str,
        raw_15m: str,
        raw_metadata: str,
        now: datetime,
    ) -> None:
        """Recover the HTTP public snapshot for ETH 5m, 15m, and metadata."""
        timestamp = self._validate_now(now)
        if self._connection_id == "":
            raise RuntimeNotActivatedError("warmup has not begun")
        if self._shutdown:
            raise RuntimeShutdownError("runtime has been shut down")
        sequence_base = self._protocol.receive_sequence
        evidence_5m = evidence_from_raw(
            raw_5m,
            operation=_HTTP_OPERATION_CANDLE_SNAPSHOT,
            received_at=timestamp,
            receive_sequence=sequence_base + 1,
            connection_id=self._connection_id,
            source_id=_SOURCE_ID_HTTP,
        )
        evidence_15m = evidence_from_raw(
            raw_15m,
            operation=_HTTP_OPERATION_CANDLE_SNAPSHOT,
            received_at=timestamp,
            receive_sequence=sequence_base + 2,
            connection_id=self._connection_id,
            source_id=_SOURCE_ID_HTTP,
        )
        evidence_metadata = evidence_from_raw(
            raw_metadata,
            operation=_HTTP_OPERATION_METADATA,
            received_at=timestamp,
            receive_sequence=sequence_base + 3,
            connection_id=self._connection_id,
            source_id=_SOURCE_ID_HTTP,
        )
        candles_5m = candles_from_snapshot(
            raw_5m, evidence_5m, requested_interval="5m"
        )
        candles_15m = candles_from_snapshot(
            raw_15m, evidence_15m, requested_interval="15m"
        )
        metadata = metadata_from_info(raw_metadata, evidence_metadata)
        self._market_data.accept_metadata(metadata)
        self._market_data.recover_snapshot("5m", candles_5m)
        self._market_data.recover_snapshot("15m", candles_15m)
        self._try_promote_to_ready(now=timestamp)

    def accept_public_frame(self, *, frame_text: str, now: datetime) -> EvaluationOutcome | None:
        """Accept one public WebSocket frame and drive one evaluation cycle.

        Returns an ``EvaluationOutcome`` if the frame produced a new triggered
        evaluation that was considered for publication, or ``None`` if the
        frame was an acknowledgement, a non-triggering candle, or a context
        update that did not produce a new closed 5m identity.
        """
        timestamp = self._validate_now(now)
        if self._connection_id == "":
            raise RuntimeNotActivatedError("warmup has not begun")
        if self._shutdown:
            raise RuntimeShutdownError("runtime has been shut down")
        if self._health_state in _BLOCKING_HEALTH_STATES:
            return None
        try:
            self._protocol.check_timeout()
            frame = self._protocol.accept_frame(frame_text)
            if frame is None:
                return None
            if frame.channel == "candle":
                return self._accept_candle_frame(frame, timestamp)
            if frame.channel == "activeAssetCtx":
                self._accept_context_frame(frame, timestamp)
                return None
            return None
        except BaseException:
            # GA-02: any malformed, rejected or authority-invalid public frame
            # received while READY (or WARMING/DEGRADED) must atomically move
            # the runtime to a blocking non-ready state before the error is
            # re-raised.  is_ready must never be true when parsing failed.
            # Do not depend on the CLI frame loop to call mark_disconnected
            # after the fact; do not swallow the original exception.
            self._withdraw_on_frame_rejection(timestamp)
            raise

    def _accept_candle_frame(
        self, frame: AcceptedPublicFrame, timestamp: datetime
    ) -> EvaluationOutcome | None:
        frame_text = _frame_text(frame)
        evidence = evidence_from_raw(
            frame_text,
            operation="WebSocket",
            received_at=timestamp,
            receive_sequence=_frame_sequence(frame),
            connection_id=_frame_connection_id(frame),
            source_id=_SOURCE_ID_WS,
        )
        candle = candle_from_websocket(frame_text, evidence)
        result = self._market_data.accept_candle(candle)
        if result == "CONFLICT":
            self._fail_closed("CANDLE_CONFLICT", now=timestamp)
            return None
        if result == "DUPLICATE":
            return None
        if candle.interval != "5m":
            return None
        if not self.is_ready:
            self._try_promote_to_ready(now=timestamp)
            return None
        return self._evaluate_new_closed_5m(timestamp)

    def _accept_context_frame(
        self, frame: AcceptedPublicFrame, timestamp: datetime
    ) -> None:
        frame_text = _frame_text(frame)
        evidence = evidence_from_raw(
            frame_text,
            operation="WebSocket",
            received_at=timestamp,
            receive_sequence=_frame_sequence(frame),
            connection_id=_frame_connection_id(frame),
            source_id=_SOURCE_ID_WS,
        )
        context = context_from_websocket(frame_text, evidence)
        self._market_data.accept_context(context)
        self._context_series.accept(context)
        if not self.is_ready:
            self._try_promote_to_ready(now=timestamp)
        return None

    def _try_promote_to_ready(self, *, now: datetime) -> None:
        if self._health_state in _BLOCKING_HEALTH_STATES:
            return
        if self._protocol.state is not PublicSessionState.ACTIVE:
            return
        snapshot = self._market_data.strategy_snapshot(now)
        if snapshot.quality.state is DataQualityState.READY:
            if self._health_state is not RuntimeHealthState.READY:
                self._transition_health(
                    to=RuntimeHealthState.READY, reason="ready-authority", now=now
                )
        else:
            if self._health_state is RuntimeHealthState.READY:
                self._transition_health(
                    to=RuntimeHealthState.NOT_READY,
                    reason=f"quality-{snapshot.quality.state.value}",
                    now=now,
                )

    def _evaluate_new_closed_5m(self, now: datetime) -> EvaluationOutcome:
        snapshot = self._market_data.strategy_snapshot(now)
        if snapshot.quality.state is not DataQualityState.READY:
            return EvaluationOutcome(
                signal_id=None,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason=f"quality-{snapshot.quality.state.value}",
            )
        candles_5m = snapshot.candles_5m
        if not candles_5m:
            return EvaluationOutcome(
                signal_id=None,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="no-closed-5m-candle",
            )
        latest_5m_identity = candles_5m[-1].identity
        if latest_5m_identity == self._last_evaluated_5m_identity:
            return EvaluationOutcome(
                signal_id=None,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="duplicate-5m-identity",
            )
        self._last_evaluated_5m_identity = latest_5m_identity
        evaluation = evaluate_signal(snapshot)
        return self._process_evaluation(evaluation, snapshot, now)

    def _process_evaluation(
        self,
        evaluation: Signal | PreparedSetup | StrategyOutput,
        snapshot: StrategySnapshot,
        now: datetime,
    ) -> EvaluationOutcome:
        emission = self._lifecycle.accept(evaluation)
        if type(evaluation) is PreparedSetup:
            advance_emission = self._lifecycle.advance(evaluation.setup_id, snapshot)
            if advance_emission is not None and advance_emission.output is not None:
                return self._publish_trigger(advance_emission, snapshot, now)
            return EvaluationOutcome(
                signal_id=evaluation.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="prepared-no-standard-trigger",
            )
        if type(evaluation) is StrategyOutput and emission is not None:
            assert emission.output is not None
            return self._publish_trigger(emission, snapshot, now)
        if type(evaluation) is StrategyOutput and emission is None:
            return EvaluationOutcome(
                signal_id=evaluation.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="duplicate-trigger-emission",
            )
        return EvaluationOutcome(
            signal_id=None,
            plan_id=None,
            shadow_order_id=None,
            notification_id=None,
            publication_bundle=None,
            notification_result=None,
            skipped_reason="no-trigger",
        )

    def _publish_trigger(
        self,
        emission: LifecycleEmission,
        snapshot: StrategySnapshot,
        now: datetime,
    ) -> EvaluationOutcome:
        output = emission.output
        if output is None:
            return EvaluationOutcome(
                signal_id=emission.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="emission-has-no-output",
            )
        if self.store.publication_exists_for_signal(output.setup_id):
            return EvaluationOutcome(
                signal_id=output.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="already-published",
            )
        candles_5m = snapshot.candles_5m
        if len(candles_5m) < 64:
            return EvaluationOutcome(
                signal_id=output.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="insufficient-5m-candles",
            )
        if snapshot.active_context is None:
            return EvaluationOutcome(
                signal_id=output.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="no-active-context",
            )
        reference_price = snapshot.active_context.reference_price
        if reference_price is None or reference_price <= 0:
            return EvaluationOutcome(
                signal_id=output.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="no-reference-price",
            )
        volatility = wilder_atr14(candles_5m[-64:])
        overlay = apply_volatility_overlay(
            output, volatility, candles_5m[-64:], reference_price
        )
        if not overlay.actionable or overlay.state is not output.state:
            return EvaluationOutcome(
                signal_id=output.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason=f"non-actionable-overlay-{overlay.actionable}",
            )
        context_summary = self._context_series.summary_at(now)
        if context_summary is None:
            return EvaluationOutcome(
                signal_id=output.setup_id,
                plan_id=None,
                shadow_order_id=None,
                notification_id=None,
                publication_bundle=None,
                notification_result=None,
                skipped_reason="no-context-summary",
            )
        plan = build_plan(
            strategy_output=output,
            reference=overlay.reference_price,
            sz_decimals=self.config.sz_decimals,
            configuration=self.config.risk_configuration,
            volatility=volatility,
            overlay=overlay,
            context_summary=context_summary,
        )
        card = build_operator_card(
            plan, now=now, quality=DataQualityState.READY
        )
        shadow = create_shadow_order(card)
        bundle, _outbox = self.store.persist_publication_bundle(
            session_id=self.session_id,
            strategy_output=output,
            volatility_snapshot=volatility,
            overlay_decision=overlay,
            trade_plan=plan,
            operator_review_card=card,
            shadow_order=shadow,
            now=now,
        )
        notification_result = self.dispatcher.dispatch_one(
            notification_id=bundle.notification_id, now=now
        )
        return EvaluationOutcome(
            signal_id=output.setup_id,
            plan_id=plan.plan_id,
            shadow_order_id=shadow.shadow_order_id,
            notification_id=bundle.notification_id,
            publication_bundle=bundle,
            notification_result=notification_result,
            skipped_reason="published",
        )

    def dispatch_pending_notifications(
        self, *, now: datetime
    ) -> tuple[NotificationDeliveryResult, ...]:
        timestamp = self._validate_now(now)
        if self._shutdown:
            return ()
        return self.dispatcher.dispatch_pending(now=timestamp)

    def mark_disconnected(self, *, now: datetime, reason: str) -> None:
        timestamp = self._validate_now(now)
        if self._shutdown:
            return
        if self._connection_id == "":
            return
        if type(reason) is not str or not reason or reason.strip() != reason:
            raise RestrictedRuntimeError("disconnect reason is invalid")
        self._market_data.mark_disconnected()
        if self._protocol.state is not PublicSessionState.CLOSED:
            self._protocol.disconnect()
        if self._health_state is not RuntimeHealthState.DISCONNECTED:
            self._transition_health(
                to=RuntimeHealthState.DISCONNECTED, reason=reason, now=timestamp
            )

    def begin_reconnect(self, *, connection_id: str, now: datetime) -> tuple[str, str, str] | None:
        """Begin a bounded reconnect attempt.

        Returns the three subscription request texts if a reconnect attempt is
        available, or ``None`` if the bounded reconnect budget is exhausted.
        """
        timestamp = self._validate_now(now)
        if self._shutdown:
            return None
        if self._connection_id == "":
            raise RuntimeNotActivatedError("warmup has not begun")
        if self._reconnect_attempt >= len(self.config.reconnect_delays_seconds):
            self._fail_closed("RECONNECT_BUDGET_EXHAUSTED", now=timestamp)
            return None
        self._reconnect_attempt += 1
        self._connection_id = connection_id
        self._market_data.begin_connection()
        self._last_evaluated_5m_identity = None
        self._protocol = PublicRuntimeProtocol(
            connection_id=connection_id,
            utc_now=self.utc_now,
            monotonic_now=self.monotonic_now,
            acknowledgement_timeout_seconds=self.config.acknowledgement_timeout_seconds,
            session_timeout_seconds=self.config.session_timeout_seconds,
        )
        requests = self._protocol.start()
        self._transition_health(
            to=RuntimeHealthState.WARMING, reason="reconnect-attempt", now=timestamp
        )
        return requests

    def _fail_closed(self, reason: str, *, now: datetime) -> None:
        if self._shutdown:
            return
        if self._health_state not in (
            RuntimeHealthState.READY,
            RuntimeHealthState.WARMING,
            RuntimeHealthState.DEGRADED,
        ):
            return
        self._transition_health(
            to=RuntimeHealthState.NOT_READY, reason=reason, now=now
        )

    def _withdraw_on_frame_rejection(self, now: datetime) -> None:
        """GA-02: atomically withdraw to a blocking non-ready state on frame rejection.

        Called from ``accept_public_frame`` and ``accept_acknowledgement`` when
        any malformed, rejected or authority-invalid frame is encountered.  The
        original exception is re-raised by the caller after this method returns;
        this method must not swallow it.  If the withdrawal itself fails (for
        example because the durable health-event store is unavailable), the
        original exception still propagates.
        """
        if self._shutdown:
            return
        if self._connection_id == "":
            return
        if self._health_state not in (
            RuntimeHealthState.READY,
            RuntimeHealthState.WARMING,
            RuntimeHealthState.DEGRADED,
        ):
            return
        try:
            self._transition_health(
                to=RuntimeHealthState.NOT_READY,
                reason="PUBLIC_FRAME_REJECTED",
                now=now,
            )
        except BaseException:
            # The original exception must remain visible; suppress any
            # secondary failure from the durable health-event record.
            pass

    def shutdown(self, *, now: datetime) -> None:
        """Deterministic shutdown: withdraw READY, close resources, persist terminal state."""
        timestamp = self._validate_now(now)
        if self._shutdown:
            return
        self._shutdown = True
        if self._connection_id != "":
            self._protocol.close()
        if self._health_state is not RuntimeHealthState.STOPPED:
            if self._health_state is not RuntimeHealthState.STOPPING:
                self._transition_health(
                    to=RuntimeHealthState.STOPPING, reason="shutdown", now=timestamp
                )
            self._transition_health(
                to=RuntimeHealthState.STOPPED, reason="shutdown-complete", now=timestamp
            )
        if self.session_id != "":
            try:
                self.store.close_runtime_session(session_id=self.session_id, now=timestamp)
            except RuntimeStoreError:
                pass

    def _validate_now(self, now: datetime) -> datetime:
        if type(now) is not datetime or now.tzinfo is not UTC:
            raise RestrictedRuntimeError("now must be a UTC datetime")
        return now


def _frame_text(frame: AcceptedPublicFrame) -> str:
    return frame.raw_text


def _frame_sequence(frame: AcceptedPublicFrame) -> int:
    return frame.receive_sequence


def _frame_connection_id(frame: AcceptedPublicFrame) -> str:
    return frame.connection_id


def canonical_runtime_summary(
    *, runtime: RestrictedPublicRuntime, now: datetime
) -> dict[str, object]:
    """Return a machine-readable local health/readiness summary.

    The summary is for local inspection only; it is not a dashboard and does
    not claim cross-process coordination.
    """
    return {
        "summary_version": "1",
        "session_id": runtime.session_id,
        "runtime_mode": _RUNTIME_MODE,
        "scope": _SCOPE,
        "health_state": runtime.health_state.value,
        "is_ready": runtime.is_ready,
        "is_shutdown": runtime.is_shutdown,
        "acknowledged_subscriptions": sorted(runtime.acknowledged_subscriptions),
        "remaining_subscriptions": list(runtime.remaining_subscriptions),
        "last_evaluated_5m_identity": (
            None
            if runtime._last_evaluated_5m_identity is None
            else list(runtime._last_evaluated_5m_identity)
        ),
        "reconnect_attempt": runtime._reconnect_attempt,
        "summary_at": now.isoformat(),
    }


def canonical_runtime_summary_bytes(*, runtime: RestrictedPublicRuntime, now: datetime) -> bytes:
    return canonical_json_bytes(canonical_runtime_summary(runtime=runtime, now=now))
