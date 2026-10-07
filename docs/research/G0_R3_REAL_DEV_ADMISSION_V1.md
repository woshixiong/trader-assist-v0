# G0 R3 real DEV research admission — V1

**Package:** `G0_R3_BINANCE_REAL_DEV_RESEARCH_ADMISSION_1`  
**Stage:** code and mock-only acceptance. **No real Binance request is authorized or performed.**

Canonical freeze: Issue #161 comment
[`6032019360`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6032019360),
Pre-code PASS
[`6031360994`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6031360994),
package state
[`6031296775`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6031296775),
and bounded research-use decision
[`6031272423`](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6031272423).
The Writer is Route B ordinary ChatGPT High and this PR changes only the five
frozen additive paths.

## What this package admits

The package implements a separate real-form R3 DEV composition without changing
the merged PR #299 synthetic-only adapter or any existing Rights, R2B Inventory,
Mapping, DEV, Sidecar, Nautilus, Strategy, CI, deployment, or execution owner.

The immutable archive universe remains exactly:

| Intended role | Physical source identity | Count | Payload state |
| --- | --- | ---: | --- |
| CURRENT_DEV | 2024-01-01 through 2024-02-29 daily USD-M 5m ZIP | 240 | real I/O CLOSED |
| FUTURE_DEV_RESERVE | 2024-03 and 2024-04 monthly USD-M 5m ZIP | 8 | SEALED; ZIP/CSV forbidden |
| CERTIFICATION_RESERVE | 2024-05 and 2024-06 monthly USD-M 5m ZIP | 8 | SEALED; ZIP/CSV forbidden |

All 256 independent `.CHECKSUM` receipt identities are required before the
whole-roster candidate can become ready. A missing, duplicated, revised, or
substituted object fails closed. A checksum is only an identity; it does not
claim payload coverage, 288-row completeness, historical exchange mechanics,
or a strategy result.

## Rights and real-network boundary

`SourceRightsProvenance(eligibility=ALLOWED, synthetic=false)` is treated as a
conditional contract shape, not a trusted rights issuer. The candidate must bind
the exact pinned Vision Dataset Terms V1.0 URL/date/hash and the exact Control
decision, carry nonempty attribution/retention constraints, and satisfy those
constraints.

That still cannot open the network in this package. Applicable current general
ToU, jurisdiction/non-circumvention, third-party restrictions, Final Review,
exact run authority, and unchanged terms are not independently executable facts
here. `PinnedHttpsResearchTransport` therefore fails with
`REAL_PROVIDER_IO_NOT_AUTHORIZED` before stdlib HTTPS. There is intentionally
no caller boolean, arbitrary `ALLOWED` object, callback, environment variable,
or test flag that can activate provider I/O.

The dormant stdlib HTTPS primitive is pinned to `https://data.binance.vision`,
uses TLS verification, disables proxies and redirects, sends no credentials,
performs one bounded request with no retry, and enforces the existing
`MAX_CHECKSUM_BYTES` / `MAX_ZIP_BYTES` owners. It remains unreachable until
a separately reviewed Control package installs an independently verifiable run
issuer. Reserve ZIP/CSV remains forbidden even after such a later change.

## Existing-owner composition and historical claims

The real-form candidate composes, rather than replaces:

- `frozen_archive_objects`, `HttpResponse`, `checked_http_response`,
  `checksum_receipt`, and `parse_verified_daily_zip`;
- `SourceRightsProvenance`, `DatasetManifest`, and
  `ReferenceMappingSnapshot`;
- `build_inventory_manifest` / `validate_inventory_manifest`;
- `DevPreregistration(evidence_kind=RIGHTS_AUTHORIZED_DEV)`,
  `DevAccessAuthority`, `DevExternalAdmission`, and `read_external_dev`;
- the existing `EvidenceSidecar(version=1)`.

A runnable candidate must bind 240 CURRENT_DEV manifest hashes plus sixteen
distinct reserve hashes in one G0/S1 preregistration, with no overlap. The
existing Inventory must cover all 256 identities. CURRENT_DEV must already be
operative `AVAILABLE`; checksum metadata alone cannot assert that fact.
Reserves remain `UNSEEN_SEALED` and non-available.

Historical mapping is limited to the offline `BAR_5M` archive-mechanism claim.
It must be `HISTORICAL` / `AVAILABLE_VERIFIED`, recorded no later than the
retrospective receipt knowledge time, and resolve the exact Binance USD-M
symbol/cut. Unknown 2024 `price_tick` and `size_step` are explicitly
`UNVERIFIED_OUTSIDE_BAR_SCOPE`; current `exchangeInfo`, synthetic metadata,
or a backdated `known_at` cannot manufacture 2024 PIT microstructure truth.

When a future separately authorized daily payload is eventually admitted, the
existing parser remains SHA-first and requires one safe ZIP member, strict
headerless 12-column USD-M rows, 13-digit epoch-ms, exact 288 ordered finalized
5-minute bars and bounded size/CRC/path semantics. Event timestamps use the
historical open time while `observed_at_ns` is the actual retrospective
retrieval time; `true_network_receive_ts=None` and
`receive_provenance=NOT_EXPOSED`.

One daily object maps to one existing bounded sidecar with
`source_bytes_hex=()` and `catalog_files=()`. The adapter verifies the
existing `read_external_dev` roundtrip. No raw provider ZIP/CSV, sidecar,
provider rows, or unapproved derived metrics belong in GitHub.

## Mock-only acceptance

Tests generate their own CSV/ZIP bytes, fake all 256 checksum receipts, and use
`MockOnlyResearchTransport`, an in-memory response table with no network
implementation. Even when tests construct a `synthetic=false`,
`eligibility=ALLOWED` rights-shaped object, it is explicitly a hypothetical
real-form fixture and is never represented as Binance-sourced evidence.

The adversarial matrix covers pinned terms/rights mismatch, missing constraints,
real-network zero-call, redirect/non-200/oversize and wrong URL, exact
240+8+8 roster, missing/duplicate/revised receipts, reserve ZIP zero-read,
full prereg/inventory binding, historical-mapping backdating, SHA-first strict
archive parsing through the existing owner, sidecar collision, bounded output,
and existing-reader replay. Existing lower-level archive tests continue to own
unsafe ZIP/CRC/path/header/time/CSV cases.

## Explicit non-claims and next gates

This code/CI package proves only deterministic **mock behavior**. It does not
prove current legal eligibility, actual Binance checksum availability, archive
payload coverage, historical tick/step, live/PIT semantics, a G0 strategy edge,
profitability, reserve contents, production readiness, or execution authority.

A later real-data run requires, separately and in order: current terms and
access eligibility evidence, genuine 256 checksum identities, historically
defensible BAR_5M mapping evidence, operative full-roster Inventory, exact
rights-bound preregistration and run authority, independent review, and a new
Control authorization that replaces the deliberately unconfigured network
issuer. Deployment, service mutation, private API, exchange write, order,
autonomous trading, Mark Ready and merge remain separate protected gates.
