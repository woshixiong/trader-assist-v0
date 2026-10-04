# PIT historical data QA foundation V1

Package `PIT_HISTORICAL_DATA_QA_FOUNDATION_1` implements the reviewed Plan V2
in `research_data/pit_qa.py`. Import the module directly; it is not a registry,
provider adapter, admission gate, calendar service, or runtime component.

The evaluator diagnoses supplied metadata and market rows. A QA PASS grants no
access or use permission. Package A retains manifest, mapping, wire/hash,
access and admission ownership. R2 owns execution/lifecycle decisions; R2B owns
inventory/allocation/reserve/sufficiency decisions. Nothing here reclassifies a
dataset, selects a Strategy, inspects performance, opens a sealed OOS/lockbox/R5
result, repairs raw data, or changes production/trading behavior.

## Public API and pure flow

```python
normalize_local_timestamp(value: LocalTimeEvidence) -> TimeNormalizationResult
qa_rows_from_events(
    events: tuple[ExternalReferenceEvent, ...],
    *, knowledge_ns: int,
    historical_evidence: tuple[HistoricalRowEvidence, ...] = (),
) -> QaProjection
evaluate_pit_qa(request: PitQaRequest) -> PitQaResult
```

`PitQaRequest` selects one nonempty original row surface: Package A events or
`QaDiagnosticRecord` records. It supplies the manifest/snapshot, knowledge cut,
`PitQaPolicy`, historical row envelopes, sessions, actions, adjustments, universe
and source bindings. Diagnostic numeric strings deliberately permit malformed
values to reach QA. Schema violations are rejected; bound-record/hash tampering
returns `F_BOUND_INPUT_INVALID` with unavailable dependent domains. Caller-created
`QaRow` or `QaProjection` objects are not accepted as evaluation authority.

The evaluator revalidates closed immutable inputs, preserves input ordinals,
recomputes projections, binds historical facts, runs A–F, derives coverage, sorts
findings deterministically and creates an independently hashed `PitQaResult`.
There is no filesystem/network I/O, ambient evaluation clock, interpolation,
deduplication, latest-revision selection, or input mutation. Integers preserve
nanosecond clocks; Decimal arithmetic uses explicit precision/rounding.

The result binds the complete request digest plus ordered original/auxiliary
hashes, action/adjustment/session/universe/source hashes, manifest, mapping,
policy and projection digest. Thus changes in source checksum, tier/exposure,
cut, instrument roster, timezone, assertions or row order change the receipt.
`access_permission_granted` is always `False`. Hashes establish binding, not
source authenticity or legal/use authority.

## Historical bridge: no inference fallback

Every `RowEvidenceKey` is the triple `(input_kind, dataset_hash,
input_record_hash)`. Events use the exact Package A record hash; diagnostics use
their own bound hash. The key never uses a symbol, observation preference, or
current mapping lookup as a substitute.

`RowProjectionProof` binds that key, source locator/content hash, provider row
locator, literal projection version `PIT_EVENT_PROJECTION_V1`, copied-field digest
and evidence reference. A provider row locator must be supplied. An event hash
is retained as a fallback diagnostic identifier, never advertised as such a
locator. The copied-field digest covers the explicitly copied diagnostic source
view; the original event hash additionally binds all original Package A fields.

`HistoricalRowEvidence` is an immutable `BoundRecord` with HISTORICAL/SYNTHETIC
basis, half-open validity, known/recorded times and an evidence reference. Its
nullable facts are native symbol, adjustment mode/basis, revision/comparison,
price/size units, source role, projection proof, local-time evidence and finality
time. SYNTHETIC envelopes are accepted only when evaluation explicitly declares
a synthetic fixture and the existing manifest declares R0. The standalone
projection function grants no such synthetic exception.

