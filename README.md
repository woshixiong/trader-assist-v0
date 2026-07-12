# Trader Assist V0

Trader Assist V0 is the bounded ETH/Hyperliquid pilot lane for trusted data,
deterministic strategy signals, deterministic risk sizing, human review, and
manual execution. Exchange write authority is not enabled.

## Current authority

```text
PROGRAM: V0-FAST-LAUNCH
TASK_ID: V0-FLP0-PILOT-AND-LONG-TERM-ROADMAP-AUTHORITY-FREEZE
STATE_BASE_SHA: c507e2fc1bad6aca175cf833e5bcca63224c3e5f
LAST_COMPLETED_IMPLEMENTATION: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
LAST_COMPLETED_IMPLEMENTATION_PR: 11
LAST_POLICY_STATE_PR: 12
ACTIVE_IMPLEMENTATION: NONE
ACTIVE_WRITE_LEASE: NONE
FIRST_RELEASE_FROZEN: TRUE
LONG_TERM_ROADMAP_FROZEN: TRUE
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
NEXT_GATE: V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE
```

## Preserved implementation authority

A0 through A6 remain the last implemented and merged runtime authority. A0
provides offline Bronze evidence and replay. A1 through A4 freeze public source,
transport-entry, preflight, and official rate-limit authorities. A5 provides
offline candle extraction. A6 provides offline cross-source candle
reconciliation. This governance freeze does not modify those contracts, schemas,
tests, or runtime behavior.

## V0-R0 Operator Assist Pilot

The first release is a one-asset, one-strategy pilot:

- primary asset: ETH;
- strategy: `ETH-LDAR-v0.1`;
- signal output: `LONG`, `SHORT`, or `WAIT`;
- signal speed class: `FAST` or `STANDARD`;
- execution: manual Hyperliquid execution after human review;
- AI role: explanation and checklist only;
- system role: data quality, deterministic signal/risk, signal card, records,
  read-only matching, replay, and pilot review.

Every valid FAST and STANDARD signal is visible. FAST is explicitly optional,
short-lived, bounded by a maximum entry boundary, and marked `DO NOT CHASE`.
STANDARD is intended to allow normal human review and order entry.

The first release forbids wallets, private keys, signing, nonces, exchange
writes, automatic entry/cancel/SL/TP, transfers, withdrawals, multi-strategy or
multi-asset routing, online learning, and automatic production mutation.

## Long-term direction

The long-term capability sequence remains:

```text
FL1 TRUSTED_DATA_RUNTIME
FL2 SIGNAL_AND_RISK_ENGINE
FL3 HUMAN_REVIEW_SURFACE
FL4 HUMAN_CONFIRMED_EXECUTION
```

R0 delivers a minimum vertical subset of FL1 through FL3. R1 may add
human-confirmed automated execution only after separate G4 implementation,
security review, Testnet, shadow, limited-capital canary, and Mainnet
authorization. Autonomous entry remains prohibited.

Authoritative details are in:

- `docs/V0_FAST_LAUNCH_PROGRAM.md`;
- `docs/architecture/STRATEGY_AND_DATA_LIFECYCLE.md`;
- `docs/architecture/PILOT_LEARNING_LOOP.md`;
- `governance/V0_FAST_LAUNCH_PROGRAM.json`;
- `governance/PROJECT_STATE.json`.
