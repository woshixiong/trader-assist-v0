# V0-01 Scope

## Active slice

`V0-01A0 / BRONZE_AND_OFFLINE_REPLAY`

This bounded slice freezes public source definitions and implements an entirely offline evidence path: exact synthetic application-payload bytes, catalog-bound domain-separated observation identities, immutable content-addressed local storage, root-wide single-writer observation authority, hash-linked manifests, one-time segment completion checkpoints, strict integrity verification, and deterministic replay reports.

## Fixed A0 authority versions

```text
A0_SCHEMA_VERSION: 0.1.0
RAW_IDENTITY_VERSION: trader-assist-v0/raw-observation/v2
OBSERVATION_SLOT_VERSION: trader-assist-v0/raw-observation-slot/v2
MANIFEST_FORMAT_VERSION: 0.1.0
MANIFEST_HASH_CHAIN_VERSION: trader-assist-v0/raw-manifest-entry/v1
MANIFEST_CHECKPOINT_VERSION: 0.1.0
MANIFEST_CHECKPOINT_HASH_VERSION: trader-assist-v0/raw-manifest-checkpoint/v1
REPLAY_REPORT_VERSION: 0.1.0
REPLAY_REPORT_HASH_VERSION: trader-assist-v0/bronze-replay-report/v1
```

A0 supports only these values. Callers cannot override them, and the generated JSON Schemas expose them as `const` authorities.

## Allowed

- ETH and BTC public-source definitions for Hyperliquid mainnet public read-only data;
- synthetic fixtures compatible with documented public response shapes;
- local filesystem Bronze storage and replay using the Python standard library;
- generated schemas and offline tests;
- one kernel-backed root-wide `ManifestWriter` authority per Bronze persistence root;
- explicit segment finalization through an immutable checkpoint.

The root-wide authority is held for the complete writer lifetime. Different segment writers do not coexist in A0. Legacy `.lock` path names are compatibility references only and are not created, removed, or used to establish ownership. A0 has no automatic stale-lock recovery.

## Prohibited

No HTTP or WebSocket client, DNS, live endpoint connection, account address, credential, wallet, signing, exchange write, Testnet/Mainnet execution enablement, strategy, candidate, AI recommendation, risk sizing, health/reconnect/backfill runtime, Silver normalization, database, dashboard, cloud SDK, or soak runner is included.

Raw payloads, manifests, checkpoints, reports, databases, logs, caches, and real operational data are runtime artifacts and must not be committed to Git.

## Authority

TraderOS remains authoritative for cross-project architecture and production governance. Public market-data definitions never authorize exchange writes. The next transport or health slice requires a separate exact-head lease and review.
