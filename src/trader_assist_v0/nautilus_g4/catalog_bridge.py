# mypy: disable-error-code="import-not-found"
"""Rebuildable Nautilus catalog binding over immutable accepted E4 evidence."""

from __future__ import annotations

import hmac
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.storage import EvidenceStore

if TYPE_CHECKING:
    class ParquetDataCatalog:
        def __init__(self, base_path: str, *args: object, **kwargs: object) -> None: ...
_BINDING_DOMAIN = b"trader-assist-v0/nautilus-g4/catalog-binding/v1\0"


class DerivedCatalogBinding(BaseModel):
    """Identity of a disposable cache; source E4 artifacts remain authoritative."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_e4_manifest_hash: Sha256Hex
    source_pit_snapshot_hash: Sha256Hex
    source_artifact_hashes: dict[str, Sha256Hex]
    source_artifact_set_hash: Sha256Hex
    cache_root: str
    rebuildable: bool = True
    authoritative_market_truth: bool = False
    binding_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"binding_hash"})

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        if not self.rebuildable or self.authoritative_market_truth:
            raise ValueError("G4 catalog must remain a rebuildable non-authoritative cache")
        ordered = dict(sorted(self.source_artifact_hashes.items()))
        if ordered != self.source_artifact_hashes:
            raise ValueError("source artifact hashes must be sorted")
        expected_set = sha256_hex(canonical_json_bytes(ordered))
        if not hmac.compare_digest(expected_set, self.source_artifact_set_hash):
            raise ValueError("source artifact set hash mismatch")
        expected = sha256_hex(_BINDING_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(expected, self.binding_hash):
            raise ValueError("binding_hash mismatch")
        return self


def bind_e4_source(
    *,
    evidence_root: Path,
    cache_root: Path,
    expected_manifest_hash: str,
) -> DerivedCatalogBinding:
    """Bind a cache identity without modifying any accepted E4 source file."""
    store = EvidenceStore(evidence_root)
    manifest = store.load_manifest()
    if not hmac.compare_digest(manifest.manifest_hash, expected_manifest_hash):
        raise ValueError("E4 source manifest does not match expected authority")
    snapshot = store.load_snapshot()
    if manifest.pit_snapshot_hash != snapshot.snapshot_hash:
        raise ValueError("E4 manifest/PIT snapshot identity conflict")
    hashes = dict(sorted(store.artifact_hashes().items()))
    source_set_hash = sha256_hex(canonical_json_bytes(hashes))
    payload: dict[str, Any] = {
        "source_e4_manifest_hash": manifest.manifest_hash,
        "source_pit_snapshot_hash": snapshot.snapshot_hash,
        "source_artifact_hashes": hashes,
        "source_artifact_set_hash": source_set_hash,
        "cache_root": str(cache_root),
        "rebuildable": True,
        "authoritative_market_truth": False,
    }
    digest = sha256_hex(_BINDING_DOMAIN + canonical_json_bytes(payload))
    return DerivedCatalogBinding.model_validate({**payload, "binding_hash": digest})


def build_empty_provider_catalog(binding: DerivedCatalogBinding) -> ParquetDataCatalog:
    """Construct the provider-native catalog owner for a disposable derived cache.

    Data conversion into Nautilus objects is intentionally a separate deterministic
    translation step; this function never turns the cache into source authority.
    """
    if not binding.rebuildable or binding.authoritative_market_truth:
        raise ValueError("invalid derived-catalog authority")
    from nautilus_trader.persistence import ParquetDataCatalog as RuntimeParquetDataCatalog

    Path(binding.cache_root).mkdir(parents=True, exist_ok=True)
    return RuntimeParquetDataCatalog(binding.cache_root)
