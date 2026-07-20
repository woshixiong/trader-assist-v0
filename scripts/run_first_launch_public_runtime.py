"""CLI entry point for the restricted public First Launch runtime.

This script is the default-off activation surface for the restricted public
First Launch runtime. Without both the ``--enable-restricted-public-runtime``
flag and the ``--mode RESTRICTED_PUBLIC_LIVE_SHADOW`` mode, it exits nonzero
and makes no network request, opens no WebSocket, creates no runtime session,
creates no database publication, and sends no notification.

After activation, the script:

1. Loads the risk configuration from a bounded JSON file.
2. Opens the SQLite durability store.
3. Creates the configured HTTPS webhook notification dispatcher.
4. Activates the restricted public runtime.
5. Recovers the HTTP public snapshot (ETH 5m, 15m, metadata).
6. Opens the WebSocket, sends the three exact subscriptions, and drives the
   runtime's frame loop.
7. Handles bounded reconnect and deterministic shutdown.

No AWS access. No LIVE_SHADOW activation. No account or exchange writes.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import signal
import ssl
import sys
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, Protocol, cast
from urllib.request import Request, urlopen

from trader_assist_v0.first_launch.configuration import RiskConfiguration
from trader_assist_v0.runtime.first_launch_notification import (
    HttpsWebhookTransport,
    NotificationConfig,
    NotificationDispatcher,
)
from trader_assist_v0.runtime.first_launch_public_runtime import (
    RestrictedPublicRuntime,
    RestrictedPublicRuntimeConfig,
)
from trader_assist_v0.runtime.first_launch_runtime_store import RuntimeStore

_RUNTIME_MODE: Final[Literal["RESTRICTED_PUBLIC_LIVE_SHADOW"]] = (
    "RESTRICTED_PUBLIC_LIVE_SHADOW"
)
_HTTP_INFO_URL: Final[str] = "https://api.hyperliquid.xyz/info"
_WEBSOCKET_URL: Final[str] = "wss://api.hyperliquid.xyz/ws"
_HTTP_TIMEOUT_SECONDS: Final[float] = 15.0
_DISPATCH_INTERVAL_SECONDS: Final[float] = 5.0
_FRAME_BUFFER_SIZE: Final[int] = 1


class CliArgumentError(RuntimeError):
    """Raised when CLI arguments do not satisfy the default-off activation gate."""


class CliConfigurationError(RuntimeError):
    """Raised when required local configuration is missing or invalid."""


@dataclass(frozen=True)
class CliArguments:
    enable_restricted_public_runtime: bool
    mode: str
    database_path: Path
    risk_configuration_path: Path
    webhook_url: str
    webhook_timeout_seconds: float
    authorization_header_name: str | None
    authorization_header_value: str | None
    acknowledgement_timeout_seconds: float
    session_timeout_seconds: float

    @property
    def is_activated(self) -> bool:
        return (
            self.enable_restricted_public_runtime
            and self.mode == _RUNTIME_MODE
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one default-off restricted public First Launch runtime."
    )
    parser.add_argument(
        "--enable-restricted-public-runtime",
        action="store_true",
        help="Default-off activation flag; without it the runtime exits nonzero.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="",
        help="Runtime mode; must be exactly RESTRICTED_PUBLIC_LIVE_SHADOW.",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
        help="SQLite database path for the durable publication/notification store.",
    )
    parser.add_argument(
        "--risk-configuration-path",
        type=Path,
        default=None,
        help="Path to the bounded JSON risk configuration file.",
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=None,
        help="HTTPS webhook URL for notification delivery.",
    )
    parser.add_argument(
        "--webhook-timeout-seconds",
        type=float,
        default=10.0,
        help="HTTPS webhook delivery timeout in seconds.",
    )
    parser.add_argument(
        "--authorization-header-name",
        type=str,
        default=None,
        help="Optional HTTPS webhook authorization header name.",
    )
    parser.add_argument(
        "--authorization-header-value",
        type=str,
        default=None,
        help="Optional HTTPS webhook authorization header value.",
    )
    parser.add_argument(
        "--acknowledgement-timeout-seconds",
        type=float,
        default=30.0,
        help="WebSocket subscription acknowledgement timeout in seconds.",
    )
    parser.add_argument(
        "--session-timeout-seconds",
        type=float,
        default=21600.0,
        help="Bounded session timeout in seconds.",
    )
    return parser


def parse_arguments(argv: tuple[str, ...]) -> CliArguments:
    args = _parser().parse_args(argv)
    return CliArguments(
        enable_restricted_public_runtime=bool(args.enable_restricted_public_runtime),
        mode=str(args.mode),
        database_path=args.database_path,
        risk_configuration_path=args.risk_configuration_path,
        webhook_url=args.webhook_url if args.webhook_url is not None else "",
        webhook_timeout_seconds=float(args.webhook_timeout_seconds),
        authorization_header_name=args.authorization_header_name,
        authorization_header_value=args.authorization_header_value,
        acknowledgement_timeout_seconds=float(args.acknowledgement_timeout_seconds),
        session_timeout_seconds=float(args.session_timeout_seconds),
    )


def validate_activation(args: CliArguments) -> None:
    """Enforce the default-off activation gate.

    Without both the enable flag and the exact mode, this exits nonzero and
    makes no network request, opens no WebSocket, creates no runtime session,
    creates no database publication, and sends no notification.
    """
    if not args.enable_restricted_public_runtime:
        raise CliArgumentError(
            "missing --enable-restricted-public-runtime flag; runtime is default-off"
        )
    if args.mode != _RUNTIME_MODE:
        raise CliArgumentError(
            f"mode must be exactly {_RUNTIME_MODE}; got {args.mode!r}"
        )


def validate_configuration(args: CliArguments) -> tuple[
    RiskConfiguration, NotificationConfig, RestrictedPublicRuntimeConfig
]:
    """Validate required local configuration before opening any network connection."""
    if args.database_path is None:
        raise CliConfigurationError("database path is required")
    if args.risk_configuration_path is None:
        raise CliConfigurationError("risk configuration path is required")
    if not args.webhook_url:
        raise CliConfigurationError("webhook URL is required")
    try:
        risk_text = args.risk_configuration_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CliConfigurationError("risk configuration file is not readable") from exc
    risk_configuration = RiskConfiguration.from_json(risk_text)
    notification_config = NotificationConfig(
        webhook_url=args.webhook_url,
        timeout_seconds=args.webhook_timeout_seconds,
        authorization_header_name=args.authorization_header_name,
        authorization_header_value=args.authorization_header_value,
    )
    runtime_config = RestrictedPublicRuntimeConfig(
        database_path=args.database_path,
        risk_configuration=risk_configuration,
        notification_config=notification_config,
        acknowledgement_timeout_seconds=args.acknowledgement_timeout_seconds,
        session_timeout_seconds=args.session_timeout_seconds,
    )
    return risk_configuration, notification_config, runtime_config


class HttpSnapshotRecovery(Protocol):
    def __call__(self) -> tuple[str, str, str]: ...


def recover_public_snapshot_default() -> tuple[str, str, str]:
    """Recover the ETH 5m, 15m, and metadata snapshot via the public HTTP endpoint."""
    context = ssl.create_default_context()

    def post(body: dict[str, object]) -> str:
        request = Request(
            _HTTP_INFO_URL,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS, context=context) as response:
            return cast(bytes, response.read()).decode("utf-8")

    raw_5m = post({"type": "candleSnapshot", "req": {"coin": "ETH", "interval": "5m"}})
    raw_15m = post({"type": "candleSnapshot", "req": {"coin": "ETH", "interval": "15m"}})
    raw_metadata = post({"type": "metaAndAssetCtxs"})
    return raw_5m, raw_15m, raw_metadata


class WebSocketConnection(Protocol):
    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


WebSocketFactory = Callable[[str], Awaitable[WebSocketConnection]]


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _monotonic_now() -> float:
    return time.monotonic()


async def _run_transport(
    *,
    runtime: RestrictedPublicRuntime,
    recover_snapshot: HttpSnapshotRecovery,
    websocket_factory: WebSocketFactory,
    websocket_url: str,
    status: Callable[[str], None],
    shutdown_event: asyncio.Event,
) -> int:
    """Drive the async transport loop: snapshot recovery, WebSocket, reconnect.

    GA-05: the initial connection uses ``begin_warmup``.  After any disconnect
    or failure, subsequent iterations use ``begin_reconnect`` (the separately
    tested reconnect lifecycle) instead of calling ``begin_warmup`` a second
    time.  Exhausting the bounded reconnect budget stops fail-closed.  Each
    reconnect attempt requires a fresh snapshot recovery and three fresh
    subscription acknowledgements before the runtime can return to READY.
    """
    first_connection = True
    while not shutdown_event.is_set():
        connection_id = f"conn-{int(_utc_now().timestamp() * 1000)}"
        try:
            requests: tuple[str, str, str] | None
            if first_connection:
                requests = runtime.begin_warmup(
                    connection_id=connection_id, now=_utc_now()
                )
                first_connection = False
            else:
                requests = runtime.begin_reconnect(
                    connection_id=connection_id, now=_utc_now()
                )
                if requests is None:
                    # Reconnect budget exhausted or runtime shutdown; stop
                    # fail-closed without attempting another connection.
                    status("ERROR reconnect budget exhausted")
                    return 1
        except Exception as exc:
            status(f"ERROR begin_connection: {type(exc).__name__}")
            return 1
        try:
            raw_5m, raw_15m, raw_metadata = recover_snapshot()
            runtime.recover_public_snapshot(
                raw_5m=raw_5m,
                raw_15m=raw_15m,
                raw_metadata=raw_metadata,
                now=_utc_now(),
            )
        except Exception as exc:
            status(f"ERROR snapshot recovery: {type(exc).__name__}")
            runtime.mark_disconnected(now=_utc_now(), reason="snapshot-recovery-failure")
            if not shutdown_event.is_set():
                await _bounded_reconnect_wait(runtime, shutdown_event)
            continue
        try:
            async with _websocket_scope(
                websocket_factory, websocket_url
            ) as websocket:
                for request_text in requests:
                    await websocket.send(request_text)
                await _frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    shutdown_event=shutdown_event,
                    status=status,
                )
        except BaseException as exc:
            status(f"ERROR websocket: {type(exc).__name__}")
            runtime.mark_disconnected(now=_utc_now(), reason=f"websocket-{type(exc).__name__}")
        if not shutdown_event.is_set():
            await _bounded_reconnect_wait(runtime, shutdown_event)
    return 0


@contextlib.asynccontextmanager
async def _websocket_scope(
    factory: WebSocketFactory, url: str
) -> AsyncIterator[WebSocketConnection]:
    connection = await factory(url)
    try:
        yield connection
    finally:
        with contextlib.suppress(BaseException):
            await connection.close()


async def _bounded_reconnect_wait(
    runtime: RestrictedPublicRuntime, shutdown_event: asyncio.Event
) -> None:
    delay = runtime.next_reconnect_delay_seconds
    if delay is None:
        return
    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
    except TimeoutError:
        pass


async def _frame_loop(
    *,
    runtime: RestrictedPublicRuntime,
    websocket: WebSocketConnection,
    shutdown_event: asyncio.Event,
    status: Callable[[str], None],
) -> None:
    dispatch_task = asyncio.create_task(
        _dispatch_loop(runtime=runtime, shutdown_event=shutdown_event)
    )
    try:
        while not shutdown_event.is_set():
            try:
                frame = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            except TimeoutError:
                continue
            if isinstance(frame, bytes):
                frame = frame.decode("utf-8")
            if not frame:
                continue
            try:
                runtime.accept_public_frame(frame_text=frame, now=_utc_now())
            except Exception as exc:
                status(f"ERROR accept_public_frame: {type(exc).__name__}")
                runtime.mark_disconnected(now=_utc_now(), reason="frame-error")
                return
    finally:
        dispatch_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await dispatch_task


async def _dispatch_loop(
    *,
    runtime: RestrictedPublicRuntime,
    shutdown_event: asyncio.Event,
) -> None:
    while not shutdown_event.is_set():
        try:
            runtime.dispatch_pending_notifications(now=_utc_now())
        except Exception:
            pass
        try:
            await asyncio.wait_for(
                shutdown_event.wait(), timeout=_DISPATCH_INTERVAL_SECONDS
            )
        except TimeoutError:
            continue


async def run_runtime(
    *,
    args: CliArguments,
    recover_snapshot: HttpSnapshotRecovery,
    websocket_factory: WebSocketFactory,
    status: Callable[[str], None],
) -> int:
    """Wire up dependencies and run the restricted public runtime transport loop."""
    # GA-01: independently enforce the default-off activation contract as the
    # first meaningful operation of run_runtime().  Direct callers must not
    # reach configuration validation, SQLite, snapshot HTTP, WebSocket factory
    # invocation, publication or notification without both the enable flag and
    # the exact RESTRICTED_PUBLIC_LIVE_SHADOW mode.  main()'s own
    # validate_activation call is not relied upon here.
    validate_activation(args)
    risk_configuration, notification_config, runtime_config = validate_configuration(args)
    store = RuntimeStore.open(runtime_config.database_path)
    transport = HttpsWebhookTransport()
    dispatcher = NotificationDispatcher(
        store=store, transport=transport, config=notification_config
    )
    runtime = RestrictedPublicRuntime(
        config=runtime_config,
        utc_now=_utc_now,
        monotonic_now=_monotonic_now,
        store=store,
        dispatcher=dispatcher,
    )
    runtime.activate(now=_utc_now())
    status(
        f"session={runtime.session_id} mode={_RUNTIME_MODE} scope=ETH_ONLY"
    )
    shutdown_event = asyncio.Event()

    def request_shutdown(*_args: object) -> None:
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, request_shutdown)
    try:
        exit_code = await _run_transport(
            runtime=runtime,
            recover_snapshot=recover_snapshot,
            websocket_factory=websocket_factory,
            websocket_url=_WEBSOCKET_URL,
            status=status,
            shutdown_event=shutdown_event,
        )
    finally:
        runtime.shutdown(now=_utc_now())
        store.close()
    return exit_code


def main(argv: tuple[str, ...] | None = None) -> int:
    if argv is None:
        argv = tuple(sys.argv[1:])
    args = parse_arguments(argv)
    try:
        validate_activation(args)
    except CliArgumentError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    if not args.is_activated:
        print("ERROR runtime is default-off; activation flag and mode required", file=sys.stderr)
        return 2

    async def _runner() -> int:
        return await run_runtime(
            args=args,
            recover_snapshot=recover_public_snapshot_default,
            websocket_factory=_default_websocket_factory,
            status=lambda message: print(message),
        )

    try:
        return asyncio.run(_runner())
    except (CliConfigurationError, CliArgumentError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        return 0


async def _default_websocket_factory(url: str) -> WebSocketConnection:
    from websockets.asyncio.client import connect

    return await connect(url)


if __name__ == "__main__":
    raise SystemExit(main())
