# Trader Assist V0

Trader Assist V0 is an isolated ETH/Hyperliquid experiment lane for reliable data observation, deterministic strategy candidates, AI evidence explanation, human authorization, and—only after separate gates—bounded API execution.

## Current stage

`V0-01A6 / OFFLINE_CANDLE_CROSS_SOURCE_RECONCILIATION_CONTRACT — ACTIVE DRAFT`

A0 completed the versioned public-source catalog, exact raw fixture/application-payload authority, local content-addressed immutable Bronze storage, append-only hash-linked manifests, and deterministic offline replay.

A1 froze public candle envelope policy, rate-limit entry-gate behavior, future read-only transport configuration checks, fixture admission rules, and the A1-to-A2 gate. It did not implement live transport.

A2 added a no-network ingress contract/helper for caller-supplied public observation bytes. Every accepted selection must pass A1 public read-only transport-entry checks, exact bytes are bound into `RawEventV0` authority, and optional Bronze persistence uses the existing A0 `BronzeStore` / `ManifestWriter` authority boundaries.

A3 froze a future public read-only transport preflight contract. It validates source identity, environment, operation class, endpoint/operation allowlist, capture-mode match, disabled-runtime default, kill-switch fail-closed semantics, credential absence, account/private absence, and no-write/no-execution proof.

A4 froze the official-only rate-limit authority contract. `RATE_LIMIT_STATUS` remains `UNRESOLVED_OFFICIAL_LIMIT`; no numeric rate-limit values are encoded; live transport remains unauthorized.

A5 is a bounded offline-only extraction slice. It accepts an exact `RawEventV0` plus caller-supplied exact matching candle payload bytes and produces a typed, domain-separated `CandlePayloadExtractionV0`. It does not read `payload_ref`, connect to any endpoint, write Bronze, emit `NormalizedEventV0`, enter Silver, reconcile revisions, or infer candle finality.

A6 is a bounded offline-only reconciliation slice. It embeds independently revalidated exact A5 WebSocket and Info candle extraction authorities, reconstructs their complete union by the A5 candle logical key through one deterministic derivation authority, and emits only `MATCH`, `CONFLICT`, `WS_ONLY`, and `INFO_ONLY` evidence. Its portable JSON Schema validates structure, mandatory serialized A5 authority fields, role/status constraints, and canonical integer difference value kinds; complete hashes, exact A5 authority, membership, ordering, counts, differences, and complete-union proof still require A6 runtime semantic validation. It applies no tolerance or source priority and does not select a canonical winner, order revisions, infer finality, emit `NormalizedEventV0`, or persist Silver data.

`mainnet public read-only` remains only a source identity and environment label. It is not Mainnet execution enablement.

This repository still contains no network client, live endpoint connection, credential, account address, wallet, signing code, nonce handling, exchange-write path, order mutation, Testnet/Mainnet execution enablement, strategy logic, AI recommendation, risk sizing, health runtime, database, dashboard, or soak runner.

## Authority boundary

- `woshixiong/trade-os` remains authoritative for cross-project architecture, governance, evidence-import requirements, and TraderOS production authorities.
- This repository is authoritative only for reviewed and merged V0 runtime source, tests, deployment, and operations.
- Public market-data definitions do not authorize exchange writes.
- Historical V3.5 code remains `SEED`, not authority, and is not copied wholesale.

See `docs/architecture/AUTHORITY_BOUNDARY.md` and the active TraderOS Issue #57.
