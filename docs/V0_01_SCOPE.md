# V0-01 Scope

## Completed slices

`V0-01A0 / BRONZE_AND_OFFLINE_REPLAY`

A0 froze public source definitions and implemented an entirely offline evidence path: exact synthetic application-payload bytes, catalog-bound domain-separated observation identities, immutable content-addressed local storage, root-wide single-writer observation authority, hash-linked manifests, one-time segment completion checkpoints, strict integrity verification, and deterministic replay reports.

A0 remains offline. It does not authorize live endpoint connection, runtime polling, WebSocket transport, reconnect, health, backfill, strategy, AI recommendation, risk sizing, or exchange execution.

`V0-01A1 / SOURCE_ENVELOPE_TRANSPORT_ENTRY_CONTRACT_FREEZE`

A1 froze public envelope policy, rate-limit entry authority, future read-only transport configuration checks, fixture admission policy, and the A1-to-A2 gate. A1 does not implement live transport.

`V0-01A2 / NO_NETWORK_PUBLIC_OBSERVATION_INGRESS_CONTRACT`

A2 added a bounded no-network ingress contract/helper layer. It accepts caller-supplied exact public observation bytes, validates every selection through the A1 public read-only transport-entry contract, binds exact bytes into `RawEventV0` authority, and can optionally persist payloads / append RawEvent entries through existing A0 Bronze authority. A2 does not implement live transport.

`V0-01A3 / PUBLIC_READONLY_TRANSPORT_PREFLIGHT_CONTRACT`

A3 froze a pure public read-only transport preflight contract for a future collector runtime. It validates configuration authority only and does not implement live transport.

`V0-01A4 / OFFICIAL_RATE_LIMIT_AUTHORITY_FREEZE`

A4 froze the official-only rate-limit authority contract required before any future public read-only live transport runtime. `RATE_LIMIT_STATUS` remains `UNRESOLVED_OFFICIAL_LIMIT`, no numeric limit values are encoded, only the frozen official source identity is accepted, and live transport remains unauthorized.

`V0-01A5 / OFFLINE_CANDLE_PAYLOAD_EXTRACTION_CONTRACT`

A5 added a bounded offline-only typed extraction contract. It consumes an exact `RawEventV0` and caller-supplied exact matching candle payload bytes and emits a deterministic, domain-separated `CandlePayloadExtractionV0`. It does not read `payload_ref`, connect to endpoints, write Bronze, emit `NormalizedEventV0`, enter Silver, reconcile revisions, or infer finality.

## Active slice

```text
ACTIVE_IMPLEMENTATION_SLICE: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
ACTIVE_IMPLEMENTATION_WRITE_LEASE: BOUNDED
```

A6 is an offline-only pairwise reconciliation contract. It consumes exact independently revalidated A5 WebSocket and Info candle extractions, compares the union of A5 logical candle keys, and emits a deterministic hash-bound report. It does not parse payloads, read `payload_ref`, connect to endpoints, write Bronze, emit `NormalizedEventV0`, enter Silver, order revisions, infer finality, select a canonical winner, or generate health, strategy, AI, risk, dashboard, or execution output.

## Fixed A0 authority versions

```text
A0_SCHEMA_VERSION: 0.1.0
RAW_IDENTITY_VERSION: trader-assist-v0/raw-observation/v2
OBSERVATION_SLOT_VERSION: trader-assist-v0/raw-observation-slot/v2
MANIFEST_FORMAT_VERSION: 0.1.0
MANIFEST_HASH_CHAIN_VERSION: trader-assist-v0/raw-manifest-entry/v1
MANIFEST_CHECKPOINT_VERSION: 0.1.0
MANIFEST_CHECKPOINT_HASH_VERSION: trader-assist-v0/raw-manifest-checkpoint/v1
REPLAY_REPORT_VERSION: 0.1.0
REPLAY_REPORT_HASH_VERSION: trader-assist-v0/bronze-replay-report/v1
```

A0 supports only these values. Callers cannot override them, and generated JSON Schemas expose them as `const` authorities where applicable.

## A1/A3/A4 authorities preserved

```text
A1_CONTRACT_ID: V0-01A1-SCOPE-FREEZE
A3_CONTRACT_ID: V0-01A3-PUBLIC-READONLY-TRANSPORT-PREFLIGHT-CONTRACT
A4_CONTRACT_ID: V0-01A4-OFFICIAL-RATE-LIMIT-AUTHORITY-FREEZE
SOURCE_ID: hyperliquid-public-mainnet
SOURCE_CATALOG_HASH: 0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7
ENVIRONMENT: mainnet public read-only
OPERATION_CLASS: public read-only observation only
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
RATE_LIMIT_ALLOWED_STATUSES: UNRESOLVED_OFFICIAL_LIMIT, OFFICIAL_NUMERIC_LIMIT_RESOLVED
CANDLE_WS_ENVELOPE_SHAPES: data:Candle, data:Candle[]
CAPTURE_MODES: WS_TEXT_UTF8_APPLICATION_PAYLOAD, HTTP_RESPONSE_BODY
ALLOWED_COINS: BTC, ETH
RUNTIME_CANDLE_INTERVALS: 1m, 3m, 5m, 15m, 1h
```

