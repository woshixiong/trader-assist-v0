# V0-01 Data Plane

## A0 completed evidence flow

```text
frozen public source catalog + catalog-entry hash
  -> exact application-payload bytes
  -> SHA-256 content identity
  -> catalog-bound observation-slot v2 identity
  -> catalog-bound raw-observation v2 identity
  -> immutable content-addressed payload
  -> kernel-backed root-wide ManifestWriter authority
  -> complete-root authority scan and conflict decision
  -> append-only hash-linked manifest + file/directory fsync
  -> one-time completion checkpoint
  -> deterministic offline replay report
```

## A1 contract-freeze insertion point

```text
official public source catalog
  -> A1 candle envelope policy: data:Candle or data:Candle[]
  -> A1 rate-limit entry gate: UNRESOLVED_OFFICIAL_LIMIT blocks live transport
  -> A1 read-only transport configuration checks
  -> A1 fixture admission policy
  -> exact RawEventV0 application-payload bytes only
```

A1 adds no transport runtime, parser, database, dashboard, strategy, AI, or risk layer.

## A2 no-network ingress insertion point

```text
caller-supplied public observation bytes
  -> A2 no-network ingress contract/helper
  -> A1 validate_read_only_transport_entry()
  -> unresolved rate-limit gate keeps live transport blocked
  -> exact payload SHA-256 + content-addressed payload ref
  -> RawEventV0.bind_observation()
  -> optional BronzeStore.write_payload()
  -> optional ManifestWriter.append()
```

A2 adds no live transport, reconnect, health, backfill, async runtime, database, strategy, AI, or risk layer.

## A3 public read-only preflight insertion point

```text
future collector configuration
  -> A3 validate_public_readonly_transport_preflight()
  -> A1 validate_read_only_transport_entry()
  -> source / environment / operation-class authority
  -> endpoint / operation / coin / interval / capture-mode authority
  -> runtime_enabled absent or false
  -> kill switch fail-closed
  -> credential absence + account/private absence + no-write/no-execution proof
  -> live_transport_authorized false while rate limits remain unresolved
```

A3 adds no HTTP/WebSocket client, socket, live connection, polling, reconnect, heartbeat, health, backfill, async runtime, database, strategy, AI, or risk layer.

`mainnet public read-only` is only a public source identity / environment label. It is not Mainnet execution enablement and does not authorize private endpoints, user/account endpoints, `/exchange`, order mutation, signing, nonces, wallets, credentials, or kill-switch bypass.

## A4 official rate-limit authority insertion point

```text
frozen official rate-limit source identity
  -> source_kind = official
  -> title = Rate limits and user limits
  -> official GitBook location
  -> status in {UNRESOLVED_OFFICIAL_LIMIT, OFFICIAL_NUMERIC_LIMIT_RESOLVED}
  -> unresolved state rejects all numeric material
  -> resolved candidate requires readable official source
  -> resolved candidate requires field names + units + operation scope
  -> ambiguity fails closed
  -> live_transport_authorized remains false
```

A4 rejects community, third-party, inferred, remembered, blog, forum, Discord, StackOverflow, and model-memory authority metadata. A4 encodes no numeric rate-limit values and adds no live transport capability.

## A5 offline candle extraction insertion point

```text
exact RawEventV0 authority + caller-supplied exact payload bytes
  -> exact-class RawEvent revalidation
  -> content-type / encoding / payload length / payload SHA-256 match
  -> supported candle endpoint + operation + capture-mode gate
  -> strict UTF-8 JSON parse with duplicate-key / BOM / non-finite rejection
  -> exact frozen candle field set
  -> exact numeric parse without binary-float conversion
  -> timestamp / OHLC / volume / trade-count invariants
  -> coin + interval equality with RawEvent authority
  -> domain-separated candle logical key
  -> ordered tuple of typed ExtractedCandleV0 items
  -> domain-separated CandlePayloadExtractionV0 hash
```

A5 supports only `hl-ws-mainnet-public/candle` and `hl-info-mainnet-public/candleSnapshot`. It accepts WebSocket `data:Candle`, WebSocket `data:Candle[]`, and Info `Candle[]` according to the frozen envelope authority. Empty arrays yield zero items and no sentinel/default event.

A5 does not read `payload_ref`, open files, connect to endpoints, execute REST requests, write Bronze or manifests, emit `NormalizedEventV0`, enter Silver, decide candle finality, order revisions, reconcile WebSocket and Info observations, detect gaps, backfill, generate health, strategy, AI, risk, dashboard, or execution output.

## A6 offline cross-source reconciliation insertion point

