# V0-01 Scope

## Completed slice

`V0-01A0 / BRONZE_AND_OFFLINE_REPLAY`

A0 froze public source definitions and implemented an entirely offline evidence path: exact synthetic application-payload bytes, catalog-bound domain-separated observation identities, immutable content-addressed local storage, root-wide single-writer observation authority, hash-linked manifests, one-time segment completion checkpoints, strict integrity verification, and deterministic replay reports.

A0 remains offline. It does not authorize live endpoint connection, runtime polling, WebSocket transport, reconnect, health, backfill, strategy, AI recommendation, risk sizing, or exchange execution.

## Active slice

`V0-01A1 / SOURCE_ENVELOPE_TRANSPORT_ENTRY_CONTRACT_FREEZE`

A1 is a bounded contract-freeze layer before any public read-only transport runtime. It freezes public envelope policy, rate-limit entry authority, future read-only transport configuration checks, fixture admission policy, and the A1-to-A2 gate.

A1 does not implement live transport.

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

A0 supports only these values. Callers cannot override them, and the generated JSON Schemas expose them as `const` authorities.

## A1 frozen authorities

```text
A1_CONTRACT_ID: V0-01A1-SCOPE-FREEZE
SOURCE_ID: hyperliquid-public-mainnet
ENVIRONMENT: mainnet public read-only
OPERATION_CLASS: public read-only observation only
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
CANDLE_WS_ENVELOPE_SHAPES: data:Candle, data:Candle[]
CAPTURE_MODES: WS_TEXT_UTF8_APPLICATION_PAYLOAD, HTTP_RESPONSE_BODY
ALLOWED_COINS: BTC, ETH
RUNTIME_CANDLE_INTERVALS: 1m, 3m, 5m, 15m, 1h
```

## A1 allowed

- freeze the public-source envelope policy for Hyperliquid candle data;
- accept and document both possible candle WebSocket raw wire envelope shapes: `data: Candle` and `data: Candle[]`;
- keep `RawEventV0` as exact application-payload byte evidence;
- define fail-closed rate-limit entry-gate behavior;
- define only future public read-only transport entry configuration checks;
- admit only synthetic documentation-derived or minimal redacted fixtures with explicit provenance;
- reject fixture payloads with operational secrets, private/account data, credentials, nonces, signatures, database/cache artifacts, or raw operational observations;
- document that A2 needs a new exact-head lease after A1 merge and external review.

## A1 prohibited

No HTTP client, WebSocket client, DNS, live endpoint connection, polling loop, reconnect runtime, heartbeat runtime, health runtime, backfill runtime, async runtime, event loop, new dependency, account address, private endpoint, user/account endpoint, credential, API wallet, signing, nonce handling, order mutation, exchange write path, Testnet/Mainnet execution enablement, strategy candidate, AI recommendation, risk sizing, Silver normalization, dashboard, database, cloud SDK, soak runner, real operational payload, log, cache, DB, source archive, or secret is included.

The A1 candle envelope contract is policy only. It does not parse candle values into strategy signals, normalize into Silver, infer trading direction, create AI advice, or size risk.

## Rate-limit entry gate

Official numeric rate limits remain `UNRESOLVED_OFFICIAL_LIMIT` until an implementation window can read and encode only official documented values. While numeric limits are unresolved, live polling, WebSocket reconnect, backfill, health runtime, or any public transport runtime remains prohibited.

Third-party, remembered, inferred, community, blog, StackOverflow, Discord, or model-memory rate-limit numbers are not authority.

## A1-to-A2 gate

A1 completion does not authorize A2 automatically.

A2 may only be considered after all of the following are true:

1. A1 PR is merged.
2. External independent exact-head review passes.
3. The rate-limit entry gate is explicit.
4. The public source envelope contract is frozen.
5. Project control grants a new exact-head lease.

## A0 lock authority preserved

The root-wide authority is held for the complete writer lifetime. Different segment writers do not coexist in A0. Legacy `.lock` path names are compatibility references only and are not created, removed, or used to establish ownership. A0 has no automatic stale-lock recovery.

**R3B-FORK**: OwnedLock binds authority to the creating process PID. `os.register_at_fork` marks all locks as FORK_INVALID in the child. All authority methods reject non-owner and fork-child callers.

**R3B-OPERATION**: ManifestWriter serializes all public operations via `threading.RLock` and `_WriterState` state machine. Repeated close is deterministic. Concurrent append/close/finalize are safe.

**R3B-ROOTNS**: OwnedLock acquires a kernel lock on the supervisor-owned authority_anchor directory, ensuring authority survives root rename/replacement. Root inode identity is verified at acquisition and at every authority boundary through the parent descriptor. The authority_anchor must be owned by the supervisor and not writable by the collector.

**R6-AUTHORITY**: The authority_anchor directory MUST be owned by the supervisor and MUST NOT be writable by the collector account. The lock file MUST be pre-created by the supervisor. `OwnedLock.acquire()` MUST NOT use `O_CREAT`. The `authority_anchor_fd` parameter is required and MUST be provided by the supervisor. Production code exposes no pathname-based authority provisioning helper. Tests that need provisioning simulate the supervisor in test-local helpers only. `BronzeStore.__init__` MUST NOT auto-create the root directory or lock object. `CloseAdapter.close()` returns a typed `CloseOutcome` enum.

**R4B-FD**: Descriptor state is tracked via `_FdState`. Process-global poison gate blocks new writers when close outcome is uncertain. Descriptor is not invalidated before `os.close`.

## Authority

TraderOS remains authoritative for cross-project architecture and production governance. Public market-data definitions never authorize exchange writes. The next transport or health slice requires a separate exact-head lease and review.
