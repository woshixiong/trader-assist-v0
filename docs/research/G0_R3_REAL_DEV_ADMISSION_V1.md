# G0 R3 real DEV research admission — V1

**Current package:** `G0_R3_BINANCE_LOCAL_FILE_DEV_INGRESS_1`  
**Stage:** bounded local-file DEV ingress acceptance. **No real Binance network request is authorized or performed by Trade OS.**

Current freeze: Issue #161 comments
[`6036824279`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6036824279),
[`6036832356`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6036832356),
Pre-code PASS
[`6036978993`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6036978993),
and Writer handoff
[`6037014299`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6037014299).
The retained real-form admission contract originated in
`G0_R3_BINANCE_REAL_DEV_RESEARCH_ADMISSION_1`; this package changes only the
three frozen existing paths and does not modify Rights, Mapping, Inventory, DEV,
Sidecar, mechanism replay, Nautilus, Strategy, CI, deployment, or execution owners.

## What this package admits

Trade OS now accepts **already-downloaded** exact Binance Public Data files from
an explicit local input root:

```text
OFFICIAL_OR_STANDARD_EXTERNAL_ACQUISITION
-> LOCAL .CHECKSUM FILES
-> EXISTING checksum_receipt / Rights / roster / Inventory / preregistration
-> LOCAL CURRENT_DEV ZIP ONLY
-> EXISTING parse_verified_daily_zip
-> EXISTING EvidenceSidecar(version=1) / read_external_dev
```

Trade OS does not own provider acquisition. No downloader, HTTP client, retry
loop, proxy, subprocess wrapper, provider SDK, database/catalog, second backtest
engine, optimizer, walk-forward framework, or Nautilus migration is introduced.

The immutable archive universe remains exactly:

| Intended role | Physical source identity | Count | Payload state |
| --- | --- | ---: | --- |
| CURRENT_DEV | 2024-01-01 through 2024-02-29 daily USD-M 5m ZIP | 240 | local ZIP allowed only after full existing pre-I/O gates |
| FUTURE_DEV_RESERVE | 2024-03 and 2024-04 monthly USD-M 5m ZIP | 8 | SEALED; checksum identity only |
| CERTIFICATION_RESERVE | 2024-05 and 2024-06 monthly USD-M 5m ZIP | 8 | SEALED; checksum identity only |

All 256 independent `.CHECKSUM` identities are required before a CURRENT_DEV
payload can be opened. A missing, duplicated, revised, substituted, or
rights-incompatible object fails closed. A checksum remains only an identity; it
does not claim payload coverage, 288-row completeness, historical exchange
mechanics, or a strategy result.

## Rights, staged disclosure, and local filesystem boundary

`SourceRightsProvenance(eligibility=ALLOWED, synthetic=false)` remains a
conditional contract shape, not a trusted rights issuer. The exact pinned terms
and current candidate constraints must pass the existing
`require_candidate_rights(...)` owner **before local checksum filesystem
access**.

Local checksum ingress then:

- confines the resolved path to an explicit input root;
- requires the exact frozen `<ZIP>.CHECKSUM` basename;
- enforces the existing checksum byte bound;
- delegates parsing and identity creation to the existing
  `checksum_receipt(...)`;
- records the caller-supplied retrospective retrieval time and local retrieval
  identity;
- permits checksum identity for CURRENT_DEV and both reserve roles.

Reserve ZIP/CSV payloads remain sealed. A reserve ZIP request is rejected by the
existing pure pre-I/O composition gate before payload path resolution, open, or
read. For CURRENT_DEV, the same gate requires the full 256-receipt and
256-manifest roster, exact Inventory, exact 240+16 preregistration split, DEV
authority/visibility/constraints, no DEV/reserve overlap, and historical BAR_5M
mapping before any local payload filesystem access.

## Existing-owner composition and parser authority

The local bridge composes, rather than replaces:

- `frozen_archive_objects`, `checksum_receipt`, `require_receipt`, and
  `parse_verified_daily_zip`;
