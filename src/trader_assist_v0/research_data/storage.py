"""Native catalog composition plus a bounded immutable evidence sidecar."""

from pathlib import Path
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .admission import (
    AdmissionObservation,
    ExternalReferenceAdmission,
    ExternalReferenceLedger,
    _AdmissionMechanics,
)
from .contracts import BoundRecord


class EvidenceSidecar(BoundRecord):
    dataset_hash: str
    mapping_hash: str
    capability_hashes: tuple[str, ...]
    policy_hash: str
    observations: tuple[AdmissionObservation, ...]
    source_bytes_hex: tuple[str, ...]
    raw_semantics: str
    catalog_files: tuple[tuple[str, str], ...]


class ReferenceDatasetStore:
    def __init__(self, root: Path, *, catalog: Any = None, max_bytes: int = 4_000_000) -> None:
        if not 0 < max_bytes <= 16_000_000:
            raise ValueError("invalid bounded evidence limit")
        self.root = root.resolve()
        self.catalog = catalog
        self.max_bytes = max_bytes

    def write_native(
        self, datatype: str, records: list[Any], admission: ExternalReferenceAdmission
    ) -> str:
        admission.dataset.require_access("PIPELINE_CORRECTNESS_ONLY", admission.satisfied)
        if not records or len(records) > admission.policy.max_observations:
            raise ValueError("bounded native batch required")
        methods = {
            "BBO": "write_quote_ticks",
            "TRADE": "write_trade_ticks",
            "BAR_1M": "write_bars",
            "BAR_5M": "write_bars",
            "MARK": "write_mark_price_updates",
            "INDEX": "write_index_price_updates",
            "DEPTH10": "write_order_book_depths",
            "L2": "write_order_book_deltas",
        }
        if datatype not in methods or self.catalog is None:
            raise ValueError("native catalog projection unavailable; retain bounded sidecar")
        # The native catalog owns Parquet serialization; no custom-data schema is invented.
        return str(getattr(self.catalog, methods[datatype])(records))

    def write(
        self,
        ledger: ExternalReferenceLedger,
        *,
        source_bytes: tuple[bytes, ...] = (),
        raw_semantics: str = "NOT_EXPOSED: normalized native callbacks",
        catalog_files: tuple[Path, ...] = (),
    ) -> tuple[Path, str]:
        admission = ledger.admission
        admission.dataset.require_access("PIPELINE_CORRECTNESS_ONLY", admission.satisfied)
        if sum(map(len, source_bytes)) > self.max_bytes:
            raise ValueError("raw evidence exceeds bound")
        # Recompute, rather than trusting mutable caller-owned ledger observations.
        check = ExternalReferenceLedger(admission)
        for observed in ledger.observations:
            if check.observe(observed.event, evaluated_at_ns=observed.evaluated_at_ns) != observed:
                raise ValueError("admission order/quality mismatch")
        bound_files: list[tuple[str, str]] = []
        for path in catalog_files:
            resolved = path.resolve()
            relative = resolved.relative_to(self.root)
            if resolved.stat().st_size > self.max_bytes:
                raise ValueError("catalog evidence exceeds bounded verification limit")
            bound_files.append((str(relative), sha256_hex(resolved.read_bytes())))
        sidecar = EvidenceSidecar.create(
            version="1",
            dataset_hash=admission.dataset.record_hash,
            mapping_hash=admission.resolver.snapshot.record_hash,
            capability_hashes=tuple(c.record_hash for c in admission.capabilities),
            policy_hash=admission.policy.record_hash,
            observations=tuple(ledger.observations),
            source_bytes_hex=tuple(b.hex() for b in source_bytes),
            raw_semantics=raw_semantics,
            catalog_files=tuple(bound_files),
        )
        encoded = canonical_json_bytes(sidecar.model_dump(mode="json"))
        if len(encoded) > self.max_bytes:
            raise ValueError("sidecar exceeds bound")
        path = self.root / f"{sidecar.record_hash}.reference.json"
        with path.open("xb") as handle:
            handle.write(encoded)
        return path, sha256_hex(encoded)


class ReferenceReplayReader:
    def __init__(self, store: ReferenceDatasetStore, admission: ExternalReferenceAdmission) -> None:
        self.store = store
        self.admission = admission

    def read(self, path: Path, checksum: str) -> tuple[AdmissionObservation, ...]:
        admission = self.admission
        # Rights/lifecycle checked before opening any evidence, including sealed files.
        admission.dataset.require_access("PIPELINE_CORRECTNESS_ONLY", admission.satisfied)
        return _read_verified(self.store, admission, path, checksum)


def _read_verified(
    store: ReferenceDatasetStore, admission: _AdmissionMechanics, path: Path, checksum: str
) -> tuple[AdmissionObservation, ...]:
    """Shared bounded replay; callers must first pass their concrete authority guard."""
    admission._require_access()
    path = path.resolve()
    path.relative_to(store.root)
    with path.open("rb") as handle:
        raw = handle.read(store.max_bytes + 1)
    if len(raw) > store.max_bytes or sha256_hex(raw) != checksum:
        raise ValueError("sidecar size/checksum mismatch")
    sidecar = EvidenceSidecar.model_validate_json(raw)
    if (
        sidecar.dataset_hash != admission.dataset.record_hash
        or sidecar.mapping_hash != admission.resolver.snapshot.record_hash
        or sidecar.policy_hash != admission.policy.record_hash
        or sidecar.capability_hashes != tuple(c.record_hash for c in admission.capabilities)
    ):
        raise ValueError("replay evidence binding mismatch")
    for relative, digest in sidecar.catalog_files:
        file = (store.root / relative).resolve()
        file.relative_to(store.root)
        with file.open("rb") as handle:
            raw_file = handle.read(store.max_bytes + 1)
        if len(raw_file) > store.max_bytes or sha256_hex(raw_file) != digest:
            raise ValueError("catalog binding checksum mismatch")
    for data in sidecar.source_bytes_hex:
        bytes.fromhex(data)
    ledger = ExternalReferenceLedger(admission)
    for observation in sidecar.observations:
        if (
            ledger.observe(observation.event, evaluated_at_ns=observation.evaluated_at_ns)
            != observation
        ):
            raise ValueError("non-deterministic/tampered admission replay")
    # Validate complete evidence before returning any observation.
    return tuple(ledger.observations)
