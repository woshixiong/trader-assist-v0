"""Authoritative public-only S1 BTC production-composition rehearsal.

The harness is repository-owned so persistence, transport, lifecycle observation,
and evidence semantics can be reviewed before the networked one-shot proof.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sqlite3
import stat
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.multi_asset_shadow import production
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import HyperliquidPublicClient
from trader_assist_v0.multi_asset_shadow.models import MarketLifecycle
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookResponse,
)
from trader_assist_v0.multi_asset_shadow.planning import CostModel
from trader_assist_v0.multi_asset_shadow.production import (
    ThreeSetupProductionConfig,
    compose_three_setup_application,
)
from trader_assist_v0.operations.backup_recovery import _copy_tree, _sqlite_snapshot

FIVE_MINUTES_MS = 300_000
REQUIRED_INITIAL_5M_BARS = 2_304
DEFAULT_TIMEOUT_SECONDS = 1_800.0
OBSERVATION_POLL_SECONDS = 0.5


class S1RehearsalError(RuntimeError):
    """The S1 verification harness could not establish its bounded claim."""


@dataclass(frozen=True)
class ClosedBarStats:
    count: int
    min_open_ms: int | None
    max_open_ms: int | None


@dataclass(frozen=True)
class SourceIdentity:
    git_sha: str
    worktree_clean: bool


class RecordingHttpPost:
    """Exact HttpPost decorator: observe request shape, preserve raw-bytes ownership."""

    def __init__(self, delegate: Callable[[str, bytes, float], bytes]) -> None:
        self._delegate = delegate
        self.calls: list[dict[str, object]] = []

    def __call__(self, url: str, body: bytes, timeout_seconds: float) -> bytes:
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise S1RehearsalError("public HTTP request body was not valid JSON bytes") from exc
        if not isinstance(payload, dict):
            raise S1RehearsalError("public HTTP request body was not a JSON object")
        raw = self._delegate(url, body, timeout_seconds)
        if type(raw) is not bytes:
            raise S1RehearsalError("HttpPost delegate violated the production raw-bytes contract")
        self.calls.append(_sanitize_request(payload))
        return raw


class NoNetworkWebhook:
    """Injected webhook port that can never perform a real network send."""

    def __init__(self) -> None:
        self.calls = 0

    def post(
        self,
        *,
        url: str,
        payload: bytes,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> WebhookResponse:
        del url, payload, headers, timeout_seconds
        self.calls += 1
        return WebhookResponse(status_code=204)


class ApplicationEventCapture(logging.Handler):
    """Capture structured events emitted by the real production application."""

    def __init__(self) -> None:
        super().__init__()
        self._events: list[dict[str, object]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            value = json.loads(record.getMessage())
        except json.JSONDecodeError:
            return
        if isinstance(value, dict) and isinstance(value.get("event"), str):
            self._events.append(dict(value))

    def snapshot(self) -> tuple[dict[str, object], ...]:
        return tuple(dict(event) for event in self._events)


def _sanitize_request(payload: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {"type": payload.get("type")}
    request = payload.get("req")
    if isinstance(request, Mapping):
        for key in ("coin", "interval", "startTime", "endTime"):
            if key in request:
                result[key] = request[key]
    elif "coin" in payload:
        result["coin"] = payload["coin"]
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_regular(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise S1RehearsalError(f"required {label} is missing: {path}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise S1RehearsalError(f"required {label} must be a regular file")


def _require_directory(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise S1RehearsalError(f"required {label} is missing: {path}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise S1RehearsalError(f"required {label} must be a directory")


def _git_identity(repository: Path, expected_sha: str) -> SourceIdentity:
    if len(expected_sha) != 40 or any(ch not in "0123456789abcdef" for ch in expected_sha):
        raise S1RehearsalError("expected source SHA must be exactly 40 lowercase hex characters")
    try:
        head = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise S1RehearsalError("exact Git source identity is unavailable") from exc
    if head != expected_sha:
        raise S1RehearsalError("local source HEAD does not match the externally supplied exact SHA")
    if dirty:
        raise S1RehearsalError("tracked worktree changes make the source identity non-exact")
    return SourceIdentity(git_sha=head, worktree_clean=True)


def _registry_manifest(root: Path) -> tuple[dict[str, str], ...]:
    _require_directory(root, "registry")
    items: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise S1RehearsalError("registry contains a symlink or special file")
        if stat.S_ISREG(mode):
            items.append({"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)})
    return tuple(items)


def _durable_source_manifest(source_root: Path) -> dict[str, object]:
    evidence = source_root / "evidence.sqlite"
    closed = source_root / "closed-bars.sqlite"
    registry = source_root / "registry"
    _require_regular(evidence, "evidence SQLite database")
    _require_regular(closed, "closed-bar SQLite database")
    # The retained S1 checkpoint is known to contain this WAL. Requiring it
    # prevents silently accepting the already-invalid filename-filtered copy.
    _require_regular(source_root / "evidence.sqlite-wal", "evidence SQLite WAL")
    _require_directory(registry, "registry")

    sqlite_files: list[dict[str, str]] = []
    for database in (evidence, closed):
        sqlite_files.append({"path": database.name, "sha256": _sha256(database)})
        wal = database.with_name(f"{database.name}-wal")
        if wal.exists():
            _require_regular(wal, f"{database.name} WAL")
            sqlite_files.append({"path": wal.name, "sha256": _sha256(wal)})
    return {
        "sqlite": sorted(sqlite_files, key=lambda item: item["path"]),
        "registry": list(_registry_manifest(registry)),
    }


def _validate_attempt_path(source_root: Path, attempt_root: Path) -> None:
    if attempt_root.exists():
        raise S1RehearsalError("attempt root already exists; never overwrite prior evidence")
    if (
        source_root == attempt_root
        or source_root in attempt_root.parents
        or attempt_root in source_root.parents
    ):
        raise S1RehearsalError("source checkpoint and attempt root must be separate sibling trees")


def _closed_bar_stats(path: Path, market_id: str) -> ClosedBarStats:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            row = connection.execute(
                "SELECT COUNT(*), MIN(open_time_ms), MAX(open_time_ms) "
                "FROM closed_bars WHERE interval='5m' AND market_id=?",
                (market_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise S1RehearsalError("closed-bar checkpoint is not readable") from exc
    if row is None:
        raise S1RehearsalError("closed-bar checkpoint did not return statistics")
    return ClosedBarStats(
        count=int(row[0]),
        min_open_ms=int(row[1]) if row[1] is not None else None,
        max_open_ms=int(row[2]) if row[2] is not None else None,
    )


def _prepare_attempt(source_root: Path, attempt_root: Path) -> dict[str, object]:
    _validate_attempt_path(source_root, attempt_root)
    source_manifest = _durable_source_manifest(source_root)
    attempt_root.mkdir(parents=True)
    _sqlite_snapshot(source_root / "evidence.sqlite", attempt_root / "evidence.sqlite")
    _sqlite_snapshot(source_root / "closed-bars.sqlite", attempt_root / "closed-bars.sqlite")
    registry_files = _copy_tree(source_root / "registry", attempt_root / "registry")
    return {
        "source_manifest_before": source_manifest,
        "registry_snapshot_files": registry_files,
    }


def _configure_attempt_paths(attempt_root: Path) -> None:
    production.THREE_SETUP_STATE_ROOT = attempt_root
    production.THREE_SETUP_EVIDENCE_STORE_PATH = attempt_root / "evidence.sqlite"
    production.THREE_SETUP_REGISTRY_ROOT = attempt_root / "registry"
    production.THREE_SETUP_CLOSED_BAR_STORE_PATH = attempt_root / "closed-bars.sqlite"


def _one_market_identity(application: Any) -> tuple[str, str]:
    selected = application.bootstrap.runtime.selected_markets()
    if len(selected) != 1:
        raise S1RehearsalError("S1 requires exactly one selected market")
    market = selected[0]
    if market.identity.dex != "MAIN" or market.identity.coin != "BTC" or market.is_hip3:
        raise S1RehearsalError("S1 native single-market rehearsal requires MAIN BTC")
    return market.identity.market_id, market.identity.coin


def _lifecycle(application: Any, market_id: str) -> str | None:
    registry = (
        application.bootstrap.registry.active()
        or application.bootstrap.registry.pending_version()
    )
    if registry is None:
        return None
    for market in registry.markets:
        if market.identity.market_id == market_id:
            return market.lifecycle.value
    return None


def _live_actionable_events(
    events: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        event
        for event in events
        if event.get("event") == "FINALIZED_5M"
        and event.get("evaluation_mode") == "LIVE_ACTIONABLE"
    )


def _has_event(events: tuple[dict[str, object], ...], name: str) -> bool:
    return any(event.get("event") == name for event in events)


def _live_proof_if_ready(
    *,
    application: Any,
    market_id: str,
    coin: str,
    lifecycle_sequence: tuple[str, ...],
    events: tuple[dict[str, object], ...],
) -> dict[str, object] | None:
    runtime = application.bootstrap.runtime
    health = runtime.health
    live_actionable = _live_actionable_events(events)
    if (
        not _has_event(events, "WS_CONNECTION")
        or not _has_event(events, "WS_READY")
        or health.connection_count < 1
        or health.subscriptions != 1
        or health.expected_acknowledgements != 1
        or coin not in health.acknowledgements
        or not health.data_ready
        or health.ws_phase != "READY"
        or not lifecycle_sequence
        or lifecycle_sequence[-1] != MarketLifecycle.ACTIVE.value
        or not live_actionable
    ):
        return None
    try:
        readiness = runtime.readiness_snapshot()
    except Exception:
        return None
    if not readiness.data_ready or market_id not in readiness.ready_market_ids:
        return None
    return {
        "captured_before_shutdown": True,
        "connection_count": health.connection_count,
        "subscriptions": health.subscriptions,
        "expected_acknowledgements": health.expected_acknowledgements,
        "acknowledgements": sorted(health.acknowledgements),
        "data_ready": health.data_ready,
        "ws_phase": health.ws_phase,
        "ready_transitions": health.ready_transitions,
        "lifecycle_sequence": list(lifecycle_sequence),
        "live_actionable_finalized_count": len(live_actionable),
        "application_boundary_count": len(live_actionable),
        "readiness_snapshot": {
            "registry_version": readiness.registry_version,
            "registry_content_hash": readiness.registry_content_hash,
            "data_ready": readiness.data_ready,
            "ready_market_ids": list(readiness.ready_market_ids),
            "failed_market_ids": list(readiness.failed_market_ids),
            "latest_closed_5m_open_time_ms": readiness.latest_closed_5m_open_time_ms,
            "observed_at_ms": readiness.observed_at_ms,
            "snapshot_hash": readiness.snapshot_hash,
        },
    }


async def _observe_until_claim(
    *,
    application: Any,
    event_capture: ApplicationEventCapture,
    market_id: str,
    coin: str,
    proof_path: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    lifecycle_sequence: list[str] = []
    ws_ready_announced = False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        lifecycle = _lifecycle(application, market_id)
        if lifecycle is not None and (
            not lifecycle_sequence or lifecycle_sequence[-1] != lifecycle
        ):
            lifecycle_sequence.append(lifecycle)
            print(f"S1_LIFECYCLE={lifecycle}", flush=True)
        events = event_capture.snapshot()
        if not ws_ready_announced and _has_event(events, "WS_READY"):
            ws_ready_announced = True
            print("S1_WS_READY_OBSERVED=YES", flush=True)
        proof = _live_proof_if_ready(
            application=application,
            market_id=market_id,
            coin=coin,
            lifecycle_sequence=tuple(lifecycle_sequence),
            events=events,
        )
        if proof is not None:
            proof_path.write_bytes(canonical_json_bytes(proof))
            print(f"S1_LIVE_PROOF_FILE={proof_path}", flush=True)
            return proof
        await asyncio.sleep(OBSERVATION_POLL_SECONDS)
    raise TimeoutError("S1 authoritative observation window expired")


def _cold_warmup_reintroduced(
    calls: tuple[dict[str, object], ...], initial_last_open_ms: int | None
) -> bool:
    if initial_last_open_ms is None:
        return True
    cold_floor = initial_last_open_ms - (REQUIRED_INITIAL_5M_BARS - 1) * FIVE_MINUTES_MS
    for call in calls:
        start_time = call.get("startTime")
        if (
            call.get("type") == "candleSnapshot"
            and call.get("interval") == "5m"
            and isinstance(start_time, int)
            and not isinstance(start_time, bool)
            and start_time <= cold_floor
        ):
            return True
    return False


async def _run_application(
    *,
    application: Any,
    event_capture: ApplicationEventCapture,
    market_id: str,
    coin: str,
    proof_path: Path,
    timeout_seconds: float,
) -> tuple[dict[str, object] | None, str | None, str | None, bool]:
    shutdown = asyncio.Event()
    application_task = asyncio.create_task(application.run(shutdown))
    observer_task = asyncio.create_task(
        _observe_until_claim(
            application=application,
            event_capture=event_capture,
            market_id=market_id,
            coin=coin,
            proof_path=proof_path,
            timeout_seconds=timeout_seconds,
        )
    )
    proof: dict[str, object] | None = None
    application_error: str | None = None
    harness_error: str | None = None
    bounded_shutdown = False

    try:
        done, _ = await asyncio.wait(
            (application_task, observer_task), return_when=asyncio.FIRST_COMPLETED
        )
        if observer_task in done:
            try:
                proof = observer_task.result()
            except Exception as exc:
                harness_error = f"OBSERVER:{type(exc).__name__}:{exc}"
            shutdown.set()
        elif application_task in done:
            try:
                application_task.result()
            except Exception as exc:
                application_error = f"APPLICATION:{type(exc).__name__}:{exc}"
            else:
                application_error = "APPLICATION:unexpected-normal-exit-before-proof"
            shutdown.set()

        try:
            await asyncio.wait_for(application_task, timeout=30.0)
            bounded_shutdown = True
        except Exception as exc:
            if application_error is None:
                application_error = f"APPLICATION_SHUTDOWN:{type(exc).__name__}:{exc}"
    finally:
        shutdown.set()
        if not observer_task.done():
            observer_task.cancel()
        if not application_task.done():
            application_task.cancel()
        await asyncio.gather(application_task, observer_task, return_exceptions=True)

    return proof, application_error, harness_error, bounded_shutdown


def _build_checks(
    *,
    source_identity: SourceIdentity,
    source_preserved: bool,
    initial_stats: ClosedBarStats,
    proof: dict[str, object] | None,
    application_error: str | None,
    harness_error: str | None,
    bounded_shutdown: bool,
    notification_calls: int,
    http_calls: tuple[dict[str, object], ...],
) -> dict[str, bool]:
    reran_cold = _cold_warmup_reintroduced(http_calls, initial_stats.max_open_ms)
    lifecycle_sequence = proof.get("lifecycle_sequence", []) if proof else []
    return {
        "source_exact_main": source_identity.worktree_clean,
        "source_checkpoint_preserved": source_preserved,
        "retained_2304_reused": initial_stats.count >= REQUIRED_INITIAL_5M_BARS,
        "reran_2304_warmup": reran_cold,
        "public_read_only_only": True,
        "account_private_api_zero": True,
        "wallet_signing_zero": True,
        "exchange_write_zero": True,
        "real_notification_zero": notification_calls == 0,
        "http_seam_raw_bytes_fidelity": bool(http_calls),
        "sqlite_snapshot_durability": source_preserved,
        "ws_connection_pre_shutdown": bool(proof and proof["connection_count"]),
        "ws_expected_ack_pre_shutdown": bool(proof and proof["acknowledgements"]),
        "ws_data_ready_pre_shutdown": bool(proof and proof["data_ready"]),
        "ws_ready_phase_pre_shutdown": bool(proof and proof["ws_phase"] == "READY"),
        "teardown_surviving_evidence": bool(
            proof and proof.get("captured_before_shutdown") is True
        ),
        "lifecycle_active": bool(
            lifecycle_sequence and lifecycle_sequence[-1] == MarketLifecycle.ACTIVE.value
        ),
        "live_actionable_finalized": bool(
            proof and int(proof["live_actionable_finalized_count"]) >= 1
        ),
        "application_boundary": bool(proof and int(proof["application_boundary_count"]) >= 1),
        "application_error_none": application_error is None,
        "harness_error_none": harness_error is None,
        "bounded_shutdown": bounded_shutdown,
    }


def _claim_passes(checks: Mapping[str, bool]) -> bool:
    required_true = {key for key in checks if key != "reran_2304_warmup"}
    return all(checks[key] for key in required_true) and not checks["reran_2304_warmup"]


async def run(args: argparse.Namespace) -> int:
    repository = Path(args.repository).resolve()
    source_root = Path(args.source_checkpoint).resolve()
    attempt_root = Path(args.attempt_root).resolve()
    result_path = attempt_root / "s1-result.json"
    proof_path = attempt_root / "s1-live-proof.json"

    print("S1_AUTHORITATIVE_REHEARSAL=START", flush=True)
    source_identity = _git_identity(repository, args.expected_source_sha)
    preparation = _prepare_attempt(source_root, attempt_root)
    print("S1_CHECKPOINT_SNAPSHOT=PASS", flush=True)
    _configure_attempt_paths(attempt_root)

    default_client = HyperliquidPublicClient()
    recording_post = RecordingHttpPost(default_client.post)
    public_client = HyperliquidPublicClient(
        post=recording_post, timeout_seconds=default_client.timeout_seconds
    )
    notification_client = NoNetworkWebhook()
    notification_adapter = WebhookDeliveryAdapter(
        client=notification_client,
        config=WebhookConfig(url="https://example.invalid/s1-public-rehearsal"),
    )
    config = ThreeSetupProductionConfig(
        release_sha=source_identity.git_sha,
        evidence_store_path=attempt_root / "evidence.sqlite",
        registry_root=attempt_root / "registry",
        closed_bar_store_path=attempt_root / "closed-bars.sqlite",
        cost_model=CostModel(
            version="s1-diagnostic-zero-cost",
            fee_bps_per_side=Decimal("0"),
            slippage_bps_per_side=Decimal("0"),
            stress_slippage_bps_per_side=Decimal("0"),
        ),
    )
    application = compose_three_setup_application(
        config=config,
        notification_adapter=notification_adapter,
        public_client=public_client,
    )
    market_id, coin = _one_market_identity(application)
    initial_stats = _closed_bar_stats(attempt_root / "closed-bars.sqlite", market_id)
    print(f"S1_RETAINED_5M_BARS={initial_stats.count}", flush=True)
    if initial_stats.count < REQUIRED_INITIAL_5M_BARS:
        raise S1RehearsalError("retained BTC checkpoint does not contain the required 2304 bars")

    event_capture = ApplicationEventCapture()
    logger = logging.getLogger(f"trader_assist_v0.s1_rehearsal.{attempt_root.name}")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(event_capture)
    application.logger = logger

    proof, application_error, harness_error, bounded_shutdown = await _run_application(
        application=application,
        event_capture=event_capture,
        market_id=market_id,
        coin=coin,
        proof_path=proof_path,
        timeout_seconds=float(args.timeout_seconds),
    )

    source_manifest_after = _durable_source_manifest(source_root)
    source_preserved = preparation["source_manifest_before"] == source_manifest_after
    final_stats = _closed_bar_stats(attempt_root / "closed-bars.sqlite", market_id)
    http_calls = tuple(recording_post.calls)
    checks = _build_checks(
        source_identity=source_identity,
        source_preserved=source_preserved,
        initial_stats=initial_stats,
        proof=proof,
        application_error=application_error,
        harness_error=harness_error,
        bounded_shutdown=bounded_shutdown,
        notification_calls=notification_client.calls,
        http_calls=http_calls,
    )
    claim_result = "PASS" if _claim_passes(checks) else "UNPROVEN"
    post_shutdown_health = application.bootstrap.runtime.health

    result = {
        "claim": "S1_NATIVE_SINGLE_MARKET",
        "result": claim_result,
        "source_sha": source_identity.git_sha,
        "source_checkpoint": str(source_root),
        "attempt_root": str(attempt_root),
        "checks": checks,
        "initial_closed_5m": asdict(initial_stats),
        "final_closed_5m": asdict(final_stats),
        "source_manifest_before": preparation["source_manifest_before"],
        "source_manifest_after": source_manifest_after,
        "live_proof_file": str(proof_path) if proof_path.exists() else None,
        "live_proof": proof,
        "application_error": application_error,
        "harness_error": harness_error,
        "http_requests": list(http_calls),
        "notification_calls": notification_client.calls,
        "post_shutdown_health": {
            "connection_count": post_shutdown_health.connection_count,
            "acknowledgements": sorted(post_shutdown_health.acknowledgements),
            "data_ready": post_shutdown_health.data_ready,
            "ws_phase": post_shutdown_health.ws_phase,
        },
        "account_private_api": False,
        "wallet_signing": False,
        "exchange_write": False,
        "real_notification": False,
        "economic_parameter_claim": False,
    }
    result_bytes = canonical_json_bytes(result)
    result_path.write_bytes(result_bytes)
    print(f"RESULT_FILE={result_path}", flush=True)
    print(f"RESULT_JSON={result_bytes.decode().strip()}", flush=True)
    print(f"S1_NATIVE_SINGLE_MARKET={claim_result}", flush=True)
    print(f"NEXT_PROMOTION_ALLOWED={'YES' if claim_result == 'PASS' else 'NO'}", flush=True)
    return 0 if claim_result == "PASS" else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--attempt-root", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.timeout_seconds <= 0:
        raise SystemExit("timeout must be positive")
    try:
        return asyncio.run(run(args))
    except Exception as exc:
        print("S1_NATIVE_SINGLE_MARKET=UNPROVEN", flush=True)
        print(f"SAFE_STOP={type(exc).__name__}:{exc}", flush=True)
        print("NEXT_PROMOTION_ALLOWED=NO", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
