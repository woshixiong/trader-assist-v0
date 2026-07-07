# Security Policy

## Current ceiling

V0-01A0 is offline and read-only. Public market-data documentation and synthetic fixtures do not authorize live connectivity or exchange writes.

The repository must not contain:

- credentials, account addresses, wallet material, signing code, API-wallet code, or private keys;
- write-capable exchange SDKs or modules;
- order submission, cancellation, modification, transfer, withdrawal, Testnet/Mainnet execution enablement, or live endpoint configuration;
- raw market/account captures, databases, logs, or unredacted operational identifiers.

## Evidence-path safety

Bronze payload, manifest, and checkpoint references are portable relative paths confined to the configured persistence root. Absolute paths, parent traversal, NUL bytes, unexpected tree entries, and symlink escape are integrity failures. Payloads are addressed by exact application-payload SHA-256; canonicalized JSON is not a substitute for raw-byte authority.

A segment is authoritative only after a one-time completion checkpoint binds its UTC date, segment ID, source-catalog version, entry count, and terminal entry hash. Missing, corrupt, truncated, reordered, inserted, deleted, or checkpoint-mismatched evidence fails replay. Replay never retrieves replacement data from a network source.

Observation slots and raw observation IDs are globally unique within one Bronze persistence root. A0 permits only one active `ManifestWriter` for the complete root. The writer holds a kernel-backed exclusive lock on an open descriptor for the Bronze root directory throughout initialization, global manifest scanning, idempotency/conflict decisions, manifest construction and publication, file fsync, parent-directory fsync, finalization, and close.

Lock correctness does not depend on a removable pathname marker. Legacy segment/global `.lock` names are not created, overwritten, unlinked, cleaned, or used as an exclusivity namespace. Acquisition failure and release close only the descriptors owned by that acquisition.

The kernel-backed exclusive lock is held on the **parent directory** of the Bronze persistence root, not the root directory itself. This ensures that authority survives root rename or replacement within the same parent directory. The root directory is opened through the locked parent descriptor, and its inode identity (st_dev, st_ino) is verified at acquisition and at every authority boundary.

Root-path loss, replacement, type change, descriptor identity mismatch, or kernel release failure places the lock and writer in a terminal compromised state; append and finalize remain disabled. A0 performs no automatic stale-lock recovery.

**Fork safety**: OwnedLock records the creating process PID. `os.register_at_fork(after_in_child=...)` marks all locks as FORK_INVALID in the child process. All authority methods (authority_fd, assert_owned, release, append, finalize, close) verify the calling PID and reject non-owner processes. A fork child cannot use or release the parent's authority.

**Descriptor lifecycle**: The lock descriptor is not invalidated before `os.close`. A `_FdState` state machine tracks each descriptor through OPEN_OWNED, UNLOCKING, CLOSING, CLOSED, CLOSE_OUTCOME_UNKNOWN, POISONED, and FORK_INVALID states. When `flock(LOCK_UN)` or `os.close` fails, the state transitions to CLOSE_OUTCOME_UNKNOWN or POISONED, and a process-global poison gate is set to prevent new writers from being created in the same process.

**Writer serialization**: ManifestWriter uses a `threading.RLock` and a `_WriterState` state machine (ACTIVE, FINALIZING, FINALIZED, CLOSING, CLOSED, COMPROMISED, FORK_INVALID) to serialize all public operations. Repeated close is deterministic and safe. Concurrent append, close, and finalize calls are serialized through the lock.

**Provisioning contract**: The Bronze persistence root must be provisioned by the collector account before any writer is created. The parent directory of the root must be writable only by the collector account. The root directory must be a real directory (not a symlink). All cooperative writers must use the same lock protocol. The parent directory must not be renamed or replaced while any writer holds authority.

The kernel lock is advisory. The persistence root and its parent must be writable only by the collector account, and other software must use the same lock protocol. A0 does not claim protection against a privileged actor that can bypass advisory locks, replace higher-level filesystem mount or parent authorities, or directly mutate opened directory entries.

## Source authority

A0 RawEvent authority is bound to the frozen public source catalog, catalog hash, catalog-entry hash, operation, instrument selection, candle interval, endpoint kind, and capture mode. A0 does not parse venue timestamps or native cursors; source event time, publish time, revision time, native ID, and native cursor must remain `None`.

## Reporting

Treat exposed secrets, unauthorized write paths, evidence tampering, path traversal, symlink escape, lock-ownership loss, manifest/checkpoint failure, global observation conflict, dependency compromise, and any future stale or unreconciled execution as security incidents.

Do not include secrets, real account identifiers, private user data, or raw authentication material in issues, pull requests, screenshots, logs, fixtures, or test output.
