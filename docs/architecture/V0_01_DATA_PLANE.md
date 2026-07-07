# V0-01A0 Bronze Data Plane

## Evidence flow

```text
frozen public source catalog + catalog-entry hash
  -> exact application-payload bytes
  -> SHA-256 content identity
  -> catalog-bound observation-slot v2 identity
  -> catalog-bound raw-observation v2 identity
  -> immutable content-addressed payload
  -> root-level global observation authority lock
  -> exclusive per-segment writer lock
  -> append-only hash-linked manifest
  -> one-time completion checkpoint
  -> deterministic offline replay report
```

## Identity separation

`payload_sha256` hashes exact bytes. JSON whitespace or key ordering changes therefore change the payload identity.

The v2 observation slot binds catalog version, catalog hash, catalog-entry hash, source, endpoint, operation, coin, candle interval, capture mode, connection, subscription, and collector-local receive sequence. The v2 raw observation identity additionally binds the payload hash. Collector-local sequence is never represented as a venue sequence.

Within one Bronze persistence root, an observation slot and a source-event ID are globally unique rather than segment-local. Re-appending the same complete RawEvent in another segment is globally idempotent and creates no second authority entry. The same slot with different RawEvent authority is a conflict.

## Persistence

Payloads use `payloads/sha256/<prefix>/<digest>.payload`. Manifest lines use `manifests/<UTC-date>/<segment>.jsonl`. Completion checkpoints use `manifests/<UTC-date>/<segment>.checkpoint.json`. Paths are portable relative paths; absolute paths are never hashed or serialized into authority records.

Payload publication writes and fsyncs a same-filesystem temporary file and atomically links it into its immutable final name without overwrite. Manifest append writes one JSON line while holding the segment lock and the short-lived global authority lock, fsyncs the file, and fsyncs the parent directory.

`ManifestWriter.close()` releases the lock but does not claim completion. `ManifestWriter.finalize()` rereads and validates the manifest, fsyncs it, binds entry count and terminal hash into a self-hashed checkpoint, publishes that checkpoint exactly once, fsyncs the parent directory, and permanently closes the segment. A finalized segment cannot be reopened for append.

## Lock authority

Segment and global locks use `O_CREAT | O_EXCL | O_NOFOLLOW`, an unpredictable token, retained file descriptor, and captured device/inode. Release rechecks the path type, device/inode, reopened descriptor, and both on-disk and owned tokens before unlinking. Deleted, replaced, token-mismatched, inode-mismatched, or symlinked locks fail closed and are not removed by the old owner. A0 does not automatically recover stale locks.

Different segment writers may coexist. Every append obtains the root-level global observation lock, validates every manifest, builds global slot and source-event maps, performs idempotency/conflict checks, appends and fsyncs, then releases the global lock. Any partial or corrupt manifest blocks new authority writes across the root.

## Path boundary

Authoritative opens walk directory file descriptors, reject symlinks with non-following metadata checks, and compare device/inode after open. Payload and manifest trees reject unexpected entries. This closes ordinary traversal and symlink escape under a non-hostile runtime account.

The implementation does not claim protection against a privileged local actor who can concurrently replace the persistence root or mutate directory entries between all kernel operations. Such an actor is outside A0's threat boundary; the persistence root must be owned and writable only by the collector account.

## Replay

Replay performs no networking and requires a valid completion checkpoint. It verifies manifest framing, strict schemas, fixed versions, index continuity, segment identity, previous hashes, self-hashes, checkpoint date/segment/catalog/count/terminal hash, payload path confinement, existence, type, byte length, SHA-256, global observation authority, optional extra terminal-hash assertion, and global orphan status.

An unfinalized segment, missing or invalid checkpoint, tail deletion, count or terminal mismatch, corrupt evidence, conflicting global authority, unexpected tree entry, or orphan payload yields `FAIL`. A zero-entry segment passes only when an empty manifest exists with an explicit completed checkpoint binding count zero and the genesis terminal hash.

The report hash excludes absolute paths, current time, random values, process IDs, and filesystem metadata, so the same evidence yields the same logical report across roots and processes.
