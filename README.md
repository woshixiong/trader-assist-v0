# Trader Assist V0

Trader Assist V0 is an isolated ETH/Hyperliquid experiment lane for reliable data observation, deterministic strategy candidates, AI evidence explanation, human authorization, and—only after separate gates—bounded API execution.

## Current stage

`V0-01A1 / SOURCE_ENVELOPE_TRANSPORT_ENTRY_CONTRACT_FREEZE`

A0 completed the versioned public-source catalog, exact raw fixture/application-payload authority, local content-addressed immutable Bronze storage, append-only hash-linked manifests, and deterministic offline replay.

A1 freezes public candle envelope policy, rate-limit entry-gate behavior, future read-only transport configuration checks, fixture admission rules, and the A1-to-A2 gate. It does not implement live transport.

It contains no network client, live endpoint connection, credential, account address, wallet, signing code, exchange-write path, Testnet/Mainnet execution enablement, strategy logic, AI recommendation, risk sizing, health runtime, database, dashboard, or soak runner.

## Authority boundary

- `woshixiong/trade-os` remains authoritative for cross-project architecture, governance, evidence-import requirements, and TraderOS production authorities.
- This repository is authoritative only for reviewed and merged V0 runtime source, tests, deployment, and operations.
- Public market-data definitions do not authorize exchange writes.
- Historical V3.5 code remains `SEED`, not authority, and is not copied wholesale.

See `docs/architecture/AUTHORITY_BOUNDARY.md` and the active TraderOS Issue #57.