## A5 frozen authorities

```text
A5_CONTRACT_ID: V0-01A5-OFFLINE-CANDLE-PAYLOAD-EXTRACTION-CONTRACT
CANDLE_EXTRACTION_SCHEMA_VERSION: 0.1.0
CANDLE_EXTRACTION_HASH_VERSION: trader-assist-v0/candle-payload-extraction/v1
CANDLE_LOGICAL_KEY_VERSION: trader-assist-v0/candle-logical-key/v1
SUPPORTED_SELECTIONS: hl-ws-mainnet-public/candle, hl-info-mainnet-public/candleSnapshot
SUPPORTED_ENVELOPES: WS_DATA_CANDLE, WS_DATA_CANDLE_ARRAY, INFO_CANDLE_ARRAY
```

The candle logical key binds source ID, coin, interval, and candle open time. It deliberately excludes endpoint so later separately authorized reconciliation may map WebSocket and Info observations to the same logical candle.

## A6 frozen authorities

```text
A6_CONTRACT_ID: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
A6_SCHEMA_VERSION: 0.1.0
A6_HASH_VERSION: trader-assist-v0/candle-cross-source-reconciliation/v1
WS_ROLE: hl-ws-mainnet-public/candle with WS_DATA_CANDLE or WS_DATA_CANDLE_ARRAY
INFO_ROLE: hl-info-mainnet-public/candleSnapshot with INFO_CANDLE_ARRAY
STATUSES: MATCH, CONFLICT, WS_ONLY, INFO_ONLY
COMPARABLE_FIELDS: close_time_ms, open_price, high_price, low_price, close_price, volume_base, trade_count
ORDERING: (open_time_ms, candle_logical_key)
```

Both inputs must have identical source, coin, and candle interval identities. Each A5 logical candle key is the sole cross-source identity. Identity inconsistency fails closed rather than becoming `CONFLICT`. Empty/empty inputs produce an empty comparison tuple and zero counts.

## A6 allowed

- exact-class independent revalidation of both A5 extraction authorities and nested candles;
- frozen WS/Info role validation and role-reversal rejection;
- complete embedded A5 extraction authorities plus matching scalar event/hash authority;
- exact logical-key union reconstruction with deterministic ordering during both construction and validation;
- one contract-layer derivation authority used by `bind()` and the data-layer reconciler;
- exact field equality without tolerance or normalization;
- typed per-item source authorities, exact field differences, status counts, and a domain-separated reconciliation hash;
- `AuthorityClass.model_validate_json(...)` as the sole supported A6 raw JSON boundary, with a pre-Pydantic canonical check that accepts only exact `canonical_json_bytes(authority)` representation;
- one-shot call-local Pydantic JSON-mode validation of the already-approved canonical bytes, preserving native Pydantic JSON-mode semantics for `strict=None`, `strict=False`, and `strict=True`, without any persistent caller-settable capability that can authorize core JSON validation;
- pre-Pydantic rejection of duplicate keys at every nesting level, `-0`, noncanonical numeric tokens, invalid UTF-8, BOM, alternate encodings, truncation, trailing material, reordered keys, alternate escapes, and other noncanonical raw forms;
- decoded Python validation through class/base `model_validate`, `TypeAdapter.validate_python`, and core `validate_python`, which authenticates only the current decoded representation and does not prove raw-wire provenance;
- intentional fail-closed behavior for inherited/core JSON, all string-validation paths, and all partial-validation paths;
- self-validating immutable models and generated JSON Schema for structural and standard JSON-Schema-expressible authority constraints.

The portable Schema enforces mandatory serialized fields for the two complete embedded A5 authorities, side-specific root WS/Info extraction roles, comparison-status/source-presence coupling, canonical ASCII nonnegative integer strings for close-time and trade-count differences, and ECMA-compatible absolute-end patterns that do not rely on terminal `$`. The Schema remains structural and JSON-Schema-expressible only. It cannot recompute A5 or A6 hashes, dynamic counts, business-key uniqueness, canonical item/difference ordering, extraction membership, cross-item identity, exact difference values, or the complete union. Runtime remains authoritative for hashes, exact A5 authority, membership, ordering, counts, differences, and complete logical-key union proof.

## A6 prohibited

A6 must not modify A5 contracts/extractor, source catalog code/documentation, existing tests/schemas, dependencies, or CI. It must not add networking, filesystem payload loading, Bronze/manifest writes, database/cloud persistence, tolerance, source priority, latest-wins, revision ordering, finality inference, canonical winner selection, gap/backfill/health runtime, `NormalizedEventV0`, Silver, strategy, AI, risk, dashboard, credentials, account endpoints, signing, nonces, `/exchange`, order mutation, or Testnet/Mainnet execution.

