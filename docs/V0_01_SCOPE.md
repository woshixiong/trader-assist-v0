# V0-01 Scope

## Completed slices

`V0-01A0 / BRONZE_AND_OFFLINE_REPLAY`

A0 froze public source definitions and implemented an entirely offline evidence path: exact synthetic application-payload bytes, catalog-bound domain-separated observation identities, immutable content-addressed local storage, root-wide single-writer observation authority, hash-linked manifests, one-time segment completion checkpoints, strict integrity verification, and deterministic replay reports.

A0 remains offline. It does not authorize live endpoint connection, runtime polling, WebSocket transport, reconnect, health, backfill, strategy, AI recommendation, risk sizing, or exchange execution.

`V0-01A1 / SOURCE_ENVELOPE_TRANSPORT_ENTRY_CONTRACT_FREEZE`

A1 froze public envelope policy, rate-limit entry authority, future read-only transport configuration checks, fixture admission policy, and the A1-to-A2 gate.

A1 does not implement live transport.

## Active slice

`V0-01A2 / NO_NETWORK_PUBLIC_OBSERVATION_INGRESS_CONTRACT`

A2 is a bounded no-network ingress contract/helper layer. It accepts caller-supplied exact public observation bytes, validates every selection through the A1 public read-only transport-entry contract, binds exact bytes into `RawEventV0` authority, and can optionally persist payloads / append RawEvent entries through existing A0 Bronze authority.

A2 does not implement live transport.

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
```

A0 supports only these values. Callers cannot override them, and the generated JSON Schemas expose them as `const` authorities.

## A1 frozen authorities used by A2

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

## A2 allowed

- add a pure no-network public observation ingress/helper layer;
- accept only caller-supplied exact bytes as public observation payload evidence;
- require injected `first_observed_time`, `collector_receive_time`, `collector_monotonic_ns`, `connection_id`, `subscription_id`, and collector-local `receive_sequence` for deterministic tests;
- validate source, environment, operation class, endpoint, operation, coin, interval, and capture mode through A1 `validate_read_only_transport_entry()`;
- bind exact bytes into `RawEventV0` using content-addressed payload hash and payload ref authority;
- keep `source_event_time`, `source_publish_time`, `source_native_id`, `source_native_cursor`, and `revision_time` unavailable until a later extractor contract;
- optionally persist payloads through `BronzeStore.write_payload()`;
- optionally append RawEvent entries through an existing A0 `ManifestWriter` so root-wide single-writer and supervisor-owned authority are preserved;
- prove unresolved rate limits still block live transport;
- test no network / async transport capability in implementation code.

## A2 prohibited

No HTTP client, WebSocket client, DNS, socket, live endpoint connection, polling loop, reconnect runtime, heartbeat runtime, health runtime, backfill runtime, async runtime, event loop, new dependency, account address, private endpoint, user/account endpoint, credential, API wallet, signing, nonce handling, order mutation, exchange write path, Testnet/Mainnet execution enablement, strategy candidate, AI recommendation, risk sizing, Silver normalization, dashboard, database, cloud SDK, soak runner, real operational payload, log, cache, DB, source archive, or secret is included.

The A2 ingress contract is not a parser, not a candle normalizer, not a strategy signal generator, not an AI advice layer, and not a risk-sizing layer.

`mainnet public read-only` is a public source identity / environment label. It is not Mainnet execution enablement.

## Rate-limit entry gate

Official numeric rate limits remain `UNRESOLVED_OFFICIAL_LIMIT` until an implementation window can read and encode only official documented values. While numeric limits are unresolved, live polling, WebSocket reconnect, backfill, health runtime, or any public transport runtime remains prohibited.

Third-party, remembered, inferred, community, blog, StackOverflow, Discord, or model-memory rate-limit numbers are not authority.

A2 must not resolve official numeric rate limits unless project control amends the task after current official docs are readable and cited.

## A1 read-only transport entry checks

The pure contract checker accepts only:

- `source_id = hyperliquid-public-mainnet`;
- `environment = mainnet public read-only`;
- `operation_class = public read-only observation only`;
- ETH/BTC when the operation requires a coin;
- candle intervals `1m`, `3m`, `5m`, `15m`, `1h` when the operation is candle-shaped;
- WebSocket capture as `WS_TEXT_UTF8_APPLICATION_PAYLOAD`;
- Info capture as `HTTP_RESPONSE_BODY`.

It rejects private, user/account, wallet/signing, nonce, order, exchange-write, unsupported source, unsupported environment, unsupported coin, unsupported interval, and unsupported capture-mode selections.

## A1 fixture admission

Fixtures committed to Git must be synthetic documentation-derived or minimal redacted examples, sanitized, and explicitly provenanced. Real raw observations, real market/account logs, wallet addresses, API keys, signatures, nonces, credentials, database/cache artifacts, and unredacted operational payloads are forbidden.

If a later read-only observation task is authorized, raw observations must remain outside Git. Only sanitized derived fixtures may be committed after review.

## A0 lock authority preserved

The root-wide authority is held for the complete writer lifetime. Different segment writers do not coexist in A0. Legacy `.lock` path names are compatibility references only and are not created, removed, or used to establish ownership. A0 has no automatic stale-lock recovery.

**R3B-FORK**: OwnedLock binds authority to the creating process PID. `os.register_at_fork` marks all locks as FORK_INVALID in the child. All authority methods reject non-owner and fork-child callers.

**R3B-OPERATION**: ManifestWriter serializes all public operations via `threading.RLock` and `_WriterState` state machine. Repeated close is deterministic. Concurrent append/close/finalize are safe.

**R3B-ROOTNS**: OwnedLock acquires a kernel lock on the supervisor-owned authority_anchor directory, ensuring authority survives root rename/replacement. Root inode identity is verified at acquisition and at every authority boundary through the parent descriptor. The authority_anchor must be owned by the supervisor and not writable by the collector.

**R6-AUTHORITY**: The authority_anchor directory MUST be owned by the supervisor and MUST NOT be writable by the collector account. The lock file MUST be pre-created by the supervisor. `OwnedLock.acquire()` MUST NOT use `O_CREAT`. The `authority_anchor_fd` parameter is required and MUST be provided by the supervisor. Production code exposes no pathname-based authority provisioning helper. Tests that need provisioning simulate the supervisor in test-local helpers only. `BronzeStore.__init__` MUST NOT auto-create the root directory or lock object. `CloseAdapter.close()` returns a typed `CloseOutcome` enum.

**R4B-FD**: Descriptor state is tracked via `_FdState`. Process-global poison gate blocks new writers when close outcome is uncertain. Descriptor is not invalidated before `os.close`.

## Authority

TraderOS remains authoritative for cross-project architecture and production governance. Public market-data definitions never authorize exchange writes. The next transport or health slice requires a separate exact-head lease and review.