The bridge checks hashes, exact key, copied-field proof, validity at the event,
`0 < known_at <= recorded_at <= knowledge_ns`, each nested reference's own bounds,
and availability inside the envelope. Nested known times cannot exceed envelope
known time; nested recorded times cannot exceed envelope recorded time. Revision
availability cannot exceed envelope knowledge. Facts with different availability
must be supported by a sufficiently late envelope or left unresolved. Invalid
or future evidence is rejected, not partially applied. Intrinsic units explicitly
present in context/OI contracts must not contradict supplied units.

Same-key identical envelopes emit `F_AUX_EXACT_DUPLICATE` WARN. Distinct envelopes
emit `F_AUX_CONFLICT` FAIL and neither wins. Unmatched keys fail. Cross-observation
contradictions about the same market fact also fail. No union, majority vote,
current-metadata backfill, or preferred-provider rule exists.

`instrument_id` **never** becomes `native_symbol`. Manifest/mapping metadata is
only compared with independently supplied row facts. Event `authority` never
becomes mapping `source_role`; `finalized=True` never invents finality time.
Missing bridge evidence remains null and blocks dependent predicates:

| Missing fact | Deterministic dependent finding |
|---|---|
| Native symbol | `C_NATIVE_SYMBOL_EVIDENCE_MISSING` / INSUFFICIENT_EVIDENCE |
| Adjustment mode | `B_ROW_ADJUSTMENT_UNKNOWN` / UNKNOWN |
| Adjustment basis | `B_ROW_BASIS_MISSING` / INSUFFICIENT_EVIDENCE |
| Revision | `D_REVISION_EVIDENCE_MISSING` / INSUFFICIENT_EVIDENCE |
| Comparison | `D_COMPARISON_EVIDENCE_MISSING` / INSUFFICIENT_EVIDENCE |
| Units/source role | C/D/F evidence-missing findings / INSUFFICIENT_EVIDENCE |
| Projection proof | `F_ROW_PROJECTION_EVIDENCE_MISSING` / INSUFFICIENT_EVIDENCE |
| Finality time | `A_FINALITY_EVIDENCE_MISSING` / INSUFFICIENT_EVIDENCE |

An event-only projection cannot PASS these dependent predicates.

## Status and eligibility

The frozen states are PASS, WARN, FAIL, UNKNOWN and INSUFFICIENT_EVIDENCE.
PASS means established correctness or evidenced non-applicability; WARN records
an established condition at caller-frozen warning severity; FAIL demonstrates
invalidity/contradiction; UNKNOWN means unresolved meaning; INSUFFICIENT_EVIDENCE
means an understood predicate lacks proof.

Aggregation precedence is:

```text
FAIL > INSUFFICIENT_EVIDENCE > UNKNOWN > WARN > PASS
```

All six domains must PASS for overall QA eligibility PASS. WARN also blocks PASS.
No finding is dropped because another is worse. Empty/missing/ambiguous input
surfaces and resource-bound exhaustion cannot pass. Findings retain stable codes,
instrument/ordinal/interval and sorted evidence locators. A domain with all checks
established receives its explicit `*_REQUIRED_CHECKS_ESTABLISHED` PASS receipt.

## A: time, supplied sessions and DST

`LocalTimeEvidence` carries a wall timestamp, IANA zone, optional fold/offset and
provenance. UTC round trips identify nonexistent local times (FAIL), ambiguous
times without fold (INSUFFICIENT_EVIDENCE), contradictory fold/offset (FAIL), and
unique/explicitly resolved instants (PASS). Invalid zone paths fail; unavailable
zone data stays insufficient. No fallback timezone/dependency is installed.

`SessionScheduleEvidence` supplies version, zone, cut, instrument roster,
open/closed `SessionInterval` records, cadence, origin and complete-grid semantics.
Intervals must be positive, nonoverlapping and historically evidenced. Optional
local boundaries must agree with supplied UTC bounds. Holiday/weekend/break/early
close/overnight truth is never generated. A complete assertion alone does not
silently explain uncovered space: supplied interval coverage must establish it.

