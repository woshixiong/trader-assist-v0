"""Independent R3 real-DEV composition with bounded local-file ingress.

Provider acquisition remains external to Trade OS. This module accepts only
already-downloaded exact .CHECKSUM and CURRENT_DEV ZIP files, preserving the
existing rights, parser, inventory, DEV-admission, and sidecar owners. The
fail-closed provider-network placeholder remains non-executable.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.research_data.admission import ExternalReferenceLedger
from trader_assist_v0.research_data.binance_archive import (
    MAX_CHECKSUM_BYTES,
    MAX_ZIP_BYTES,
    ArchiveObject,
    BinanceKline,
    ChecksumReceipt,
    checked_http_response,
    checksum_receipt,
    frozen_archive_objects,
    parse_verified_daily_zip,
    require_frozen_object,
    require_receipt,
)
from trader_assist_v0.research_data.binance_research_transport import (
    MockOnlyResearchTransport,
    PinnedHttpsResearchTransport,
    require_candidate_rights,
)
from trader_assist_v0.research_data.contracts import (
    BarPayload,
    CapabilityState,
    ControlReplan,
    DatasetManifest,
    ExternalReferenceEvent,
    SourceMode,
    SourceRightsProvenance,
    TimestampProvenance,
)
from trader_assist_v0.research_data.mapping import PitReferenceResolver
from trader_assist_v0.research_data.storage import EvidenceSidecar
from trader_assist_v0.research_inventory.builder import validate_inventory_manifest
from trader_assist_v0.research_inventory.contracts import (
    DatasetInventoryManifest,
    InventoryRole,
    InventoryState,
)
from trader_assist_v0.research_replay.dev_archive import (
    ENVELOPE_BYTES,
    G0_QUESTION,
    G0_STRATEGY,
    PreparedDailySidecar,
    metadata_for_object,
    metadata_ledger,
)
from trader_assist_v0.research_replay.dev_evidence import (
    DevExternalAdmission,
    read_external_dev,
)
from trader_assist_v0.research_replay.dev_lifecycle import (
    DevPreregistration,
    DevVisibilityPolicy,
)

REAL_MAX_SIDECAR_BYTES = 4_000_000


def _read_confined_local_file(
    input_root: Path,
    local_path: Path,
    *,
    expected_name: str,
    limit: int,
) -> bytes:
    """Read one exact already-downloaded file, confined to an explicit root."""
    if not isinstance(input_root, Path) or not isinstance(local_path, Path):
        raise TypeError("pathlib.Path input root/path required")
    if type(expected_name) is not str or not expected_name:
        raise TypeError("exact expected local basename required")
    if type(limit) is not int or limit <= 0:
        raise TypeError("positive local byte bound required")
    root = input_root.resolve()
    if not root.is_dir():
        raise ValueError("local input root must be an existing directory")
    resolved = local_path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError("local archive path escapes explicit input root") from exc
    if resolved.name != expected_name:
        raise ValueError("local archive basename does not match frozen object")
    if not resolved.is_file():
        raise ValueError("local archive path must be an existing regular file")
    size = resolved.stat().st_size
    if size <= 0 or size > limit:
        raise ValueError("bounded local file exceeded")
    with resolved.open("rb") as handle:
        raw = handle.read(size)
    if len(raw) != size or resolved.stat().st_size != size:
        raise ValueError("local archive changed during bounded read")
    return raw


def read_local_checksum_receipt(
    obj: ArchiveObject,
    *,
    input_root: Path,
    checksum_path: Path,
    rights: SourceRightsProvenance,
    satisfied: frozenset[str],
    retrieved_at_ns: int,
    retrieval_identity: str,
) -> ChecksumReceipt:
    """Admit one local .CHECKSUM identity after rights, never provider I/O."""
    require_candidate_rights(rights, satisfied)
    require_frozen_object(obj)
    raw = _read_confined_local_file(
        input_root,
        checksum_path,
        expected_name=obj.zip_name + ".CHECKSUM",
        limit=MAX_CHECKSUM_BYTES,
    )
    return checksum_receipt(
        obj,
        raw,
        retrieved_at_ns=retrieved_at_ns,
        retrieval_identity=retrieval_identity,
    )


def require_complete_frozen_receipts(
    receipts: tuple[ChecksumReceipt, ...],
) -> tuple[ChecksumReceipt, ...]:
    """Exactly 240 daily + 16 sealed monthly identities; no synthetic hash filling."""
    if type(receipts) is not tuple:
        raise TypeError("immutable 256 receipt tuple required")
    ledger = metadata_ledger(receipts)
    missing = [row.object.zip_url for row in ledger if row.receipt is None]
    if missing:
        raise ControlReplan(
            f"REAL_DEV_NOT_READY: missing {len(missing)} exact checksum identities: "
            + ", ".join(missing)
        )
    if len(receipts) != 256:
        raise ControlReplan("exact 256 distinct real source identities required")
    return tuple(row.receipt for row in ledger if row.receipt is not None)


def bind_candidate_real_dataset(
    obj: ArchiveObject,
    receipt: ChecksumReceipt,
    *,
    mapping_hash: str,
    rights: SourceRightsProvenance,
    satisfied: frozenset[str],
) -> DatasetManifest:
    """Shape-only real identity; NEVER proof that fake test bytes came from Binance."""
    require_receipt(obj, receipt)
    r = require_candidate_rights(rights, satisfied)
    metadata = dict(metadata_for_object(obj, synthetic=False))
    if obj.role_intent == "CURRENT_DEV":
        metadata.update(
            current_evidence_role="DEV",
            permitted_output_visibility="DEV_LOCAL_AND_AGGREGATE",
            result_visibility_state="DEV",
            first_opened_at="NOT_OPENED",
            open_reason="CONDITIONAL_OFFLINE_REAL_DEV_RESEARCH",
            strategy_version_allowed=G0_STRATEGY,
            primary_research_question=G0_QUESTION,
        )
    else:
        metadata.update(
            first_opened_at="NOT_OPENED",
            open_reason="SEALED_RESERVE_CHECKSUM_IDENTITY_ONLY",
            result_visibility_state="UNSEEN_SEALED",
        )
    return DatasetManifest.create(
        version="G0_BINANCE_REAL_DEV_CANDIDATE_V1",
        dataset_id=f"BINANCE_UM_5M_{obj.symbol}_{obj.period}_{obj.role_intent}",
        source="BINANCE_VISION_UM_PUBLIC_ARCHIVE",
        source_tier="R3",
        exposure_state="DEV_EXPOSED" if obj.role_intent == "CURRENT_DEV" else "UNSEEN_SEALED",
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
        metadata=tuple(sorted(metadata.items())),
        rights=r,
    )


@dataclass(frozen=True, slots=True)
class FrozenRealDevCandidate:
    """Whole source universe + existing R2B/DEV owners; not an external I/O permit."""

    receipts: tuple[ChecksumReceipt, ...]
    datasets: tuple[DatasetManifest, ...]
    inventory: DatasetInventoryManifest
    preregistration: DevPreregistration
    visibility: DevVisibilityPolicy
    satisfied_constraints: frozenset[str]

    def require_frozen(self, rights: SourceRightsProvenance) -> None:
        r = require_candidate_rights(rights, self.satisfied_constraints)
        receipts = require_complete_frozen_receipts(self.receipts)
        objects = frozen_archive_objects()
        if len(self.datasets) != 256 or len({d.record_hash for d in self.datasets}) != 256:
            raise ControlReplan("complete unique 256 real rights-bound manifests required")
        mapping_hashes = {ds.mapping_hash for ds in self.datasets}
        if len(mapping_hashes) != 1:
            raise ControlReplan("one bound historical mapping snapshot required")
        mapping_hash = next(iter(mapping_hashes))
        by_url = {d.source_locator: d for d in self.datasets}
        if len(by_url) != 256 or set(by_url) != {o.zip_url for o in objects}:
            raise ControlReplan("frozen manifest URL roster incomplete or altered")
        for obj, receipt in zip(objects, receipts, strict=True):
            expected = bind_candidate_real_dataset(
                obj, receipt, mapping_hash=mapping_hash, rights=r,
                satisfied=self.satisfied_constraints,
            )
            if by_url[obj.zip_url] != expected:
                raise PermissionError("rights/dataset/checksum/role immutable binding mismatch")
        pre = DevPreregistration.model_validate_json(self.preregistration.model_dump_json())
        dev = tuple(
            by_url[o.zip_url].record_hash
            for o in objects if o.role_intent == "CURRENT_DEV"
        )
        reserves = tuple(
            by_url[o.zip_url].record_hash
            for o in objects if o.role_intent != "CURRENT_DEV"
        )
        if (
            pre.stage != "S1" or pre.group != "G0"
            or pre.evidence_kind != "RIGHTS_AUTHORIZED_DEV"
            or pre.dataset_hashes != dev or pre.reserve_hashes != reserves
            or pre.strategy_version != G0_STRATEGY or pre.question != G0_QUESTION
            or pre.run_authority_ref == pre.r0_ref
            or pre.run_authority_ref == pre.r1_ref
        ):
            raise PermissionError("256 full roster G0 real prereg/run authority missing")
        vis = DevVisibilityPolicy.model_validate_json(self.visibility.model_dump_json())
        if (
            vis.record_hash != pre.visibility_hash
            or vis.channel != "DEV_LOCAL_AND_AGGREGATE"
            or vis.max_rows < 288 or vis.max_bytes > REAL_MAX_SIDECAR_BYTES
            or vis.sealed_access or vis.promotion != "PROHIBITED"
        ):
            raise PermissionError("incompatible bounded frozen visibility")
        inventory = validate_inventory_manifest(self.inventory)
        if len(inventory.entries) != 256:
            raise ControlReplan("no partial/metadata-only source universe is executable")
        inv_by_url = {entry.dataset.source_locator: entry for entry in inventory.entries}
        if set(inv_by_url) != set(by_url):
            raise PermissionError("operative inventory has wrong frozen identities")
        for obj in objects:
            row = inv_by_url[obj.zip_url]
            role = InventoryRole.CURRENT_DEV if obj.role_intent == "CURRENT_DEV" else (
                InventoryRole.FUTURE_DEV_RESERVE if obj.role_intent == "FUTURE_DEV_RESERVE"
                else InventoryRole.CERTIFICATION_RESERVE
            )
            if (
                row.dataset != by_url[obj.zip_url] or row.allocation.role != role
                or row.allocation.intended_use != "STRATEGY_DEV_RESEARCH"
                or row.allocation.binding.dataset_manifest_hash != row.dataset.record_hash
            ):
                raise PermissionError("operative R2B allocation/rights mismatch")
            if role == InventoryRole.CURRENT_DEV:
                if row.inventory_state != InventoryState.AVAILABLE:
                    raise ControlReplan(
                        "verified CURRENT_DEV inventory unavailable; checksum is not coverage"
                    )
            elif (
                row.dataset.exposure_state != "UNSEEN_SEALED"
                or row.inventory_state == InventoryState.AVAILABLE
            ):
                raise PermissionError("reserve must remain sealed and non-available")
        if set(pre.dataset_hashes) & set(pre.reserve_hashes):
            raise PermissionError("DEV/reserve overlap forbidden")


def _require_historical_bar_only(
    obj: ArchiveObject, receipt: ChecksumReceipt, admission: DevExternalAdmission
) -> None:
    if type(admission) is not DevExternalAdmission:
        raise TypeError("original DEV admission required")
    admission._require_access()
    snapshot = admission.resolver.snapshot
    if admission.dataset.mapping_hash != snapshot.record_hash:
        raise PermissionError("historical mapping snapshot hash mismatch")
    records = [
        record for record in snapshot.records
        if record.provider == "BINANCE" and record.venue == "BINANCE_UM"
        and record.native_symbol == obj.symbol and record.instrument_id == obj.symbol
        and record.valid_from <= obj.start_ns and record.valid_to >= obj.end_ns
    ]
    if len(records) != 1:
        raise ControlReplan("unambiguous historical archive BAR_5M identity not proven")
    record = records[0]
    specs = dict(record.contract_specification)
    if (
        record.product != "USD_M_FUTURES"
        or record.metadata_basis != "HISTORICAL"
        or record.source_role != "RESEARCH_IMPORT"
        or record.support_state != CapabilityState.AVAILABLE_VERIFIED
        or record.listing_state != "LISTED"
        or record.known_at < obj.end_ns
        or record.recorded_at < record.known_at
        or record.recorded_at > receipt.retrieved_at_ns
        or not record.source_locator.startswith(
            "https://data.binance.vision/data/futures/um/"
        )
        or any(
            not specs.get(key, "").startswith("UNVERIFIED_OUTSIDE_BAR_SCOPE")
            for key in ("price_tick", "size_step")
        )
    ):
        raise ControlReplan("historical mapping/PIT claims exceed evidenced archive BAR_5M")
    caps = admission.capabilities
    if len(caps) != 1:
        raise PermissionError("only one frozen historical BAR_5M capability")
    c = caps[0]
    if (
        c.provider != "BINANCE" or c.venue != "BINANCE_UM"
        or c.product != "USD_M_FUTURES" or c.datatype != "BAR_5M"
        or c.source_mode != SourceMode.FREE_REFERENCE_IMPORT
        or c.adapter_owner != "FREE_FILE"
        or c.adapter_state != CapabilityState.AVAILABLE_VERIFIED or not c.enabled
        or c.source_exposes is not True
        or not (c.proof_locator or "").startswith("https://")
        or not c.source_evidence.startswith("https://")
        or "synthetic" in c.source_evidence.lower()
    ):
        raise PermissionError("no synthetic/live/alternate capability substitution")
    resolved = PitReferenceResolver(snapshot).resolve(
        "BINANCE", obj.symbol, obj.start_ns,
        receipt.retrieved_at_ns, production=True,
    )
    if resolved != record:
        raise ControlReplan("retrospective knowledge-time mapping cannot resolve")


def require_before_mock_zip(
    obj: ArchiveObject, receipt: ChecksumReceipt, admission: DevExternalAdmission,
    candidate: FrozenRealDevCandidate,
) -> None:
    """Pure pre-I/O invariant; no caller's ALLOWED claim permits live transport."""
    if obj.role_intent != "CURRENT_DEV":
        raise PermissionError("reserve ZIP is never a DEV payload")
    require_receipt(obj, receipt)
    admission._require_access()
    ds = admission.authority.require(admission.dataset, admission.preregistration)
    rights = ds.rights
    if rights is None:
        raise PermissionError("no real rights identity")
    candidate.require_frozen(rights)
    if rights.synthetic or admission.preregistration != candidate.preregistration:
        raise PermissionError("synthetic evidence or different prereg is not real DEV")
    match = [r for r in candidate.receipts if r.zip_url == obj.zip_url]
    if len(match) != 1 or match[0] != receipt:
        raise PermissionError("exact daily checksum receipt changed")
    if ds not in candidate.datasets or ds.mapping_hash != admission.resolver.snapshot.record_hash:
        raise PermissionError("dataset not in full sealed source roster")
    if (
        admission.authority.visibility != candidate.visibility.channel
        or admission.policy.max_observations < 288
        or not admission.authority.satisfied_constraints
        or frozenset(admission.authority.satisfied_constraints) != candidate.satisfied_constraints
    ):
        raise PermissionError("DEV authority/visibility/rights constraints changed")
    _require_historical_bar_only(obj, receipt, admission)


