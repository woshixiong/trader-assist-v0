# V0 Fast Launch Program

## Authority

```text
PROGRAM: V0-FAST-LAUNCH
RELEASE_ID: V0-R0
TASK_ID: V0-FLP0-PILOT-AND-LONG-TERM-ROADMAP-AUTHORITY-FREEZE
GOVERNANCE_LEVEL: G2
STATE_BASE_SHA: c507e2fc1bad6aca175cf833e5bcca63224c3e5f
```

This document freezes the first Operator Assist Pilot and the unchanged
long-term Human-Confirmed Automated Execution direction. It is product,
architecture, governance, and project-state authority only. It does not
implement or authorize runtime.

## First release

The first release uses ETH and one strategy, `ETH-LDAR-v0.1`.

```text
EXECUTION_MODE: MANUAL_EXECUTION_WITH_SYSTEM_ASSISTANCE
AUTOMATIC_EXCHANGE_WRITE: PROHIBITED
AI_ROLE: EXPLANATION_AND_CHECKLIST_ONLY
ALL_VALID_SIGNALS_VISIBLE: YES
POST_LAUNCH_LEARNING_LOOP: MANDATORY
```

The system target is real-time public read-only data, DataQualityState,
deterministic signal and risk, a TradePlan, FAST/STANDARD signal card, human
decision capture, manual Hyperliquid execution, read-only order/fill observation,
matching, replay, and versioned findings.

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

R0 is the minimum vertical subset of FL1 through FL3. R1 adds only
human-confirmed automated execution under a separately reviewed G4 gateway.
Autonomous entry remains prohibited.

## Development route

Before first launch there are two main PRs: this FLP0 authority freeze and the
FLP1 end-to-end vertical Operator Assist Pilot. Only `BLOCKER` findings prevent
merge; other validated findings become `FOLLOW_UP`.

## Current false gates

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
```

The machine-readable authority is
`governance/V0_FAST_LAUNCH_PROGRAM.json`. The safe-stop project snapshot is
`governance/PROJECT_STATE.json`.