Source ns/ms conversion, causal availability and original per-stream ordering are
checked. Bars require ordered bounds, matching OPEN/CLOSE stamp, declared duration,
finalized status, and explicit `bar_end <= finalized_at <= observed_at <= knowledge`.
A close-stamped bar wholly contained in the cut/session may end at the cut/session
close. Resolver, adjustment, auxiliary and state evidence must independently cover
that exact timestamp; their half-open bounds are never extended automatically.
Absent network RECEIVE remains absent.

## B: actions and adjustments

`CorporateActionEvidence` supplies instrument/action ID, type, effective and
known/recorded times, ratio and treatments. Define `r = new shares / old shares`.
Forward splits require `r > 1`; reverse splits require `0 < r < 1`.

For an explicitly declared backward split basis, pre-action price factor is
`1/r`; share-volume factor is `r` only for declared SHARE_VOLUME treatment and
SHARES units. UNCHANGED volume uses factor 1; UNKNOWN volume treatment remains
insufficient. Explicit UNADJUSTED factors are 1 and must declare that treatment.

`AdjustmentEvidence` binds instrument/cut, mode/basis/basis time, units,
completeness, action-ID factor schedule and exact-input raw-price/raw-volume pairs.
Actions compose in effective-time order; the effective-time boundary receives
post-action treatment. Factors, exact-input per-price-field raw evidence and supplied price/volume pairs
must agree within the frozen Decimal tolerance. Missing pairs/factors, future
facts, mixing, unit/basis or numerical contradictions block PASS. Every adjusted BAR open/high/low/close (or TRADE price/BBO bid/ask) needs its own
bound `raw_price_fields` proof; a matching close alone cannot establish a row PASS.
Raw pairs additionally prove the declared price/volume transformation; hashes do not
prove decoding or provenance authenticity.

Price jumps alone never prove a split. DIVIDEND/OTHER transformations and total
return adjustment remain insufficient until a supplied executable convention is
supported; this foundation invents none. Retrospective arithmetic does not create
earlier causal availability.

## C: identity, state and survivorship

The unchanged `PitReferenceResolver` requires exactly one verified mapping at
`valid_from <= event < valid_to` with both knowledge clocks no later than the
requested cut, and LISTED state. Independent row symbol/provider/venue/product,
units and source role must agree. Missing facts remain insufficient; ambiguities,
wrong reused-ticker owner, future mapping, state violations and contradictions fail.

`UniverseEvidence` supplies complete historical membership/state intervals,
provenance, cut and survivorship limits. Missing/incomplete state history cannot
PASS. HALTED/DELISTED intervals explain absence only when explicitly evidenced;
rows in them fail. Symbol changes require supplied continuity assertions. A
present-day/prospective basis is not a historical bridge. Nonoverlapping ticker
reuse is evaluated with the existing half-open owner rules.

## D: rows, duplicates, revisions, comparisons and outliers

Stream identity is provider/venue/product/instrument/payload-kind/source-mode.
Native identity adds native ID. Market-fact identity includes payload values,
sequence, source timestamp/unit and bar bounds/stamp. Observation/init/receive
changes alone do not create conflicting facts. Same identity/same fact is an
exact duplicate at frozen WARN/FAIL severity; different fact is FAIL. Distinct
native IDs sharing one required bar slot fail. No data is removed.

Finite Decimal strings, positive prices, nonnegative sizes, OHLC containment,
BBO ordering and declared sequence continuity are checked. FUNDING/PREMIUM may be
signed; MARK/INDEX/ORACLE prices must be positive. Unknown sequence meaning stays
UNKNOWN. Depth shapes without a supported diagnostic projection cannot PASS.

`HistoricalRevisionFact` requires explicit UNREVISED/REVISED/UNKNOWN evidence,
revision ID, availability and predecessor binding. VALIDATE_CHAIN requires an
available predecessor for the same stream/event with earlier revision availability;
REJECT_REVISED rejects it. Revision labels never excuse duplicate conflicts or
select a latest row.

`HistoricalComparisonFact` requires an evidenced comparison group and exact
counterpart hashes, or explicit evidenced non-applicability. Comparisons require
reciprocal identity, different providers, same event/instrument/type, compatible
units/basis and frozen tolerance. Missing counterparts are insufficient;
incompatible binding fails; numerical disagreement uses frozen WARN/FAIL severity.