## A5 allowed

- exact-class revalidation of `RawEventV0`;
- exact caller-supplied payload-byte hash and length verification;
- strict UTF-8 JSON decoding with duplicate-key, BOM, malformed, and non-finite-number rejection;
- only official candle fields `t`, `T`, `s`, `i`, `o`, `c`, `h`, `l`, `v`, and `n`;
- exact numeric parsing without binary-float conversion;
- positive OHLC, nonnegative volume/trade count, ordered timestamps, and OHLC range validation;
- exact coin/interval binding to RawEvent authority;
- deterministic typed candle items, logical keys, extraction ordering, and extraction hash;
- empty arrays with zero extracted items and no sentinel/default event.

## A5 preserved boundary

A5 must not modify `events.py`, `source_catalog.py`, `ingress.py`, `bronze.py`, or `replay.py`. It must not add HTTP/WebSocket clients, sockets, DNS, async runtime, event loop, live endpoint connection, polling, reconnect, heartbeat, health, backfill, REST request execution, filesystem payload loading, Bronze/manifest writes, database, cloud SDK, dependency changes, credentials, account/user material, wallet/signing/nonces, `/exchange`, order mutation, `NormalizedEventV0` emission, Silver normalization, revision ordering, finality inference, reconciliation, strategy, AI, risk sizing, dashboard, Testnet/Mainnet execution, or raw operational artifacts.

## Rate-limit entry gate

Official numeric rate limits remain `UNRESOLVED_OFFICIAL_LIMIT`. While unresolved, live polling, WebSocket reconnect, backfill, health runtime, or any public transport runtime remains prohibited. Third-party, remembered, inferred, community, blog, StackOverflow, Discord, or model-memory rate-limit material is not authority.

## A1/A3 read-only transport checks

The pure contract checkers accept only the frozen source, public read-only environment and operation class, ETH/BTC where required, candle intervals `1m`, `3m`, `5m`, `15m`, `1h`, WebSocket capture as `WS_TEXT_UTF8_APPLICATION_PAYLOAD`, and Info capture as `HTTP_RESPONSE_BODY`. They reject private, user/account, wallet/signing, nonce, order, exchange-write, unsupported source/environment/coin/interval/capture-mode, credential, kill-switch bypass, and execution selections.

## A1 fixture admission

Fixtures committed to Git must be synthetic documentation-derived or minimal redacted examples, sanitized, and explicitly provenanced. Real raw observations, real market/account logs, wallet addresses, API keys, signatures, nonces, credentials, database/cache artifacts, and unredacted operational payloads are forbidden. A5 adds no payload fixture.

## A0 lock authority preserved

The root-wide authority is held for the complete writer lifetime. Different segment writers do not coexist in A0. Legacy `.lock` path names are compatibility references only and are not created, removed, or used to establish ownership. A0 has no automatic stale-lock recovery.

**R3B-FORK**: OwnedLock binds authority to the creating process PID. `os.register_at_fork` marks all locks as FORK_INVALID in the child. All authority methods reject non-owner and fork-child callers.

**R3B-OPERATION**: ManifestWriter serializes all public operations via `threading.RLock` and `_WriterState` state machine. Repeated close is deterministic. Concurrent append/close/finalize are safe.

**R3B-ROOTNS**: OwnedLock acquires a kernel lock on the supervisor-owned authority_anchor directory, ensuring authority survives root rename/replacement. Root inode identity is verified at acquisition and at every authority boundary through the parent descriptor. The authority_anchor must be owned by the supervisor and not writable by the collector.

**R6-AUTHORITY**: The authority_anchor directory MUST be owned by the supervisor and MUST NOT be writable by the collector account. The lock file MUST be pre-created by the supervisor. `OwnedLock.acquire()` MUST NOT use `O_CREAT`. The `authority_anchor_fd` parameter is required and MUST be provided by the supervisor. Production code exposes no pathname-based authority provisioning helper. Tests that need provisioning simulate the supervisor in test-local helpers only. `BronzeStore.__init__` MUST NOT auto-create the root directory or lock object. `CloseAdapter.close()` returns a typed `CloseOutcome` enum.

**R4B-FD**: Descriptor state is tracked via `_FdState`. Process-global poison gate blocks new writers when close outcome is uncertain. Descriptor is not invalidated before `os.close`.

## Authority

TraderOS remains authoritative for cross-project architecture and production governance. Public market-data definitions never authorize exchange writes. Completion of A6 does not authorize live transport, health, backfill, finality inference, revision ordering, canonical winner selection, normalized events, Silver, strategy, AI, risk, dashboard, execution, or A7. Every later slice requires a separate exact-head scope freeze, write lease, CI run, external independent review, and finalization authorization.
