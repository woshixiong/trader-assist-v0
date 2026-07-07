# V0-01 Scope

## Active slice

`V0-01A0 / BRONZE_AND_OFFLINE_REPLAY`

This bounded slice freezes public source definitions and implements an entirely offline evidence path: exact synthetic application-payload bytes, domain-separated observation identities, immutable content-addressed local storage, a single-writer hash-linked manifest, strict integrity verification, and deterministic replay reports.

## Allowed

- ETH and BTC public-source definitions for Hyperliquid mainnet public read-only data;
- synthetic fixtures compatible with documented public response shapes;
- local filesystem Bronze storage and replay using the Python standard library;
- generated schemas and offline tests.

## Prohibited

No HTTP or WebSocket client, DNS, live endpoint connection, account address, credential, wallet, signing, exchange write, Testnet/Mainnet execution enablement, strategy, candidate, AI recommendation, risk sizing, health/reconnect/backfill runtime, database, dashboard, cloud SDK, or soak runner is included.

Raw payloads, manifests, reports, databases, logs, caches, and real operational data are runtime artifacts and must not be committed to Git.

## Authority

TraderOS remains authoritative for cross-project architecture and production governance. Public market-data definitions never authorize exchange writes. The next transport or health slice requires a separate exact-head lease and review.
