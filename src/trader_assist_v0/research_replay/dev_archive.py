"""Synthetic-only Binance daily DEV composition on existing R2B/DEV/sidecar owners.

No real Binance market payload is authorized here. No network client is supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.research_data.admission import ExternalReferenceLedger
from trader_assist_v0.research_data.binance_archive import (
    MAX_ZIP_BYTES,
    ArchiveObject,
    ChecksumReceipt,
    HttpResponse,
    checked_http_response,
    frozen_archive_objects,
    parse_verified_daily_zip,
    require_frozen_object,
    require_receipt,
)
from trader_assist_v0.research_data.contracts import (
    REQUIRED_DATASET_METADATA,
    BarPayload,
    DatasetManifest,
    ExternalReferenceEvent,
    IntendedUseEligibility,
    SourceMode,
    SourceRightsProvenance,
    TimestampProvenance,
)
from trader_assist_v0.research_data.storage import EvidenceSidecar
from trader_assist_v0.research_inventory.builder import (
    _binding,
    build_inventory_manifest,
    validate_inventory_manifest,
)
from trader_assist_v0.research_inventory.contracts import (
    AllocationItem,
    DatasetInventoryManifest,
    InventoryAllocationSpec,
    InventoryRole,
    InventoryState,
)

from .dev_evidence import DevExternalAdmission
from .dev_lifecycle import DevVisibilityPolicy

G0_STRATEGY = "FL-MA-PRICE-ACTION-v0.1"
G0_QUESTION = (
    "Does frozen Three Setup Champion show a coherent after-cost mechanism "
    "against frozen simple baselines on external R3 DEV?"
)
MAX_SIDECAR_BYTES = 4_000_000
ENVELOPE_BYTES = 4096 + 288 * 8192


@dataclass(frozen=True, slots=True)
class MetadataIdentity:
    """Intended allocation is metadata, never an operative R2B role."""

    object: ArchiveObject
    intended_role: str
    operative_role: str
    receipt: ChecksumReceipt | None


@dataclass(frozen=True, slots=True)
class PreparedDailySidecar:
    path: Path
    checksum: str
    record_hash: str
    dataset_hash: str
    observations: int
    encoded_bytes: int


def metadata_ledger(
    receipts: tuple[ChecksumReceipt, ...] = (),
) -> tuple[MetadataIdentity, ...]:
    """Keep all 240/8/8 intents even when no .CHECKSUM exists (no fake hashes)."""
    objects = frozen_archive_objects()
    by_url: dict[str, ChecksumReceipt] = {}
    for receipt in receipts:
        matches = [item for item in objects if item.zip_url == receipt.zip_url]
        if len(matches) != 1:
            raise ValueError("receipt for an unfrozen archive identity")
        require_receipt(matches[0], receipt)
        if receipt.zip_url in by_url:
            raise ValueError("duplicate checksum receipt identity")
        by_url[receipt.zip_url] = receipt
    return tuple(
        MetadataIdentity(item, item.role_intent, "METADATA_ONLY_EXCLUDED",
                         by_url.get(item.zip_url))
        for item in objects
    )


def metadata_for_object(
    obj: ArchiveObject, *, synthetic: bool = False
) -> tuple[tuple[str, str], ...]:
    """Never invent unavailable QA/outcome facts or historical receive times."""
    require_frozen_object(obj)
    m = dict.fromkeys(REQUIRED_DATASET_METADATA, "UNKNOWN_NOT_ATTESTED")
    m.update(
        strategy_version_allowed=G0_STRATEGY,
        primary_research_question=G0_QUESTION,
        current_evidence_role="DEV" if synthetic else obj.role_intent,
        permitted_output_visibility=(
            "DEV_LOCAL_AND_AGGREGATE" if synthetic else "METADATA_ONLY_EXCLUDED"
        ),
        result_visibility_state="DEV" if synthetic else "UNSEEN_SEALED",
        first_opened_at="SYNTHETIC_FIXTURE_ONLY" if synthetic else "NOT_OPENED",
        open_reason="SYNTHETIC_ENGINEERING" if synthetic else "RIGHTS_NOT_ADMITTED",
        point_in_time_universe="FROZEN_2024_G0_ARCHIVE_IDENTITIES_NOT_PIT_CERTIFIED",
        symbol_mapping=f"{obj.symbol}:EXACT_ARCHIVE_SYMBOL_NOT_PRODUCTION_MAPPING",
        timezone_dst_policy="UTC_NO_DST",
        session_calendar_version="UTC_24X7_ARCHIVE_ONLY",
        data_revision_status="UNKNOWN_POSSIBLE_POST_DAY_CORRECTIONS",
        fee_profile_version="G0_SYNTHETIC_COST_NOT_BINANCE_FEES",
        friction_profile_version="G0_SYNTHETIC_VENUE_OVERLAY",
        oracle_basis_model_version="NOT_APPLICABLE_ARCHIVE_BARS",
        duplicate_policy="FAIL_CLOSED",
        missing_bar_policy="FAIL_CLOSED",
        bad_tick_policy="FAIL_CLOSED",
        provider_disagreement_policy="NOT_EVALUATED_SINGLE_ARCHIVE",
    )
    return tuple(sorted(m.items()))


def bind_archive_dataset(
    obj: ArchiveObject,
    receipt: ChecksumReceipt,
    *,
    mapping_hash: str,
    rights: SourceRightsProvenance | None = None,
) -> DatasetManifest:
    """Metadata-only unless explicitly synthetic ALLOWED CURRENT_DEV.

    This package never upgrades real rights, even if caller claims ALLOWED.
    """
    require_receipt(obj, receipt)
    if rights is not None:
        if type(rights) is not SourceRightsProvenance:
            raise TypeError("exact rights contract required")
        rights = SourceRightsProvenance.model_validate_json(rights.model_dump_json())
        if rights.eligibility == IntendedUseEligibility.ALLOWED and not rights.synthetic:
            raise PermissionError("real Binance rights admission needs a separate Control")
        if rights.synthetic and (
            obj.role_intent != "CURRENT_DEV"
            or rights.eligibility != IntendedUseEligibility.ALLOWED
            or rights.intended_use != "STRATEGY_DEV_RESEARCH"
        ):
            raise PermissionError("synthetic fixtures only on frozen CURRENT_DEV")
    synthetic = rights is not None and rights.synthetic
    return DatasetManifest.create(
        version="G0_BINANCE_ARCHIVE_DATASET_V1",
        dataset_id=f"BINANCE_UM_5M_{obj.symbol}_{obj.period}_{obj.role_intent}",
        source="BINANCE_VISION_UM_PUBLIC_ARCHIVE",
        source_tier="R3",
        exposure_state="DEV_EXPOSED" if synthetic else "UNSEEN_SEALED",
        venue="BINANCE_UM",
        asset_class="CRYPTO_PERPETUAL",
        instruments=(obj.symbol,),
        start_ns=obj.start_ns,
        end_ns=obj.end_ns,
        resolution="5m",
        datatypes=("BAR_5M",),
        timezone="UTC",
        session_semantics="UTC_24X7_FIVE_MINUTE",
        checksum=receipt.archive_sha256,
        source_locator=obj.zip_url,
        mapping_hash=mapping_hash,
        metadata=metadata_for_object(obj, synthetic=synthetic),
        rights=rights,
    )


def metadata_only_inventory(
    receipts: tuple[ChecksumReceipt, ...],
    *,
    mapping_hash: str,
    freeze_locator: str,
    freeze_hash: str,
) -> DatasetInventoryManifest | None:
    """R2B metadata only for checksum-bound rows; no synthetic checksum fabrication.

    The complete source/intended-role roster is available from metadata_ledger().
    Rows without receipts cannot become DatasetManifest records.
    """
    ledger = metadata_ledger(receipts)
    rows = tuple(
        bind_archive_dataset(item.object, item.receipt, mapping_hash=mapping_hash)
        for item in ledger if item.receipt is not None
    )
    if not rows:
        return None
    by_url = {item.object.zip_url: item for item in ledger}
    items = tuple(
        AllocationItem(
            binding=_binding(ds),
            role=InventoryRole.METADATA_ONLY_EXCLUDED,
            block_id=f"G0_{by_url[ds.source_locator].intended_role}_{ds.instruments[0]}",
            intended_use="STRATEGY_DEV_RESEARCH_NOT_AUTHORIZED",
            inventory_state=InventoryState.UNKNOWN,
            limitations=(
                "REAL_RIGHTS_UNKNOWN_OR_PROHIBITED",
                "NO_ZIP_OPEN_NO_MARKET_COVERAGE_CLAIM",
                "INTENDED_ROLE_NON_OPERATIVE",
            ),
            reason=f"intended={by_url[ds.source_locator].intended_role}; operative=metadata-only",
        )
        for ds in rows
    )
    spec = InventoryAllocationSpec.create(
        spec_id="G0_R3_BINANCE_METADATA_ONLY_V1",
        freeze_evidence_locator=freeze_locator,
        freeze_evidence_hash=freeze_hash,
        strategy_version=G0_STRATEGY,
        primary_research_question=G0_QUESTION,
        items=items,
    )
    return build_inventory_manifest(datasets=rows, allocation=spec)


def _require_synthetic_current_dev(
    obj: ArchiveObject,
    receipt: ChecksumReceipt,
    admission: DevExternalAdmission,
    inventory: DatasetInventoryManifest,
    visibility: DevVisibilityPolicy,
) -> None:
    """All immutable contracts validated before opener, ZIP, output-root or sidecar I/O."""
    require_receipt(obj, receipt)
    if obj.role_intent != "CURRENT_DEV":
        raise PermissionError("sealed monthly reserve payload cannot be accessed")
    if type(admission) is not DevExternalAdmission:
        raise TypeError("concrete DEV admission required")
    if type(visibility) is not DevVisibilityPolicy:
        raise TypeError("concrete DEV visibility required")
    admission._require_access()
    ds = admission.authority.require(admission.dataset, admission.preregistration)
    if (
        ds.rights is None
        or not ds.rights.synthetic
        or ds.rights.eligibility != IntendedUseEligibility.ALLOWED
        or admission.preregistration.evidence_kind != "SYNTHETIC_ENGINEERING"
    ):
        raise PermissionError("only synthetic engineering receipts may open fixture ZIP")
    expected = bind_archive_dataset(
        obj, receipt, mapping_hash=ds.mapping_hash, rights=ds.rights
    )
    if expected != ds:
        raise PermissionError("Binance object/dataset/rights/metadata binding mismatch")
    checked = validate_inventory_manifest(inventory)
    matching = [entry for entry in checked.entries if entry.dataset.record_hash == ds.record_hash]
    if len(matching) != 1:
        raise PermissionError("exact inventory dataset binding missing")
    row = matching[0]
    if (
        row.allocation.role != InventoryRole.CURRENT_DEV
        or row.inventory_state != InventoryState.AVAILABLE
        or row.allocation.binding.dataset_manifest_hash != ds.record_hash
        or row.allocation.intended_use != "STRATEGY_DEV_RESEARCH"
    ):
        raise PermissionError("metadata-only or reserve role cannot be operative DEV")
    vis = DevVisibilityPolicy.model_validate_json(visibility.model_dump_json())
    if (
        vis.record_hash != admission.preregistration.visibility_hash
        or vis.channel != admission.authority.visibility
        or vis.max_rows < 288
        or vis.max_bytes > MAX_SIDECAR_BYTES
        or admission.policy.max_observations < 288
    ):
        raise PermissionError("frozen visibility/observation bound mismatch")
    caps = admission.capabilities
    if len(caps) != 1:
        raise PermissionError("exactly one synthetic BAR_5M import capability required")
    cap = caps[0]
    if (
        cap.provider != "BINANCE"
        or cap.venue != "BINANCE_UM"
        or cap.product != "USD_M_FUTURES"
        or cap.datatype != "BAR_5M"
        or cap.source_mode != SourceMode.FREE_REFERENCE_IMPORT
        or cap.adapter_owner != "FREE_FILE"
        or not cap.source_evidence.startswith("synthetic://")
        or not (cap.proof_locator or "").startswith("synthetic://")
    ):
        raise PermissionError("no live/alternate provider or unsupported adapter substitution")
    records = admission.resolver.snapshot.records
    if not records or any(
        record.metadata_basis != "SYNTHETIC" for record in records
    ):
        raise PermissionError("synthetic mapping receipts required")
    if ds.record_hash in admission.preregistration.reserve_hashes:
        raise PermissionError("reserve hash is not executable")


def prepare_current_dev_sidecar(
    obj: ArchiveObject,
    receipt: ChecksumReceipt,
    admission: DevExternalAdmission,
    inventory: DatasetInventoryManifest,
    visibility: DevVisibilityPolicy,
    *,
    opener: Callable[[str, int], HttpResponse],
    output_root: Path,
) -> PreparedDailySidecar:
    """Consume exactly one *injected synthetic* fake HTTP ZIP into one local DEV sidecar."""
    _require_synthetic_current_dev(obj, receipt, admission, inventory, visibility)
    response = opener(obj.zip_url, MAX_ZIP_BYTES)
    raw = checked_http_response(response, expected_url=obj.zip_url, limit=MAX_ZIP_BYTES)
    bars = parse_verified_daily_zip(
        obj, raw, receipt, finalized_as_of_ns=receipt.retrieved_at_ns
    )
    ds = admission.dataset
    cap = admission.capabilities[0]
    ledger = ExternalReferenceLedger(admission)
    for bar in bars:
        ts_event = bar.open_ms * 1_000_000
        event = ExternalReferenceEvent.create(
            version="G0_BINANCE_SYNTHETIC_IMPORT_V1",
            provider=cap.provider,
            venue=cap.venue,
            product=cap.product,
            instrument_id=obj.symbol,
            mapping_hash=ds.mapping_hash,
            dataset_hash=ds.record_hash,
            capability_hash=cap.record_hash,
            rights_hash=ds.rights.record_hash if ds.rights else "",
            source_mode=SourceMode.FREE_REFERENCE_IMPORT,
            native_id=f"{obj.symbol}:{bar.open_ms}",
            sequence=None,
            timestamps=TimestampProvenance(
                source_ts=str(bar.open_ms),
                source_unit="ms",
                ts_event=ts_event,
                observed_at_ns=receipt.retrieved_at_ns,
                true_network_receive_ts=None,
                receive_provenance="NOT_EXPOSED",
            ),
            payload=BarPayload(
                interval_minutes=5,
                start_ns=ts_event,
                end_ns=(bar.close_ms + 1) * 1_000_000,
                timestamp_meaning="OPEN",
                aggregation_origin="BINANCE_UM_OFFLINE_FINALIZED_SYNTHETIC",
                finalized=True,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            ),
        )
        observed = ledger.observe(event, evaluated_at_ns=receipt.retrieved_at_ns)
        if not observed.admitted or observed.duplicate or observed.out_of_order:
            raise ValueError("non-canonical daily DEV observation")
    if len(ledger.observations) != 288:
        raise ValueError("incomplete daily DEV admission")
    # Preserve the exact original owner wire representation, not a new schema/writer.
    sidecar = EvidenceSidecar.create(
        version="1",
        dataset_hash=ds.record_hash,
        mapping_hash=admission.resolver.snapshot.record_hash,
        capability_hashes=tuple(c.record_hash for c in admission.capabilities),
        policy_hash=admission.policy.record_hash,
        observations=tuple(ledger.observations),
        source_bytes_hex=(),
        raw_semantics="SYNTHETIC_ENGINEERING_OFFLINE_5M; NETWORK_RECEIVE_NOT_EXPOSED",
        catalog_files=(),
    )
    encoded = canonical_json_bytes(sidecar.model_dump(mode="json"))
    if (
        len(encoded) > min(visibility.max_bytes, MAX_SIDECAR_BYTES)
        or len(encoded) > ENVELOPE_BYTES
    ):
        raise ValueError("bounded existing DEV sidecar/envelope limit exceeded")
    _require_synthetic_current_dev(obj, receipt, admission, inventory, visibility)
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{sidecar.record_hash}.reference.json"
    with path.open("xb") as handle:
        handle.write(encoded)
    return PreparedDailySidecar(
        path, sha256_hex(encoded), sidecar.record_hash, ds.record_hash,
        len(ledger.observations), len(encoded),
    )
