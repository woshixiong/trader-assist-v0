# Security Policy

## Current ceiling

V0-01A0 is offline and read-only. Public market-data documentation and synthetic fixtures do not authorize live connectivity or exchange writes.

The repository must not contain:

- credentials, account addresses, wallet material, signing code, API-wallet code, or private keys;
- write-capable exchange SDKs or modules;
- order submission, cancellation, modification, transfer, withdrawal, Testnet/Mainnet execution enablement, or live endpoint configuration;
- raw market/account captures, databases, logs, or unredacted operational identifiers.

## Evidence-path safety

Bronze payload and manifest references must be portable relative paths confined to the configured persistence root. Absolute paths, parent traversal, NUL bytes, and symlink escape are integrity failures. Payloads are addressed by exact application-payload SHA-256; canonicalized JSON is not a substitute for raw-byte authority.

A payload that reaches storage without a manifest entry is retained and reported as an orphan. Missing, corrupt, truncated, reordered, inserted, deleted, or path-escaping evidence fails replay; replay never retrieves replacement data from a network source.

## Reporting

Treat exposed secrets, unauthorized write paths, evidence tampering, path traversal, symlink escape, manifest-chain failure, dependency compromise, and any future stale or unreconciled execution as security incidents.

Do not include secrets, real account identifiers, private user data, or raw authentication material in issues, pull requests, screenshots, logs, fixtures, or test output.
