# Security Policy

## Current ceiling

V0-01A0 is offline and read-only. Public market-data documentation and synthetic fixtures do not authorize live connectivity or exchange writes.

The repository must not contain:

- credentials, account addresses, wallet material, signing code, API-wallet code, or private keys;
- write-capable exchange SDKs or modules;
- order submission, cancellation, modification, transfer, withdrawal, Testnet/Mainnet execution enablement, or live endpoint configuration;
- raw market/account captures, databases, logs, or unredacted operational identifiers.

## Evidence-path safety

Bronze payload, manifest, checkpoint, and lock references are portable relative paths confined to the configured persistence root. Absolute paths, parent traversal, NUL bytes, unexpected tree entries, and symlink escape are integrity failures. Payloads are addressed by exact application-payload SHA-256; canonicalized JSON is not a substitute for raw-byte authority.

A segment is authoritative only after a one-time completion checkpoint binds its UTC date, segment ID, source-catalog version, entry count, and terminal entry hash. Missing, corrupt, truncated, reordered, inserted, deleted, or checkpoint-mismatched evidence fails replay. Replay never retrieves replacement data from a network source.

Observation slots and raw observation IDs are globally unique within one Bronze persistence root. Appends are serialized by a root-level authority lock and fail closed if any manifest is partial, corrupt, duplicated, or conflicting.

Segment and global locks retain an unpredictable owner token, open file descriptor, device, and inode. Release verifies the current path, regular-file type, inode, and token before unlinking. A deleted, replaced, mismatched, or symlinked lock is never silently removed by the old owner. Stale-lock recovery is not automatic in A0.

## Source authority

A0 RawEvent authority is bound to the frozen public source catalog, catalog hash, catalog-entry hash, operation, instrument selection, candle interval, endpoint kind, and capture mode. A0 does not parse venue timestamps or native cursors; source event time, publish time, revision time, native ID, and native cursor must remain `None`.

## Reporting

Treat exposed secrets, unauthorized write paths, evidence tampering, path traversal, symlink escape, lock-ownership loss, manifest/checkpoint failure, global observation conflict, dependency compromise, and any future stale or unreconciled execution as security incidents.

Do not include secrets, real account identifiers, private user data, or raw authentication material in issues, pull requests, screenshots, logs, fixtures, or test output.