def _prepare_real_form_sidecar(
    obj: ArchiveObject,
    receipt: ChecksumReceipt,
    admission: DevExternalAdmission,
    candidate: FrozenRealDevCandidate,
    bars: tuple[BinanceKline, ...],
    *,
    output_root: Path,
    registry_hash: str,
    observed_at_ns: int,
    event_version: str,
    raw_semantics: str,
) -> PreparedDailySidecar:
    """Build the existing bounded sidecar shape from already-verified bars."""
    if type(observed_at_ns) is not int or observed_at_ns < obj.end_ns:
        raise ValueError("retrospective local observation time required")
    ds, c = admission.dataset, admission.capabilities[0]
    ledger = ExternalReferenceLedger(admission)
    for bar in bars:
        event_ns = bar.open_ms * 1_000_000
        event = ExternalReferenceEvent.create(
            version=event_version,
            provider="BINANCE", venue="BINANCE_UM", product="USD_M_FUTURES",
            instrument_id=obj.symbol, mapping_hash=ds.mapping_hash,
            dataset_hash=ds.record_hash, capability_hash=c.record_hash,
            rights_hash=ds.rights.record_hash if ds.rights else "",
            source_mode=SourceMode.FREE_REFERENCE_IMPORT,
            native_id=f"{obj.symbol}:{bar.open_ms}", sequence=None,
            timestamps=TimestampProvenance(
                source_ts=str(bar.open_ms), source_unit="ms", ts_event=event_ns,
                observed_at_ns=observed_at_ns,
                true_network_receive_ts=None, receive_provenance="NOT_EXPOSED",
            ),
            payload=BarPayload(
                interval_minutes=5, start_ns=event_ns,
                end_ns=(bar.close_ms + 1) * 1_000_000,
                timestamp_meaning="OPEN", aggregation_origin="BINANCE_UM_OFFLINE_FINALIZED",
                finalized=True, open=bar.open, high=bar.high, low=bar.low,
                close=bar.close, volume=bar.volume,
            ),
        )
        observed = ledger.observe(event, evaluated_at_ns=observed_at_ns)
        if not observed.admitted or observed.duplicate or observed.out_of_order:
            raise ValueError("noncanonical daily real-form observation")
    if len(ledger.observations) != 288:
        raise ValueError("incomplete daily source")
    sidecar = EvidenceSidecar.create(
        version="1", dataset_hash=ds.record_hash,
        mapping_hash=admission.resolver.snapshot.record_hash,
        capability_hashes=(c.record_hash,), policy_hash=admission.policy.record_hash,
        observations=tuple(ledger.observations), source_bytes_hex=(),
        raw_semantics=raw_semantics, catalog_files=(),
    )
    encoded = canonical_json_bytes(sidecar.model_dump(mode="json"))
    if len(encoded) > min(ENVELOPE_BYTES, candidate.visibility.max_bytes, REAL_MAX_SIDECAR_BYTES):
        raise ValueError("bounded real-form DEV sidecar too large")
    require_before_mock_zip(obj, receipt, admission, candidate)
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{sidecar.record_hash}.reference.json"
    with path.open("xb") as handle:
        handle.write(encoded)
    digest = sha256_hex(encoded)
    replay = read_external_dev(root, path, digest, registry_hash, admission)
    if len(replay) != 288 or any(
        row.ts_receive is not None or row.receive_provenance != "NOT_EXPOSED"
        for row in replay
    ):
        raise ValueError("existing DEV reader failed real-form roundtrip")
    return PreparedDailySidecar(
        path, digest, sidecar.record_hash, ds.record_hash, len(replay), len(encoded),
    )


