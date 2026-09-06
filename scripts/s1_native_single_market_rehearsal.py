#!/usr/bin/env python3
"""Repository-owned, public/read-only S1 BTC rehearsal harness.

This harness exists only to prove the frozen S1_NATIVE_SINGLE_MARKET claim.  It
never owns trading/application semantics.  It snapshots the retained local
checkpoint into a new isolated attempt root, runs the real Three Setup public
composition, and persists pre-teardown WebSocket evidence so graceful shutdown
cannot erase the proof surface.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import os
import sqlite3
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.multi_asset_shadow import production
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    INFO_URL,
    HttpPost,
    HyperliquidPublicClient,
)
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookResponse,
)
from trader_assist_v0.multi_asset_shadow.planning import CostModel
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode
from trader_assist_v0.operations.backup_recovery import _sqlite_snapshot

CLAIM = "S1_NATIVE_SINGLE_MARKET"
RESULT_SCHEMA = "trader-assist-v0/s1-native-single-market-rehearsal/v1"
_WITNESS_SCHEMA = "trader-assist-v0/s1-session-witness/v1"
_ALLOWED_PROVIDER_TYPES = frozenset({"candleSnapshot", "l2Book"})
_REQUIRED_SQLITE = ("evidence.sqlite", "closed-bars.sqlite")
_REGISTRY_DIR = "registry"


class S1HarnessError(RuntimeError):
    """The verification harness cannot make an authoritative S1 claim."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _logical_sqlite_hash(path: Path) -> str:
    """Hash logical SQLite contents without relying on main/WAL file bytes."""
    digest = hashlib.sha256()
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            for line in connection.iterdump():
                digest.update(line.encode("utf-8"))
                digest.update(b"\n")
    except sqlite3.Error as exc:
        raise S1HarnessError(f"SQLite logical read failed for {path.name}") from exc
    return digest.hexdigest()


def _tree_manifest(root: Path) -> tuple[tuple[str, str], ...]:
    if not root.is_dir() or root.is_symlink():
        raise S1HarnessError("registry checkpoint must be a real directory")
    files: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise S1HarnessError("registry checkpoint contains a symlink or special file")
        if stat.S_ISREG(mode):
            files.append((path.relative_to(root).as_posix(), _sha256(path)))
    return tuple(files)


def _copy_registry(source: Path, destination: Path) -> None:
    before = _tree_manifest(source)
    destination.mkdir(parents=True, exist_ok=False)
    for relative, _ in before:
        src = source / relative
        dst = destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
    if _tree_manifest(destination) != before:
        raise S1HarnessError("registry snapshot identity mismatch")


@dataclass(frozen=True)
class CheckpointSnapshot:
    source_checkpoint: Path
    attempt_root: Path
    source_preserved: bool
    sqlite_logical_hashes: dict[str, str]
    registry_manifest_hash: str


def snapshot_checkpoint(source_checkpoint: Path, attempt_root: Path) -> CheckpointSnapshot:
    """Create one isolated snapshot using owning-component durability semantics."""
    source = source_checkpoint.resolve()
    attempt = attempt_root.resolve()
    if source == attempt or source in attempt.parents or attempt in source.parents:
        raise S1HarnessError("source checkpoint and attempt root must be disjoint")
    if not source.is_dir() or source.is_symlink():
        raise S1HarnessError("source checkpoint is unavailable")
    if attempt.exists():
        raise S1HarnessError("attempt root already exists")

    db_before: dict[str, str] = {}
    for name in _REQUIRED_SQLITE:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise S1HarnessError(f"required checkpoint database is missing: {name}")
        db_before[name] = _logical_sqlite_hash(path)
    registry_source = source / _REGISTRY_DIR
    registry_before = _tree_manifest(registry_source)

    attempt.mkdir(parents=True, exist_ok=False)
    try:
        for name in _REQUIRED_SQLITE:
            _sqlite_snapshot(source / name, attempt / name)
            if _logical_sqlite_hash(attempt / name) != db_before[name]:
                raise S1HarnessError(f"SQLite snapshot logical identity mismatch: {name}")
        _copy_registry(registry_source, attempt / _REGISTRY_DIR)

        db_after = {name: _logical_sqlite_hash(source / name) for name in _REQUIRED_SQLITE}
        registry_after = _tree_manifest(registry_source)
        preserved = db_after == db_before and registry_after == registry_before
        if not preserved:
            raise S1HarnessError("source checkpoint logical state changed during snapshot")
    except Exception:
        # The source checkpoint is never removed.  A failed destination is kept
        # as forensic evidence rather than recursively deleted by the harness.
        raise

    registry_digest = hashlib.sha256()
    for relative, digest in registry_before:
        registry_digest.update(relative.encode("utf-8"))
        registry_digest.update(b"\0")
        registry_digest.update(digest.encode("ascii"))
        registry_digest.update(b"\n")
    return CheckpointSnapshot(
        source_checkpoint=source,
        attempt_root=attempt,
        source_preserved=True,
        sqlite_logical_hashes=db_before,
        registry_manifest_hash=registry_digest.hexdigest(),
    )


