"""DEV readers compose the original owners after an explicit before-I/O gate."""

from pathlib import Path

from trader_assist_v0.multi_asset_shadow.shadow_records.records import ImmutableRecord
from trader_assist_v0.nautilus_e4.storage import EvidenceStore
from trader_assist_v0.research_data.admission import AdmissionPolicy, _AdmissionMechanics
from trader_assist_v0.research_data.contracts import DatasetManifest, ProviderCapability
from trader_assist_v0.research_data.mapping import PitReferenceResolver
from trader_assist_v0.research_data.storage import ReferenceDatasetStore, _read_verified

from .contracts import Opportunity
from .dev_contracts import DevAccessAuthority, DevObservation
from .dev_lifecycle import DevPreregistration
from .evidence import _bind_domain_records, _e4_fields, _external_fields


class DevExternalAdmission(_AdmissionMechanics):
    def __init__(
        self,
        dataset: DatasetManifest,
        resolver: PitReferenceResolver,
        capabilities: tuple[ProviderCapability, ...],
        policy: AdmissionPolicy,
        authority: DevAccessAuthority,
        preregistration: DevPreregistration,
    ) -> None:
        self.authority = authority
        self.preregistration = preregistration
        authority.require(dataset, preregistration)
        super().__init__(dataset, resolver, capabilities, policy, production=False)

    def _require_access(self) -> None:
        if type(self) is not DevExternalAdmission:
            raise TypeError("concrete DEV admission required")
        self.authority.require(self.dataset, self.preregistration)


def read_external_dev(
    root: Path,
    path: Path,
    checksum: str,
    registry_hash: str,
    admission: DevExternalAdmission,
    *,
    max_bytes: int = 4_000_000,
) -> tuple[DevObservation, ...]:
    # Gate before even ReferenceDatasetStore.__init__ resolves the root.
    if type(admission) is not DevExternalAdmission:
        raise TypeError("concrete DEV admission required")
    admission._require_access()
    store = ReferenceDatasetStore(root, max_bytes=max_bytes)
    observed = _read_verified(store, admission, path, checksum)
    return tuple(
        DevObservation.create(
            **{
                **_external_fields(admission, raw, registry_hash),
                "version": "DEV_OBSERVATION_V1",
                "authority": admission.authority,
            }
        )
        for raw in observed
        if raw.admitted and not raw.duplicate
    )


def read_e4_dev(
    store: EvidenceStore,
    dataset: DatasetManifest,
    expected_manifest: str,
    expected_snapshot: str,
    registry_hash: str,
    authority: DevAccessAuthority,
    preregistration: DevPreregistration,
) -> tuple[DevObservation, ...]:
    ds = authority.require(dataset, preregistration)
    return tuple(
        DevObservation.create(**{**fields, "version": "DEV_OBSERVATION_V1", "authority": authority})
        for fields in _e4_fields(store, ds, expected_manifest, expected_snapshot, registry_hash)
    )


def bind_domain_records_dev(
    opportunity: Opportunity,
    records: tuple[ImmutableRecord, ...],
    dataset: DatasetManifest,
    authority: DevAccessAuthority,
    preregistration: DevPreregistration,
) -> Opportunity:
    authority.require(dataset, preregistration)
    return _bind_domain_records(opportunity, records)
