"""Bounded observations/admission for the native archive, never a storage owner.

Retain all source and catalog files. Stop capture rather than evict unreviewed
data. Sizes/mtime are writer progress evidence only, never typed integrity or
market freshness. The native writer alone flushes, seals and promotes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_ARCHIVE_BYTES = 8 * 1024**3
DEFAULT_CAPTURE_SECONDS = 900


@dataclass(frozen=True)
class ArchiveObservation:
    total_bytes: int
    stage_bytes: int
    stage_files: int
    newest_stage_ns: int

    def evidence(self, *, now_ns: int) -> dict[str, object]:
        recent = self.stage_files > 0 and 0 <= now_ns - self.newest_stage_ns <= 15_000_000_000
        return {
            "total_bytes": self.total_bytes,
            "stage_bytes": self.stage_bytes,
            "stage_files": self.stage_files,
            "writer": "STAGING_ACTIVITY_OBSERVED" if recent else "UNKNOWN_OR_QUIET",
            "writer_integrity": "UNVERIFIED_UNTIL_NATIVE_CLOSE_AND_TYPED_READBACK",
            "catalog": "CURRENT_RUN_PENDING_CLOSE",
            "retention": "RETAIN_ALL_STOP_AT_BUDGET_NO_AUTOMATIC_DELETION",
        }


def observe_archive(root: Path, stage: Path | None = None) -> ArchiveObservation:
    if root.is_symlink():
        raise RuntimeError("ARCHIVE_SYMLINK_NOT_SUPPORTED")
    total = staged = files = newest = 0
    for path in root.rglob("*"):
        # Never follow an external archive tree or let its size escape admission.
        if path.is_symlink():
            raise RuntimeError("ARCHIVE_SYMLINK_NOT_SUPPORTED")
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue  # Native sealing renames a partial while it is observed.
        if not path.is_file():
            continue
        total += stat.st_size
        if stage is not None and path.is_relative_to(stage) and ".feather" in path.name:
            staged += stat.st_size
            files += 1
            newest = max(newest, stat.st_mtime_ns)
    return ArchiveObservation(total, staged, files, newest)


def require_archive_capacity(
    observation: ArchiveObservation, *, max_bytes: int, free_bytes: int, minimum_free_bytes: int
) -> None:
    if max_bytes <= 0 or minimum_free_bytes <= 0:
        raise ValueError("archive limits must be positive")
    if observation.total_bytes >= max_bytes:
        raise RuntimeError("ARCHIVE_BUDGET_EXHAUSTED_SOURCES_RETAINED")
    if free_bytes < minimum_free_bytes:
        raise RuntimeError("DISK_LOW")
