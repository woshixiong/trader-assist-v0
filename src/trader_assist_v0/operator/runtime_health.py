"""Bounded read-only consumer of the disposable E4 health projection."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .contracts import RUNTIME_HEALTH_FILENAME, RuntimeHealthSnapshot, RuntimeHealthView

MAX_SNAPSHOT_BYTES = 4096


def read_runtime_health(evidence_path: Path, *, now_ms: int) -> RuntimeHealthView:
    """Fresh-read on every use; no cache, transport or recovery responsibility."""
    try:
        with evidence_path.with_name(RUNTIME_HEALTH_FILENAME).open("rb") as source:
            raw = source.read(MAX_SNAPSHOT_BYTES + 1)
    except OSError:
        return RuntimeHealthView(None, ("RUNTIME_HEALTH_UNAVAILABLE",))
    if len(raw) > MAX_SNAPSHOT_BYTES:
        return RuntimeHealthView(None, ("RUNTIME_HEALTH_INVALID",))
    try:
        snapshot = RuntimeHealthSnapshot.model_validate_json(raw)
    except ValidationError:
        return RuntimeHealthView(None, ("RUNTIME_HEALTH_INVALID",))
    reasons = []
    age = now_ms - snapshot.observed_ms
    maximum_age = min(180_000, max(15_000, 3 * snapshot.publication_interval_ms))
    if age < 0:
        reasons.append("RUNTIME_HEALTH_FUTURE")
    elif age > maximum_age:
        reasons.append("RUNTIME_HEALTH_STALE")
    if not snapshot.running:
        reasons.append("RUNTIME_NOT_RUNNING")
    if not snapshot.data_ready:
        reasons.append("RUNTIME_DATA_NOT_READY")
    if snapshot.stream_health != "HEALTHY":
        reasons.append("RUNTIME_STREAM_NOT_HEALTHY")
    if snapshot.continuity_requirements_remaining != 0:
        reasons.append("RUNTIME_CONTINUITY_PENDING")
    if snapshot.warmup_readiness != "READY":
        reasons.append("RUNTIME_WARMUP_NOT_READY")
    if snapshot.storage_failures != 0:
        reasons.append("RUNTIME_STORAGE_FAILURE")
    return RuntimeHealthView(snapshot, tuple(reasons))
