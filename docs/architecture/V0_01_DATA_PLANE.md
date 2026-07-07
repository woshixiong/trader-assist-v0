# V0-01A0 Bronze Data Plane

## Evidence flow

```text
versioned public source catalog
  -> exact application-payload bytes
  -> SHA-256 content identity
  -> domain-separated observation identity
  -> immutable content-addressed payload
  -> exclusive single-writer manifest
  -> hash-chain verification
  -> deterministic offline replay report
```

## Identity separation

`payload_sha256` hashes exact bytes. JSON whitespace or key ordering changes therefore change the payload identity.

The observation slot binds catalog version, source, endpoint, connection, subscription, and collector-local receive sequence. The raw observation identity additionally binds the payload hash. Collector-local sequence is never represented as a venue sequence.

The same payload observed twice occupies one blob but two observation slots. Re-appending the exact same slot and payload is idempotent. The same slot with a different payload is a conflict.

## Persistence

Payloads use `payloads/sha256/<prefix>/<digest>.payload`. Manifest lines use `manifests/<UTC-date>/<segment>.jsonl`. Paths are portable relative paths; absolute paths are never hashed or serialized into authority records.

Payload publication writes and fsyncs a same-filesystem temporary file and atomically links it into its immutable final name without overwrite. Manifest append writes one JSON line under an exclusive `O_CREAT|O_EXCL` lock, fsyncs the file, and fsyncs the parent directory. Unknown stale locks fail closed.

## Path boundary

Authoritative opens walk directory file descriptors, reject symlinks with non-following metadata checks, and compare device/inode after open. Payload and manifest trees reject unexpected entries. This closes ordinary traversal and symlink escape under a non-hostile runtime account.

The implementation does not claim protection against a privileged local actor who can concurrently replace the persistence root or mutate directory entries between all kernel operations. Such an actor is outside A0's threat boundary; the persistence root must be owned and writable only by the collector account.

## Replay

Replay performs no networking. It verifies manifest framing, strict schemas, index continuity, segment identity, previous hashes, self-hashes, payload path confinement, existence, type, byte length, SHA-256, terminal hash, and global orphan status. Any missing, corrupt, partial, conflicting, unexpected, or orphan evidence yields `FAIL`.

The report hash excludes absolute paths, current time, random values, process IDs, and filesystem metadata, so the same evidence yields the same logical report across roots and processes.
