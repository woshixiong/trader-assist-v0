# Trader Assist V0

Trader Assist V0 is an isolated ETH/Hyperliquid experiment lane for reliable data observation, deterministic strategy candidates, AI evidence explanation, human authorization, and—only after separate gates—bounded API execution.

## Current authority

```text
PROGRAM: V0-FAST-LAUNCH
STATE_KIND: SAFE_STOP_SNAPSHOT
STATE_BASE_SHA: 95e4a9ebaedb028de68d859627a37dfc142c8602
HISTORICAL_PR15_TASK_ID: V0-FLP1B0B-CAPTURE-NOW-AUTHORITY-AMENDMENT
HISTORICAL_PR15_BASE_SHA: 78d2d37bfe5a4f3f1d382a2a96e57896ae9676ae
HISTORICAL_PR15_HEAD: b7c26c019f64ab627dffc3bde4ab5a35071b6fc5
PR15_MERGE_COMMIT_AND_CURRENT_MAIN: 95e4a9ebaedb028de68d859627a37dfc142c8602
LAST_COMPLETED_IMPLEMENTATION: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
LAST_COMPLETED_IMPLEMENTATION_PR: 11
LAST_POLICY_STATE_PR: 15
ACTIVE_MILESTONE: V0-R0-CAPTURE-ONLY
ACTIVE_TASK_ID: NONE
ACTIVE_WRITE_LEASE: NONE
FIRST_RELEASE_FROZEN: TRUE
LONG_TERM_ROADMAP_FROZEN: TRUE
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
NEXT_GATE: V0-FLP1B0B-FIRST-LAUNCH-CRITICAL-PATH-AND-ETH-MINIMUM-VALIDATION-READONLY-PLANNING
```

A0 completed the versioned public-source catalog, exact raw fixture/application-payload authority, local content-addressed immutable Bronze storage, append-only hash-linked manifests, and deterministic offline replay.

A1 froze public candle envelope policy, rate-limit entry-gate behavior, future read-only transport configuration checks, fixture admission rules, and the A1-to-A2 gate. It did not implement live transport.

A2 added a no-network ingress contract/helper for caller-supplied public observation bytes. Every accepted selection must pass A1 public read-only transport-entry checks, exact bytes are bound into `RawEventV0` authority, and optional Bronze persistence uses the existing A0 `BronzeStore` / `ManifestWriter` authority boundaries.

A3 froze a future public read-only transport preflight contract. It validates source identity, environment, operation class, endpoint/operation allowlist, capture-mode match, disabled-runtime default, kill-switch fail-closed semantics, credential absence, account/private absence, and no-write/no-execution proof.

A4 froze the official-only rate-limit authority contract. `RATE_LIMIT_STATUS` remains `UNRESOLVED_OFFICIAL_LIMIT`; no numeric limit values are encoded; live transport remains unauthorized.

A5 is a bounded offline-only extraction slice. It accepts an exact `RawEventV0` plus caller-supplied exact matching candle payload bytes and produces a typed, domain-separated `CandlePayloadExtractionV0`. It does not read `payload_ref`, connect to any endpoint, write Bronze, emit `NormalizedEventV0`, enter Silver, reconcile revisions, or infer candle finality.

A6 completed the bounded offline-only reconciliation slice and was merged via PR #11. It embeds independently revalidated exact A5 WebSocket and Info candle extraction authorities, reconstructs their complete union by the A5 candle logical key through one deterministic derivation authority, and emits only `MATCH`, `CONFLICT`, `WS_ONLY`, and `INFO_ONLY` evidence. Its portable JSON Schema validates structure, mandatory serialized A5 authority fields, role/status constraints, and canonical integer difference value kinds; complete hashes, exact A5 authority, membership, ordering, counts, differences, and complete-union proof still require A6 runtime semantic validation. It applies no tolerance or source priority and does not select a canonical winner, order revisions, infer finality, emit `NormalizedEventV0`, or persist Silver data.

The Capture Now T1 authority amendment freezes `R0: CAPTURE_ONLY`,
`R1: ETH_OPERATOR_ASSIST`, `T1: CONTRACT_SCHEMA_GOVERNANCE_ONLY`, and
`T2: SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME`. No FLP1 implementation or
runtime authority is enabled by this governance freeze.

`mainnet public read-only` remains only a source identity and environment label. It is not Mainnet execution enablement.

This repository still contains no network client, live endpoint connection, credential, account address, wallet, signing code, nonce handling, exchange-write path, order mutation, Testnet/Mainnet execution enablement, strategy logic, AI recommendation, risk sizing, health runtime, database, dashboard, or soak runner.

## V0-R0 Capture Only

The active first release is Capture-only for ETH. It authorizes Capture
contracts and generated schema, with `active_strategy_count = 0`; network
runtime, strategy runtime, signal recommendation, risk sizing, TradePlan,
FAST/STANDARD presentation, account/order/fill observation, manual execution,
and exchange execution are all false. R0 has no ETH-LDAR, OI/funding strategy,
or registry requirement.

The former ETH Operator Assist Pilot semantics are preserved as future `V0-R1`:
ETH-only, ETH-LDAR or a separately approved future ETH strategy,
`LONG`/`SHORT`/`WAIT`, deterministic risk, TradePlan, FAST/STANDARD signal
cards, human review, manual execution, read-only order/fill observation,
plan/outcome matching, replay, and learning loop. R1 is not implemented or
authorized in T1.

The first release forbids wallets, private keys, signing, nonces, exchange writes, automatic entry/cancel/SL/TP, transfers, withdrawals, multiple active strategies or assets, automatic routing, online learning, and automatic production mutation.

## Long-term direction

```text
FL1 TRUSTED_DATA_RUNTIME
FL2 SIGNAL_AND_RISK_ENGINE
FL3 HUMAN_REVIEW_SURFACE
FL4 HUMAN_CONFIRMED_EXECUTION
```

R0 is Capture-only. R1 may later deliver the Operator Assist subset of FL1
through FL3 after a separate gate; a separately authorized T2 may implement
ETH public Capture runtime only. Human-confirmed automated execution is
deferred under `future_human_confirmed_execution`, unassigned to any release, and
requires a separate G4 implementation, security review, Testnet, shadow,
limited-capital canary, and Mainnet authorization. Autonomous entry remains
prohibited.

See `docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md` for the Capture Now authority
contract, local safety policy, endpoint allowlist, rate-limit immutability, and
RAW_PUBLIC_EVIDENCE_PLANE / CAPTURE_AUTHORITY_PLANE boundary.

## Authority boundary

- `woshixiong/trade-os` remains authoritative for cross-project architecture, governance, evidence-import requirements, and TraderOS production authorities.
- This repository is authoritative only for reviewed and merged V0 runtime source, tests, deployment, and operations.
- Public market-data definitions do not authorize exchange writes.
- Historical V3.5 code remains `SEED`, not authority, and is not copied wholesale.

See `docs/architecture/AUTHORITY_BOUNDARY.md`, `docs/V0_FAST_LAUNCH_PROGRAM.md`, and the active TraderOS Issue #57.
