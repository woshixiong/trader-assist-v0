# V0-01A0 Bronze Data Plane

## Evidence flow

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

## Identity separation

`payload_sha256` hashes exact bytes. JSON whitespace or key ordering changes therefore change the payload identity.

The v2 observation slot binds catalog version, catalog hash, catalog-entry hash, source, endpoint, operation, coin, candle interval, capture mode, connection, subscription, and collector-local receive sequence. The v2 raw observation identity additionally binds the payload hash. Collector-local sequence is never represented as a venue sequence.

Within one Bronze persistence root, an observation slot and a source-event ID are globally unique rather than segment-local. Re-appending the same complete RawEvent in another segment is globally idempotent and creates no second authority entry. The same slot with different RawEvent authority is a conflict.

## Persistence

Payloads use `payloads/sha256/<prefix>/<digest>.payload`. Manifest lines use `manifests/<UTC-date>/<segment>.jsonl`. Completion checkpoints use `manifests/<UTC-date>/<segment>.checkpoint.json`. Paths are portable relative paths; absolute paths are never hashed or serialized into authority records.

Payload publication writes and fsyncs a same-filesystem temporary file and atomically links it into its immutable final name without overwrite. Manifest append runs under the root-wide writer authority, validates every manifest, performs global idempotency/conflict checks, writes exactly one JSON line, fsyncs the manifest, and fsyncs the parent directory before the authority may be released.

`ManifestWriter.close()` releases the root-wide authority but does not claim completion. `ManifestWriter.finalize()` rereads and validates the manifest while the same authority remains continuously held, fsyncs it, binds entry count and terminal hash into a self-hashed checkpoint, publishes that checkpoint exactly once, fsyncs the parent directory, and then closes. A finalized segment cannot be reopened for append.

## Lock authority

A0 uses a root-wide single-writer protocol. `ManifestWriter` opens the Bronze root directory with no-follow directory semantics and obtains an exclusive non-blocking `fcntl.flock` on that retained descriptor. The same descriptor anchors storage traversal for the complete writer lifetime, including initialization, complete-root scan, slot/source-event decision, manifest publication, file fsync, directory fsync, and checkpoint publication.

The protocol does not create or delete lock pathname markers. `lock_ref()` and `global_authority_lock_ref()` remain compatibility names only; their presence, absence, token contents, replacement, or symlink substitution cannot create a second writer namespace and is never cleaned by ordinary release. Acquisition cleanup and release operate only on the descriptor owned by that acquisition, eliminating blind-unlink and verify-then-unlink races.

Different segment writers do not coexist in A0. A second writer for any date or segment in the same Bronze root fails closed until the active writer releases its kernel authority. After release, global replay of every manifest preserves cross-segment and cross-date idempotency/conflict semantics. Any partial, corrupt, duplicated, or conflicting manifest blocks new authority writes across the root.

Root-path loss, replacement, non-directory substitution, descriptor identity mismatch, or kernel release failure transitions the lock and writer to a terminal compromised state. Its owned descriptor is closed, append/finalize remain disabled, repeated release is deterministic, and no current pathname is removed. A0 does not automatically recover stale authority.

## Path boundary

Authoritative opens walk directory file descriptors, reject symlinks with non-following metadata checks, and compare device/inode after open. Payload and manifest trees reject unexpected entries. This closes ordinary traversal and symlink escape under a non-hostile runtime account.

The kernel lock is advisory. All cooperative writers must use this protocol, and the persistence root plus its parent must be writable only by the collector account. The implementation does not claim protection against a privileged local actor that can bypass advisory locks, replace higher-level mount or parent authorities, or directly mutate opened directory entries. Such an actor is outside A0's threat boundary.

## Replay

Replay performs no networking and requires a valid completion checkpoint. It verifies manifest framing, strict schemas, fixed versions, index continuity, segment identity, previous hashes, self-hashes, checkpoint date/segment/catalog/count/terminal hash, payload path confinement, existence, type, byte length, SHA-256, global observation authority, optional extra terminal-hash assertion, and global orphan status.

An unfinalized segment, missing or invalid checkpoint, tail deletion, count or terminal mismatch, corrupt evidence, conflicting global authority, unexpected tree entry, or orphan payload yields `FAIL`. A zero-entry segment passes only when an empty manifest exists with an explicit completed checkpoint binding count zero and the genesis terminal hash.

The report hash excludes absolute paths, current time, random values, process IDs, and filesystem metadata, so the same evidence yields the same logical report across roots and processes.
