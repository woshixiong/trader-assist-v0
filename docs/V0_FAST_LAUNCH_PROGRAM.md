# V0 Fast Launch Program

## Authority

```text
PROGRAM: V0-FAST-LAUNCH
RELEASE_ID: V0-R0
TASK_ID: V0-FLP1B0B-CAPTURE-NOW-AUTHORITY-AMENDMENT
GOVERNANCE_LEVEL: G2
STATE_BASE_SHA: 78d2d37bfe5a4f3f1d382a2a96e57896ae9676ae
```

This document now freezes Capture Now T1. It is contract, schema, governance,
and project-state authority only. It does not implement or authorize runtime.

## Release authority

```text
R0: CAPTURE_ONLY
R1: ETH_OPERATOR_ASSIST
FIRST_LAUNCH_PRIMARY_ASSET: ETH
BTC_FIRST_LAUNCH_REQUIREMENT: NONE
BTC_FIRST_LAUNCH_BLOCKER: NO
T1: CONTRACT_SCHEMA_GOVERNANCE_ONLY
T2: SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME
```

## First release

The active first release is `V0-R0` Capture-only for ETH.

```text
ACTIVE_STRATEGY_COUNT: 0
CAPTURE_CONTRACTS_AUTHORIZED: TRUE
NETWORK_RUNTIME_AUTHORIZED: FALSE
STRATEGY_RUNTIME_AUTHORIZED: FALSE
SIGNAL_RECOMMENDATION_AUTHORIZED: FALSE
RISK_SIZING_AUTHORIZED: FALSE
TRADE_PLAN_AUTHORIZED: FALSE
ACCOUNT_RUNTIME_AUTHORIZED: FALSE
EXCHANGE_EXECUTION_AUTHORIZED: FALSE
```

The system target of real-time public read-only data, DataQualityState,
deterministic signal and risk, a TradePlan, FAST/STANDARD signal card, human
decision capture, manual Hyperliquid execution, read-only order/fill observation,
matching, replay, and versioned findings is preserved as future `V0-R1`
ETH Operator Assist. It remains not implemented and not authorized in T1.

## FAST and STANDARD

FAST and STANDARD are speed classes of the same strategy.

FAST alerts every valid fast signal and displays `FAST / OPTIONAL`, short expiry,
maximum entry boundary, and `DO NOT CHASE`. Non-execution is not automatically a
strategy failure. The pilot measures whether the operator had enough time.

STANDARD alerts every valid standard signal with a longer expiry and enough time
for normal human checks and order entry. An accepted STANDARD signal is expected
to be executed.

The minimum patterns are `LIQUIDITY_SWEEP_RECLAIM_FAST` and
`LIQUIDITY_SWEEP_PULLBACK_STANDARD`.

## Strategy and data lifecycle

Strategies and the platform are independently versioned. Every strategy declares
a `StrategyManifest`. Every normalized data product declares a
`DataProductManifest`. Strategy dependencies are explicit. New data cannot
silently affect an existing strategy. Disabled strategies and data retain
historical decoders, records, and replay capability.

## Pilot learning loop

The mandatory loop is:

```text
Data Snapshot
-> Signal
-> TradePlan
-> Human Decision
-> Actual Order/Fill Observation
-> Outcome
-> Deviation Analysis
-> Finding
-> Versioned Improvement
```

No online learning or automatic production-rule mutation is allowed. Every
improvement proceeds through hypothesis, new version, tests, replay, shadow,
review, and release.

## Capability roadmap

```text
FL1 TRUSTED_DATA_RUNTIME
FL2 SIGNAL_AND_RISK_ENGINE
FL3 HUMAN_REVIEW_SURFACE
FL4 HUMAN_CONFIRMED_EXECUTION
```

R0 is Capture-only. R1 may later deliver ETH Operator Assist after a separate
gate. Human-confirmed automated execution is deferred under
`future_human_confirmed_execution`, has no assigned release, and requires a
separately reviewed G4 gateway. Autonomous entry remains prohibited.

## Development route

T1 is bounded to contract, schema, governance, and docs. T2 is a separate future
ETH public Capture runtime gate. Only `BLOCKER` findings prevent merge; other
validated findings become `FOLLOW_UP`.

## Current false gates

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
CONFLICT_STATE: OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED
SUPERSESSION_STATE: EFFECTIVE_VARIANT_UNDETERMINED
AUTHORITY_HASH: 0e327e566589d8030ff00d4d009eb4b6827679ab508133d66840b2c245dc53df
SOURCE_CATALOG_HASH: 0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7
SOURCE_COUNT: 2
FACT_COUNT: 25
UNKNOWN_COUNT: 14
```

The machine-readable authority is
`governance/V0_FAST_LAUNCH_PROGRAM.json`. The safe-stop project snapshot is
`governance/PROJECT_STATE.json`.
