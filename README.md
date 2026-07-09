# Trader Assist V0

Trader Assist V0 is an isolated ETH/Hyperliquid experiment lane for reliable data observation, deterministic strategy candidates, AI evidence explanation, human authorization, and—only after separate gates—bounded API execution.

## Current stage

`V0-01A2 / NO_NETWORK_PUBLIC_OBSERVATION_INGRESS_CONTRACT`

A0 completed the versioned public-source catalog, exact raw fixture/application-payload authority, local content-addressed immutable Bronze storage, append-only hash-linked manifests, and deterministic offline replay.

A1 froze public candle envelope policy, rate-limit entry-gate behavior, future read-only transport configuration checks, fixture admission rules, and the A1-to-A2 gate. It did not implement live transport.

A2 adds a no-network ingress contract/helper for caller-supplied public observation bytes. Every accepted selection must pass A1 public read-only transport-entry checks, exact bytes are bound into `RawEventV0` authority, and optional Bronze persistence uses the existing A0 `BronzeStore` / `ManifestWriter` authority boundaries.

`mainnet public read-only` is a public source identity and environment label only. It is not Mainnet execution enablement.

This repository still contains no network client, live endpoint connection, credential, account address, wallet, signing code, nonce handling, exchange-write path, order mutation, Testnet/Mainnet execution enablement, strategy logic, AI recommendation, risk sizing, health runtime, database, dashboard, or soak runner.

## Authority boundary

- `woshixiong/trade-os` remains authoritative for cross-project architecture, governance, evidence-import requirements, and TraderOS production authorities.
- This repository is authoritative only for reviewed and merged V0 runtime source, tests, deployment, and operations.
- Public market-data definitions do not authorize exchange writes.
- Historical V3.5 code remains `SEED`, not authority, and is not copied wholesale.

See `docs/architecture/AUTHORITY_BOUNDARY.md` and the active TraderOS Issue #57.
