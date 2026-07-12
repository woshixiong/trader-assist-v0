# Executor Instructions

## Repository state

```text
PROGRAM: V0-FAST-LAUNCH
TASK_ID: V0-FLP0-PILOT-AND-LONG-TERM-ROADMAP-AUTHORITY-FREEZE
STATE_BASE_SHA: c507e2fc1bad6aca175cf833e5bcca63224c3e5f
LAST_COMPLETED_IMPLEMENTATION: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
LAST_COMPLETED_IMPLEMENTATION_PR: 11
LAST_POLICY_STATE_PR: 12
ACTIVE_IMPLEMENTATION: NONE
ACTIVE_WRITE_LEASE: NONE
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
NEXT_GATE: V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE
```

## Frozen authority

A0 through A6 remain unchanged and authoritative. The Fast Launch freeze is
product, architecture, governance, and machine state only. It creates no
collector, strategy runtime, risk runtime, UI, account observation runtime,
wallet, signing, nonce, or exchange-write capability.

## First release

`V0-R0` is the `V0-FLP1-DECISION-TO-OUTCOME-OPERATOR-ASSIST-PILOT`.

It is bounded to ETH and `ETH-LDAR-v0.1`. The system must expose every valid
FAST and STANDARD signal. FAST and STANDARD are speed classes of one strategy,
not separate strategies. Human execution is manual. AI explains evidence and
checklists only.

## Current bounded task

`NONE`

This branch is a safe-stop governance snapshot awaiting external independent
review. Any repair requires a new exact-head bounded write lease. Do not infer
authorization from this file, a PR body, a previous report, or CI status.

## Next gate

Only a separate project-control scope freeze may authorize
`V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE`. That scope freeze must resolve
applicable public transport and read-only account observation authority before
runtime implementation.

## Forbidden without a new lease

- changes under `src/**`;
- runtime contract or existing schema changes;
- dependency, lockfile, `pyproject.toml`, or CI changes;
- endpoint connections or real market-data acquisition;
- strategy, risk, UI, or account observation runtime;
- credentials, wallets, signing, nonces, exchange writes, orders, or transfers;
- numeric rate-limit authority not sourced and frozen through the official gate;
- Testnet or Mainnet execution enablement;
- Mark Ready, merge, branch deletion, or later-phase implementation;
- modifications to `woshixiong/trade-os`.

## Required lifecycle

Every later bounded task requires current GitHub verification, exact base/head
guards, explicit file allowlist, applicable tests, exact-head CI, external
independent review, and separate finalization authorization. A writer cannot be
the final independent reviewer.