@dataclass
class SessionWitness:
    """Monotonic teardown-surviving observation of production session events."""

    path: Path
    events: list[dict[str, object]] = field(default_factory=list)
    _sequence: int = 0

    def record(self, event: str, fields: dict[str, object]) -> None:
        self._sequence += 1
        payload: dict[str, object] = {
            "schema": _WITNESS_SCHEMA,
            "sequence": self._sequence,
            "event": event,
            "fields": fields,
        }
        encoded = canonical_json_bytes(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(encoded + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.events.append(payload)

    @property
    def connection_proven(self) -> bool:
        return any(item["event"] == "CONNECTION" for item in self.events)

    @property
    def acknowledgement_proven(self) -> bool:
        for item in self.events:
            if item["event"] != "ACK_PROGRESS":
                continue
            fields = item["fields"]
            if not isinstance(fields, dict):
                continue
            acknowledged = fields.get("acknowledged")
            expected = fields.get("expected")
            if (
                isinstance(acknowledged, int)
                and isinstance(expected, int)
                and expected > 0
                and acknowledged >= expected
            ):
                return True
        return False

    @property
    def ready_proven(self) -> bool:
        for item in self.events:
            if item["event"] != "READY":
                continue
            fields = item["fields"]
            if not isinstance(fields, dict):
                continue
            acknowledged = fields.get("acknowledged")
            expected = fields.get("expected")
            if (
                isinstance(acknowledged, int)
                and isinstance(expected, int)
                and expected > 0
                and acknowledged >= expected
            ):
                return True
        return False


@dataclass
class CountingRawPost:
    """Observe outgoing public request types while preserving the raw-bytes seam."""

    delegate: HttpPost
    request_types: list[str] = field(default_factory=list)

    def __call__(self, url: str, body: bytes, timeout_seconds: float) -> bytes:
        if url != INFO_URL:
            raise S1HarnessError("provider request escaped the public Hyperliquid /info endpoint")
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise S1HarnessError("provider request body is not valid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
            raise S1HarnessError("provider request type is unavailable")
        request_type = payload["type"]
        self.request_types.append(request_type)
        raw = self.delegate(url, body, timeout_seconds)
        if not isinstance(raw, bytes):
            raise S1HarnessError("HttpPost contract requires raw bytes")
        return raw


@dataclass
class NoNetworkWebhook:
    """Deterministic notification sink; never performs external I/O."""

    calls: int = 0

    def post(self, **_: object) -> WebhookResponse:
        self.calls += 1
        return WebhookResponse(204)


@dataclass(frozen=True)
class ClaimInputs:
    application_error: str | None
    harness_error: str | None
    timed_out: bool
    source_preserved: bool
    connection_proven: bool
    acknowledgement_proven: bool
    ready_proven: bool
    live_actionable_finalized_count: int
    final_lifecycle: str | None
    provider_request_types: tuple[str, ...]


def classify_claim(inputs: ClaimInputs) -> tuple[str, str | None]:
    """Separate application failure from invalid/incomplete harness proof."""
    if inputs.harness_error is not None or inputs.timed_out or not inputs.source_preserved:
        return "UNPROVEN", "WRAPPER_OR_HARNESS_FAILURE"
    if inputs.application_error is not None:
        return "FAIL", "APPLICATION_FAILURE"
    if any(item not in _ALLOWED_PROVIDER_TYPES for item in inputs.provider_request_types):
        return "FAIL", "UNEXPECTED_PROVIDER_REQUEST"
    if (
        inputs.connection_proven
        and inputs.acknowledgement_proven
        and inputs.ready_proven
        and inputs.live_actionable_finalized_count >= 1
        and inputs.final_lifecycle == "ACTIVE"
    ):
        return "PASS", None
    return "FAIL", "S1_CLAIM_NOT_SATISFIED"


def _closed_bar_summary(path: Path) -> dict[str, int | None]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            row = connection.execute(
                "SELECT COUNT(*), MIN(open_time_ms), MAX(open_time_ms) "
                "FROM closed_bars WHERE interval='5m'"
            ).fetchone()
    except sqlite3.Error as exc:
        raise S1HarnessError("closed-bar result inspection failed") from exc
    assert row is not None
    return {"count": int(row[0]), "min_open_ms": row[1], "max_open_ms": row[2]}


def _set_attempt_production_paths(attempt_root: Path) -> None:
    """Process-local path remap only; production source files remain unchanged."""
    production.THREE_SETUP_STATE_ROOT = attempt_root
    production.THREE_SETUP_EVIDENCE_STORE_PATH = attempt_root / "evidence.sqlite"
    production.THREE_SETUP_REGISTRY_ROOT = attempt_root / "registry"
    production.THREE_SETUP_CLOSED_BAR_STORE_PATH = attempt_root / "closed-bars.sqlite"


def _validate_source_sha(value: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise S1HarnessError("source SHA must be exactly 40 lowercase hexadecimal characters")
    return value


async def _run_application(
    *,
    attempt_root: Path,
    source_sha: str,
    timeout_seconds: float,
    witness: SessionWitness,
    post: CountingRawPost,
    webhook: NoNetworkWebhook,
) -> dict[str, object]:
    _set_attempt_production_paths(attempt_root)
    config = production.ThreeSetupProductionConfig(
        release_sha=source_sha,
        evidence_store_path=attempt_root / "evidence.sqlite",
        registry_root=attempt_root / "registry",
        closed_bar_store_path=attempt_root / "closed-bars.sqlite",
        cost_model=CostModel(
            version="s1-diagnostic-rehearsal",
            fee_bps_per_side=Decimal("0"),
            slippage_bps_per_side=Decimal("0"),
            stress_slippage_bps_per_side=Decimal("2"),
        ),
        acknowledgement_timeout_seconds=30.0,
        notification_poll_seconds=1.0,
    )
    public_client = HyperliquidPublicClient(post=post)
    notification_adapter = WebhookDeliveryAdapter(
        client=webhook,
        config=WebhookConfig(url="https://example.invalid/trade-os-s1-no-network"),
    )
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=notification_adapter,
        public_client=public_client,
    )
    runtime = application.bootstrap.runtime
    selected = runtime.selected_markets()
    if len(selected) != 1 or selected[0].identity.coin != "BTC":
        application.bootstrap.close()
        application.bootstrap.data_authority.store.close()
        raise S1HarnessError("retained checkpoint is not the exact BTC-only S1 topology")

    shutdown = asyncio.Event()
    lifecycle_sequence: list[str] = [selected[0].lifecycle.value]
    live_actionable_finalized_count = 0
    original_session = runtime.on_session_event
    original_finalized = runtime.on_finalized_5m
    if original_finalized is None:
        application.bootstrap.close()
        application.bootstrap.data_authority.store.close()
        raise S1HarnessError("production finalized-boundary callback is unavailable")

    def session_observer(event: str, fields: dict[str, object]) -> None:
        witness.record(event, fields)
        if original_session is not None:
            original_session(event, fields)

    async def finalized_observer(bar: Any, mode: BoundaryMode) -> object | None:
        nonlocal live_actionable_finalized_count
        result = original_finalized(bar, mode)
        if inspect.isawaitable(result):
            result = await result
        active = application.bootstrap.registry.active()
        lifecycle: str | None = None
        if active is not None and len(active.markets) == 1:
            lifecycle = active.markets[0].lifecycle.value
            if not lifecycle_sequence or lifecycle_sequence[-1] != lifecycle:
                lifecycle_sequence.append(lifecycle)
        witness.record(
            "HARNESS_FINALIZED_OBSERVATION",
            {
                "evaluation_mode": mode.value,
                "lifecycle": lifecycle,
                "open_time_ms": int(bar.open_time_ms),
            },
        )
        if mode is BoundaryMode.LIVE_ACTIONABLE:
            live_actionable_finalized_count += 1
            shutdown.set()
        return result

    runtime.on_session_event = session_observer
    runtime.on_finalized_5m = finalized_observer

    application_error: str | None = None
    timed_out = False
    try:
        await asyncio.wait_for(application.run(shutdown), timeout=timeout_seconds)
    except TimeoutError:
        timed_out = True
        shutdown.set()
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # exact type is evidence; raw message may contain provider detail
        application_error = type(exc).__name__

    final_lifecycle = lifecycle_sequence[-1] if lifecycle_sequence else None
    return {
        "application_error": application_error,
        "timed_out": timed_out,
        "lifecycle_sequence": lifecycle_sequence,
        "final_lifecycle": final_lifecycle,
        "live_actionable_finalized_count": live_actionable_finalized_count,
    }


def _write_result(path: Path, result: dict[str, object]) -> None:
    path.write_bytes(canonical_json_bytes(result))


def run_rehearsal(
    *,
    source_checkpoint: Path,
    attempt_root: Path,
    source_sha: str,
    timeout_seconds: float,
    post_factory: Callable[[], HttpPost] | None = None,
) -> dict[str, object]:
    """Execute one isolated S1 proof attempt and return its canonical result packet."""
    source_sha = _validate_source_sha(source_sha)
    if timeout_seconds <= 0:
        raise S1HarnessError("timeout must be positive")
    snapshot = snapshot_checkpoint(source_checkpoint, attempt_root)
    witness = SessionWitness(attempt_root / "s1-session-witness.jsonl")
    default_client = HyperliquidPublicClient()
    delegate = post_factory() if post_factory is not None else default_client.post
    post = CountingRawPost(delegate)
    webhook = NoNetworkWebhook()

    harness_error: str | None = None
    application_observation: dict[str, object] = {
        "application_error": None,
        "timed_out": False,
        "lifecycle_sequence": [],
        "final_lifecycle": None,
        "live_actionable_finalized_count": 0,
    }
    try:
        application_observation = asyncio.run(
            _run_application(
                attempt_root=attempt_root,
                source_sha=source_sha,
                timeout_seconds=timeout_seconds,
                witness=witness,
                post=post,
                webhook=webhook,
            )
        )
    except S1HarnessError as exc:
        harness_error = type(exc).__name__

    live_actionable_finalized_count = application_observation[
        "live_actionable_finalized_count"
    ]
    if not isinstance(live_actionable_finalized_count, int) or isinstance(
        live_actionable_finalized_count, bool
    ):
        raise S1HarnessError("live-actionable finalized count is not an integer")

    inputs = ClaimInputs(
        application_error=(
            str(application_observation["application_error"])
            if application_observation["application_error"] is not None
            else None
        ),
        harness_error=harness_error,
        timed_out=bool(application_observation["timed_out"]),
        source_preserved=snapshot.source_preserved,
        connection_proven=witness.connection_proven,
        acknowledgement_proven=witness.acknowledgement_proven,
        ready_proven=witness.ready_proven,
        live_actionable_finalized_count=live_actionable_finalized_count,
        final_lifecycle=(
            str(application_observation["final_lifecycle"])
            if application_observation["final_lifecycle"] is not None
            else None
        ),
        provider_request_types=tuple(post.request_types),
    )
    claim_result, failure_class = classify_claim(inputs)
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "claim": CLAIM,
        "claim_result": claim_result,
        "failure_class": failure_class,
        "source_sha": source_sha,
        "source_checkpoint": str(snapshot.source_checkpoint),
        "attempt_root": str(snapshot.attempt_root),
        "source_checkpoint_preserved": snapshot.source_preserved,
        "reran_2304_warmup": False,
        "public_read_only_only": True,
        "account_private_api": False,
        "wallet_signing": False,
        "exchange_write": False,
        "real_notification": False,
        "fake_notification_calls": webhook.calls,
        "http_post_returns_raw_bytes": True,
        "provider_request_types": post.request_types,
        "metadata_requests_zero": not any(
            item in {"meta", "metaAndAssetCtxs", "allPerpMetas", "perpDexs"}
            for item in post.request_types
        ),
        "ws": {
            "connection_proven_pre_teardown": witness.connection_proven,
            "acknowledgement_proven_pre_teardown": witness.acknowledgement_proven,
            "ready_proven_pre_teardown": witness.ready_proven,
            "witness_event_count": len(witness.events),
            "witness_path": str(witness.path),
        },
        "application_error": application_observation["application_error"],
        "harness_error": harness_error,
        "timed_out": application_observation["timed_out"],
        "lifecycle_sequence": application_observation["lifecycle_sequence"],
        "final_lifecycle": application_observation["final_lifecycle"],
        "live_actionable_finalized_count": application_observation[
            "live_actionable_finalized_count"
        ],
        "final_closed_5m": _closed_bar_summary(attempt_root / "closed-bars.sqlite"),
        "checkpoint_identity": {
            "sqlite_logical_hashes": snapshot.sqlite_logical_hashes,
            "registry_manifest_hash": snapshot.registry_manifest_hash,
        },
    }
    _write_result(attempt_root / "s1-result.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-public-s1-rehearsal", action="store_true")
    parser.add_argument("--claim", default="")
    parser.add_argument("--source-checkpoint", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=420.0)
    return parser


def main(argv: tuple[str, ...] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.enable_public_s1_rehearsal or args.claim != CLAIM:
        raise S1HarnessError("S1 public rehearsal is default-off and claim-bound")
    result = run_rehearsal(
        source_checkpoint=args.source_checkpoint,
        attempt_root=args.attempt_root,
        source_sha=args.source_sha,
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
    except (OSError, ValueError, S1HarnessError) as exc:
        print(f"S1_HARNESS_SAFE_STOP={type(exc).__name__}")
        raise SystemExit(2) from None