```text
exact A5 WebSocket extraction + exact A5 Info extraction
  -> strict current-representation checks before any coercive conversion
  -> independent exact-class A5 authority, logical-key and extraction-hash revalidation
  -> frozen endpoint / operation / envelope role validation
  -> identical source / coin / candle-interval identity gate
  -> one contract-layer derivation authority builds the complete logical-key union
  -> deterministic (open_time_ms, candle_logical_key) ordering
  -> exact comparable-field equality in frozen field order
  -> MATCH / CONFLICT / WS_ONLY / INFO_ONLY items
  -> exact status counts
  -> embed both complete A5 extraction authorities and matching scalar authority
  -> domain-separated CandleCrossSourceReconciliationV0 hash over all authority
  -> runtime reconstructs and requires the same exact complete union
```

A6 binds each item to its logical identity, nullable WS/Info candle and extraction authorities, and exact ordered differences. The report also embeds both complete A5 extraction authorities, and its scalar source-event and extraction-hash fields must match them. `bind()` accepts only those two exact extractions; the data layer calls the same derivation authority. Every accepted report independently revalidates the embedded A5 authorities and reconstructs comparisons, membership, ordering, differences, and counts from their exact logical-key union before checking the final hash. Identity inconsistency fails closed. Empty/empty inputs yield an empty comparison tuple and four zero counts.

The portable A6 JSON Schema validates structure, mandatory serialized fields for both embedded A5 authorities, JSON types and patterns, frozen WS/Info role pairings, status/source-presence constraints, and canonical ASCII nonnegative integer strings for close-time and trade-count differences. Schema validation alone does not authenticate an A6 report; runtime semantic validation remains mandatory for A5/A6 hash recomputation, exact A5 authority, extraction membership, dynamic counts, uniqueness, canonical item and difference ordering, cross-item identity, exact difference authority, and complete-union proof.

A6 applies no tolerance, normalization, source priority, latest-wins rule, revision ordering, finality inference, or canonical winner selection. It emits no `NormalizedEventV0`, writes no Silver or other persistence, and adds no network, health, gap, backfill, strategy, AI, risk, dashboard, credential, or execution capability.

## Current authority state

```text
PROGRAM: V0-FAST-LAUNCH
STATE_BASE_SHA: c507e2fc1bad6aca175cf833e5bcca63224c3e5f
LAST_COMPLETED_IMPLEMENTATION: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
LAST_COMPLETED_IMPLEMENTATION_PR: 11
LAST_POLICY_STATE_PR: 12
ACTIVE_IMPLEMENTATION: NONE
ACTIVE_WRITE_LEASE: NONE
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
NEXT_GATE: V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE
```

## Identity separation

`payload_sha256` hashes exact bytes. JSON whitespace or key ordering therefore changes payload identity.

The v2 observation slot binds catalog version, catalog hash, catalog-entry hash, source, endpoint, operation, coin, candle interval, capture mode, connection, subscription, and collector-local receive sequence. The v2 raw observation identity additionally binds payload hash. Collector-local sequence is never represented as a venue sequence.

A5 preserves RawEvent authority unchanged. `CandlePayloadExtractionV0` separately binds the source event ID, payload hash, endpoint, operation, coin, interval, envelope shape, ordered typed candle items, and extraction hash.

The candle logical key binds source ID, coin, interval, and open time. It excludes endpoint so a later separately reviewed reconciliation slice may compare WebSocket and Info observations of the same logical candle. A5 performs no reconciliation or latest-wins decision.

Within one Bronze persistence root, an observation slot and source-event ID remain globally unique rather than segment-local. A5 adds no persistence authority.

## A1 public source envelope authority

The candle WebSocket contract accepts only:

```text
data: Candle
data: Candle[]
```

These tokens describe public envelope policy and payload shape. They are not runtime subscription, connection, or transport-recovery code.

## A1/A2/A3/A4/A5/A6 rate-limit authority

`RATE_LIMIT_STATUS` remains `UNRESOLVED_OFFICIAL_LIMIT`. While present, the gate blocks live public transport, polling, reconnect, backfill, and health runtime. A5 and A6 are offline and do not weaken or bypass this gate.

Only the frozen official Hyperliquid rate-limit source identity may supply authority metadata. Even a resolved metadata candidate does not by itself authorize live transport.

## A1/A3 read-only transport entry checks

