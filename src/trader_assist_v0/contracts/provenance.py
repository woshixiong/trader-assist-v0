from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .common import Sha256Hex, StrictModel, UTCDateTime


class SeedDispositionV0(StrEnum):
    SEED_NOT_IMPORTED = "SEED_NOT_IMPORTED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    REJECTED_FOR_V0_00 = "REJECTED_FOR_V0_00"
    IMPORTED_BEHIND_CONTRACT = "IMPORTED_BEHIND_CONTRACT"


class SeedProvenanceEntryV0(StrictModel):
    source_archive_sha256: Sha256Hex
    source_path: str = Field(min_length=1, max_length=600)
    source_file_sha256: Sha256Hex
    disposition: SeedDispositionV0
    retained_concepts: tuple[str, ...]
    rejected_behaviors: tuple[str, ...]
    target_paths: tuple[str, ...] = ()
    reviewed_at: UTCDateTime
    rationale: str = Field(min_length=1, max_length=3000)
