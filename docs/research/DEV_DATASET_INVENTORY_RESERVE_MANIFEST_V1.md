# DEV dataset inventory / reserve manifest V1

R2B freezes already-authorized in-memory metadata before performance inspection.
It validates caller-frozen roles and blocks. It never opens a source locator,
computes Strategy results, chooses allocation, or grants research access.

## Ownership and APIs

`research_inventory.contracts` owns the immutable inventory contracts, with
existing DatasetManifest and rights records embedded unchanged. `builder` owns
pure validation and canonical serialization:

```python
build_inventory_manifest(*, datasets, allocation, facts=())
validate_inventory_manifest(manifest)
inventory_manifest_bytes(manifest)
inventory_manifest_from_bytes(payload)
```

Use concrete frozen models and tuples. No reader, provider, file handle, callback,
or path argument exists. All source/terms/evidence locators remain opaque strings.
Callers must already have authorization to supply the metadata; a locator or hash
is not authenticated authority. Facts must explicitly declare NON_OUTCOME and
bind a dataset, inventory method and evidence identity. The builder cannot prove
how callers acquired those facts.

The manifest binds complete upstream metadata/hashes/checksums, source/tier,
venue, instruments, half-open time cut, resolution/datatypes, mapping/session,
exposure/evidence role, rights/intended use, Strategy/question, caller-frozen
allocation/reserves, inventory states, limitations and optional count facts.
No upstream hash or field order is changed.

## Roles and cut protections

| Role | Exposure requirement | Meaning |
| --- | --- | --- |
| CURRENT_DEV | DEV_EXPOSED, excluding R0/R6 | Inventory of current DEV; exact STRATEGY_DEV_RESEARCH rights required |
| FUTURE_DEV_RESERVE | DEV_EXPOSED or UNSEEN_SEALED | Reserved identity; no access permission |
| CERTIFICATION_RESERVE | UNSEEN_SEALED or VALIDATION_SEALED | Pristine reserve identity; no certification decision |
| SEALED_VALIDATION | VALIDATION_SEALED | Metadata-only identity |
| FINAL_LOCKBOX | FINAL_LOCKBOX_SEALED | Metadata-only identity |
| METADATA_ONLY_EXCLUDED | Any existing state | Explicitly excluded; no usable research credit |

Non-ALLOWED/missing rights require metadata-only exclusion. Research-use roles
check exact intended use and all attribution/retention constraints through the
existing pure rights check. DatasetManifest.require_access is never invoked.
Current DEV refuses missing/unavailable/unknown inventory and unknown critical
bindings. Non-available states require explicit limitations.

Exactly one allocation row must cover every dataset. Duplicate IDs/hashes,
orphan facts, repeated fact/cell keys and inconsistent binding fields reject.
Whole cuts only: upstream owners must supply any separately authorized sub-cut.
Exposure and pristine status are never changed or restored.

Cuts use [start_ns, end_ns). Adjacent cuts do not overlap. Shared venue/instrument
overlap is checked regardless of source, resolution or datatype. Unknown venue
or instrument cannot establish disjointness. Overlap with incompatible roles or
different blocks rejects, including current DEV versus future DEV/certification
reserve, validation or lockbox. Complementary records can share one compatible
role/block; their counts are not aggregated as independent observations.
Different checksums/source records do not prove independence. Cross-venue
correlation, purge/embargo and causal sufficiency require separate evidence.

## Unknown inventory and counts

InventoryState is AVAILABLE, INCOMPLETE, MISSING, UNAVAILABLE or UNKNOWN.
CountState is KNOWN, UNKNOWN or REQUIRES_SEPARATE_INVENTORY. Count kinds are
INDEPENDENT_EVENT, CORRELATION_CLUSTER and REQUIRED_CELL. Known counts are strict
nonnegative integers; unknown states carry no value. Required-cell facts carry
an exact cell ID. Omitted facts mean no inventory count evidence was supplied:
UNKNOWN / REQUIRES_SEPARATE_INVENTORY, never zero or sufficient.

Every output carries sufficiency_assessment=NOT_ASSESSED. Even complete known
counts do not prove sufficiency, research eligibility, independent samples,
parameter adequacy or a passing research gate. No numerical gate is owned here.

## Canonical identity and future R2 seam

New allocation items/constraints/limitations and facts are deterministically
sorted. Upstream DatasetManifest tuple order is preserved because its record
hash binds that order. The normalized allocation spec receives its own hash;
input-order permutations may change the supplied spec hash but yield the same
normalized allocation hash in the manifest.

Existing BoundRecord semantics own both hashes:

```text
SHA256(concrete_type_name + NUL + canonical_json_bytes(payload_without_record_hash))
```

DatasetInventoryManifest.record_hash is the inventory fingerprint;
InventoryAllocationSpec.record_hash is the allocation fingerprint. No generated
clock, environment value, UUID or file checksum enters construction. Source
checksums are supplied identities and are never verified by opening data.
Validation rechecks concrete snapshots and all nested hashes, allocation
semantics and normalized representation. Deserialization refuses duplicate JSON
keys, extra fields, unsupported versions, nonfinite numbers and stale hashes.
Rehashing only an outer envelope cannot conceal invalid nested records.

A future separately authorized R2 run may reference exactly:

```text
inventory_manifest_hash = manifest.record_hash
allocation_spec_hash = manifest.allocation_spec.record_hash
```

The caller must bind those values to the exact inventory/Strategy/question and
run authority. R2B imports/owns no DevPreregistration, trial, replay, reporting,
candidate roster, parameter selection or second research lifecycle. Adding
fields to existing R2 contracts is outside this package.

## Validation and acceptance evidence

Synthetic fixtures cover the frozen twelve acceptance items: zero outcome/I/O
reads; deterministic bytes/hash; exact binding rejection; sealed metadata-only;
illegal allocation/overlap; reserve protection; unknown never sufficient; the
two-hash future reference; disjoint paths; adversarial malformed metadata;
fail-on-I/O sentinels; serialized nested/outer tampering.

Sentinels cover file opens/reads/stat/resolve/enumeration, sockets/URL opening,
subprocess and DatasetManifest.require_access during generation, validation and
serialization/deserialization. Dependency imports and repository scope checks
occur outside the generation interval. No real data is used.

```bash
export PYTHONPATH="$PWD/src"
python -m pytest -q tests/test_research_inventory_manifest.py
python -m pytest -q tests/test_research_data_contracts.py
python -m ruff check src/trader_assist_v0/research_inventory tests/test_research_inventory_manifest.py
python -m mypy src/trader_assist_v0/research_inventory
python -m compileall -q src/trader_assist_v0/research_inventory
python -c 'import trader_assist_v0.research_inventory'
git diff --check
python -m pytest -q tests/test_research_inventory_manifest.py -k exact_changed_path_allowlist
```

Frozen base: d8ca8aff1daa3ade72264254376c12b145989710. Scope is exactly the three
new research_inventory modules, test_research_inventory_manifest.py and this
document. Any existing/sixth path, raw/outcome I/O, exposure mutation, R2
authority duplication or provider/dependency/workflow/runtime expansion requires
CONTROL_REPLAN before mutation. No CLI, service, database, crawler, optimizer,
production integration or deployment is introduced.