The pure contract checkers accept only the frozen source, public read-only environment and operation class, ETH/BTC when required, candle intervals `1m`, `3m`, `5m`, `15m`, `1h`, WebSocket capture as `WS_TEXT_UTF8_APPLICATION_PAYLOAD`, and Info capture as `HTTP_RESPONSE_BODY`. They reject private, user/account, wallet/signing, nonce, order, exchange-write, unsupported source/environment/coin/interval/capture-mode, credential, kill-switch bypass, and execution selections.

## A1 fixture admission

Fixtures committed to Git must be synthetic documentation-derived or minimal redacted examples, sanitized, and explicitly provenanced. Real raw observations, market/account logs, wallet addresses, API keys, signatures, nonces, credentials, database/cache artifacts, and unredacted operational payloads are forbidden. A5 adds no payload fixture.

## Persistence

Payloads use `payloads/sha256/<prefix>/<digest>.payload`. Manifest lines use `manifests/<UTC-date>/<segment>.jsonl`. Completion checkpoints use `manifests/<UTC-date>/<segment>.checkpoint.json`. Paths are portable relative paths; absolute paths are never hashed or serialized into authority records.

Payload publication writes and fsyncs a same-filesystem temporary file and atomically links it into its immutable final name without overwrite. Manifest append runs under root-wide writer authority, validates every manifest, performs global idempotency/conflict checks, writes one JSON line, fsyncs the manifest, and fsyncs the parent directory before authority may be released.

`ManifestWriter.close()` releases authority but does not claim completion. `ManifestWriter.finalize()` validates and fsyncs the manifest while authority remains continuously held, publishes a one-time self-hashed checkpoint, fsyncs the parent directory, and then closes.

## Lock and path authority

A0 uses a root-wide exclusive non-blocking `fcntl.flock` on a supervisor-provisioned lock file in the `authority_anchor` directory. The protocol does not create or delete lock pathname markers. Root-path loss, replacement, descriptor mismatch, or uncertain close transitions the writer to a fail-closed terminal state.

Authoritative opens walk directory file descriptors, reject symlinks, and compare device/inode identity. The kernel lock is advisory; all cooperative writers must use the protocol. Privileged local actors able to bypass advisory locks or mutate supervisor authorities remain outside the stated A0 threat boundary.

## Replay

Replay performs no networking and requires a valid completion checkpoint. It verifies manifest framing, schemas, fixed versions, index continuity, segment identity, hash chain, checkpoint binding, payload confinement/existence/type/length/SHA-256, global observation authority, terminal hash, and orphan status.

An unfinalized segment, missing/invalid checkpoint, tail deletion, corrupt evidence, conflicting authority, unexpected tree entry, or orphan payload yields `FAIL`. A zero-entry segment passes only with an explicit completed zero-entry checkpoint.

## Fast Launch target data plane

```text
Source Adapter
-> Raw Observation
-> Validation
-> Normalized Data Product
-> Feature Provider
-> StrategyInput
-> ETH-LDAR-v0.1
-> LONG / SHORT / WAIT
-> deterministic risk sizing
-> TradePlan
-> FAST / STANDARD signal card
-> Human Decision
-> manual exchange action
-> read-only account/order/fill observation
-> plan/outcome matching
-> replay and learning findings
```

A strategy must never consume raw exchange JSON directly. Every normalized data product and strategy has a versioned manifest; dependencies are explicit, and new data cannot silently affect an existing strategy.

R0 requires ETH 5m and 15m candles, mark/mid reference, ETH OI, Funding, timestamps, freshness, gap/conflict state, heartbeat, reconnect, bounded backoff, and replay-compatible records. These are frozen product requirements, not current live runtime authority.

Read-only account/order/fill observation is also a future R0 requirement, but `ACCOUNT_READONLY_RUNTIME_AUTHORIZED` remains false. FLP1 scope freeze must separately define identity, privacy, matching confidence, failure states, and CSV/XLSX fallback authority before implementation.

R0 ends at system assistance and manual exchange execution. R1 may add human-confirmed execution only through a separately reviewed G4 gateway with immutable OrderIntent, idempotency, expiry, revalidation, fill-aware protection, kill switch, dead-man protection, audit, Testnet, shadow, and limited-capital canary gates. Autonomous entry remains prohibited.

## Next gate

A6 completion and the FLP0 authority freeze do not authorize live public transport, health, reconnect, backfill, finality inference, revision ordering, canonical winner selection, normalized events, Silver, strategy runtime, AI recommendation runtime, risk runtime, dashboard runtime, account observation runtime, Testnet/Mainnet execution, or exchange writes. The next gate is `V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE`. Every future slice still requires a separate exact-main scope freeze, explicit write lease and file allowlist, applicable CI success, external independent review, and separate finalization authorization.
