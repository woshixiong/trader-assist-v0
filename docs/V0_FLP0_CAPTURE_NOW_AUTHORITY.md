# V0 FLP0 Capture Now Authority

## Authority Snapshot

```text
CURRENT_STATE_KIND: SAFE_STOP_SNAPSHOT
CURRENT_MAIN_BASE_SHA: 16963297e0ce27ed3919f52e1e536ff730f5a5b9
HISTORICAL_PR15_TASK_ID: V0-FLP1B0B-CAPTURE-NOW-AUTHORITY-AMENDMENT
HISTORICAL_PR15_BASE_SHA: 78d2d37bfe5a4f3f1d382a2a96e57896ae9676ae
HISTORICAL_PR15_HEAD: b7c26c019f64ab627dffc3bde4ab5a35071b6fc5
PR15_MERGE_COMMIT: 95e4a9ebaedb028de68d859627a37dfc142c8602
POST_MERGE_AUTHORITY_SYNC_PR: 16
LAST_POLICY_STATE_PR: 15
ACTIVE_MILESTONE: V0-R0-CAPTURE-ONLY
ACTIVE_TASK_ID: V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME-CANDIDATE
ACTIVE_WRITE_LEASE: V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME-WRITE-LEASE-1
R0: CAPTURE_ONLY
R1: ETH_OPERATOR_ASSIST
FIRST_LAUNCH_PRIMARY_ASSET: ETH
BTC_FIRST_LAUNCH_REQUIREMENT: NONE
BTC_FIRST_LAUNCH_BLOCKER: NO
T1: CONTRACT_SCHEMA_GOVERNANCE_ONLY
T2_HISTORICAL_T1_AUTHORITY: SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME
T2_CURRENT_BRANCH_STATUS: DEFAULT_OFF_IMPLEMENTATION_CANDIDATE
NEXT_GATE: V0-FLP1B0B-FIRST-LAUNCH-CRITICAL-PATH-AND-ETH-MINIMUM-VALIDATION-READONLY-PLANNING
```

T1 freezes the Capture Now authority contract, generated JSON Schema, governance
state, and documentation. It starts no runtime, opens no socket, performs no DNS
or endpoint connection, writes no database or filesystem evidence, and grants no
strategy, risk, account, credential, or exchange execution authority.

T1 remains the historical contract/schema authority. T2 is a minimal
implementation candidate and does not change R0 into a signal product. Its fixed
ETH 5m/15m public WebSocket runtime is default-off. This implementation task does
not connect to the endpoint or create a real permit. After merge and separate
project-control approval, one external durable single-use permit may authorize
exactly one controlled connection attempt. The application protocol heartbeat is
allowed only to maintain that existing one connection. Automatic reconnect,
backfill, and Info HTTP remain prohibited, as do strategy, signal, risk, account,
credential, and execution capabilities. `PROJECT_STATE.json` remains the
unchanged historical safe-stop snapshot, including historical PR #16 authority.

## Plane Boundary

`RAW_PUBLIC_EVIDENCE_PLANE` remains the A0-A6 offline raw-evidence authority:
canonical JSON, SHA-256, `RawEventV0` identity, content-addressed evidence,
manifest, checkpoint, replay, and root-wide single-writer rules.

`CAPTURE_AUTHORITY_PLANE` is a separate Capture-only contract plane. It may
reference evidence IDs and hashes, but T1 does not connect it to RawEvent,
Bronze, ingress, replay runtime, normalized events, Silver, strategy, AI, risk,
dashboard, account observation, Testnet/Mainnet execution, or exchange writes.

## R0 and R1

R0 is `CAPTURE_ONLY`:

- `release_id = V0-R0`
- `primary_asset = ETH`
- `active_strategy_count = 0`
- `capture_contracts_authorized = true`
- `network_runtime_authorized = false`
- `strategy_runtime_authorized = false`
- `signal_recommendation_authorized = false`
- `risk_sizing_authorized = false`
- `trade_plan_authorized = false`
- `account_runtime_authorized = false`
- `exchange_execution_authorized = false`
- no ETH-LDAR, signal recommendation, OI/funding strategy requirement,
  deterministic risk, TradePlan, FAST/STANDARD presentation, account/order/fill
  observation, manual-execution workflow, or registry requirement

R1 preserves the former future ETH Operator Assist semantics: ETH-only,
ETH-LDAR or separately approved future ETH strategy, `LONG`/`SHORT`/`WAIT`,
deterministic risk, TradePlan, FAST/STANDARD presentation, human review, manual
execution, read-only account/order/fill observation, plan/outcome matching,
replay, and learning loop. In T1 it remains future, not implemented, and not
authorized.

The former human-confirmed automated execution controls are deferred under
`future_human_confirmed_execution`, with no release assigned, release authority
false, status `DEFERRED_SEPARATE_G4_GATE`, autonomous entry prohibited, human
confirmation required, implementation unauthorized, Testnet unauthorized, and
Mainnet unauthorized.

