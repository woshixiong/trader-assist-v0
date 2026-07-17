"""Default-off, one-shot public ETH operator-assist composition runtime.

This module deliberately has no import-time activity.  It receives only public
market observations and a locally supplied equity value; it has no private
state, credentials, or execution capability.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final, Literal, Protocol, cast
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

from websockets.asyncio.client import connect

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.market_data import DataQualityState, EthMarketData
from trader_assist_v0.first_launch.operator_review import (
    OperatorReviewCard,
    ShadowOrder,
    build_operator_card,
    create_shadow_order,
    render_terminal,
)
from trader_assist_v0.first_launch.strategy import (
    PlanError,
    PreparedSetup,
    Signal,
    SignalState,
    StrategyOutput,
    advance_prepare,
    build_plan,
    evaluate_signal,
)

TASK_ID: Final[Literal["V0-FLP1-CE1-PUBLIC-ETH-OPERATOR-ASSIST-SESSION"]] = (
    "V0-FLP1-CE1-PUBLIC-ETH-OPERATOR-ASSIST-SESSION"
)
INFO_URL: Final = "https://api.hyperliquid.xyz/info"
WEBSOCKET_URL: Final = "wss://api.hyperliquid.xyz/ws"
_MAX_RESPONSE_BYTES: Final = 2 * 1024 * 1024
_PERMIT_MAX_BYTES: Final = 16 * 1024
_ACK_TIMEOUT_SECONDS: Final = 20.0
_PERMIT_FIELDS = frozenset(
    {"task_id", "permit_id", "expected_git_sha", "manual_equity_usd", "max_session_seconds"}
)
_PERMIT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_RECEIPT_DOMAIN = b"trader-assist-v0/flp1-ce1-permit-receipt/v1"
_RECORD_DOMAIN = b"trader-assist-v0/flp1-ce1-shadow-record/v1"
_RECEIPT_DIRECTORY = "first-launch-operator-assist-permit-receipts"


class OperatorAssistError(RuntimeError):
    """A bounded session stop; no recovery or alternate authority is attempted."""


class PermitError(OperatorAssistError):
    pass


class RepositoryStateError(OperatorAssistError):
    pass


class OutputPathError(OperatorAssistError):
    pass


class PublicHttpError(OperatorAssistError):
    pass


class PublicWebSocketError(OperatorAssistError):
    pass


class ProtocolAcknowledgementError(PublicWebSocketError):
    pass


class MarketDataWarmupError(OperatorAssistError):
    pass


class SessionTimeoutError(OperatorAssistError):
    pass


class LifecycleCompositionError(OperatorAssistError):
    pass


class ShadowRecordError(OperatorAssistError):
    pass


@dataclass(frozen=True)
class StartPermit:
    permit_id: str
    expected_git_sha: str
    manual_equity_usd: Decimal
    max_session_seconds: int


@dataclass(frozen=True)
class PublicHttpResponse:
    status: int
    body: bytes


@dataclass(frozen=True)
class OperatorAssistResult:
    task_id: Literal["V0-FLP1-CE1-PUBLIC-ETH-OPERATOR-ASSIST-SESSION"]
    permit_id: str
    session_id: str
    shadow_output: Path
    record_hash: str
    shadow_order_id: str
    card_id: str
    setup_id: str
    plan_id: str
    signal_speed: Literal["FAST", "STANDARD"]
    submission_status: Literal["NOT_SUBMITTED"] = "NOT_SUBMITTED"


class WebSocketConnection(Protocol):
    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


HttpPost = Callable[[str], PublicHttpResponse]
WebSocketFactory = Callable[[], Awaitable[WebSocketConnection]]
Display = Callable[[str], None]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON value")


def _strict_json(text: str) -> object:
    try:
        return json.loads(
            text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise PermitError("strict JSON is required") from exc


def _read_permit(path: Path) -> StartPermit:
    try:
        before = path.lstat()
    except OSError as exc:
        raise PermitError("start permit must be an existing regular file") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise PermitError("start permit must be a regular non-symlink file")
    if before.st_uid != os.geteuid() or stat.S_IMODE(before.st_mode) != 0o600:
        raise PermitError("start permit owner or mode is invalid")
    try:
        fd = os.open(path, os.O_RDONLY | _NOFOLLOW)
    except OSError as exc:
        raise PermitError("start permit cannot be opened safely") from exc
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise PermitError("start permit identity changed")
        chunks: list[bytes] = []
        while chunk := os.read(fd, 4096):
            chunks.append(chunk)
            if sum(map(len, chunks)) > _PERMIT_MAX_BYTES:
                raise PermitError("start permit exceeds the bounded size")
    finally:
        os.close(fd)
    try:
        document = _strict_json(b"".join(chunks).decode("utf-8", errors="strict"))
    except UnicodeDecodeError as exc:
        raise PermitError("start permit must be UTF-8") from exc
    if type(document) is not dict or set(document) != _PERMIT_FIELDS:
        raise PermitError("start permit fields are not exact")
    values = cast(dict[str, object], document)
    if (
        values["task_id"] != TASK_ID
        or type(values["permit_id"]) is not str
        or _PERMIT_ID_RE.fullmatch(values["permit_id"]) is None
        or type(values["expected_git_sha"]) is not str
        or _SHA_RE.fullmatch(values["expected_git_sha"]) is None
        or type(values["manual_equity_usd"]) is not str
        or _DECIMAL_RE.fullmatch(values["manual_equity_usd"]) is None
        or type(values["max_session_seconds"]) is not int
        or isinstance(values["max_session_seconds"], bool)
    ):
        raise PermitError("start permit values are invalid")
    try:
        equity = Decimal(values["manual_equity_usd"])
    except InvalidOperation as exc:
        raise PermitError("manual equity is invalid") from exc
    duration = values["max_session_seconds"]
    if not equity.is_finite() or equity <= 0 or not 1 <= duration <= 21600:
        raise PermitError("start permit values are outside their bounded range")
    return StartPermit(values["permit_id"], values["expected_git_sha"], equity, duration)


def _git(
    repo_root: Path, *args: str, error: type[OperatorAssistError] = RepositoryStateError
) -> str:
    try:
        completed = subprocess.run(
            ("git", *args), cwd=repo_root, check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise error("repository authority validation failed") from exc
    return completed.stdout.strip()


def _validate_repository(repo_root: Path, permit: StartPermit) -> Path:
    try:
        root = Path(_git(repo_root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    except OSError as exc:
        raise RepositoryStateError("repository root is invalid") from exc
    if root != repo_root.resolve():
        raise RepositoryStateError("repository root does not match runtime scope")
    origin = _git(root, "remote", "get-url", "origin")
    if not re.search(r"(?:github\.com[:/])woshixiong/trader-assist-v0(?:\.git)?$", origin):
        raise RepositoryStateError("repository origin is not authorized")
    if _git(root, "rev-parse", "--verify", "HEAD^{commit}") != permit.expected_git_sha:
        raise RepositoryStateError("permit SHA does not match HEAD")
    if _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise RepositoryStateError("repository must be clean")
    return root


def _validate_output_path(path: Path) -> None:
    parent = path.parent
    try:
        metadata = parent.lstat()
    except OSError as exc:
        raise OutputPathError("shadow-output parent must exist") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise OutputPathError("shadow-output parent is not a real directory")
    try:
        path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise OutputPathError("shadow-output target cannot be inspected") from exc
    raise OutputPathError("shadow-output target must not already exist")


def _common_dir(repo_root: Path) -> Path:
    candidate = Path(_git(repo_root, "rev-parse", "--git-common-dir", error=PermitError))
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise PermitError("Git common directory is unavailable") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise PermitError("Git common directory is unsafe")
    return candidate.resolve(strict=True)


def _fsync_directory(fd: int) -> None:
    try:
        os.fsync(fd)
    except OSError as exc:
        raise ShadowRecordError("directory fsync failed") from exc


def _consume_permit(repo_root: Path, permit: StartPermit) -> None:
    common = _common_dir(repo_root)
    root_fd = os.open(common, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)
    try:
        try:
            os.mkdir(_RECEIPT_DIRECTORY, 0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        receipt_dir_meta = os.stat(_RECEIPT_DIRECTORY, dir_fd=root_fd, follow_symlinks=False)
        if stat.S_ISLNK(receipt_dir_meta.st_mode) or not stat.S_ISDIR(receipt_dir_meta.st_mode):
            raise PermitError("permit receipt directory is unsafe")
        receipt_fd = os.open(
            _RECEIPT_DIRECTORY, os.O_RDONLY | _DIRECTORY | _NOFOLLOW, dir_fd=root_fd
        )
        try:
            opened = os.fstat(receipt_fd)
            if opened.st_uid != os.geteuid() or stat.S_IMODE(opened.st_mode) != 0o700:
                raise PermitError("permit receipt directory owner or mode is invalid")
            filename = hashlib.sha256(
                _RECEIPT_DOMAIN + b"\0" + permit.permit_id.encode()
            ).hexdigest()
            payload = {
                "permit_id": permit.permit_id,
                "receipt_hash": "",
                "task_id": TASK_ID,
                "version": 1,
            }
            payload["receipt_hash"] = hashlib.sha256(
                _RECEIPT_DOMAIN
                + b"\0"
                + canonical_json_bytes({k: v for k, v in payload.items() if k != "receipt_hash"})
            ).hexdigest()
            raw = canonical_json_bytes(payload)
            try:
                fd = os.open(
                    filename,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                    0o600,
                    dir_fd=receipt_fd,
                )
            except FileExistsError as exc:
                raise PermitError("permit_id has already been consumed") from exc
            try:
                os.write(fd, raw)
                os.fsync(fd)
                verified = os.fstat(fd)
                if verified.st_uid != os.geteuid() or stat.S_IMODE(verified.st_mode) != 0o600:
                    raise PermitError("permit receipt mode is invalid")
            except OSError as exc:
                with contextlib.suppress(OSError):
                    os.unlink(filename, dir_fd=receipt_fd)
                raise PermitError("permit receipt durability failed") from exc
            finally:
                os.close(fd)
            _fsync_directory(receipt_fd)
        finally:
            os.close(receipt_fd)
    finally:
        os.close(root_fd)


def _default_http_post(body: str) -> PublicHttpResponse:
    request = Request(
        INFO_URL,
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/json", "Content-Length": str(len(body.encode()))},
        method="POST",
    )
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=15) as response:
            content = response.read(_MAX_RESPONSE_BYTES + 1)
            return PublicHttpResponse(response.status, content)
    except OSError as exc:
        raise PublicHttpError("public HTTP request failed") from exc


def _post_json(post: HttpPost, payload: dict[str, object]) -> str:
    raw_request = canonical_json_bytes(payload).decode("utf-8")
    response = post(raw_request)
    if type(response) is not PublicHttpResponse or response.status < 200 or response.status >= 300:
        raise PublicHttpError("public HTTP response is not successful")
    if len(response.body) > _MAX_RESPONSE_BYTES:
        raise PublicHttpError("public HTTP response exceeds bound")
    try:
        return response.body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PublicHttpError("public HTTP response is not UTF-8") from exc


async def _default_websocket() -> WebSocketConnection:
    try:
        return cast(WebSocketConnection, await connect(WEBSOCKET_URL, proxy=None, open_timeout=15))
    except OSError as exc:
        raise PublicWebSocketError("public WebSocket connection failed") from exc


def _subscription(interval: str | None = None) -> dict[str, object]:
    subscription: dict[str, object] = {"type": "activeAssetCtx", "coin": "ETH"}
    if interval is not None:
        subscription = {"type": "candle", "coin": "ETH", "interval": interval}
    return {"method": "subscribe", "subscription": subscription}


def _is_acknowledgement(raw: str, expected: dict[str, object]) -> bool:
    try:
        value = json.loads(
            raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ProtocolAcknowledgementError("subscription acknowledgement is malformed") from exc
    if type(value) is not dict or value.get("channel") != "subscriptionResponse":
        return False
    data = value.get("data")
    if type(data) is not dict or data.get("subscription") != expected["subscription"]:
        raise ProtocolAcknowledgementError("subscription acknowledgement does not match")
    return True


def _record_payload(
    *,
    session_id: str,
    permit_id: str,
    shadow: ShadowOrder,
    card: OperatorReviewCard,
    created_at: datetime,
) -> dict[str, object]:
    return {
        "record_version": 1,
        "session_id": session_id,
        "permit_id": permit_id,
        "record_hash": "",
        "shadow_order_id": shadow.shadow_order_id,
        "shadow_order_hash": shadow.canonical_hash,
        "card_id": card.card_id,
        "card_hash": card.canonical_hash,
        "setup_id": shadow.setup_id,
        "setup_hash": shadow.setup_hash,
        "plan_id": shadow.plan_id,
        "plan_hash": shadow.plan_hash,
        "submission_status": "NOT_SUBMITTED",
        "manual_execution_required": True,
        "created_at": created_at.isoformat(),
        "shadow_order_payload": shadow.payload(),
    }


def _record_hash(payload: dict[str, object]) -> str:
    body = dict(payload)
    body.pop("record_hash", None)
    return hashlib.sha256(_RECORD_DOMAIN + b"\0" + canonical_json_bytes(body)).hexdigest()


def _write_record(path: Path, payload: dict[str, object]) -> str:
    payload["record_hash"] = _record_hash(payload)
    raw = canonical_json_bytes(payload)
    parent_fd = os.open(path.parent, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)
    try:
        try:
            fd = os.open(
                path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW, 0o600, dir_fd=parent_fd
            )
        except FileExistsError as exc:
            raise ShadowRecordError("shadow record must not overwrite a target") from exc
        try:
            written = os.write(fd, raw)
            if written != len(raw):
                raise OSError("short shadow record write")
            os.fsync(fd)
            metadata = os.fstat(fd)
            if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
                raise ShadowRecordError("shadow record identity is invalid")
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.unlink(path.name, dir_fd=parent_fd)
            raise ShadowRecordError("shadow record durability failed") from exc
        finally:
            os.close(fd)
        _fsync_directory(parent_fd)
    finally:
        os.close(parent_fd)
    try:
        reread = path.read_bytes()
        decoded = json.loads(
            reread.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ShadowRecordError("shadow record cannot be reread") from exc
    if (
        type(decoded) is not dict
        or reread != raw
        or decoded != payload
        or _record_hash(decoded) != payload["record_hash"]
    ):
        raise ShadowRecordError("shadow record verification failed")
    return cast(str, payload["record_hash"])


def _compose(
    data: EthMarketData,
    *,
    now: datetime,
    equity: Decimal,
    prepared: PreparedSetup | None,
    decided: frozenset[str],
) -> tuple[PreparedSetup | None, OperatorReviewCard, ShadowOrder | None]:
    snapshot = data.strategy_snapshot(now)
    try:
        current: Signal | PreparedSetup | StrategyOutput
        if prepared is None:
            current = evaluate_signal(snapshot, decided_setup_ids=decided)
        else:
            current = advance_prepare(
                prepared, snapshot, already_decided=prepared.provenance.setup_id in decided
            )
        if type(current) is PreparedSetup:
            signal = Signal(
                SignalState.PREPARE,
                current.provenance.side,
                "STANDARD",
                current.provenance.setup_id,
                "AWAITING_CONFIRMATION",
            )
            return (
                current,
                build_operator_card(signal, now=now, quality=snapshot.quality.state),
                None,
            )
        if type(current) is Signal:
            return None, build_operator_card(current, now=now, quality=snapshot.quality.state), None
        if type(current) is not StrategyOutput:
            raise LifecycleCompositionError("strategy output authority is invalid")
        if (
            snapshot.quality.state is not DataQualityState.READY
            or snapshot.active_context is None
            or snapshot.metadata is None
        ):
            raise LifecycleCompositionError("actionable output lacks ready public authority")
        reference = snapshot.active_context.reference_price
        if reference is None:
            raise LifecycleCompositionError("public reference price is invalid")
        plan = build_plan(
            strategy_output=current,
            reference=reference,
            equity=equity,
            sz_decimals=snapshot.metadata.sz_decimals,
        )
        card = build_operator_card(plan, now=now, quality=snapshot.quality.state)
        return None, card, create_shadow_order(card)
    except (PlanError, ValueError) as exc:
        raise LifecycleCompositionError("strategy lifecycle composition failed") from exc


async def run_first_launch_operator_assist(
    *,
    permit_path: Path,
    shadow_output: Path,
    repo_root: Path | None = None,
    http_post: HttpPost | None = None,
    websocket_factory: WebSocketFactory | None = None,
    display: Display | None = None,
    clock: Callable[[], datetime] | None = None,
) -> OperatorAssistResult:
    """Run one public-data session, returning only after one durable shadow record."""
    root = (repo_root or Path.cwd()).resolve()
    permit = _read_permit(permit_path)
    _validate_repository(root, permit)
    _validate_output_path(shadow_output)
    _consume_permit(root, permit)
    now = clock or (lambda: datetime.now(UTC))
    post = http_post or _default_http_post
    data = EthMarketData()
    data.begin_connection()
    try:
        metadata = _post_json(post, {"type": "metaAndAssetCtxs"})
        data.ingest_metadata_info(
            metadata, received_at=now(), receive_sequence=1, connection_id="warmup"
        )
        end = int(now().timestamp() * 1000)
        for sequence, interval, count, width in ((2, "5m", 64, 300000), (3, "15m", 32, 900000)):
            response = _post_json(
                post,
                {
                    "type": "candleSnapshot",
                    "req": {
                        "coin": "ETH",
                        "interval": interval,
                        "startTime": end - count * width,
                        "endTime": end,
                    },
                },
            )
            data.ingest_candle_snapshot(
                response,
                interval=cast(Literal["5m", "15m"], interval),
                received_at=now(),
                receive_sequence=sequence,
                connection_id="warmup",
            )
    except (PublicHttpError, ValueError) as exc:
        raise MarketDataWarmupError("public warm-up failed") from exc
    socket = await (websocket_factory or _default_websocket)()
    deadline = time.monotonic() + permit.max_session_seconds
    subscriptions = (_subscription("5m"), _subscription("15m"), _subscription())
    prepared: PreparedSetup | None = None
    decided: frozenset[str] = frozenset()
    evaluated_identity: tuple[str, str, int] | None = None
    try:
        for subscription in subscriptions:
            await socket.send(canonical_json_bytes(subscription).decode("utf-8"))
        acknowledgements: set[str] = set()
        while len(acknowledgements) != len(subscriptions):
            remaining = min(_ACK_TIMEOUT_SECONDS, deadline - time.monotonic())
            if remaining <= 0:
                raise SessionTimeoutError("subscription acknowledgement deadline expired")
            frame = await asyncio.wait_for(socket.recv(), timeout=remaining)
            if isinstance(frame, bytes):
                raise PublicWebSocketError("binary public WebSocket frame is prohibited")
            matched = [item for item in subscriptions if _is_acknowledgement(frame, item)]
            if len(matched) != 1:
                raise ProtocolAcknowledgementError("unexpected subscription acknowledgement")
            key = canonical_json_bytes(matched[0]).decode("utf-8")
            if key in acknowledgements:
                raise ProtocolAcknowledgementError("duplicate subscription acknowledgement")
            acknowledgements.add(key)
        while time.monotonic() < deadline:
            frame = await asyncio.wait_for(
                socket.recv(), timeout=max(0.01, deadline - time.monotonic())
            )
            if isinstance(frame, bytes):
                raise PublicWebSocketError("binary public WebSocket frame is prohibited")
            try:
                result = data.ingest_websocket(
                    frame,
                    received_at=now(),
                    receive_sequence=len(acknowledgements) + 1,
                    connection_id="session",
                )
            except ValueError as exc:
                raise PublicWebSocketError("public WebSocket observation is invalid") from exc
            if result == "CONTEXT_ACCEPTED" or result == "ACCEPTED":
                snapshot = data.strategy_snapshot(now())
                latest = snapshot.candles_5m[-1].identity if snapshot.candles_5m else None
                if latest is not None and latest != evaluated_identity:
                    evaluated_identity = latest
                    prepared, card, shadow = _compose(
                        data,
                        now=now(),
                        equity=permit.manual_equity_usd,
                        prepared=prepared,
                        decided=decided,
                    )
                    if display is not None:
                        display(render_terminal(card))
                    if shadow is not None:
                        record = _record_payload(
                            session_id=str(uuid4()),
                            permit_id=permit.permit_id,
                            shadow=shadow,
                            card=card,
                            created_at=now(),
                        )
                        record_hash = _write_record(shadow_output, record)
                        return OperatorAssistResult(
                            TASK_ID,
                            permit.permit_id,
                            cast(str, record["session_id"]),
                            shadow_output,
                            record_hash,
                            shadow.shadow_order_id,
                            card.card_id,
                            shadow.setup_id,
                            shadow.plan_id,
                            cast(Literal["FAST", "STANDARD"], card.payload["speed"]),
                        )
        raise SessionTimeoutError("session maximum duration expired without a shadow record")
    finally:
        data.mark_disconnected()
        with contextlib.suppress(Exception):
            await socket.close()
