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

A1 adds no HTTP client, WebSocket client, DNS, live endpoint connection, polling loop, reconnect runtime, heartbeat runtime, health runtime, backfill runtime, event loop, async runtime, database, dashboard, cloud SDK, strategy logic, AI recommendation, or risk sizing.

## Identity separation

`payload_sha256` hashes exact bytes. JSON whitespace or key ordering changes therefore change the payload identity.

The v2 observation slot binds catalog version, catalog hash, catalog-entry hash, source, endpoint, operation, coin, candle interval, capture mode, connection, subscription, and collector-local receive sequence. The v2 raw observation identity additionally binds the payload hash. Collector-local sequence is never represented as a venue sequence.

Within one Bronze persistence root, an observation slot and a source-event ID are globally unique rather than segment-local. Re-appending the same complete RawEvent in another segment is globally idempotent and creates no second authority entry. The same slot with different RawEvent authority is a conflict.

A1 does not parse candle payloads into source-native IDs, source-native cursors, normalized timestamps, Silver events, strategy signals, AI explanations, or risk fields. Those fields remain unavailable until a later separately reviewed extractor/normalizer contract exists.

## A1 public source envelope authority

The candle WebSocket contract accepts only these frozen public envelope shapes:

```text
data:Candle
data:Candle[]
```

These tokens describe public envelope policy and fixture shape. They are not runtime subscription code, not connection code, and not transport recovery logic.

## A1 rate-limit authority

`RATE_LIMIT_STATUS` remains `UNRESOLVED_OFFICIAL_LIMIT`. While that value is present, the entry gate blocks live public transport, polling, reconnect, backfill, and health runtime. A later task may encode official numeric limits only if the values are clearly present in official Hyperliquid documentation at implementation time.

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

## Persistence

Payloads use `payloads/sha256/<prefix>/<digest>.payload`. Manifest lines use `manifests/<UTC-date>/<segment>.jsonl`. Completion checkpoints use `manifests/<UTC-date>/<segment>.checkpoint.json`. Paths are portable relative paths; absolute paths are never hashed or serialized into authority records.

Payload publication writes and fsyncs a same-filesystem temporary file and atomically links it into its immutable final name without overwrite. Manifest append runs under the root-wide writer authority, validates every manifest, performs global idempotency/conflict checks, writes exactly one JSON line, fsyncs the manifest, and fsyncs the parent directory before the authority may be released.

`ManifestWriter.close()` releases the root-wide authority but does not claim completion. `ManifestWriter.finalize()` rereads and validates the manifest while the same authority remains continuously held, fsyncs it, binds entry count and terminal hash into a self-hashed checkpoint, publishes that checkpoint exactly once, fsyncs the parent directory, and then closes. A finalized segment cannot be reopened for append.

## Lock authority

A0 uses a root-wide single-writer protocol. `ManifestWriter` acquires an exclusive non-blocking `fcntl.flock` on a lock file within the authority_anchor directory, not the root directory itself. The lock file is pre-created by the supervisor and opened by `OwnedLock.acquire()` through the supervisor-provided anchor directory fd. The authority_anchor directory descriptor is owned by the supervisor and passed to `OwnedLock.acquire()` as the `authority_anchor_fd` parameter.

The protocol does not create or delete lock pathname markers. `lock_ref()` and `global_authority_lock_ref()` remain compatibility names only; their presence, absence, token contents, replacement, or symlink substitution cannot create a second writer namespace and is never cleaned by ordinary release. Acquisition cleanup and release operate only on the descriptor owned by that acquisition, eliminating blind-unlink and verify-then-unlink races.

Different segment writers do not coexist in A0. A second writer for any date or segment in the same Bronze root fails closed until the active writer releases its kernel authority. After release, global replay of every manifest preserves cross-segment and cross-date idempotency/conflict semantics. Any partial, corrupt, duplicated, or conflicting manifest blocks new authority writes across the root.

Root-path loss, replacement, non-directory substitution, descriptor identity mismatch, or kernel release failure transitions the lock and writer to a terminal compromised state. Its owned descriptor is closed, append/finalize remain disabled, repeated release is deterministic, and no current pathname is removed. A0 does not automatically recover stale authority.

## Path boundary

Authoritative opens walk directory file descriptors, reject symlinks with non-following metadata checks, and compare device/inode after open. Payload and manifest trees reject unexpected entries. This closes ordinary traversal and symlink escape under a non-hostile runtime account.

The kernel lock is advisory. All cooperative writers must use this protocol. Bronze root contents are collector-writable; the authority_anchor and root immediate parent are supervisor-controlled and not collector-writable. The collector must not create, replace, chmod, rename, delete, or otherwise mutate the authority_anchor, root immediate parent, or authority lock object. The implementation does not claim protection against a privileged local actor that can bypass advisory locks, replace higher-level mount or parent authorities, or directly mutate opened directory entries. Such an actor is outside A0's threat boundary.

## Replay

Replay performs no networking and requires a valid completion checkpoint. It verifies manifest framing, strict schemas, fixed versions, index continuity, segment identity, previous hashes, self-hashes, checkpoint date/segment/catalog/count/terminal hash, payload path confinement, existence, type, byte length, SHA-256, global observation authority, optional extra terminal-hash assertion, and global orphan status.

An unfinalized segment, missing or invalid checkpoint, tail deletion, count or terminal mismatch, corrupt evidence, conflicting global authority, unexpected tree entry, or orphan payload yields `FAIL`. A zero-entry segment passes only when an empty manifest exists with an explicit completed checkpoint binding count zero and the genesis terminal hash.

The report hash excludes absolute paths, current time, random values, process IDs, and filesystem metadata, so the same evidence yields the same logical report across roots and processes.

## A1-to-A2 gate

A2 is not authorized by A1 completion alone. A2 may only be considered after A1 merge, external exact-head review PASS, explicit rate-limit gate, frozen public envelope contract, and a new exact-head write lease from project control.