## Capture Contract

`CaptureRecordV0` is a `record_type` tagged union containing exactly
`SignalCaptureV0`, `CapturePlanV0`, `ShadowOrderIntentV0`,
`HumanObservationV0`, `MarketPathEvidenceV0`, `CaptureLifecycleEventV0`,
`RuntimeControlEventV0`, and `CaptureKillStateV0`. The schema `$defs` contains
all 15 Capture objects, including manifest, checkpoint, replay, local safety,
and endpoint allowlist contracts.

Capture plans are structured non-executable evidence references. They contain
an ordered, unique, non-empty `evidence_refs` tuple and no free-text summary.
They are not TradePlans and cannot carry size, notional, leverage, risk,
authoritative entry, stop, take profit, order type, submit, execute, permit,
metadata, dictionary, or JSON-blob fields. `WAIT` allows zero or one
non-actionable CapturePlan and zero ShadowOrderIntent records. Shadow intents
contain only the fixed `NON_EXECUTABLE_MARKET_PATH_HYPOTHESIS` kind and an
ordered, unique, non-empty evidence-reference tuple. They are shadow-only,
non-executable, never exchange-submittable, and expose no free-text authority
channel.

Signal, Plan, and Shadow machine evidence references must resolve to exactly
one earlier `MarketPathEvidenceV0` record version in manifest order. Missing,
ambiguous, future, or differently typed Capture records cannot serve as machine
evidence. Validators treat references as opaque IDs; they do not parse strings
as JSON, natural language, order parameters, permits, or execution authority.

`HumanObservationV0.observation_text` is an operator note only. No graph,
ledger, replay, lifecycle, or runtime-control validator reads it, or any other
bounded display text, as Plan, Shadow, order, execution, sizing, or permit
authority.

Market-path evidence is grouped by `market_path_series_ref` in manifest order.
One series keeps one source identity; its normal chain starts at sequence zero,
increments by exactly one, and never overlaps, moves backward, or extends a
previous finalized window. Corrections and supersessions must target an earlier
record in the same series, source, sequence, and exact window. New market data
requires a new sequence record. Missing ranges remain ordered, unique, and
non-overlapping. Market-path evidence does not adjudicate PnL, MFE, MAE,
R multiple, winners, or outcomes.

Lifecycle events and runtime-control events have different `record_type`, hash
domains, legal event kinds, and validators. Lifecycle subjects are limited to
Signal, Plan, Shadow, HumanObservation, and MarketPath records. Created events
have no correction, supersession, or references; corrected and superseded
events carry exactly their matching earlier same-type target; window-finalized
events apply only to MarketPath. Lifecycle events cannot carry start permits,
connection, kill, resume, or recovery authority.

Runtime-control events form per-`runtime_scope_ref` chains in manifest order.
Start carries only one single-use permit, kill carries only a real earlier kill
state, integrity completion carries only its integrity reference, and resume
carries permit, integrity, and current unresolved kill references. Permits are
single-use across start and resume. Resume requires an integrity event after the
matching kill and before resume; it resolves that kill exactly once. Capture
record IDs cannot masquerade as runtime scopes, permits, integrity references,
or kill states.

Permit references are globally single-use. Each integrity reference has one
completion event and one owning runtime scope. Each kill-state record ID has
one owning scope and cannot be re-engaged or resumed after global resolution.
Resume requires the unresolved kill and integrity completion owned by its own
scope. Independent scopes remain valid only with distinct kill, integrity, and
permit authority.

Kill state always fails closed and remains runtime unauthorized. Killed state
has no resume references; blocked state has no permit or runtime event and may
refer only to an earlier completed integrity check; permitted state requires a
matching earlier valid resume event, its new single-use permit, and integrity
reference.

## Pure Ledger Validation

`validate_capture_record_graph`, `validate_capture_manifest_chain`,
`validate_capture_checkpoint`, `validate_capture_checkpoint_advance`,
`build_capture_replay_report`, and `validate_capture_replay_report` are pure
in-memory contract functions. They accept exact tuples and exact concrete
Capture models, keep no mutable global state, perform no I/O or networking, and
grant no runtime or execution authority.

Manifest entries bind observation slot, writer epoch, writer authority, record
ID/hash, duplicate classification, previous hash, and entry hash. Entry indexes
start at zero and are contiguous; the hash chain, writer epoch, and writer
authority are constant. Aggregate identity is the exact version key
`(record_id, record_hash)`. The unique manifest version set exactly equals the
provided unique version set. Identical version keys cannot be duplicated in the
records tuple, while the same record ID with different hashes is representable.
First slot/version use is `UNIQUE`; the same slot and version key is
`EXACT_DUPLICATE`; the same slot with a different version key is
`CONFLICTING_DUPLICATE`. All versions of one record ID must retain the original
slot, so neither an exact version nor a same-ID conflict can evade detection by
changing slots.

