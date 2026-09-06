#!/usr/bin/env python3
"""Repository-owned, observer-only S1 BTC public rehearsal harness.

The harness proves the frozen S1_NATIVE_SINGLE_MARKET claim without becoming
application authority.  It never writes evidence from production callbacks,
never opens the retained source checkpoint with SQLite, and never performs
account/private/signing/exchange-write operations.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import stat
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Final

from scripts.verify_exact_release import ExactReleaseError, build_release_manifest, exact_clean_head
from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.multi_asset_shadow import production
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    INFO_URL,
    HttpPost,
    HyperliquidPublicClient,
)
from trader_assist_v0.multi_asset_shadow.models import MarketLifecycle
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookResponse,
)
from trader_assist_v0.multi_asset_shadow.planning import CostModel
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.operations.backup_recovery import RecoveryError, _sqlite_snapshot

CLAIM: Final = "S1_NATIVE_SINGLE_MARKET"
RESULT_SCHEMA: Final = "trader-assist-v0/s1-native-single-market-rehearsal/v2"
WITNESS_SCHEMA: Final = "trader-assist-v0/s1-production-journal-witness/v1"
MANIFEST_SCHEMA: Final = "trader-assist-v0/s1-checkpoint-byte-manifest/v1"
FIVE_MINUTES_MS: Final = 300_000
RETAINED_HISTORY_MIN_BARS: Final = 2_304
MAX_BOUNDED_CATCHUP_BARS: Final = RETAINED_HISTORY_MIN_BARS - 1
_ALLOWED_PROVIDER_TYPES: Final = frozenset({"candleSnapshot", "l2Book"})
_REQUIRED_SQLITE: Final = ("evidence.sqlite", "closed-bars.sqlite")
_PRE_ACTIVE: Final = {
    MarketLifecycle.WARMING,
    MarketLifecycle.HISTORY_READY,
    MarketLifecycle.SNAPSHOT_READY,
}


class S1HarnessError(RuntimeError):
    """Typed verification-harness safe stop."""

    def __init__(self, message: str, *, failure_class: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


@dataclass(frozen=True)
class RawEntry:
    path: str
    kind: str
    size: int | None
    sha256: str | None


@dataclass(frozen=True)
class CheckpointImport:
    source: Path
    quarantine: Path
    working: Path
    state: Path
    source_manifest: tuple[RawEntry, ...]
    manifest_sha256: str
    checkpoint_json_sha256: str
    market_id: str
    retained_count: int
    retained_first_open_ms: int
    retained_last_open_ms: int
    pre_run_catchup_bars: int


@dataclass(frozen=True)
class JournalEntry:
    sequence: int
    message: str


@dataclass(frozen=True)
class JournalProof:
    connection: bool
    acknowledgement: bool
    ready: bool
    live_boundary_open_ms: int | None
    boundary_report: bool
    readiness_after_boundary: bool

    @property
    def complete(self) -> bool:
        return (
            self.connection
            and self.acknowledgement
            and self.ready
            and self.live_boundary_open_ms is not None
            and self.boundary_report
            and self.readiness_after_boundary
        )


@dataclass(frozen=True)
class RequestObservation:
    request_type: str | None
    interval: str | None
    start_ms: int | None
    end_ms: int | None


@dataclass
class JournalCaptureHandler(logging.Handler):
    """No-I/O observer.  emit() must never throw into the production logger."""

    entries: list[JournalEntry] = field(default_factory=list, init=False)
    capture_error: str | None = field(default=None, init=False)
    _sequence: int = field(default=0, init=False)
    _guard: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        logging.Handler.__init__(self, level=logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            with self._guard:
                self._sequence += 1
                self.entries.append(JournalEntry(self._sequence, message))
        except BaseException as exc:
            try:
                with self._guard:
                    if self.capture_error is None:
                        self.capture_error = type(exc).__name__
            except BaseException:
                return

    def snapshot(self) -> tuple[tuple[JournalEntry, ...], str | None]:
        with self._guard:
            return tuple(self.entries), self.capture_error


@dataclass
class AuditingRawPost:
    """Transparent public-HTTP observer; application/provider semantics stay delegated."""

    delegate: HttpPost
    observations: list[RequestObservation] = field(default_factory=list, init=False)
    audit_error: str | None = field(default=None, init=False)
    _guard: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def _latch(self, exc: BaseException) -> None:
        try:
            with self._guard:
                if self.audit_error is None:
                    self.audit_error = type(exc).__name__
        except BaseException:
            return

    def __call__(self, url: str, body: bytes, timeout_seconds: float) -> bytes:
        try:
            request_type: str | None = None
            interval: str | None = None
            start_ms: int | None = None
            end_ms: int | None = None
            if url != INFO_URL or not isinstance(body, bytes) or timeout_seconds <= 0:
                raise ValueError("public HTTP seam identity is invalid")
            decoded = json.loads(body)
            if not isinstance(decoded, dict):
                raise ValueError("public HTTP body is not an object")
            raw_type = decoded.get("type")
            if isinstance(raw_type, str):
                request_type = raw_type
            if request_type == "candleSnapshot":
                request = decoded.get("req")
                if isinstance(request, dict):
                    raw_interval = request.get("interval")
                    raw_start = request.get("startTime")
                    raw_end = request.get("endTime")
                    interval = raw_interval if isinstance(raw_interval, str) else None
                    start_ms = (
                        raw_start
                        if isinstance(raw_start, int) and not isinstance(raw_start, bool)
                        else None
                    )
                    end_ms = (
                        raw_end
                        if isinstance(raw_end, int) and not isinstance(raw_end, bool)
                        else None
                    )
            with self._guard:
                self.observations.append(
                    RequestObservation(request_type, interval, start_ms, end_ms)
                )
        except BaseException as exc:
            self._latch(exc)
        return self.delegate(url, body, timeout_seconds)

    def snapshot(self) -> tuple[tuple[RequestObservation, ...], str | None]:
        with self._guard:
            return tuple(self.observations), self.audit_error


@dataclass
class NoNetworkWebhook:
    """Injected notification sink.  It records calls and performs no external I/O."""

    calls: int = 0

    def post(self, **_: object) -> WebhookResponse:
        self.calls += 1
        return WebhookResponse(204)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_payload(entries: tuple[RawEntry, ...]) -> dict[str, object]:
    return {
        "schema": MANIFEST_SCHEMA,
        "entries": [
            {
                "path": entry.path,
                "kind": entry.kind,
                "size": entry.size,
                "sha256": entry.sha256,
            }
            for entry in entries
        ],
    }


def _manifest_digest(entries: tuple[RawEntry, ...]) -> str:
    return hashlib.sha256(canonical_json_bytes(_manifest_payload(entries))).hexdigest()


def _raw_tree_manifest(root: Path) -> tuple[RawEntry, ...]:
    if not root.is_dir() or root.is_symlink():
        raise S1HarnessError(
            "checkpoint root must be a real directory",
            failure_class="CHECKPOINT_QUARANTINE_FAILURE",
        )
    entries: list[RawEntry] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        mode = path.lstat().st_mode
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(mode):
            raise S1HarnessError(
                "checkpoint contains a symlink",
                failure_class="CHECKPOINT_QUARANTINE_FAILURE",
            )
        if stat.S_ISDIR(mode):
            entries.append(RawEntry(relative, "directory", None, None))
            continue
        if not stat.S_ISREG(mode):
            raise S1HarnessError(
                "checkpoint contains a special file",
                failure_class="CHECKPOINT_QUARANTINE_FAILURE",
            )
        entries.append(RawEntry(relative, "file", path.stat().st_size, _sha256(path)))
    return tuple(entries)


def _copy_exact_tree(source: Path, destination: Path, expected: tuple[RawEntry, ...]) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for entry in expected:
        target = destination / entry.path
        if entry.kind == "directory":
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / entry.path, target)
    if _raw_tree_manifest(destination) != expected:
        raise S1HarnessError(
            "byte-exact checkpoint clone identity mismatch",
            failure_class="CHECKPOINT_QUARANTINE_FAILURE",
        )


def _checkpoint_json(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_file() or path.is_symlink():
        raise S1HarnessError(
            "checkpoint.json is missing",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )
    try:
        decoded = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise S1HarnessError(
            "checkpoint.json is invalid",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        ) from exc
    if not isinstance(decoded, dict):
        raise S1HarnessError(
            "checkpoint.json must be an object",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )
    return decoded, _sha256(path)


def _retained_history_summary(path: Path) -> tuple[str, int, int, int]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            rows = connection.execute(
                "SELECT market_id, COUNT(*), MIN(open_time_ms), MAX(open_time_ms) "
                "FROM closed_bars WHERE interval='5m' GROUP BY market_id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise S1HarnessError(
            "retained closed-bar state is unreadable",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        ) from exc
    if len(rows) != 1:
        raise S1HarnessError(
            "retained checkpoint is not single-market",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )
    market_id, count, first_open, last_open = rows[0]
    if (
        not isinstance(market_id, str)
        or not isinstance(count, int)
        or not isinstance(first_open, int)
        or not isinstance(last_open, int)
        or count < RETAINED_HISTORY_MIN_BARS
        or last_open - first_open != (count - 1) * FIVE_MINUTES_MS
    ):
        raise S1HarnessError(
            "retained 5m history is not the required contiguous BTC checkpoint",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )
    return market_id, count, first_open, last_open


def _checkpoint_topology(working: Path) -> tuple[str, MarketLifecycle]:
    registry = MarketRegistryManager(working / "registry", metadata_validator=lambda _: True)
    version = registry.active() or registry.pending_version()
    if version is None or len(version.markets) != 1:
        raise S1HarnessError(
            "checkpoint Registry is not one market",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )
    market = version.markets[0]
    if (
        market.display != "BTC"
        or market.identity.coin != "BTC"
        or market.lifecycle in {MarketLifecycle.DISABLED, MarketLifecycle.OUTCOMES_COMPLETE}
    ):
        raise S1HarnessError(
            "checkpoint Registry is not the retained BTC S1 topology",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )
    return market.identity.market_id, market.lifecycle


def _latest_completed_open(clock: Callable[[], datetime]) -> int:
    now = clock()
    if now.tzinfo is not UTC:
        raise S1HarnessError(
            "harness clock must be exact UTC",
            failure_class="CHECKPOINT_RESUME_VIOLATION",
        )
    observed_ms = int(now.timestamp() * 1000)
    return observed_ms - observed_ms % FIVE_MINUTES_MS - FIVE_MINUTES_MS


def _bounded_catchup_bars(last_open_ms: int, clock: Callable[[], datetime]) -> int:
    target = _latest_completed_open(clock)
    if target < last_open_ms or (target - last_open_ms) % FIVE_MINUTES_MS:
        raise S1HarnessError(
            "retained checkpoint is ahead of or misaligned with the run clock",
            failure_class="CHECKPOINT_RESUME_VIOLATION",
        )
    count = (target - last_open_ms) // FIVE_MINUTES_MS
    if count > MAX_BOUNDED_CATCHUP_BARS:
        raise S1HarnessError(
            "retained checkpoint is too stale for bounded catch-up",
            failure_class="CHECKPOINT_RESUME_VIOLATION",
        )
    return count


def _copy_registry(working: Path, state: Path) -> None:
    source = working / "registry"
    expected = _raw_tree_manifest(source)
    _copy_exact_tree(source, state / "registry", expected)


def _import_checkpoint(
    source_checkpoint: Path,
    attempt_root: Path,
    *,
    clock: Callable[[], datetime],
) -> CheckpointImport:
    source = source_checkpoint.resolve()
    attempt = attempt_root.resolve()
    if source == attempt or source in attempt.parents or attempt in source.parents:
        raise S1HarnessError(
            "source checkpoint and attempt root must be disjoint",
            failure_class="CHECKPOINT_QUARANTINE_FAILURE",
        )
    if attempt.exists():
        raise S1HarnessError(
            "attempt root already exists",
            failure_class="CHECKPOINT_QUARANTINE_FAILURE",
        )

    before = _raw_tree_manifest(source)
    checkpoint_rel = "checkpoint.json"
    if not any(item.path == checkpoint_rel and item.kind == "file" for item in before):
        raise S1HarnessError(
            "checkpoint.json is not present in retained source",
            failure_class="CHECKPOINT_QUARANTINE_FAILURE",
        )

    attempt.mkdir(parents=True, exist_ok=False)
    quarantine = attempt / "checkpoint-quarantine"
    working = attempt / "checkpoint-working"
    state = attempt / "state"
    provenance = attempt / "provenance"
    _copy_exact_tree(source, quarantine, before)
    after_copy = _raw_tree_manifest(source)
    if after_copy != before:
        raise S1HarnessError(
            "retained source changed while quarantining",
            failure_class="CHECKPOINT_QUARANTINE_FAILURE",
        )
    _copy_exact_tree(quarantine, working, before)
    if _raw_tree_manifest(quarantine) != before:
        raise S1HarnessError(
            "unopened quarantine changed unexpectedly",
            failure_class="CHECKPOINT_QUARANTINE_FAILURE",
        )

    _, checkpoint_hash = _checkpoint_json(working / "checkpoint.json")
    registry_market_id, _ = _checkpoint_topology(working)
    retained_market_id, count, first_open, last_open = _retained_history_summary(
        working / "closed-bars.sqlite"
    )
    if retained_market_id != registry_market_id:
        raise S1HarnessError(
            "Registry and retained history market identities differ",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )
    catchup = _bounded_catchup_bars(last_open, clock)

    state.mkdir(parents=True, exist_ok=False)
    try:
        for name in _REQUIRED_SQLITE:
            source_db = working / name
            if not source_db.is_file() or source_db.is_symlink():
                raise S1HarnessError(
                    f"required checkpoint database is missing: {name}",
                    failure_class="CHECKPOINT_IMPORT_FAILURE",
                )
            _sqlite_snapshot(source_db, state / name)
        _copy_registry(working, state)
    except S1HarnessError:
        raise
    except (OSError, sqlite3.Error, RecoveryError) as exc:
        raise S1HarnessError(
            "SQLite/Registry checkpoint normalization failed",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        ) from exc

    normalized_market_id, normalized_count, normalized_first, normalized_last = (
        _retained_history_summary(state / "closed-bars.sqlite")
    )
    if (
        normalized_market_id != retained_market_id
        or normalized_count != count
        or normalized_first != first_open
        or normalized_last != last_open
    ):
        raise S1HarnessError(
            "normalized retained history identity changed",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )

    provenance.mkdir(parents=True, exist_ok=False)
    (provenance / "checkpoint.json").write_bytes((quarantine / "checkpoint.json").read_bytes())
    manifest_bytes = canonical_json_bytes(_manifest_payload(before))
    (provenance / "source-byte-manifest.json").write_bytes(manifest_bytes)

    return CheckpointImport(
        source=source,
        quarantine=quarantine,
        working=working,
        state=state,
        source_manifest=before,
        manifest_sha256=_manifest_digest(before),
        checkpoint_json_sha256=checkpoint_hash,
        market_id=retained_market_id,
        retained_count=count,
        retained_first_open_ms=first_open,
        retained_last_open_ms=last_open,
        pre_run_catchup_bars=catchup,
    )


def bind_release_identity(repo_root: Path, expected_head: str) -> tuple[str, str]:
    try:
        head = exact_clean_head(repo_root.resolve(), expected_head=expected_head)
        manifest = build_release_manifest(repo_root.resolve(), release_sha=head)
    except ExactReleaseError as exc:
        raise S1HarnessError(
            "exact release identity failed",
            failure_class="RELEASE_IDENTITY_FAILURE",
        ) from exc
    digest = manifest.get("manifest_sha256")
    if not isinstance(digest, str):
        raise S1HarnessError(
            "exact release manifest digest is unavailable",
            failure_class="RELEASE_IDENTITY_FAILURE",
        )
    return head, digest


def _decode_journal(entries: tuple[JournalEntry, ...]) -> tuple[dict[str, object], ...]:
    decoded: list[dict[str, object]] = []
    for expected, entry in enumerate(entries, start=1):
        if entry.sequence != expected:
            raise S1HarnessError(
                "journal capture sequence is invalid",
                failure_class="OBSERVER_CAPTURE_FAILURE",
            )
        try:
            value = json.loads(entry.message)
        except json.JSONDecodeError as exc:
            raise S1HarnessError(
                "production journal is not JSON",
                failure_class="OBSERVER_CAPTURE_FAILURE",
            ) from exc
        if not isinstance(value, dict) or not isinstance(value.get("event"), str):
            raise S1HarnessError(
                "production journal event shape is invalid",
                failure_class="OBSERVER_CAPTURE_FAILURE",
            )
        decoded.append(value)
    return tuple(decoded)


def _ack_complete(event: dict[str, object]) -> bool:
    acknowledged = event.get("acknowledged")
    expected = event.get("expected")
    return (
        isinstance(acknowledged, int)
        and not isinstance(acknowledged, bool)
        and isinstance(expected, int)
        and not isinstance(expected, bool)
        and expected > 0
        and acknowledged >= expected
    )


def _journal_proof(events: tuple[dict[str, object], ...]) -> JournalProof:
    connection = False
    acknowledgement = False
    ready = False
    live_boundary: int | None = None
    report = False
    readiness = False
    report_sequence = -1
    for sequence, event in enumerate(events, start=1):
        name = event["event"]
        if name == "WS_CONNECTION":
            connection = True
        elif name == "WS_ACK_PROGRESS" and _ack_complete(event):
            acknowledgement = True
        elif name == "WS_READY" and _ack_complete(event):
            ready = True
        elif name == "FINALIZED_5M" and event.get("evaluation_mode") == "LIVE_ACTIONABLE":
            boundary = event.get("boundary_open_time_ms")
            if isinstance(boundary, int) and not isinstance(boundary, bool):
                live_boundary = boundary
                report = False
                readiness = False
                report_sequence = -1
        elif (
            name == "BOUNDARY_REPORT"
            and live_boundary is not None
            and event.get("boundary_open_time_ms") == live_boundary
        ):
            report = True
            report_sequence = sequence
        elif (
            name == "READINESS"
            and report
            and sequence > report_sequence
            and event.get("data_ready") is True
        ):
            readiness = True
    return JournalProof(connection, acknowledgement, ready, live_boundary, report, readiness)


async def _monitor_journal(
    capture: JournalCaptureHandler,
    shutdown: asyncio.Event,
) -> tuple[JournalProof | None, str | None]:
    while not shutdown.is_set():
        entries, capture_error = capture.snapshot()
        if capture_error is not None:
            shutdown.set()
            return None, capture_error
        try:
            proof = _journal_proof(_decode_journal(entries))
        except S1HarnessError as exc:
            shutdown.set()
            return None, exc.failure_class
        if proof.complete:
            shutdown.set()
            return proof, None
        await asyncio.sleep(0.05)
    return None, None


def _set_production_paths(state: Path) -> None:
    production.THREE_SETUP_STATE_ROOT = state
    production.THREE_SETUP_EVIDENCE_STORE_PATH = state / "evidence.sqlite"
    production.THREE_SETUP_REGISTRY_ROOT = state / "registry"
    production.THREE_SETUP_CLOSED_BAR_STORE_PATH = state / "closed-bars.sqlite"


@dataclass(frozen=True)
class ApplicationObservation:
    application_error: str | None
    timed_out: bool
    cleanup_timed_out: bool
    monitor_error: str | None
    callback_failure_types: tuple[str, ...]
    nonrecoverable_market_ids: tuple[str, ...]


async def _run_application(
    *,
    state: Path,
    release_sha: str,
    timeout_seconds: float,
    public_client: HyperliquidPublicClient,
    webhook: NoNetworkWebhook,
    capture: JournalCaptureHandler,
    clock: Callable[[], datetime],
) -> ApplicationObservation:
    _set_production_paths(state)
    config = production.ThreeSetupProductionConfig(
        release_sha=release_sha,
        evidence_store_path=state / "evidence.sqlite",
        registry_root=state / "registry",
        closed_bar_store_path=state / "closed-bars.sqlite",
        cost_model=CostModel(
            version="s1-observer-only-rehearsal",
            fee_bps_per_side=Decimal("0"),
            slippage_bps_per_side=Decimal("0"),
            stress_slippage_bps_per_side=Decimal("2"),
        ),
        acknowledgement_timeout_seconds=30.0,
        notification_poll_seconds=1.0,
    )
    notification_adapter = WebhookDeliveryAdapter(
        client=webhook,
        config=WebhookConfig(url="https://example.invalid/trade-os-s1-no-network"),
    )
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=notification_adapter,
        public_client=public_client,
        clock=clock,
    )
    selected = application.bootstrap.runtime.selected_markets()
    if (
        len(selected) != 1
        or selected[0].identity.coin != "BTC"
        or selected[0].identity.market_id == ""
    ):
        application.bootstrap.close()
        application.bootstrap.data_authority.store.close()
        raise S1HarnessError(
            "normalized state is not the exact BTC-only S1 topology",
            failure_class="CHECKPOINT_IMPORT_FAILURE",
        )

    observer_logger = logging.Logger("trade_os.s1.observer_only", level=logging.INFO)
    observer_logger.propagate = False
    observer_logger.addHandler(capture)
    application.logger = observer_logger

    shutdown = asyncio.Event()
    application_task = asyncio.create_task(
        application.run(shutdown), name="s1-production-application"
    )
    monitor_task = asyncio.create_task(
        _monitor_journal(capture, shutdown), name="s1-production-journal-monitor"
    )
    application_error: str | None = None
    monitor_error: str | None = None
    timed_out = False
    cleanup_timed_out = False
    try:
        done, _ = await asyncio.wait(
            (application_task, monitor_task),
            timeout=timeout_seconds,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not done:
            timed_out = True
            shutdown.set()
        elif monitor_task in done:
            _, monitor_error = monitor_task.result()
            shutdown.set()

        try:
            await asyncio.wait_for(application_task, timeout=30.0)
        except TimeoutError:
            cleanup_timed_out = True
            application_task.cancel()
            await asyncio.gather(application_task, return_exceptions=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            application_error = type(exc).__name__
    finally:
        shutdown.set()
        if not monitor_task.done():
            monitor_task.cancel()
        await asyncio.gather(monitor_task, return_exceptions=True)

    callback_types = tuple(
        item.error_type for item in application.bootstrap.runtime.health.callback_failures
    )
    nonrecoverable = tuple(sorted(application.bootstrap.runtime.health.nonrecoverable_markets))
    return ApplicationObservation(
        application_error=application_error,
        timed_out=timed_out,
        cleanup_timed_out=cleanup_timed_out,
        monitor_error=monitor_error,
        callback_failure_types=callback_types,
        nonrecoverable_market_ids=nonrecoverable,
    )


def _persist_journal(
    path: Path,
    entries: tuple[JournalEntry, ...],
) -> tuple[tuple[dict[str, object], ...], str]:
    decoded = _decode_journal(entries)
    expected_records = tuple(
        {
            "schema": WITNESS_SCHEMA,
            "sequence": entry.sequence,
            "journal": journal,
        }
        for entry, journal in zip(entries, decoded, strict=True)
    )
    try:
        with path.open("wb") as handle:
            for record in expected_records:
                handle.write(canonical_json_bytes(record) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        raw = path.read_bytes()
        observed = tuple(json.loads(line) for line in raw.splitlines())
    except (OSError, json.JSONDecodeError) as exc:
        raise S1HarnessError(
            "journal witness persistence failed",
            failure_class="WITNESS_PERSISTENCE_FAILURE",
        ) from exc
    if observed != expected_records or len(raw.splitlines()) != len(expected_records):
        raise S1HarnessError(
            "journal witness round-trip identity mismatch",
            failure_class="WITNESS_PERSISTENCE_FAILURE",
        )
    return decoded, hashlib.sha256(raw).hexdigest()


def _provider_audit(
    observations: tuple[RequestObservation, ...],
    *,
    retained_last_open_ms: int,
) -> tuple[bool, int, tuple[str, ...]]:
    request_types = tuple(
        item.request_type if item.request_type is not None else "UNKNOWN"
        for item in observations
    )
    if any(item not in _ALLOWED_PROVIDER_TYPES for item in request_types):
        return False, 0, request_types
    five_minute_windows = [
        item
        for item in observations
        if item.request_type == "candleSnapshot" and item.interval == "5m"
    ]
    max_window_bars = 0
    for item in five_minute_windows:
        if item.start_ms is None or item.end_ms is None or item.end_ms < item.start_ms:
            return False, max_window_bars, request_types
        if item.start_ms <= retained_last_open_ms:
            return False, max_window_bars, request_types
        span = item.end_ms - item.start_ms + 1
        window_bars = (span + FIVE_MINUTES_MS - 1) // FIVE_MINUTES_MS
        max_window_bars = max(max_window_bars, window_bars)
    return True, max_window_bars, request_types


def _production_failure_events(events: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    hard = {"PRODUCTION_CHILD_EXIT_UNEXPECTED", "NOTIFICATION_FAILURE"}
    return tuple(str(event["event"]) for event in events if event["event"] in hard)


def _final_registry_state(state: Path) -> tuple[str | None, str | None]:
    registry = MarketRegistryManager(state / "registry", metadata_validator=lambda _: True)
    active = registry.active()
    if active is None or len(active.markets) != 1:
        return None, None
    return active.markets[0].identity.market_id, active.markets[0].lifecycle.value


def _write_result(path: Path, result: dict[str, object]) -> None:
    try:
        with path.open("wb") as handle:
            handle.write(canonical_json_bytes(result))
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise S1HarnessError(
            "result persistence failed",
            failure_class="WITNESS_PERSISTENCE_FAILURE",
        ) from exc


def run_rehearsal(
    *,
    repo_root: Path,
    expected_head: str,
    source_checkpoint: Path,
    attempt_root: Path,
    timeout_seconds: float,
    post_factory: Callable[[], HttpPost] | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, object]:
    """Run one exact, isolated, public/read-only S1 proof attempt."""

    if timeout_seconds <= 0:
        raise S1HarnessError(
            "timeout must be positive",
            failure_class="OBSERVER_CAPTURE_FAILURE",
        )
    release_sha, release_manifest_sha = bind_release_identity(repo_root, expected_head)
    imported = _import_checkpoint(source_checkpoint, attempt_root, clock=clock)

    default_client = HyperliquidPublicClient()
    delegate = post_factory() if post_factory is not None else default_client.post
    audit = AuditingRawPost(delegate)
    public_client = HyperliquidPublicClient(post=audit)
    webhook = NoNetworkWebhook()
    capture = JournalCaptureHandler()

    observation = asyncio.run(
        _run_application(
            state=imported.state,
            release_sha=release_sha,
            timeout_seconds=timeout_seconds,
            public_client=public_client,
            webhook=webhook,
            capture=capture,
            clock=clock,
        )
    )

    entries, capture_error = capture.snapshot()
    if capture_error is not None or observation.monitor_error is not None:
        failure = capture_error or observation.monitor_error
        raise S1HarnessError(
            f"production journal capture failed: {failure}",
            failure_class="OBSERVER_CAPTURE_FAILURE",
        )

    events, witness_sha = _persist_journal(attempt_root / "s1-session-witness.jsonl", entries)
    proof = _journal_proof(events)

    source_after = _raw_tree_manifest(imported.source)
    quarantine_after = _raw_tree_manifest(imported.quarantine)
    source_preserved = (
        source_after == imported.source_manifest
        and quarantine_after == imported.source_manifest
    )

    request_observations, audit_error = audit.snapshot()
    if audit_error is not None:
        failure_class = "PROVIDER_AUDIT_FAILURE"
        claim_result = "UNPROVEN"
        provider_audit_ok = False
        requested_5m_bars = 0
        request_types: tuple[str, ...] = ()
    else:
        provider_audit_ok, requested_5m_bars, request_types = _provider_audit(
            request_observations,
            retained_last_open_ms=imported.retained_last_open_ms,
        )
        failure_class = None
        claim_result = "UNPROVEN"

    production_failure_events = _production_failure_events(events)
    if not source_preserved:
        claim_result, failure_class = "UNPROVEN", "CHECKPOINT_QUARANTINE_FAILURE"
    elif audit_error is not None:
        claim_result, failure_class = "UNPROVEN", "PROVIDER_AUDIT_FAILURE"
    elif not provider_audit_ok:
        if any(item not in _ALLOWED_PROVIDER_TYPES for item in request_types):
            claim_result, failure_class = "FAIL", "UNEXPECTED_PROVIDER_REQUEST"
        else:
            claim_result, failure_class = "UNPROVEN", "CHECKPOINT_RESUME_VIOLATION"
    elif observation.cleanup_timed_out:
        claim_result, failure_class = "UNPROVEN", "INCONCLUSIVE_TIMEOUT"
    elif observation.timed_out:
        claim_result, failure_class = "UNPROVEN", "INCONCLUSIVE_TIMEOUT"
    elif (
        observation.application_error is not None
        or observation.callback_failure_types
        or production_failure_events
    ):
        claim_result, failure_class = "FAIL", "APPLICATION_FAILURE"
    elif observation.nonrecoverable_market_ids:
        claim_result, failure_class = "FAIL", "S1_CLAIM_NOT_SATISFIED"
    elif proof.complete:
        claim_result, failure_class = "PASS", None
    else:
        claim_result, failure_class = "FAIL", "S1_CLAIM_NOT_SATISFIED"

    final_market_id, final_lifecycle = _final_registry_state(imported.state)
    _, final_count, final_first, final_last = _retained_history_summary(
        imported.state / "closed-bars.sqlite"
    )
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "claim": CLAIM,
        "claim_result": claim_result,
        "failure_class": failure_class,
        "release_sha": release_sha,
        "release_manifest_sha256": release_manifest_sha,
        "source_checkpoint": str(imported.source),
        "attempt_root": str(attempt_root.resolve()),
        "source_checkpoint_preserved": source_preserved,
        "checkpoint_byte_manifest_sha256": imported.manifest_sha256,
        "checkpoint_json_sha256": imported.checkpoint_json_sha256,
        "quarantine_unopened_by_harness_sqlite": True,
        "retained_history": {
            "market_id": imported.market_id,
            "count": imported.retained_count,
            "first_open_ms": imported.retained_first_open_ms,
            "last_open_ms": imported.retained_last_open_ms,
        },
        "pre_run_catchup_bars": imported.pre_run_catchup_bars,
        "max_5m_request_window_bars": requested_5m_bars,
        "reran_2304_warmup": requested_5m_bars >= RETAINED_HISTORY_MIN_BARS,
        "public_read_only_only": True,
        "account_private_api": False,
        "wallet_signing": False,
        "exchange_write": False,
        "real_notification": False,
        "fake_notification_calls": webhook.calls,
        "http_post_raw_bytes_delegated": True,
        "provider_request_types": request_types,
        "provider_audit_error": audit_error,
        "journal": {
            "entry_count": len(entries),
            "witness_sha256": witness_sha,
            "connection_proven_pre_teardown": proof.connection,
            "acknowledgement_proven_pre_teardown": proof.acknowledgement,
            "ready_proven_pre_teardown": proof.ready,
            "live_boundary_open_ms": proof.live_boundary_open_ms,
            "boundary_report_proven": proof.boundary_report,
            "readiness_after_boundary_proven": proof.readiness_after_boundary,
        },
        "application_error": observation.application_error,
        "callback_failure_types": observation.callback_failure_types,
        "nonrecoverable_market_ids": observation.nonrecoverable_market_ids,
        "production_failure_events": production_failure_events,
        "timed_out": observation.timed_out,
        "cleanup_timed_out": observation.cleanup_timed_out,
        "final_registry_market_id": final_market_id,
        "final_lifecycle": final_lifecycle,
        "final_closed_5m": {
            "count": final_count,
            "first_open_ms": final_first,
            "last_open_ms": final_last,
        },
    }
    _write_result(attempt_root / "s1-result.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-public-s1-rehearsal", action="store_true")
    parser.add_argument("--claim", default="")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--source-checkpoint", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=1_800.0)
    return parser


def main(argv: tuple[str, ...] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.enable_public_s1_rehearsal or args.claim != CLAIM:
        raise S1HarnessError(
            "S1 public rehearsal is default-off and claim-bound",
            failure_class="AUTHORITY_GUARD_FAILURE",
        )
    result = run_rehearsal(
        repo_root=args.repo_root,
        expected_head=args.expected_head,
        source_checkpoint=args.source_checkpoint,
        attempt_root=args.attempt_root,
        timeout_seconds=args.timeout_seconds,
    )
    print("PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS")
    print(f"CLAIM_UNDER_TEST={CLAIM}")
    print(f"CLAIM_RESULT={result['claim_result']}")
    print(f"NEXT_PROMOTION_ALLOWED={'YES' if result['claim_result'] == 'PASS' else 'NO'}")
    print(f"RESULT_FILE={args.attempt_root / 's1-result.json'}")
    return 0 if result["claim_result"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except S1HarnessError as exc:
        print(f"S1_HARNESS_SAFE_STOP={exc.failure_class}")
        raise SystemExit(2) from None