def prepare_mock_real_dev_sidecar(
    obj: ArchiveObject, receipt: ChecksumReceipt, admission: DevExternalAdmission,
    candidate: FrozenRealDevCandidate, *,
    mock: MockOnlyResearchTransport, output_root: Path, registry_hash: str,
) -> PreparedDailySidecar:
    """Simulated hypothetical real admission using FAKE data and MOCK HTTP ONLY."""
    require_before_mock_zip(obj, receipt, admission, candidate)
    if type(mock) is not MockOnlyResearchTransport:
        raise TypeError("only mock transport is executable in this path")
    response = mock.request(obj, "ZIP")
    raw = checked_http_response(
        response, expected_url=obj.zip_url, limit=MAX_ZIP_BYTES,
    )
    bars = parse_verified_daily_zip(
        obj, raw, receipt, finalized_as_of_ns=receipt.retrieved_at_ns,
    )
    return _prepare_real_form_sidecar(
        obj, receipt, admission, candidate, bars,
        output_root=output_root, registry_hash=registry_hash,
        observed_at_ns=receipt.retrieved_at_ns,
        event_version="G0_BINANCE_REAL_DEV_MOCK_WIRE_V1",
        raw_semantics="OFFLINE_5M_FAKE_PROVIDER_FIXTURE; NETWORK_RECEIVE_NOT_EXPOSED",
    )