Manifest chronology and positions use version keys. Every ID-only graph
reference passes one resolver: zero versions is missing, one is exact, and more
than one is ambiguous. No validator silently chooses one hash version. A
correctly classified same-ID/different-hash conflict is a valid diagnostic
manifest fact, but ambiguous graph references fail and the conflict forces
replay `FAIL`; no validator chooses a latest value.

Checkpoints bind genesis root, terminal hash/index, manifest and unique-version
counts, writer epoch/authority, and finalized integrity-only state. Exact
duplicate manifest entries do not increase `record_count`; conflicting versions
do. Advance
validation accepts an exact duplicate checkpoint or an append-only manifest
extension with the old chain as an exact prefix and the same root. Truncation,
rollback, count regression, and history rewrite fail closed.

Replay reports are built deterministically from records, manifest, and
checkpoint. Public direct `bind` is prohibited. Consumers must call
`validate_capture_replay_report`, which rebuilds and compares every field even
when a supplied report has an internally valid hash. `PASS` requires valid graph
and chain integrity, valid checkpoint binding, zero missing references, and zero
conflicting duplicates. Reports contain no PnL, profitability, win rate, Sharpe,
MFE/MAE, R multiple, winner, outcome, or promotion authority.

An ambiguous same-ID graph reference does not masquerade as missing evidence:
zero-version references increment `missing_reference_count`, while multi-version
ambiguity makes graph/chain integrity fail. A correctly classified conflict can
therefore produce a deterministic, externally revalidated `FAIL` report without
making manifest or checkpoint validation choose a version.

## Exact PR Scope Gate

Normal pytest validates a frozen static 10-file contract and does not read Git
history. The explicit PR CLI reads committed, staged, and unstaged
`--name-status -z --no-renames` byte streams and requires the frozen committed
map of ten modifications and zero additions. Scope authority is exact
changed path/status authority, not Git copy provenance. With `--no-renames`, a
rename deterministically appears as source `D` plus destination `A`; deletion
and the missing/unexpected/status mismatch therefore fail without similarity
thresholds or `renameLimit` behavior.

Copying content from an unchanged source into an authorized A/M target adds no
changed path and is not file-scope expansion; that target remains fully subject
to content review and its exact frozen status. Copying into an unauthorized
target fails as an unexpected `A`. No semantic-copy or provenance-copy
detection is claimed. Untracked files, deletion, type change, unmerged, unknown,
broken, non-UTF-8, truncated or malformed NUL data, status mismatch, and
unexpected paths all fail closed. Tabs and newlines remain path bytes rather
than record delimiters. The CLI performs no fetch, network, or GitHub API call
and accepts only an explicit 40-character base SHA.

## Local Safety and Endpoint Allowlist

`CaptureLocalSafetyPolicyV0` is a local safety policy, not a Hyperliquid
official fact. It fixes one active WebSocket connection, one connection attempt
per manual durable single-use non-replayable start permit, no automatic
reconnect, no automatic backfill, no active probes, and no Info HTTP requests.
It adds no cooldown, automatic resume, or permit reuse.

`CaptureEndpointAllowlistV0` remains the T1 ratified contract-only authority; its
`runtime_authorized` field remains false. T2 does not rewrite that historical
contract or claim global live-transport authorization. Its separate local
single-use permit gate is bounded to the fixed candidate runtime.
It allows only `hyperliquid-public-mainnet` endpoint `hl-ws-mainnet-public`,
WebSocket public read-only observation, operation `candle`, coin `ETH`,
intervals `5m` and `15m`, capture mode `WS_TEXT_UTF8_APPLICATION_PAYLOAD`,
source catalog version `hyperliquid-public-mainnet.0.1.0`, and source catalog
hash `0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7`.
It rejects BTC, Info HTTP, `candleSnapshot`, `1m`, `3m`, `1h`, other endpoints
or operations, private/account/exchange surfaces, credentials, reconnect,
backfill, and `runtime_authorized = true`.

## Rate-Limit Authority

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
CONFLICT_STATE: OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED
SUPERSESSION_STATE: EFFECTIVE_VARIANT_UNDETERMINED
AUTHORITY_HASH: 0e327e566589d8030ff00d4d009eb4b6827679ab508133d66840b2c245dc53df
SOURCE_CATALOG_HASH: 0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7
SOURCE_COUNT: 2
FACT_COUNT: 25
UNKNOWN_COUNT: 14
```

The following gates remain false: `transition_eligible`,
`live_transport_authorized`, `account_readonly_runtime_authorized`,
`testnet_execution_authorized`, `mainnet_execution_authorized`, and
`flp1_implementation_authorized`. The T1 write lease is not runtime or product
implementation authority.