`OutlierPolicy` binds units, explicit bounds, contiguous same-stream adjacency,
across-session treatment and severity. Missing policy is UNKNOWN. Adjacent bar
comparisons require contiguous bounds; nonbar comparisons require evidenced
contiguous sequence. No repair, statistical threshold fitting, or Strategy returns
are generated.

## E: expected coverage and gaps

Expected bars come only from supplied cut/session intervals, positive cadence and
origin. Only complete grid intervals are expected. Partial boundaries remain
insufficient; invalid/off-grid rows fail. Unsupported nonbar continuity stays
insufficient rather than inventing a cadence.

`CoverageDiagnostic` reports expected, present-unique, missing, invalid and duplicate
counts, first/last expected/observed boundaries and interval gap kinds. Exact
duplicates do not inflate present-unique coverage. Supplied closures produce
SESSION_EXPLAINED PASS; supplied HALTED/DELISTED absence produces STATE_EXPLAINED
PASS; expected in-session absence uses frozen WARN/FAIL. Uncovered calendar space
produces DATA_MISSING_OR_UNKNOWN / INSUFFICIENT_EVIDENCE. No interpolation occurs.

## F: provenance completeness

Package A continues to validate exact `REQUIRED_DATASET_METADATA` keys and hashes.
UNKNOWN placeholders remain UNKNOWN; N/A assertions without predicate evidence
remain insufficient. Semantic declarations are compared with independently supplied
evidence: mapping/universe hashes, session version, missing/duplicate/disagreement
severities, outlier hash, revision policy, timezone/DST convention and action/
adjustment policy. Adjustment mode declarations avoid a manifest→row→adjustment→
manifest hash cycle; full adjustment/action record hashes are bound in the result.
Opaque Strategy version/question provenance is never evaluated as performance.

`SourceBindingEvidence` binds manifest hash, locator, checksum, supplied bytes and
projection-proof hashes. Bytes are checked in memory; no locator is opened.
Source checksum, row projection and supporting source-to-record assertions are
separate requirements. Missing support blocks PASS. Evidence hashes establish
integrity/binding only; no authenticity or access permission is claimed.

## Synthetic acceptance and validation

`tests/test_research_data_pit_qa.py` supplies complete synthetic R0 A–F evidence,
including every bridge fact, explicit action-free UNADJUSTED treatment, source
bytes, row proof, calendar/state history, policies and explicit comparison N/A.
Split/reverse-split and action-chain fixtures additionally provide factors and
exact-input raw pairs; provider fixtures supply reciprocal comparison identity.

The Plan V2 named matrix covers event-only/null projection; no symbol/metadata
fallback; hash/key/locator/availability failures; duplicate/conflicting auxiliary
records; each required missing fact; DST/offset/ns precision; sessions/finality;
future/ambiguous mapping, ticker reuse, listing/halt/delisting, symbol continuity
and survivorship; split factors/basis/volume/dividends; native/bar duplicates,
nonfinite/OHLC/BBO/signed values; sequence/revision/provider/outlier policies;
closure/state/missing/partial/grid gaps; empty inputs; provenance/checksum;
aggregation/determinism/input immutability; closed performance fields and unchanged
Package A wire/access behavior. Additional tests cover envelope availability,
resource bounds, intrinsic source units and independent close-boundary evidence.

Run the package's frozen validation matrix in the existing qualified Python 3.12
venv: focused PIT tests, five Package A regression files, focused ruff/mypy,
repository ruff/mypy/compileall, V5 governance, schema export check, secrets scan,
installed dependency-lock verification, full pytest excluding only the specified
V4 governance file, diff whitespace and combined tracked/untracked allowlist.
No dependencies, package exports, schema registries, calendars, providers or
execution surfaces are changed. Required ownership/dependency/path expansion must
return CONTROL_REPLAN before affected mutation.
