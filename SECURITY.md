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

Lock correctness does not depend on a removable pathname marker. Legacy segment/global `.lock` names are not created, overwritten, unlinked, cleaned, or used as an exclusivity namespace. Acquisition failure and release close only the descriptor owned by that acquisition. Root-path loss, replacement, type change, descriptor identity mismatch, or kernel release failure places the lock and writer in a terminal compromised state; append and finalize remain disabled. A0 performs no automatic stale-lock recovery.

The kernel lock is advisory. The persistence root and its parent must be writable only by the collector account, and other software must use the same lock protocol. A0 does not claim protection against a privileged actor that can bypass advisory locks, replace higher-level filesystem mount or parent authorities, or directly mutate opened directory entries.

## Source authority

A0 RawEvent authority is bound to the frozen public source catalog, catalog hash, catalog-entry hash, operation, instrument selection, candle interval, endpoint kind, and capture mode. A0 does not parse venue timestamps or native cursors; source event time, publish time, revision time, native ID, and native cursor must remain `None`.

## Reporting

Treat exposed secrets, unauthorized write paths, evidence tampering, path traversal, symlink escape, lock-ownership loss, manifest/checkpoint failure, global observation conflict, dependency compromise, and any future stale or unreconciled execution as security incidents.

Do not include secrets, real account identifiers, private user data, or raw authentication material in issues, pull requests, screenshots, logs, fixtures, or test output.