def prepare_local_real_dev_sidecar(
    obj: ArchiveObject,
    receipt: ChecksumReceipt,
    admission: DevExternalAdmission,
    candidate: FrozenRealDevCandidate,
    *,
    input_root: Path,
    zip_path: Path,
    output_root: Path,
    registry_hash: str,
    observed_at_ns: int,
) -> PreparedDailySidecar:
    """Consume one already-downloaded CURRENT_DEV ZIP after the full pre-I/O gate."""
    require_before_mock_zip(obj, receipt, admission, candidate)
    raw = _read_confined_local_file(
        input_root, zip_path, expected_name=obj.zip_name, limit=MAX_ZIP_BYTES,
    )
    bars = parse_verified_daily_zip(
        obj, raw, receipt, finalized_as_of_ns=observed_at_ns,
    )
    return _prepare_real_form_sidecar(
        obj, receipt, admission, candidate, bars,
        output_root=output_root, registry_hash=registry_hash,
        observed_at_ns=observed_at_ns,
        event_version="G0_BINANCE_REAL_DEV_LOCAL_FILE_WIRE_V1",
        raw_semantics="OFFLINE_5M_EXTERNAL_LOCAL_FILE; NETWORK_RECEIVE_NOT_EXPOSED",
    )


def prepare_real_dev_sidecar(
    obj: ArchiveObject, receipt: ChecksumReceipt, admission: DevExternalAdmission,
    candidate: FrozenRealDevCandidate, *,
    transport: PinnedHttpsResearchTransport, output_root: Path, registry_hash: str,
) -> PreparedDailySidecar:
    """Fail-closed provider boundary; local-file ingress is the executable path."""
    require_before_mock_zip(obj, receipt, admission, candidate)
    if type(transport) is not PinnedHttpsResearchTransport:
        raise TypeError("exact pinned stdlib transport required")
    # The transport itself independently refuses I/O; never substitute a mock
    # path or a caller-provided callback as real run authority.
    rights = admission.dataset.rights
    assert rights is not None
    transport.request(
        obj, "ZIP", rights=rights, satisfied=candidate.satisfied_constraints,
    )
    raise PermissionError("REAL_PROVIDER_IO_NOT_AUTHORIZED")
