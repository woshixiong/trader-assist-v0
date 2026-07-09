# Security

## V0-01A1 Contract-Freeze Threat Model

V0-01A1 is a public-source contract freeze only. It freezes candle envelope policy, rate-limit entry-gate behavior, future public read-only transport configuration checks, fixture admission policy, and the A1-to-A2 gate.

A1 still has no HTTP client, WebSocket client, DNS, live endpoint connection, polling loop, reconnect runtime, heartbeat runtime, health runtime, backfill runtime, async runtime, event loop, credentials, account address, wallet, signing, nonce handling, order mutation, exchange-write path, Testnet/Mainnet execution enablement, strategy logic, AI recommendation, risk sizing, database, dashboard, cloud SDK, or soak runner.

## A1 Fixture Security

Fixtures committed to Git must be synthetic documentation-derived or minimal redacted examples with explicit provenance. Real raw observations, real market/account logs, private/user/account data, wallet addresses, API keys, signatures, nonces, credentials, database artifacts, caches, unredacted observations, and raw operational payloads are forbidden.

If later read-only observation is authorized, raw observations must remain outside Git. Only sanitized derived fixtures may be committed after review.

## A1 Rate-Limit Security

Official numeric rate limits are currently `UNRESOLVED_OFFICIAL_LIMIT`. While unresolved, live polling, WebSocket reconnect, backfill, health runtime, and any public transport runtime remain blocked. Third-party, remembered, inferred, community, blog, StackOverflow, Discord, or model-memory rate-limit numbers are not authority.

## V0-01A0 Threat Model

V0-01A0 is offline and read-only. Public market-data documentation and synthetic
fixtures do not authorize live connectivity or exchange writes.

## Authority Model

### Supervisor-Owned Authority Anchor

The Bronze persistence root MUST be provisioned by the collector account before
any writer is created. The `authority_anchor` directory (parent of the root by
default) MUST be owned by the supervisor and MUST NOT be writable by the
collector account. The authority_anchor MUST be a real directory (not a symlink)
and MUST remain stable for the lifetime of all writers. The root directory MUST
be a real directory (not a symlink) and MUST reside under the authority_anchor.

### Supervisor Contract

The supervisor MUST:
- Own the authority_anchor directory and lock object
- Pre-create the `.bronze-global-observation-authority.lock` file within the
  authority_anchor directory
- Provide a pre-opened `authority_anchor_fd` (directory file descriptor) to
  `OwnedLock.acquire()` and `ManifestWriter`
- Ensure the authority_anchor directory is NOT writable by the collector
  account (effective UID/GID/other write bits)
- Ensure the root immediate parent directory is NOT writable by the collector
- Ensure the authority_anchor MUST NOT be renamed or replaced while any writer
  holds authority

The collector MAY:
- Write payload, manifest, and checkpoint data within the root directory

The collector MUST NOT:
- Rename, delete, or replace the authority_anchor directory
- Rename, delete, or replace the root immediate parent directory
- Create or replace the authority lock object
- Write to the authority_anchor directory

### Root-Namespace Authority

The kernel-backed exclusive lock is held on the lock file within the
**authority_anchor directory** (supervisor-owned parent of the Bronze
persistence root), not the root directory itself. This ensures that authority
survives root rename or replacement within the same authority_anchor directory.

A0 permits only one active `ManifestWriter` for the complete root. The writer
holds a kernel-backed exclusive lock on an open descriptor for the lock file
throughout initialization, global manifest scanning, idempotency/conflict
decisions, manifest construction and publication, file fsync, parent-directory
fsync, finalization, and close.

### Effective-Writability Check

`OwnedLock.acquire()` MUST verify that the collector does not have write
permission on the authority_anchor directory via an fd-addressed path such as
`/proc/self/fd/<authority_anchor_fd>` with `os.access(..., os.W_OK,
effective_ids=True)`, or a platform-equivalent effective UID/GID mode check. If
the collector can write the authority_anchor, or the check cannot be performed,
the acquire MUST fail closed with `LockOwnershipError`.

### Lock File Contract

The lock file `.bronze-global-observation-authority.lock` MUST be pre-created by
the supervisor within the authority_anchor directory. `OwnedLock.acquire()` MUST
NOT use `O_CREAT` to create the lock file. If the lock file is missing, the
acquire MUST fail closed. The lock file MUST be a regular file (not a symlink).

### Root Identity Verification

The root inode identity (st_dev, st_ino) MUST be verified at acquisition and at
every authority boundary through the authority_anchor descriptor. The lock file
inode identity (st_dev, st_ino) MUST be verified via `os.fstat`. If either
identity is lost, the authority MUST fail closed. Append and finalize MUST be
blocked after root identity loss.

### Fork Safety

OwnedLock records the creating process PID. `os.register_at_fork(after_in_child=...)`
marks all locks as FORK_INVALID in the child process. All authority methods
(`authority_fd`, `assert_owned`, `release`, `append`, `finalize`, `close`)
verify the calling PID and reject non-owner processes. A fork child MUST NOT
use or release the parent's authority. `_lock_fd` is set to -1 in the child to
prevent accidental `flock(LOCK_UN)`.

### Descriptor Lifecycle

The lock descriptor is NOT invalidated before `os.close`. A `_FdState` state
machine tracks each descriptor through OPEN_OWNED, UNLOCKING, CLOSING, CLOSED,
CLOSE_OUTCOME_UNKNOWN, KNOWN_OPEN_AFTER_PRE_SYSCALL_FAILURE, POISONED, and
FORK_INVALID states. `CloseAdapter.close()` returns a typed `CloseOutcome`
(CLOSED, PRE_SYSCALL_FAILED_KNOWN_OPEN, POST_SYSCALL_UNKNOWN) rather than
relying on unclassified OSError. When `flock(LOCK_UN)` or `os.close` fails,
the state transitions to uncertain states, and a process-global poison gate
is set to prevent new writers from being created in the same process.

### Poison Gate

The `_BRONZE_POISON_GATE` is a one-way process-level flag. Once set to 1, it
MUST NOT be reset by production code. There is NO production reset poison gate
API. When the poison gate is set, `OwnedLock.acquire()` and `ManifestWriter`
MUST fail closed.

### Diagnostic Preservation

When close failures occur, diagnostic fd numbers (`_fd_diagnostic`,
`_lock_fd_diagnostic`, `_parent_fd_diagnostic`) are preserved for forensic
analysis. The `_operable` flags (`_fd_operable`, `_lock_fd_operable`,
`_parent_fd_operable`) prevent retry operations on potentially closed and
reused fd numbers.

### Evidence-Path Safety

Bronze payload, manifest, and checkpoint references are portable relative paths
confined to the configured persistence root. Absolute paths, parent traversal,
NUL bytes, unexpected tree entries, and symlink escape are integrity failures.

### Kernel Lock Scope

The kernel lock is advisory. All cooperative writers MUST use this protocol, and
Bronze root contents are collector-writable. The authority_anchor and root
immediate parent are supervisor-controlled and not collector-writable. The
implementation does not claim protection against a privileged local actor that
can bypass advisory locks, replace higher-level mount or parent authorities, or
directly mutate opened directory entries. Such an actor is outside A0's threat
boundary.
