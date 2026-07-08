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

A0 uses a root-wide single-writer protocol. `ManifestWriter` acquires an exclusive non-blocking `fcntl.flock` on a **lock file** within the authority_anchor directory (supervisor-provided directory fd), not the root directory itself. The lock file is pre-created by the supervisor via `_open_anchor_fd(store)` and the file descriptor is managed separately from the anchor directory fd. The authority_anchor directory descriptor is owned by the supervisor and passed to `OwnedLock.acquire()` as the `authority_anchor_fd` parameter.

**Supervisor-provided anchor (R4-SUPERVISOR)**: The `authority_anchor_fd` is a supervisor-owned directory file descriptor passed to `OwnedLock.acquire()`. If `authority_anchor_fd` is `None` or invalid, the lock fails closed. The lock file at `.bronze-global-observation-authority.lock` within the anchor directory must be pre-created by the supervisor — `acquire()` never creates it via `O_CREAT`. The helper `_open_anchor_fd(store)` provides backward-compatible anchor provisioning: it creates the lock file if missing, opens the anchor directory, and returns the fd. The `_lock_fd` field on `OwnedLock` holds the lock file descriptor acquired by the instance, while `_parent_fd` is replaced by the externally-owned `authority_anchor_fd`.

**Stable namespace authority (R3B-ROOTNS)**: Locking the lock file within the supervisor-owned authority_anchor directory ensures authority survives root rename or replacement within the same authority_anchor directory. The root inode identity (st_dev, st_ino) is verified at acquisition and at every authority boundary through the authority_anchor descriptor. The lock file inode identity (st_dev, st_ino) is verified via `os.fstat`. If either identity is lost, the authority fails closed. The authority_anchor must be owned by the supervisor and not writable by the collector.

**Fork safety (R3B-FORK)**: `OwnedLock` records the creating process PID. On fork, `os.register_at_fork(after_in_child=...)` marks all locks as FORK_INVALID, sets `_lock_fd` to -1, and removes the lock from the fork registry. All authority methods (authority_fd, assert_owned, release, append, finalize, close) verify the calling PID and reject non-owner and fork-child callers. The child's `_lock_fd` is invalidated to prevent accidental `flock(LOCK_UN)` on the inherited lock file descriptor.

**Descriptor lifecycle (R4B-FD)**: Each descriptor is tracked through a `_FdState` state machine (OPEN_OWNED, KNOWN_OPEN_AFTER_PRE_SYSCALL_FAILURE, UNLOCKING, CLOSING, CLOSED, CLOSE_OUTCOME_UNKNOWN, POISONED, FORK_INVALID). The descriptor is not invalidated before `os.close`. When `flock(LOCK_UN)` or `os.close` fails, the state transitions to uncertain states, and a process-global `_BRONZE_POISON_GATE` is set to prevent new writers in the same process. The `CloseAdapter` injection seam enables fault-injection testing by allowing tests to substitute a custom `close()` implementation that can fail before or after the syscall.

**Writer serialization (R3B-OPERATION)**: `ManifestWriter` uses a `threading.RLock` and a `_WriterState` state machine (ACTIVE, FINALIZING, FINALIZED, CLOSING, CLOSED, COMPROMISED, POISONED, FORK_INVALID) to serialize all public operations. Repeated close is deterministic and safe. Concurrent append, close, and finalize calls are serialized through the lock.

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