- `SourceRightsProvenance`, `DatasetManifest`, and
  `ReferenceMappingSnapshot`;
- `build_inventory_manifest` / `validate_inventory_manifest`;
- `DevPreregistration(evidence_kind=RIGHTS_AUTHORIZED_DEV)`,
  `DevAccessAuthority`, `DevExternalAdmission`, and `read_external_dev`;
- the existing `EvidenceSidecar(version=1)`.

For a CURRENT_DEV ZIP, the local bridge only performs bounded path confinement
and bounded byte reading after the full existing gate. SHA-first verification,
safe ZIP-member rules, strict headerless 12-column USD-M rows, epoch-ms checks,
exact 288 ordered finalized five-minute bars, CRC/path/size rules, and CSV
semantics remain owned by `parse_verified_daily_zip(...)`.

Historical mapping remains limited to the offline `BAR_5M` mechanism claim.
Unknown 2024 `price_tick` and `size_step` remain
`UNVERIFIED_OUTSIDE_BAR_SCOPE`; current exchange metadata, synthetic metadata,
or backdated knowledge time cannot manufacture 2024 PIT microstructure truth.

A successfully admitted local daily object produces the existing real-form event
and sidecar shape. Event time remains the historical bar open time, while
`observed_at_ns` is the caller-supplied retrospective local observation time.
`true_network_receive_ts=None`, `receive_provenance=NOT_EXPOSED`,
`source_bytes_hex=()`, and `catalog_files=()` are retained. No raw Binance
ZIP/CSV bytes or sidecar payloads belong in GitHub.

## Provider acquisition ownership

External acquisition is commodity infrastructure. The run operator may use exact
official Binance Public Data object URLs with official or standard maintained
tools outside Trade OS. Tool output is not trusted merely because a helper
returned it: the frozen object roster and SHA-256 receipt validation remain the
authority.

The existing `PinnedHttpsResearchTransport` remains fail-closed and
non-executable. It is not promoted into a provider client, and this package does
not create a future obligation to build one. Reserve payload acquisition/open is
not authorized for convenience.

## Acceptance coverage

Tests generate all checksum/ZIP fixtures locally and make zero real Binance
requests. They prove:

- invalid rights fail before checksum filesystem access;
- checksum path escape, wrong basename, oversize, and malformed content fail;
- local checksum ingress delegates to the existing receipt semantics;
- reserve checksum identity is allowed;
- reserve ZIP and incomplete 256-candidate requests fail before payload
  filesystem access;
- a valid full fake 256 identity plus exact fake CURRENT_DEV ZIP produces one
  bounded real-form sidecar through the existing parser and DEV reader;
- ZIP SHA mismatch and malformed archives still fail in the existing parser;
- source bytes remain absent from the sidecar;
- the existing mock-only path remains valid;
- no network/subprocess/downloader capability is added.

Existing lower-level archive tests continue to own the detailed unsafe
ZIP/CRC/path/header/time/CSV adversarial matrix.

## Explicit non-claims and next gates

This package does not prove current legal eligibility, actual Binance checksum
availability, archive coverage, historical tick/step, a G0 strategy edge,
profitability, reserve contents, production readiness, or execution authority.

After this package eventually passes exact-head CI, fresh Final Independent
Review, and merge, the retained run-level route is:

```text
EXTERNAL OFFICIAL/STANDARD ACQUISITION OF EXACT .CHECKSUM FILES
-> BUILD/FREEZE 256 RECEIPTS + RIGHTS/MAPPING/INVENTORY/PREREG
-> EXTERNAL ACQUISITION OF CURRENT_DEV ZIP ONLY
-> LOCAL INGEST TO EXISTING SIDECARS
-> EXISTING G0 MECHANISM REPLAY
```

Real provider acquisition, real G0 replay, reserve payload access, deployment,
service mutation, private API, exchange write, order actions, autonomous
trading, Mark Ready, and merge remain separate retained gates.
